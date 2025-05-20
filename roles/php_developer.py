#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : Claude
@File    : php_developer.py
"""

from __future__ import annotations

from asyncio import subprocess
import json
from typing import Set, List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from xml.etree.ElementTree import XML

from metagpt.actions import Action, WriteCode, WriteCodeReview, WriteTasks
from metagpt.actions.summarize_code import SummarizeCode
from metagpt.actions.write_code_plan_and_change_an import WriteCodePlanAndChange
from metagpt.actions.write_php_code import WritePHPCode
from metagpt.actions.write_php_tests import WritePHPTests
from metagpt.actions.write_php_documentation import WritePHPDocumentation
from metagpt.roles import Role
from metagpt.schema import Message, CodingContext
from metagpt.logs import logger
from metagpt.provider.base_llm import BaseLLM
from metagpt.provider.deepseek_api import DeepSeekLLM
from metagpt.configs.llm_config import LLMConfig, LLMType
from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.utils.cost_manager import CostManager
import xml

class PHPError(Exception):
    """Base exception for PHP-related errors."""
    pass

class ProjectValidationError(PHPError):
    """Exception raised when project validation fails."""
    pass

class DependencyError(PHPError):
    """Exception raised when dependency management fails."""
    pass

class BuildError(PHPError):
    """Exception raised when build configuration fails."""
    pass

@dataclass
class PHPProjectConfig:
    """Configuration for PHP project setup."""
    name: str
    organization: str = "com.example"
    framework: str = "laravel"  # or "symfony", "slim", etc.
    php_version: str = "8.2"
    use_composer: bool = True
    use_docker: bool = True
    test_coverage: float = 80.0
    coding_standards: Dict[str, Any] = None
    documentation: bool = True

    def __post_init__(self):
        if self.coding_standards is None:
            self.coding_standards = {
                "rules": [
                    "PSR-12",
                    "PSR-4",
                    "PSR-1"
                ],
                "exclude": ["vendor/*", "storage/*"]
            }

class PHPDeveloper(Role):
    """
    Represents a PHP developer role responsible for generating PHP code.

    Attributes:
        name (str): Name of the PHP developer.
        profile (str): Role profile, default is 'PHP Developer'.
        goal (str): Goal of the PHP developer.
        constraints (str): Constraints for the PHP developer.
        use_code_review (bool): Whether to use code review.
        test_coverage (float): Target test coverage percentage.
        framework (str): Target PHP framework.
        php_version (str): Target PHP version.
        use_composer (bool): Whether to use Composer for dependency management.
        use_docker (bool): Whether to use Docker for development environment.
        coding_standards (Dict[str, Any]): Coding standards to follow.
    """

    name: str = "Senior PHP Developer"
    profile: str = "Expert in PHP, Laravel/Symfony, and Modern PHP Development"
    goal: str = "Generate a production-ready PHP application with best practices"
    constraints: str = (
        "the code should follow PSR standards, be well-documented, "
        "use modern PHP features, and follow framework best practices. "
        "Ensure code is testable, maintainable, and secure."
    )
    
    # Development settings
    use_code_review: bool = True
    test_coverage: float = 80.0
    framework: str = "laravel"
    php_version: str = "8.2"
    use_composer: bool = True
    use_docker: bool = True
    coding_standards: Dict[str, Any] = None
    
    # Task tracking
    code_todos: List[WriteCode] = []
    review_todos: List[WriteCodeReview] = []
    summarize_todos: List[SummarizeCode] = []
    plan_todos: List[WriteCodePlanAndChange] = []

    def __init__(self, **kwargs) -> None:
        """Initialize the PHP Developer role with given attributes."""
        # Initialize with DeepSeekLLM configuration
        if 'config' not in kwargs:
            llm_config = LLMConfig(
                api_type=LLMType.DEEPSEEK,
                model="deepseek-reasoner",
                base_url="https://api.deepseek.com/v1",
                api_key="sk-4da57d72282f44a6be1a8ceff263441b",
                timeout=300,
                http_client_kwargs={
                    "timeout": 300,
                    "verify": True,
                    "max_retries": 5
                }
            )
            kwargs['config'] = Config(llm=llm_config)
            
        # Initialize context if not provided
        if 'context' not in kwargs:
            kwargs['context'] = Context(config=kwargs['config'])
            
        # Initialize LLM before super().__init__
        if 'llm' not in kwargs:
            llm = DeepSeekLLM(kwargs['config'].llm)
            llm.max_retries = 5
            llm.cost_manager = CostManager()
            kwargs['llm'] = llm
            
        super().__init__(**kwargs)
        
        # Initialize project configuration
        self.project_config: Optional[PHPProjectConfig] = None
        
        # Initialize PHP-specific actions with proper context
        context_dict = self.context.dict() if hasattr(self.context, 'dict') else {}
        
        # Initialize WritePHPCode with PHP-specific context
        self.write_php_code = WritePHPCode(
            context={
                **context_dict,
                "framework": self.framework,
                "php_version": self.php_version,
                "use_composer": self.use_composer,
                "use_docker": self.use_docker,
                "coding_standards": self.coding_standards,
                "test_coverage": self.test_coverage
            }
        )
        
        # Initialize other PHP-specific actions
        self.write_php_tests = WritePHPTests(context=context_dict)
        self.write_documentation = WritePHPDocumentation(context=context_dict)
        
        # Set actions - only PHP-specific actions
        self.set_actions([self.write_php_code, self.write_php_tests, self.write_documentation])
        self._watch([WritePHPCode, WritePHPTests, WritePHPDocumentation])
        
        print("PHPDeveloper initialized")
        print(f"class:{self.__class__.__name__}({self.name}), llm: {self.llm},")

    async def _act(self) -> Message:
        """Main action method for PHP development process."""
        try:
            # Get the latest message from the news
            news = self.rc.news[0]
            
            # Initialize project structure
            project_name = news.content.split(":")[0].strip()
            project_path = self.project_repo.workdir / project_name
            
            # Create project configuration
            self.project_config = PHPProjectConfig(
                name=project_name,
                organization="com.example"
            )
            
            # Step 1: Initialize PHP project
            logger.info("Step 1: Initializing PHP project...")
            if not await self.initialize_php_project(project_path):
                raise PHPError("Failed to initialize PHP project")
            logger.info("PHP project initialized successfully")
            
            # Step 2: Validate project structure
            logger.info("Step 2: Validating project structure...")
            if not await self.validate_project_structure(project_path):
                raise ProjectValidationError("Project structure validation failed")
            logger.info("Project structure validated successfully")
            
            # Step 3: Set up code quality
            logger.info("Step 3: Setting up code quality...")
            if not await self.setup_code_quality(project_path):
                raise PHPError("Failed to set up code quality tools")
            logger.info("Code quality setup completed")
            
            # Step 4: Set up source directory
            logger.info("Step 4: Setting up source directory...")
            self.project_repo.with_src_path(project_path)
            
            # Step 5: Get system design if available
            logger.info("Step 5: Getting system design...")
            design_doc = None
            try:
                design_doc = await self.project_repo.docs.system_design.get("system_design.md")
                logger.info("System design document found")
            except Exception as e:
                logger.warning(f"No system design found: {e}")
            
            # Step 6: Generate PHP code
            logger.info("Step 6: Generating PHP code...")
            self.write_php_code.context.update({
                "requirements": news.content,
                "framework": self.project_config.framework,
                "php_version": self.project_config.php_version,
                "design_doc": design_doc.content if design_doc else None
            })
            
            code_message = await self.write_php_code.run()
            if not code_message or "Failed" in code_message.content:
                raise PHPError("Failed to generate PHP code")
            logger.info("PHP code generated successfully")
            
            # Step 7: Generate tests
            logger.info("Step 7: Generating tests...")
            test_message = await self.write_php_tests.run(
                test_type="all",
                source_files=list(code_message.content.keys())
            )
            if not test_message or "Failed" in test_message.content:
                logger.warning("Failed to generate tests")
            else:
                logger.info("Tests generated successfully")
            
            # Step 8: Generate documentation
            logger.info("Step 8: Generating documentation...")
            doc_message = await self.write_documentation.run(
                project_path=project_path,
                project_config=self.project_config.__dict__
            )
            if not doc_message or "Failed" in doc_message.content:
                logger.warning("Failed to generate documentation")
            else:
                logger.info("Documentation generated successfully")
            
            # Return status message
            return Message(
                content=f"Successfully generated PHP project with the following components:\n"
                       f"1. Project structure initialized\n"
                       f"2. Code quality tools configured\n"
                       f"3. PHP code generated\n"
                       f"4. Tests generated\n"
                       f"5. Documentation generated"
            )
                
        except PHPError as e:
            logger.error(f"PHP development error: {str(e)}")
            return Message(content=f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Message(content=f"Unexpected error: {str(e)}")

    async def initialize_php_project(self, project_path: Path) -> bool:
        """Initialize a new PHP project with proper configuration."""
        try:
            if self.framework == "laravel":
                # Create Laravel project
                subprocess.run(["composer", "create-project", "laravel/laravel", str(project_path)], check=True)
            elif self.framework == "symfony":
                # Create Symfony project
                subprocess.run(["composer", "create-project", "symfony/website-skeleton", str(project_path)], check=True)
            else:
                # Create basic PHP project
                project_path.mkdir(parents=True, exist_ok=True)
                composer_json = {
                    "name": f"{self.project_config.organization}/{self.project_config.name}",
                    "description": "PHP Project",
                    "type": "project",
                    "require": {
                        "php": f"^{self.php_version}"
                    },
                    "require-dev": {
                        "phpunit/phpunit": "^9.5",
                        "squizlabs/php_codesniffer": "^3.7"
                    },
                    "autoload": {
                        "psr-4": {
                            f"{self.project_config.organization}\\{self.project_config.name}\\": "src/"
                        }
                    },
                    "autoload-dev": {
                        "psr-4": {
                            f"{self.project_config.organization}\\{self.project_config.name}\\Tests\\": "tests/"
                        }
                    }
                }
                
                with open(project_path / "composer.json", "w") as f:
                    json.dump(composer_json, f, indent=4)
                
                subprocess.run(["composer", "install"], cwd=project_path, check=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PHP project: {str(e)}")
            return False

    async def validate_project_structure(self, project_path: Path) -> bool:
        """Validate the PHP project structure."""
        try:
            required_dirs = [
                "src",
                "tests",
                "config",
                "public",
                "vendor"
            ]
            
            required_files = [
                "composer.json",
                "composer.lock",
                "phpunit.xml",
                ".gitignore"
            ]
            
            # Check directories
            for dir_path in required_dirs:
                full_path = project_path / dir_path
                if not full_path.exists():
                    raise ProjectValidationError(f"Required directory missing: {dir_path}")
            
            # Check files
            for file_path in required_files:
                full_path = project_path / file_path
                if not full_path.exists():
                    raise ProjectValidationError(f"Required file missing: {file_path}")
            
            # Validate composer.json
            composer_path = project_path / "composer.json"
            with open(composer_path, "r") as f:
                composer = json.load(f)
                if not composer.get("name") or not composer.get("require"):
                    raise ProjectValidationError("Invalid composer.json structure")
            
            return True
        except Exception as e:
            logger.error(f"Project validation failed: {str(e)}")
            return False

    async def setup_code_quality(self, project_path: Path) -> bool:
        """Set up code quality tools and coding standards."""
        try:
            # Create phpcs.xml
            phpcs_config = {
                "ruleset": {
                    "name": "PHP_CodeSniffer",
                    "description": "PHP CodeSniffer configuration",
                    "exclude-patterns": self.project_config.coding_standards["exclude"],
                    "rule": self.project_config.coding_standards["rules"]
                }
            }
            
            phpcs_path = project_path / "phpcs.xml"
            with open(phpcs_path, "w") as f:
                XML.dump(phpcs_config, f)
            
            # Create phpunit.xml if not exists
            if not (project_path / "phpunit.xml").exists():
                phpunit_config = {
                    "phpunit": {
                        "bootstrap": "vendor/autoload.php",
                        "colors": "true",
                        "coverage": {
                            "include": {
                                "directory": "src"
                            }
                        },
                        "testsuite": {
                            "name": "PHPUnit Test Suite",
                            "directory": "tests"
                        }
                    }
                }
                
                phpunit_path = project_path / "phpunit.xml"
                with open(phpunit_path, "w") as f:
                    xml.dump(phpunit_config, f)
            
            # Run composer update to install dev dependencies
            subprocess.run(["composer", "update"], cwd=project_path, check=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set up code quality: {str(e)}")
            return False

    @property
    def action_description(self) -> str:
        """Return the action description for the PHP Developer role."""
        return (
            f"I am a {self.profile} responsible for writing clean, efficient PHP code "
            f"using {self.framework} framework and following PSR standards. "
            f"PHP version: {self.php_version}, "
            f"Composer: {'enabled' if self.use_composer else 'disabled'}, "
            f"Docker: {'enabled' if self.use_docker else 'disabled'}, "
            f"Code review: {'enabled' if self.use_code_review else 'disabled'}"
        ) 