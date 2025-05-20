#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_php_documentation.py
"""

from typing import Dict, Any
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePHPDocumentation(Action):
    """Action for generating PHP project documentation."""

    name: str = "WritePHPDocumentation"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the PHP documentation generation action.
        
        Args:
            **kwargs: Additional arguments including:
                - project_path: Path to the PHP project
                - project_config: Project configuration dictionary
        
        Returns:
            Message: A message containing the generated documentation
        """
        try:
            # Get project configuration
            project_path = kwargs.get("project_path", "")
            project_config = kwargs.get("project_config", {})
            
            # Generate documentation prompt
            prompt = f"""Generate comprehensive documentation for a PHP project with the following configuration:

Project Configuration:
{project_config}

Please provide the following documentation in markdown format:
1. Project Overview
   - Project description
   - Framework overview
   - Architecture overview
   - Key features

2. Getting Started
   - Prerequisites
   - Installation steps
   - Running the application
   - Development setup

3. Project Structure
   - Directory structure
   - Key components
   - File organization

4. Architecture
   - MVC implementation
   - Service layer
   - Repository pattern
   - Dependency injection

5. Database
   - Database schema
   - Migrations
   - Seeders
   - Query optimization

6. API Documentation
   - API endpoints
   - Request/Response formats
   - Authentication
   - Error handling

7. Testing
   - Testing strategy
   - Unit tests
   - Feature tests
   - Integration tests
   - Test coverage

8. Deployment
   - Deployment process
   - Environment configuration
   - Server requirements
   - CI/CD integration

9. Code Style and Quality
   - PSR standards
   - Code style guidelines
   - Code review process
   - Best practices

10. Troubleshooting
    - Common issues
    - Debugging tips
    - Performance optimization
    - Security considerations

Format the response as a JSON object with the following structure:
{{
    "docs/README.md": "Main documentation content",
    "docs/ARCHITECTURE.md": "Architecture documentation",
    "docs/API.md": "API documentation",
    "docs/TESTING.md": "Testing documentation",
    "docs/DEPLOYMENT.md": "Deployment documentation"
}}
"""
            
            # Get documentation from LLM
            doc_response = await self._aask(prompt)
            doc_blocks = CodeParser.parse_code(block="", text=doc_response)
            
            if not isinstance(doc_blocks, dict):
                return Message(content="Failed to generate documentation")
            
            return Message(content=doc_response)
            
        except Exception as e:
            return Message(content=f"Failed to generate documentation: {str(e)}") 