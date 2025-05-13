# metagpt/provider/deepseek.py
from __future__ import annotations

import json
import re
from typing import Optional, Union

from openai import APIConnectionError, AsyncOpenAI, AsyncStream
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from metagpt.configs.llm_config import LLMType
from metagpt.provider.base_llm import BaseLLM
from metagpt.provider.constant import GENERAL_FUNCTION_SCHEMA
from metagpt.provider.llm_provider_registry import register_provider
from metagpt.utils.token_counter import count_input_tokens, count_output_tokens

# DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
# DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

@register_provider([LLMType.DEEPSEEK])
class DeepSeekLLM(BaseLLM):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.model = self.config.model
        self.aclient = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
        
    def _build_request_params(self, messages: list[dict], **kwargs) -> dict:
        return {
            "messages": messages,
            "model": self.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs
        }

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type(APIConnectionError)
    )
    async def acompletion(self, messages: list[dict], **kwargs) -> ChatCompletion:
        params = self._build_request_params(messages, **kwargs)
        response = await self.aclient.chat.completions.create(**params)
        self._update_costs(response.usage)
        return response

    async def acompletion_text(self, messages: list[dict], **kwargs) -> str:
        response = await self.acompletion(messages, **kwargs)
        return response.choices[0].message.content

    def _calc_usage(self, messages: list[dict], response: str) -> CompletionUsage:
        return CompletionUsage(
            prompt_tokens=count_input_tokens(messages, self.model),
            completion_tokens=count_output_tokens(response, self.model),
            total_tokens=0
        )

    def _update_costs(self, usage: CompletionUsage):
        if self.config.cost_manager:
            self.config.cost_manager.update_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                self.model
            )