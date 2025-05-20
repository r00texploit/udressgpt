#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_python_code.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePythonCode(Action):
    """Action for generating Python-specific code with best practices."""

    name: str = "WritePythonCode"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the Python code generation action.
        
        Returns:
            Message: A message containing the generated Python code.
        """
        # Get project requirements from context
        requirements = self.context.get("requirements", "")
        python_version = self.context.get("python_version", "3.9")
        code_style = self.context.get("code_style", "pep8")
        use_type_hints = self.context.get("use_type_hints", True)
        use_docstrings = self.context.get("use_docstrings", True)
        use_async = self.context.get("use_async", True)
        use_modern_features = self.context.get("use_modern_features", True)
        
        # Generate code using LLM
        prompt = f"""Generate Python code based on the following requirements:
        
        Requirements:
        {requirements}
        
        Python Version: {python_version}
        Code Style: {code_style}
        Type Hints: {'enabled' if use_type_hints else 'disabled'}
        Docstrings: {'enabled' if use_docstrings else 'disabled'}
        Async: {'enabled' if use_async else 'disabled'}
        Modern Features: {'enabled' if use_modern_features else 'disabled'}
        
        Follow these guidelines:
        1. Follow PEP 8 style guide
        2. Use type hints where appropriate
        3. Add comprehensive docstrings
        4. Implement proper error handling
        5. Use modern Python features
        6. Follow SOLID principles
        7. Write testable code
        
        Generate the following files:
        1. Main application file
        2. Core modules and utilities
        3. Feature-specific modules
        4. Service layer implementation
        5. Repository layer implementation
        6. Error handling implementation
        
        For each file, use this format:
        ```python:src/app/main.py
        # File content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated code
        code_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(code_blocks, dict):
            logger.error("Failed to parse generated code blocks")
            return Message(content="Failed to generate Python code. Please check the LLM response format.")
        
        # Validate code structure
        required_files = [
            "src/app/main.py",
            "src/app/core/error_handler.py",
            "src/app/core/config.py",
            "src/app/core/logger.py",
        ]
        
        missing_files = [f for f in required_files if f not in code_blocks]
        if missing_files:
            logger.warning(f"Missing required files: {', '.join(missing_files)}")
        
        # Generate additional files if needed
        if missing_files:
            additional_prompt = f"""Generate the following missing Python files:
            {', '.join(missing_files)}
            
            Follow the same coding standards and patterns as before.
            """
            
            additional_rsp = await self._aask(additional_prompt)
            additional_blocks = CodeParser.parse_code(block="", text=additional_rsp)
            
            if isinstance(additional_blocks, dict):
                code_blocks.update(additional_blocks)
        
        # Return generated code
        return Message(
            content=str(code_blocks),
            role="Python Developer",
            cause_by=self.name
        )

    def _validate_code_structure(self, code_blocks: Dict[str, str]) -> List[str]:
        """Validate the structure of generated Python code.
        
        Args:
            code_blocks: Dictionary of file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for main application file
        if "src/app/main.py" not in code_blocks:
            errors.append("Missing main.py file")
        
        # Check for core structure
        core_files = [
            "src/app/core/error_handler.py",
            "src/app/core/config.py",
            "src/app/core/logger.py",
        ]
        
        for file in core_files:
            if file not in code_blocks:
                errors.append(f"Missing core file: {file}")
        
        # Check for feature structure
        feature_dirs = [d for d in code_blocks.keys() if "src/app/features/" in d]
        if not feature_dirs:
            errors.append("Missing feature implementations")
        
        return errors

    def _validate_module_structure(self, code: str) -> List[str]:
        """Validate the structure of Python modules.
        
        Args:
            code: Module code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for imports
        if "import " not in code and "from " not in code:
            errors.append("Missing imports")
        
        # Check for docstrings if enabled
        if self.context.get("use_docstrings", True) and '"""' not in code and "'''" not in code:
            errors.append("Missing module docstring")
        
        # Check for type hints if enabled
        if self.context.get("use_type_hints", True) and "->" not in code and ": " not in code:
            errors.append("Missing type hints")
        
        # Check for error handling
        if "try:" not in code and "except" not in code:
            errors.append("Missing error handling")
        
        return errors 