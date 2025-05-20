#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : write_python_documentation.py
"""

from typing import Dict, Any, Optional
from pathlib import Path

from metagpt.actions import Action
from metagpt.schema import Message
from metagpt.utils.common import CodeParser
from metagpt.logs import logger

class WritePythonDocumentation(Action):
    """Action for generating Python-specific documentation with best practices."""

    name: str = "WritePythonDocumentation"
    context: Dict[str, Any] = {}

    async def run(self, project_path: Optional[str] = None, project_config: Optional[Dict[str, Any]] = None) -> Message:
        """Run the Python documentation generation action.
        
        Args:
            project_path: Path to the Python project
            project_config: Dictionary containing project configuration
            
        Returns:
            Message: A message containing the generated Python documentation.
        """
        # Get project requirements from context
        requirements = self.context.get("requirements", "")
        python_version = self.context.get("python_version", "3.9")
        use_sphinx = self.context.get("use_sphinx", True)
        use_mkdocs = self.context.get("use_mkdocs", True)
        
        # Generate documentation using LLM
        prompt = f"""Generate comprehensive documentation for a Python project based on the following requirements:
        
        Requirements:
        {requirements}
        
        Python Version: {python_version}
        Documentation Tools: {'Sphinx and MkDocs' if use_sphinx and use_mkdocs else 'Sphinx' if use_sphinx else 'MkDocs'}
        
        Follow these guidelines:
        1. Use clear and concise language
        2. Include code examples
        3. Document all public APIs
        4. Include setup and installation instructions
        5. Document configuration options
        6. Include troubleshooting guides
        7. Follow Google style docstrings
        
        Generate the following documentation files:
        1. README.md with project overview
        2. Architecture documentation
        3. API documentation
        4. Development guide
        5. Deployment guide
        6. Contributing guide
        
        For each file, use this format:
        ```markdown:docs/README.md
        # Documentation content here
        ```
        """
        
        rsp = await self._aask(prompt)
        
        # Parse and validate generated documentation
        doc_blocks = CodeParser.parse_code(block="", text=rsp)
        if not isinstance(doc_blocks, dict):
            logger.error("Failed to parse generated documentation blocks")
            return Message(content="Failed to generate Python documentation. Please check the LLM response format.")
        
        # Validate documentation structure
        required_files = [
            "docs/README.md",
            "docs/ARCHITECTURE.md",
            "docs/API.md",
            "docs/DEVELOPMENT.md",
            "docs/DEPLOYMENT.md",
            "docs/CONTRIBUTING.md",
        ]
        
        missing_files = [f for f in required_files if f not in doc_blocks]
        if missing_files:
            logger.warning(f"Missing required documentation files: {', '.join(missing_files)}")
        
        # Generate additional documentation files if needed
        if missing_files:
            additional_prompt = f"""Generate the following missing documentation files:
            {', '.join(missing_files)}
            
            Follow the same documentation standards and patterns as before.
            """
            
            additional_rsp = await self._aask(additional_prompt)
            additional_blocks = CodeParser.parse_code(block="", text=additional_rsp)
            
            if isinstance(additional_blocks, dict):
                doc_blocks.update(additional_blocks)
        
        # Validate documentation quality
        validation_errors = self._validate_documentation_quality(doc_blocks)
        if validation_errors:
            logger.warning(f"Documentation quality issues found: {', '.join(validation_errors)}")
        
        # Return generated documentation
        return Message(
            content=str(doc_blocks),
            role="Python Developer",
            cause_by=self.name
        )

    def _validate_documentation_quality(self, doc_blocks: Dict[str, str]) -> list[str]:
        """Validate the quality of generated Python documentation.
        
        Args:
            doc_blocks: Dictionary of documentation file paths and their contents
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        for file_path, content in doc_blocks.items():
            # Check for basic structure
            if "# " not in content:
                errors.append(f"Missing title in {file_path}")
            
            # Check for code blocks
            if "```python" not in content and "```bash" not in content:
                errors.append(f"Missing code examples in {file_path}")
            
            # Check for links
            if "[" not in content and "]" not in content:
                errors.append(f"Missing links in {file_path}")
            
            # Check for specific content based on file type
            if "README.md" in file_path:
                if "## Installation" not in content:
                    errors.append("Missing installation instructions in README.md")
                if "## Usage" not in content:
                    errors.append("Missing usage instructions in README.md")
            
            elif "ARCHITECTURE.md" in file_path:
                if "## System Design" not in content:
                    errors.append("Missing system design in ARCHITECTURE.md")
                if "## Components" not in content:
                    errors.append("Missing components description in ARCHITECTURE.md")
            
            elif "API.md" in file_path:
                if "## Endpoints" not in content:
                    errors.append("Missing API endpoints in API.md")
                if "## Authentication" not in content:
                    errors.append("Missing authentication details in API.md")
            
            elif "DEVELOPMENT.md" in file_path:
                if "## Setup" not in content:
                    errors.append("Missing development setup in DEVELOPMENT.md")
                if "## Testing" not in content:
                    errors.append("Missing testing instructions in DEVELOPMENT.md")
            
            elif "DEPLOYMENT.md" in file_path:
                if "## Prerequisites" not in content:
                    errors.append("Missing deployment prerequisites in DEPLOYMENT.md")
                if "## Steps" not in content:
                    errors.append("Missing deployment steps in DEPLOYMENT.md")
            
            elif "CONTRIBUTING.md" in file_path:
                if "## Guidelines" not in content:
                    errors.append("Missing contribution guidelines in CONTRIBUTING.md")
                if "## Process" not in content:
                    errors.append("Missing contribution process in CONTRIBUTING.md")
        
        return errors

    def _get_project_config(self) -> Dict[str, Any]:
        """Get project configuration from context.
        
        Returns:
            Dictionary containing project configuration
        """
        return {
            "name": self.context.get("name", "Python Project"),
            "version": self.context.get("version", "1.0.0"),
            "description": self.context.get("description", ""),
            "author": self.context.get("author", ""),
            "license": self.context.get("license", "MIT"),
            "python_version": self.context.get("python_version", "3.9"),
            "dependencies": self.context.get("dependencies", []),
            "dev_dependencies": self.context.get("dev_dependencies", []),
        } 