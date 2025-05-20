#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_php_tests.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePHPTests(Action):
    """Action for generating PHP-specific tests."""

    name: str = "WritePHPTests"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the PHP test generation action.
        
        Args:
            test_type: Type of tests to generate (all, unit, feature, integration)
            source_files: List of source files to test
            
        Returns:
            Message: A message containing the generated PHP tests.
        """
        test_type = kwargs.get("test_type", "all")
        source_files = kwargs.get("source_files", [])
        
        # Generate tests using LLM
        prompt = f"""Generate PHP tests based on the following requirements:
        
        Test Type: {test_type}
        Source Files: {', '.join(source_files)}
        
        Follow these guidelines:
        1. Use PHPUnit for testing
        2. Follow PSR-12 coding standards
        3. Write descriptive test names
        4. Use proper assertions
        5. Mock external dependencies
        6. Test edge cases
        7. Follow AAA pattern (Arrange, Act, Assert)
        
        Generate the following test files:
        1. Unit tests for services and repositories
        2. Feature tests for controllers
        3. Integration tests for API endpoints
        4. Test cases for edge cases and error handling
        
        For each file, use this format:
        ```php:tests/Unit/Services/UserServiceTest.php
        // Test file content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated tests
        test_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(test_blocks, dict):
            logger.error("Failed to parse generated test blocks")
            return Message(content="Failed to generate PHP tests. Please check the LLM response format.")
        
        # Validate test structure
        required_test_files = self._get_required_test_files(test_type, source_files)
        missing_files = [f for f in required_test_files if f not in test_blocks]
        
        if missing_files:
            logger.warning(f"Missing required test files: {', '.join(missing_files)}")
            
            # Generate additional test files if needed
            additional_prompt = f"""Generate the following missing PHP test files:
            {', '.join(missing_files)}
            
            Follow the same testing approach as before.
            """
            
            additional_rsp = await self._aask(additional_prompt)
            additional_blocks = CodeParser.parse_code(block="", text=additional_rsp)
            
            if isinstance(additional_blocks, dict):
                test_blocks.update(additional_blocks)
        
        # Validate test quality
        validation_errors = self._validate_test_quality(test_blocks)
        if validation_errors:
            logger.warning(f"Test quality issues: {', '.join(validation_errors)}")
        
        # Return generated tests
        return Message(
            content=str(test_blocks),
            role="PHP Developer",
            cause_by=self.name
        )

    def _get_required_test_files(self, test_type: str, source_files: List[str]) -> List[str]:
        """Get the list of required test files based on test type and source files.
        
        Args:
            test_type: Type of tests to generate (all, unit, feature, integration)
            source_files: List of source files to test
            
        Returns:
            List of required test file paths
        """
        required_files = []
        
        if test_type in ["all", "unit"]:
            # Add unit tests
            for source_file in source_files:
                if source_file.endswith(".php") and ("Service" in source_file or "Repository" in source_file):
                    test_file = source_file.replace("src/", "tests/Unit/").replace(".php", "Test.php")
                    required_files.append(test_file)
        
        if test_type in ["all", "feature"]:
            # Add feature tests
            for source_file in source_files:
                if source_file.endswith(".php") and "Controller" in source_file:
                    test_file = source_file.replace("src/", "tests/Feature/").replace(".php", "Test.php")
                    required_files.append(test_file)
        
        if test_type in ["all", "integration"]:
            # Add integration tests
            required_files.append("tests/Integration/ApiTest.php")
        
        return required_files

    def _validate_test_quality(self, test_blocks: Dict[str, str]) -> List[str]:
        """Validate the quality of generated PHP tests.
        
        Args:
            test_blocks: Dictionary of test file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        for file_path, content in test_blocks.items():
            if "Test.php" in file_path:
                if "unit" in file_path.lower():
                    errors.extend(self._validate_unit_test(content))
                elif "feature" in file_path.lower():
                    errors.extend(self._validate_feature_test(content))
                elif "integration" in file_path.lower():
                    errors.extend(self._validate_integration_test(content))
        
        return errors

    def _validate_unit_test(self, content: str) -> List[str]:
        """Validate the structure of PHP unit tests.
        
        Args:
            content: Unit test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper test class structure
        if "extends TestCase" not in content:
            errors.append("Test class must extend TestCase")
        
        # Check for test methods
        if "public function test" not in content:
            errors.append("Missing test methods")
        
        # Check for assertions
        if "assert" not in content:
            errors.append("Missing assertions")
        
        # Check for test setup
        if "setUp" not in content:
            errors.append("Missing setUp method")
        
        return errors

    def _validate_feature_test(self, content: str) -> List[str]:
        """Validate the structure of PHP feature tests.
        
        Args:
            content: Feature test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper test class structure
        if "extends TestCase" not in content:
            errors.append("Test class must extend TestCase")
        
        # Check for test methods
        if "public function test" not in content:
            errors.append("Missing test methods")
        
        # Check for HTTP assertions
        if "assertStatus" not in content and "assertJson" not in content:
            errors.append("Missing HTTP assertions")
        
        # Check for test setup
        if "setUp" not in content:
            errors.append("Missing setUp method")
        
        return errors

    def _validate_integration_test(self, content: str) -> List[str]:
        """Validate the structure of PHP integration tests.
        
        Args:
            content: Integration test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper test class structure
        if "extends TestCase" not in content:
            errors.append("Test class must extend TestCase")
        
        # Check for test methods
        if "public function test" not in content:
            errors.append("Missing test methods")
        
        # Check for API assertions
        if "assertStatus" not in content and "assertJson" not in content:
            errors.append("Missing API assertions")
        
        # Check for database assertions
        if "assertDatabaseHas" not in content and "assertDatabaseMissing" not in content:
            errors.append("Missing database assertions")
        
        return errors 