#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_flutter_tests.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message, Document
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WriteFlutterTests(Action):
    """Action for generating Flutter tests."""

    name: str = "WriteFlutterTests"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the Flutter test generation action.
        
        Returns:
            Message: A message containing the generated Flutter tests.
        """
        # Get context information
        filename = self.i_context.filename if hasattr(self.i_context, 'filename') else None
        content = self.i_context.content if hasattr(self.i_context, 'content') else None
        dependencies = self.i_context.dependencies if hasattr(self.i_context, 'dependencies') else []
        
        # Generate test code using LLM
        prompt = f"""Generate Flutter tests for the following file:
        
        File: {filename}
        Content: {content}
        Dependencies: {dependencies}
        
        Follow these guidelines:
        1. Write unit tests for business logic
        2. Write widget tests for UI components
        3. Write integration tests for feature flows
        4. Use proper test organization
        5. Include test documentation
        6. Follow Flutter testing best practices
        7. Ensure good test coverage
        
        Generate the tests for this specific file. Use this format:
        ```dart:{filename}_test.dart
        // Test file content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated code
        code_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(code_blocks, dict):
            logger.error("Failed to parse generated test code blocks")
            return Message(content="Failed to generate Flutter tests. Please check the LLM response format.")
        
        # Create test context
        test_context = {
            "filename": f"{filename}_test.dart",
            "test_doc": Document(content=code_blocks.get(f"{filename}_test.dart", "")),
            "dependencies": dependencies
        }
        
        # Return generated tests
        return Message(
            content=str(test_context),
            role="Flutter Developer",
            cause_by=self.name
        )

    def _get_required_test_files(self, test_type: str, source_files: List[str]) -> List[str]:
        """Get the list of required test files based on test type and source files.
        
        Args:
            test_type: Type of tests to generate (all, widget, unit, integration)
            source_files: List of source files to test
            
        Returns:
            List of required test file paths
        """
        required_files = []
        
        if test_type in ["all", "widget"]:
            # Add widget tests
            for source_file in source_files:
                if source_file.endswith(".dart") and "widget" in source_file.lower():
                    test_file = source_file.replace("lib/", "test/").replace(".dart", "_test.dart")
                    required_files.append(test_file)
        
        if test_type in ["all", "unit"]:
            # Add unit tests
            for source_file in source_files:
                if source_file.endswith(".dart") and "widget" not in source_file.lower():
                    test_file = source_file.replace("lib/", "test/").replace(".dart", "_test.dart")
                    required_files.append(test_file)
        
        if test_type in ["all", "integration"]:
            # Add integration tests
            required_files.append("integration_test/app_test.dart")
        
        return required_files

    def _validate_test_quality(self, test_blocks: Dict[str, str]) -> List[str]:
        """Validate the quality of generated Flutter tests.
        
        Args:
            test_blocks: Dictionary of test file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        for file_path, content in test_blocks.items():
            # Check for proper test imports
            if "import 'package:flutter_test/flutter_test.dart';" not in content:
                errors.append(f"Missing Flutter test import in {file_path}")
            
            # Check for test group
            if "group(" not in content:
                errors.append(f"Missing test group in {file_path}")
            
            # Check for test cases
            if "test(" not in content:
                errors.append(f"Missing test cases in {file_path}")
            
            # Check for proper test naming
            if "testWidgets(" in content and "test(" in content:
                errors.append(f"Mixing widget and unit tests in {file_path}")
            
            # Check for proper test documentation
            if "///" not in content and "//" not in content:
                errors.append(f"Missing test documentation in {file_path}")
        
        return errors

    def _validate_widget_test(self, content: str) -> List[str]:
        """Validate the structure of Flutter widget tests.
        
        Args:
            content: Widget test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper widget test structure
        if "testWidgets(" not in content:
            errors.append("Missing testWidgets function")
        
        # Check for widget testing utilities
        if "pumpWidget(" not in content and "pump(" not in content:
            errors.append("Missing widget testing utilities")
        
        # Check for widget finders
        if "find." not in content:
            errors.append("Missing widget finders")
        
        # Check for widget interactions
        if "tester.tap(" not in content and "tester.enterText(" not in content:
            errors.append("Missing widget interactions")
        
        return errors

    def _validate_unit_test(self, content: str) -> List[str]:
        """Validate the structure of Flutter unit tests.
        
        Args:
            content: Unit test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper unit test structure
        if "test(" not in content:
            errors.append("Missing test function")
        
        # Check for assertions
        if "expect(" not in content:
            errors.append("Missing assertions")
        
        # Check for test setup
        if "setUp(" not in content and "setUpAll(" not in content:
            errors.append("Missing test setup")
        
        # Check for test teardown
        if "tearDown(" not in content and "tearDownAll(" not in content:
            errors.append("Missing test teardown")
        
        return errors

    def _validate_integration_test(self, content: str) -> List[str]:
        """Validate the structure of Flutter integration tests.
        
        Args:
            content: Integration test code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper integration test structure
        if "integration_test" not in content:
            errors.append("Missing integration test imports")
        
        # Check for app initialization
        if "main()" not in content:
            errors.append("Missing app initialization")
        
        # Check for test group
        if "group(" not in content:
            errors.append("Missing test group")
        
        # Check for test cases
        if "test(" not in content:
            errors.append("Missing test cases")
        
        return errors 