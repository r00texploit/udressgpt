#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : python_developer.py
"""

from __future__ import annotations

from asyncio import subprocess
from typing import Set, List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import toml

from metagpt.actions import Action, WriteCode, WriteCodeReview, WriteTasks, WritePythonCode, WritePythonTests, WritePythonDocumentation
from metagpt.actions.summarize_code import SummarizeCode
from metagpt.actions.write_code_plan_and_change_an import WriteCodePlanAndChange
from metagpt.roles import Role
from metagpt.schema import Message, CodingContext
from metagpt.logs import logger
from metagpt.provider.base_llm import BaseLLM
from metagpt.provider.deepseek_api import DeepSeekLLM
from metagpt.configs.llm_config import LLMConfig, LLMType
from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.utils.cost_manager import CostManager

class PythonError(Exception):
    """Base exception for Python-related errors."""
    pass

class ProjectValidationError(PythonError):
    """Exception raised when project validation fails."""
    pass

class DependencyError(PythonError):
    """Exception raised when dependency management fails."""
    pass

class BuildError(PythonError):
    """Exception raised when build configuration fails."""
    pass

@dataclass
class PythonProjectConfig:
    """Configuration for Python project setup."""
    name: str
    organization: str = "com.example"
    python_version: str = "3.9"
    use_poetry: bool = True
    use_docker: bool = True
    test_coverage: float = 80.0
    code_style: str = "pep8"
    use_type_hints: bool = True
    use_docstrings: bool = True
    use_async: bool = True
    use_modern_features: bool = True
    documentation: bool = True

    def __post_init__(self):
        if self.code_style not in ["pep8", "google", "numpy"]:
            raise ValueError(f"Unsupported code style: {self.code_style}")

class PythonDeveloper(Role):
    """
    Represents a Python developer role responsible for generating Python code.

    Attributes:
        name (str): Name of the Python developer.
        profile (str): Role profile, default is 'Python Developer'.
        goal (str): Goal of the Python developer.
        constraints (str): Constraints for the Python developer.
        use_code_review (bool): Whether to use code review.
        test_coverage (float): Target test coverage percentage.
        python_version (str): Target Python version.
        code_style (str): Code style guide to follow (e.g., 'pep8', 'google').
        use_type_hints (bool): Whether to enforce type hints.
        use_docstrings (bool): Whether to enforce docstrings.
        use_async (bool): Whether to use async/await patterns.
        use_modern_features (bool): Whether to use modern Python features.
    """

    name: str = "Senior Python Developer"
    profile: str = "Expert in Python, Clean Architecture, and Modern Python Development"
    goal: str = "Generate a production-ready Python application with best practices"
    constraints: str = (
        "the code should follow PEP 8 style guide, be well-documented with docstrings, "
        "include type hints, and follow Python best practices. Use modern Python features "
        "when appropriate and ensure code is testable and maintainable."
    )
    
    # Development settings
    use_code_review: bool = True
    test_coverage: float = 80.0
    python_version: str = "3.9"
    code_style: str = "pep8"
    use_type_hints: bool = True
    use_docstrings: bool = True
    use_async: bool = True
    use_modern_features: bool = True
    use_poetry: bool = True
    use_docker: bool = True
    
    # Task tracking
    code_todos: List[WriteCode] = []
    review_todos: List[WriteCodeReview] = []
    summarize_todos: List[SummarizeCode] = []
    plan_todos: List[WriteCodePlanAndChange] = []

    def __init__(self, **kwargs) -> None:
        """Initialize the Python Developer role with given attributes."""
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
        self.project_config: Optional[PythonProjectConfig] = None
        
        # Initialize actions with proper context
        self._init_actions()
        self._watch([WriteTasks, SummarizeCode, WriteCode, WriteCodeReview, WriteCodePlanAndChange, WritePythonCode, WritePythonTests, WritePythonDocumentation])

    def _init_actions(self) -> None:
        """Initialize actions with proper context."""
        context = {
            "python_version": self.python_version,
            "code_style": self.code_style,
            "use_type_hints": self.use_type_hints,
            "use_docstrings": self.use_docstrings,
            "use_async": self.use_async,
            "use_modern_features": self.use_modern_features,
            "test_coverage": self.test_coverage,
            "use_poetry": self.use_poetry,
            "use_docker": self.use_docker
        }
        
        # Initialize actions with context
        write_code = WriteCode(context=context)
        code_review = WriteCodeReview(context=context)
        summarize = SummarizeCode(context=context)
        plan = WriteCodePlanAndChange(context=context)
        write_python_code = WritePythonCode(context=context)
        write_python_tests = WritePythonTests(context=context)
        write_python_documentation = WritePythonDocumentation(context=context)
        
        self.set_actions([write_code, code_review, summarize, plan, write_python_code, write_python_tests, write_python_documentation])

    def _update_context(self, context: Dict[str, Any]) -> None:
        """Update the role's context with development settings."""
        for key, value in context.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Reinitialize actions with updated context
        self._init_actions()

    async def initialize_python_project(self, project_path: Path) -> bool:
        """Initialize a new Python project with proper configuration."""
        try:
            if self.use_poetry:
                # Create Poetry project
                subprocess.run(["poetry", "new", str(project_path)], check=True)
                
                # Update pyproject.toml with common dependencies
                pyproject_path = project_path / "pyproject.toml"
                if pyproject_path.exists():
                    with open(pyproject_path, "r") as f:
                        pyproject_content = f.read()
                    
                    # Add common dependencies
                    dependencies = {
                        "pytest": "^7.0.0",
                        "pytest-cov": "^4.0.0",
                        "black": "^23.0.0",
                        "isort": "^5.0.0",
                        "mypy": "^1.0.0",
                        "flake8": "^6.0.0",
                        "pydantic": "^2.0.0",
                        "fastapi": "^0.100.0",
                        "uvicorn": "^0.23.0",
                        "sqlalchemy": "^2.0.0",
                        "alembic": "^1.0.0",
                        "python-dotenv": "^1.0.0"
                    }
                    
                    # Update pyproject.toml
                    updated_content = await self._update_pyproject_dependencies(pyproject_content, dependencies)
                    with open(pyproject_path, "w") as f:
                        f.write(updated_content)
            else:
                # Create basic Python project
                project_path.mkdir(parents=True, exist_ok=True)
                
                # Create requirements.txt
                requirements = [
                    f"python>={self.python_version}",
                    "pytest>=7.0.0",
                    "pytest-cov>=4.0.0",
                    "black>=23.0.0",
                    "isort>=5.0.0",
                    "mypy>=1.0.0",
                    "flake8>=6.0.0",
                    "pydantic>=2.0.0",
                    "fastapi>=0.100.0",
                    "uvicorn>=0.23.0",
                    "sqlalchemy>=2.0.0",
                    "alembic>=1.0.0",
                    "python-dotenv>=1.0.0"
                ]
                
                with open(project_path / "requirements.txt", "w") as f:
                    f.write("\n".join(requirements))
                
                # Create setup.py
                setup_py = f'''from setuptools import setup, find_packages

setup(
    name="{self.project_config.name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        {", ".join(f'"{req}"' for req in requirements)}
    ],
    python_requires=">={self.python_version}",
)
'''
                with open(project_path / "setup.py", "w") as f:
                    f.write(setup_py)
            
            # Create project structure
            for dir_name in ["src", "tests", "docs"]:
                (project_path / dir_name).mkdir(exist_ok=True)
            
            # Create .gitignore
            gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/

# Distribution
dist/
build/
'''
            with open(project_path / ".gitignore", "w") as f:
                f.write(gitignore_content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Python project: {str(e)}")
            return False

    async def validate_project_structure(self, project_path: Path) -> bool:
        """Validate the Python project structure."""
        try:
            required_dirs = [
                "src",
                "tests",
                "docs"
            ]
            
            required_files = [
                "pyproject.toml" if self.use_poetry else "setup.py",
                "requirements.txt" if not self.use_poetry else None,
                ".gitignore",
                "README.md"
            ]
            
            # Check directories
            for dir_path in required_dirs:
                full_path = project_path / dir_path
                if not full_path.exists():
                    raise ProjectValidationError(f"Required directory missing: {dir_path}")
            
            # Check files
            for file_path in required_files:
                if file_path:  # Skip None values
                    full_path = project_path / file_path
                    if not full_path.exists():
                        raise ProjectValidationError(f"Required file missing: {file_path}")
            
            # Validate pyproject.toml or setup.py
            if self.use_poetry:
                pyproject_path = project_path / "pyproject.toml"
                with open(pyproject_path, "r") as f:
                    pyproject = toml.load(f)
                    if not pyproject.get("tool", {}).get("poetry", {}).get("name"):
                        raise ProjectValidationError("Invalid pyproject.toml structure")
            else:
                setup_path = project_path / "setup.py"
                if not setup_path.exists():
                    raise ProjectValidationError("setup.py missing")
            
            return True
        except Exception as e:
            logger.error(f"Project validation failed: {str(e)}")
            return False

    async def setup_code_quality(self, project_path: Path) -> bool:
        """Set up code quality tools and coding standards."""
        try:
            # Create pyproject.toml with tool configurations
            if self.use_poetry:
                pyproject_path = project_path / "pyproject.toml"
                with open(pyproject_path, "r") as f:
                    pyproject = toml.load(f)
                
                # Add tool configurations
                pyproject["tool"] = {
                    "black": {
                        "line-length": 88,
                        "target-version": [self.python_version]
                    },
                    "isort": {
                        "profile": "black",
                        "multi_line_output": 3
                    },
                    "mypy": {
                        "python_version": self.python_version,
                        "strict": True,
                        "ignore_missing_imports": True
                    },
                    "pytest": {
                        "testpaths": ["tests"],
                        "python_files": "test_*.py",
                        "addopts": f"--cov=src --cov-report=term-missing --cov-fail-under={self.test_coverage}"
                    }
                }
                
                with open(pyproject_path, "w") as f:
                    toml.dump(pyproject, f)
            else:
                # Create setup.cfg
                setup_cfg = f'''[flake8]
max-line-length = 88
extend-ignore = E203
exclude = .git,__pycache__,build,dist

[mypy]
python_version = {self.python_version}
strict = True
ignore_missing_imports = True

[tool:pytest]
testpaths = tests
python_files = test_*.py
addopts = --cov=src --cov-report=term-missing --cov-fail-under={self.test_coverage}
'''
                with open(project_path / "setup.cfg", "w") as f:
                    f.write(setup_cfg)
            
            # Create pre-commit config
            pre_commit_config = '''repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8

-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
    -   id: mypy
        additional_dependencies: [types-all]
'''
            with open(project_path / ".pre-commit-config.yaml", "w") as f:
                f.write(pre_commit_config)
            
            # Install pre-commit hooks
            subprocess.run(["pre-commit", "install"], cwd=project_path, check=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set up code quality: {str(e)}")
            return False

    async def _act(self) -> List[Dict[str, Any]]:
        """Execute the main action process for Python development."""
        results = []
        
        # Initialize Python project
        project_config = self._get_project_config()
        await self.initialize_python_project(project_config)
        
        # Validate project structure
        self.validate_project_structure()
        
        # Setup code quality tools
        self.setup_code_quality()
        
        # Generate Python code
        code_result = await self.actions[0].run()
        results.append({"type": "code", "content": code_result.content})
        
        # Generate tests
        test_result = await self.actions[1].run()
        results.append({"type": "tests", "content": test_result.content})
        
        # Generate documentation
        doc_result = await self.actions[2].run()
        results.append({"type": "documentation", "content": doc_result.content})
        
        return results

    def _get_project_config(self) -> PythonProjectConfig:
        """Get project configuration from context."""
        return PythonProjectConfig(
            name=self.context.get("name", "python_project"),
            organization=self.context.get("organization", "my_org"),
            python_version=self.context.get("python_version", "3.9"),
            use_poetry=self.context.get("use_poetry", True),
            use_docker=self.context.get("use_docker", True),
            test_coverage=self.context.get("test_coverage", 80),
            code_style=self.context.get("code_style", "pep8"),
            use_type_hints=self.context.get("use_type_hints", True),
            use_docstrings=self.context.get("use_docstrings", True),
            use_async=self.context.get("use_async", True),
            use_modern_features=self.context.get("use_modern_features", True),
            documentation=self.context.get("documentation", True),
        )

    @property
    def action_description(self) -> str:
        """Return the action description for the Python Developer role."""
        return (
            f"I am a {self.profile} responsible for writing clean, efficient Python code "
            f"following {self.code_style} style guide and best practices. "
            f"Python version: {self.python_version}, "
            f"Type hints: {'enabled' if self.use_type_hints else 'disabled'}, "
            f"Docstrings: {'enabled' if self.use_docstrings else 'disabled'}, "
            f"Async: {'enabled' if self.use_async else 'disabled'}, "
            f"Modern features: {'enabled' if self.use_modern_features else 'disabled'}, "
            f"Poetry: {'enabled' if self.use_poetry else 'disabled'}, "
            f"Docker: {'enabled' if self.use_docker else 'disabled'}"
        ) 