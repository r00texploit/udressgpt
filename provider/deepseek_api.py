# metagpt/provider/deepseek.py
from __future__ import annotations

import json
import re
import asyncio
from typing import Optional, Union

from openai import APIConnectionError, AsyncOpenAI, AsyncStream, APIError, RateLimitError, APITimeoutError
from openai._base_client import AsyncHttpxClientWrapper
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
    wait_exponential,
    retry_if_exception,
)

from metagpt.configs.llm_config import LLMConfig, LLMType
from metagpt.const import USE_CONFIG_TIMEOUT
from metagpt.logs import log_llm_stream, logger
from metagpt.provider.base_llm import BaseLLM
from metagpt.provider.constant import GENERAL_FUNCTION_SCHEMA
from metagpt.provider.llm_provider_registry import register_provider
from metagpt.utils.common import CodeParser, log_and_reraise
from metagpt.utils.token_counter import count_message_tokens, count_string_tokens
from metagpt.utils.cost_manager import CostManager


def is_connection_error(exception):
    """Check if the exception is a connection-related error"""
    return isinstance(exception, (APIConnectionError, APITimeoutError, asyncio.TimeoutError))


@register_provider([LLMType.DEEPSEEK])
class DeepSeekLLM(BaseLLM):
    """DeepSeek API implementation using OpenAI-compatible interface"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._init_client()
        self.auto_max_tokens = False
        self.cost_manager: Optional[CostManager] = None
        self.max_retries = 5  # Increased from 3 to 5
        self.retry_delay = 1  # Initial delay in seconds
        self.max_retry_delay = 30  # Maximum delay in seconds

    def _init_client(self):
        """Initialize the DeepSeek client"""
        self.model = self.config.model
        self.pricing_plan = self.config.pricing_plan or self.model
        kwargs = self._make_client_kwargs()
        self.aclient = AsyncOpenAI(**kwargs)

    def _make_client_kwargs(self) -> dict:
        kwargs = {
            "api_key": self.config.api_key,
            "base_url": self.config.base_url or "https://api.deepseek.com/v1",
            "timeout": self.get_timeout(self.config.timeout or 60),  # Default timeout of 60 seconds
            "max_retries": self.max_retries,
        }

        # Add proxy support if configured
        if proxy_params := self._get_proxy_params():
            kwargs["http_client"] = AsyncHttpxClientWrapper(**proxy_params)

        return kwargs

    def _get_proxy_params(self) -> dict:
        params = {}
        if self.config.proxy:
            params = {"proxies": self.config.proxy}
        if self.config.base_url:
            params["base_url"] = self.config.base_url
        return params

    def _cons_kwargs(self, messages: list[dict], timeout=USE_CONFIG_TIMEOUT, **extra_kwargs) -> dict:
        kwargs = {
            "messages": messages,
            "temperature": self.config.temperature,
            "model": self.model,
            "timeout": self.get_timeout(timeout),
        }
        if extra_kwargs:
            kwargs.update(extra_kwargs)
        return kwargs

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        after=after_log(logger, logger.level("WARNING").name),
        retry=retry_if_exception(is_connection_error),
        retry_error_callback=log_and_reraise,
    )
    async def _achat_completion(self, messages: list[dict], timeout=USE_CONFIG_TIMEOUT) -> ChatCompletion:
        """Implementation of chat completion for DeepSeek"""
        try:
            kwargs = self._cons_kwargs(messages, timeout=self.get_timeout(timeout))
            response = await self.aclient.chat.completions.create(**kwargs)
            self._update_costs(response.usage)
            return response
        except Exception as e:
            logger.error(f"DeepSeek API error in _achat_completion: {str(e)}")
            if is_connection_error(e):
                logger.warning("Connection error detected, will retry...")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        after=after_log(logger, logger.level("WARNING").name),
        retry=retry_if_exception(is_connection_error),
        retry_error_callback=log_and_reraise,
    )
    async def _achat_completion_stream(self, messages: list[dict], timeout: int = USE_CONFIG_TIMEOUT) -> str:
        """Implementation of streaming chat completion for DeepSeek"""
        try:
            kwargs = self._cons_kwargs(messages, timeout=self.get_timeout(timeout), stream=True)
            response = await self.aclient.chat.completions.create(**kwargs)
            
            usage = None
            collected_messages = []
            async for chunk in response:
                chunk_message = chunk.choices[0].delta.content or "" if chunk.choices else ""
                finish_reason = chunk.choices[0].finish_reason if chunk.choices and hasattr(chunk.choices[0], "finish_reason") else None
                log_llm_stream(chunk_message)
                collected_messages.append(chunk_message)
                if finish_reason:
                    if hasattr(chunk, "usage"):
                        usage = CompletionUsage(**chunk.usage)
                    elif hasattr(chunk.choices[0], "usage"):
                        usage = CompletionUsage(**chunk.choices[0].usage)

            log_llm_stream("\n")
            full_reply_content = "".join(collected_messages)
            if not usage:
                usage = self._calc_usage(messages, full_reply_content)

            self._update_costs(usage)
            return full_reply_content
        except Exception as e:
            logger.error(f"DeepSeek API error in _achat_completion_stream: {str(e)}")
            if is_connection_error(e):
                logger.warning("Connection error detected, will retry...")
            raise

    async def acompletion(self, messages: list[dict], timeout=USE_CONFIG_TIMEOUT) -> ChatCompletion:
        return await self._achat_completion(messages, timeout=self.get_timeout(timeout))

    async def acompletion_text(self, messages: list[dict], stream=False, timeout=USE_CONFIG_TIMEOUT) -> str:
        """Get completion text, optionally streaming the response"""
        try:
            if stream:
                return await self._achat_completion_stream(messages, timeout=timeout)
            response = await self._achat_completion(messages, timeout=self.get_timeout(timeout))
            return self.get_choice_text(response)
        except Exception as e:
            logger.error(f"DeepSeek API error in acompletion_text: {str(e)}")
            raise

    async def _achat_completion_function(self, messages: list[dict], timeout: int = USE_CONFIG_TIMEOUT, **chat_configs) -> ChatCompletion:
        """Implementation of function calling for DeepSeek"""
        try:
            messages = self.format_msg(messages)
            kwargs = self._cons_kwargs(messages=messages, timeout=self.get_timeout(timeout), **chat_configs)
            response = await self.aclient.chat.completions.create(**kwargs)
            self._update_costs(response.usage)
            return response
        except Exception as e:
            logger.error(f"DeepSeek API error in _achat_completion_function: {str(e)}")
            raise

    async def aask_code(self, messages: list[dict], timeout: int = USE_CONFIG_TIMEOUT, **kwargs) -> dict:
        """Use function calling to get code responses"""
        try:
            if "tools" not in kwargs:
                configs = {"tools": [{"type": "function", "function": GENERAL_FUNCTION_SCHEMA}]}
                kwargs.update(configs)
            response = await self._achat_completion_function(messages, **kwargs)
            return self.get_choice_function_arguments(response)
        except Exception as e:
            logger.error(f"DeepSeek API error in aask_code: {str(e)}")
            raise

    def get_choice_text(self, response: ChatCompletion) -> str:
        """Get the text content from the response"""
        return response.choices[0].message.content if response.choices else ""

    def get_choice_function_arguments(self, response: ChatCompletion) -> dict:
        """Get function call arguments from the response"""
        try:
            message = response.choices[0].message
            if (
                message.tool_calls is not None
                and message.tool_calls[0].function is not None
                and message.tool_calls[0].function.arguments is not None
            ):
                try:
                    return json.loads(message.tool_calls[0].function.arguments, strict=False)
                except json.decoder.JSONDecodeError as e:
                    error_msg = f"Got JSONDecodeError for \n{'--'*40} \n{message.tool_calls[0].function.arguments}, {str(e)}"
                    logger.error(error_msg)
                    return self._parse_arguments(message.tool_calls[0].function.arguments)
            elif message.tool_calls is None and message.content is not None:
                code_formats = "```"
                if message.content.startswith(code_formats) and message.content.endswith(code_formats):
                    code = CodeParser.parse_code(None, message.content)
                    return {"language": "python", "code": code}
                return {"language": "markdown", "code": self.get_choice_text(response)}
            else:
                logger.error(f"Failed to parse \n {response}\n")
                raise Exception(f"Failed to parse \n {response}\n")
        except Exception as e:
            logger.error(f"Error in get_choice_function_arguments: {str(e)}")
            raise

    def _parse_arguments(self, arguments: str) -> dict:
        """Parse arguments in function call"""
        try:
            if "language" not in arguments and "code" not in arguments:
                logger.warning(f"Not found `code`, `language`, We assume it is pure code:\n {arguments}\n. ")
                return {"language": "python", "code": arguments}

            language_pattern = re.compile(r'[\"\']?language[\"\']?\s*:\s*["\']([^"\']+?)["\']', re.DOTALL)
            language_match = language_pattern.search(arguments)
            language_value = language_match.group(1) if language_match else "python"

            code_pattern = r'(["\'`]{3}|["\'`])([\s\S]*?)\1'
            try:
                code_value = re.findall(code_pattern, arguments)[-1][-1]
            except Exception as e:
                logger.error(f"{e}, when re.findall({code_pattern}, {arguments})")
                code_value = None

            if code_value is None:
                raise ValueError(f"Parse code error for {arguments}")
            return {"language": language_value, "code": code_value}
        except Exception as e:
            logger.error(f"Error in _parse_arguments: {str(e)}")
            raise

    def _calc_usage(self, messages: list[dict], response: str) -> CompletionUsage:
        """Calculate token usage"""
        try:
            prompt_tokens = count_message_tokens(messages, self.model)
            completion_tokens = count_string_tokens(response, self.model)
            return CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        except Exception as e:
            logger.error(f"Error in _calc_usage: {str(e)}")
            raise

    def _get_max_tokens(self, messages: list[dict]):
        """Get max tokens for completion"""
        if not self.auto_max_tokens:
            return self.config.max_token
        return min(self.config.max_token, 4096)  # DeepSeek models typically have a 4096 token limit

    def _update_costs(self, usage: CompletionUsage):
        """Update cost tracking"""
        try:
            if self.config.cost_manager:
                self.config.cost_manager.update_cost(
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    self.model
                )
        except Exception as e:
            logger.error(f"Error in _update_costs: {str(e)}")
            raise 