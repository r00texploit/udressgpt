#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_php_code.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePHPCode(Action):
    """Action for generating PHP-specific code with best practices."""

    name: str = "WritePHPCode"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the PHP code generation action.
        
        Returns:
            Message: A message containing the generated PHP code.
        """
        # Get project requirements from context
        requirements = self.context.get("requirements", "")
        framework = self.context.get("framework", "laravel")
        php_version = self.context.get("php_version", "8.2")
        
        # Generate code using LLM
        prompt = f"""Generate PHP code based on the following requirements:
        
        Requirements:
        {requirements}
        
        Framework: {framework}
        PHP Version: {php_version}
        
        Follow these guidelines:
        1. Use PSR-12 coding standards
        2. Follow framework best practices
        3. Implement proper error handling
        4. Add PHPDoc comments
        5. Use type hints
        6. Implement proper dependency injection
        7. Follow SOLID principles
        
        Generate the following files:
        1. Main application file
        2. Core classes and interfaces
        3. Feature-specific controllers and models
        4. Service layer implementation
        5. Repository layer implementation
        6. Error handling implementation
        
        For each file, use this format:
        ```php:src/App/Http/Controllers/HomeController.php
        // File content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated code
        code_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(code_blocks, dict):
            logger.error("Failed to parse generated code blocks")
            return Message(content="Failed to generate PHP code. Please check the LLM response format.")
        
        # Validate code structure
        required_files = [
            "src/App/Http/Controllers/HomeController.php",
            "src/App/Exceptions/Handler.php",
            "src/App/Services/BaseService.php",
            "src/App/Repositories/BaseRepository.php",
        ]
        
        missing_files = [f for f in required_files if f not in code_blocks]
        if missing_files:
            logger.warning(f"Missing required files: {', '.join(missing_files)}")
        
        # Generate additional files if needed
        if missing_files:
            additional_prompt = f"""Generate the following missing PHP files:
            {', '.join(missing_files)}
            
            Follow the same framework and coding standards as before.
            """
            
            additional_rsp = await self._aask(additional_prompt)
            additional_blocks = CodeParser.parse_code(block="", text=additional_rsp)
            
            if isinstance(additional_blocks, dict):
                code_blocks.update(additional_blocks)
        
        # Return generated code
        return Message(
            content=str(code_blocks),
            role="PHP Developer",
            cause_by=self.name
        )

    def _validate_code_structure(self, code_blocks: Dict[str, str]) -> List[str]:
        """Validate the structure of generated PHP code.
        
        Args:
            code_blocks: Dictionary of file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for main controller
        if "src/App/Http/Controllers/HomeController.php" not in code_blocks:
            errors.append("Missing HomeController.php file")
        
        # Check for core structure
        core_files = [
            "src/App/Exceptions/Handler.php",
            "src/App/Services/BaseService.php",
            "src/App/Repositories/BaseRepository.php",
        ]
        
        for file in core_files:
            if file not in code_blocks:
                errors.append(f"Missing core file: {file}")
        
        # Check for feature structure
        feature_dirs = [d for d in code_blocks.keys() if "src/App/Http/Controllers/" in d]
        if not feature_dirs:
            errors.append("Missing feature implementations")
        
        return errors

    def _validate_class_structure(self, code: str) -> List[str]:
        """Validate the structure of PHP classes.
        
        Args:
            code: Class code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper class structure
        if "class " not in code:
            errors.append("Missing class declaration")
        
        # Check for namespace
        if "namespace " not in code:
            errors.append("Missing namespace declaration")
        
        # Check for use statements
        if "use " not in code:
            errors.append("Missing use statements")
        
        # Check for proper constructor
        if "__construct" not in code:
            errors.append("Missing constructor")
        
        return errors 