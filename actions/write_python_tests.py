#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_python_tests.py
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePythonTests(Action):
    """Action for generating Python-specific tests with best practices."""

    name: str = "WritePythonTests"
    context: Dict[str, Any] = {}

    async def run(self, test_type: str = "all", source_files: Optional[List[str]] = None) -> Message:
        """Run the Python test generation action.
        
        Args:
            test_type: Type of tests to generate (unit, integration, e2e, all)
            source_files: List of source files to test
            
        Returns:
            Message: A message containing the generated Python tests.
        """
        # Get project requirements from context
        requirements = self.context.get("requirements", "")
        python_version = self.context.get("python_version", "3.9")
        test_coverage = self.context.get("test_coverage", 80)
        use_pytest = self.context.get("use_pytest", True)
        use_mock = self.context.get("use_mock", True)
        
        # Generate tests using LLM
        prompt = f"""Generate Python tests based on the following requirements:
        
        Requirements:
        {requirements}
        
        Python Version: {python_version}
        Test Framework: {'pytest' if use_pytest else 'unittest'}
        Test Coverage Target: {test_coverage}%
        Use Mocking: {'enabled' if use_mock else 'disabled'}
        Test Type: {test_type}
        Source Files: {', '.join(source_files) if source_files else 'all'}
        
        Follow these guidelines:
        1. Follow pytest best practices
        2. Use fixtures where appropriate
        3. Implement proper test isolation
        4. Use mocking for external dependencies
        5. Write descriptive test names
        6. Include edge cases and error scenarios
        7. Follow AAA pattern (Arrange, Act, Assert)
        
        Generate the following test files:
        1. Unit tests for core modules
        2. Integration tests for services
        3. End-to-end tests for features
        4. Test fixtures and utilities
        
        For each file, use this format:
        ```python:tests/unit/test_core.py
        # Test file content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated tests
        test_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(test_blocks, dict):
            logger.error("Failed to parse generated test blocks")
            return Message(content="Failed to generate Python tests. Please check the LLM response format.")
        
        # Validate test structure
        required_files = [
            "tests/unit/test_core.py",
            "tests/integration/test_services.py",
            "tests/e2e/test_features.py",
            "tests/conftest.py",
        ]
        
        missing_files = [f for f in required_files if f not in test_blocks]
        if missing_files:
            logger.warning(f"Missing required test files: {', '.join(missing_files)}")
        
        # Generate additional test files if needed
        if missing_files:
            additional_prompt = f"""Generate the following missing test files:
            {', '.join(missing_files)}
            
            Follow the same testing standards and patterns as before.
            """
            
            additional_rsp = await self._aask(additional_prompt)
            additional_blocks = CodeParser.parse_code(block="", text=additional_rsp)
            
            if isinstance(additional_blocks, dict):
                test_blocks.update(additional_blocks)
        
        # Validate test quality
        validation_errors = self._validate_test_quality(test_blocks)
        if validation_errors:
            logger.warning(f"Test quality issues found: {', '.join(validation_errors)}")
        
        # Return generated tests
        return Message(
            content=str(test_blocks),
            role="Python Developer",
            cause_by=self.name
        )

    def _validate_test_quality(self, test_blocks: Dict[str, str]) -> List[str]:
        """Validate the quality of generated Python tests.
        
        Args:
            test_blocks: Dictionary of test file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        for file_path, content in test_blocks.items():
            # Check for test imports
            if "import pytest" not in content and "import unittest" not in content:
                errors.append(f"Missing test framework import in {file_path}")
            
            # Check for test classes/functions
            if "def test_" not in content and "class Test" not in content:
                errors.append(f"Missing test functions/classes in {file_path}")
            
            # Check for assertions
            if "assert " not in content:
                errors.append(f"Missing assertions in {file_path}")
            
            # Check for fixtures if using pytest
            if "conftest.py" in file_path and "@pytest.fixture" not in content:
                errors.append("Missing pytest fixtures in conftest.py")
            
            # Check for mocking if enabled
            if self.context.get("use_mock", True) and "mock" not in content.lower():
                errors.append(f"Missing mocking in {file_path}")
        
        return errors

    def _validate_test_coverage(self, test_blocks: Dict[str, str], source_files: List[str]) -> List[str]:
        """Validate test coverage against source files.
        
        Args:
            test_blocks: Dictionary of test file paths and their contents
            source_files: List of source files to test
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Map source files to expected test files
        source_to_test = {
            "src/app/core/": "tests/unit/test_core.py",
            "src/app/services/": "tests/integration/test_services.py",
            "src/app/features/": "tests/e2e/test_features.py",
        }
        
        for source_file in source_files:
            # Find matching test file
            test_file = None
            for prefix, test_path in source_to_test.items():
                if source_file.startswith(prefix):
                    test_file = test_path
                    break
            
            if test_file and test_file not in test_blocks:
                errors.append(f"Missing test file for {source_file}")
        
        return errors 