#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_flutter_code.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message, Document
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WriteFlutterCode(Action):
    """Action for generating Flutter code."""

    name: str = "WriteFlutterCode"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the Flutter code generation action.
        
        Returns:
            Message: A message containing the generated Flutter code.
        """
        # Get context information
        filename = self.i_context.filename if hasattr(self.i_context, 'filename') else None
        content = self.i_context.content if hasattr(self.i_context, 'content') else None
        dependencies = self.i_context.dependencies if hasattr(self.i_context, 'dependencies') else []
        
        # Generate code using LLM
        prompt = f"""Generate Flutter code for the following file:
        
        File: {filename}
        Content: {content}
        Dependencies: {dependencies}
        
        Follow these guidelines:
        1. Use appropriate architecture based on project needs
        2. Implement proper state management
        3. Follow Flutter best practices
        4. Include proper error handling
        5. Add comments and documentation
        6. Use proper widget composition
        7. Implement responsive design
        
        Generate the code for this specific file. Use this format:
        ```dart:{filename}
        // File content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated code
        code_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(code_blocks, dict):
            logger.error("Failed to parse generated code blocks")
            return Message(content="Failed to generate Flutter code. Please check the LLM response format.")
        
        # Create coding context
        coding_context = {
            "filename": filename,
            "code_doc": Document(content=code_blocks.get(filename, "")),
            "dependencies": dependencies
        }
        
        # Return generated code
        return Message(
            content=str(coding_context),
            role="Flutter Developer",
            cause_by=self.name
        )

    def _validate_code_structure(self, code_blocks: Dict[str, str]) -> List[str]:
        """Validate the structure of generated Flutter code.
        
        Args:
            code_blocks: Dictionary of file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for main.dart
        if "lib/main.dart" not in code_blocks:
            errors.append("Missing main.dart file")
        
        # Check for core structure
        core_files = [
            "lib/core/error/error_handler.dart",
            "lib/core/network/api_client.dart",
            "lib/core/utils/constants.dart",
        ]
        
        for file in core_files:
            if file not in code_blocks:
                errors.append(f"Missing core file: {file}")
        
        # Check for feature structure
        feature_dirs = [d for d in code_blocks.keys() if d.startswith("lib/features/")]
        if not feature_dirs:
            errors.append("Missing feature implementations")
        
        return errors

    def _validate_widget_structure(self, code: str) -> List[str]:
        """Validate the structure of Flutter widgets.
        
        Args:
            code: Widget code to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check for proper widget structure
        if "extends StatelessWidget" not in code and "extends StatefulWidget" not in code:
            errors.append("Widget must extend StatelessWidget or StatefulWidget")
        
        # Check for build method
        if "Widget build(" not in code:
            errors.append("Missing build method")
        
        # Check for proper constructor
        if "const " not in code and "super(" not in code:
            errors.append("Missing proper constructor")
        
        return errors

class WriteFlutterCodeReview(WriteFlutterCode):
    """Action for reviewing Flutter code."""
    name: str = "WriteFlutterCodeReview" 