#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_flutter_documentation.py
"""

from typing import Dict, Any, List
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message, Document
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WriteFlutterDocumentation(Action):
    """Action for generating Flutter documentation."""

    name: str = "WriteFlutterDocumentation"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the Flutter documentation generation action.
        
        Returns:
            Message: A message containing the generated Flutter documentation.
        """
        # Get context information
        filename = self.i_context.filename if hasattr(self.i_context, 'filename') else None
        content = self.i_context.content if hasattr(self.i_context, 'content') else None
        dependencies = self.i_context.dependencies if hasattr(self.i_context, 'dependencies') else []
        
        # Generate documentation using LLM
        prompt = f"""Generate Flutter documentation for the following file:
        
        File: {filename}
        Content: {content}
        Dependencies: {dependencies}
        
        Follow these guidelines:
        1. Document the purpose and functionality
        2. Include usage examples
        3. Document parameters and return values
        4. Include code comments
        5. Follow Flutter documentation best practices
        6. Use proper markdown formatting
        7. Include architecture diagrams if needed
        
        Generate the documentation for this specific file. Use this format:
        ```markdown:{filename}.md
        // Documentation content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated documentation
        doc_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(doc_blocks, dict):
            logger.error("Failed to parse generated documentation blocks")
            return Message(content="Failed to generate Flutter documentation. Please check the LLM response format.")
        
        # Create documentation context
        doc_context = {
            "filename": f"{filename}.md",
            "doc_doc": Document(content=doc_blocks.get(f"{filename}.md", "")),
            "dependencies": dependencies
        }
        
        # Return generated documentation
        return Message(
            content=str(doc_context),
            role="Flutter Developer",
            cause_by=self.name
        ) 