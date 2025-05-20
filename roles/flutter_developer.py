from metagpt.roles import Role
from metagpt.schema import Message, Document
from metagpt.utils.common import CodeParser, any_to_name, any_to_str_set
from typing import ClassVar, Set, List, Dict, Any, Optional
from metagpt.logs import logger
from pathlib import Path

from metagpt.actions.write_flutter_code import WriteFlutterCode, WriteFlutterCodeReview
from metagpt.actions.write_flutter_tests import WriteFlutterTests
from metagpt.actions.write_flutter_documentation import WriteFlutterDocumentation
from pydantic import Field, ConfigDict
import subprocess
import json
import re
import yaml
from enum import Enum
from dataclasses import dataclass

from metagpt.provider.base_llm import BaseLLM
from metagpt.provider.deepseek_api import DeepSeekLLM
from metagpt.configs.llm_config import LLMConfig, LLMType
from openai.types import CompletionUsage
from metagpt.utils.cost_manager import CostManager

from metagpt.config2 import Config
from metagpt.context import Context

from actions.action import Action

class FlutterError(Exception):
    """Base exception for Flutter-related errors."""
    pass

class ProjectValidationError(FlutterError):
    """Exception raised when project validation fails."""
    pass

class DependencyError(FlutterError):
    """Exception raised when dependency management fails."""
    pass

class BuildError(FlutterError):
    """Exception raised when build configuration fails."""
    pass

@dataclass
class FlutterProjectConfig:
    """Configuration for Flutter project setup."""
    name: str
    organization: str = "com.example"
    platforms: List[str] = None
    architecture: str = "clean"
    state_management: str = "provider"
    test_coverage: float = 80.0
    lint_rules: Dict[str, Any] = None
    documentation: bool = True

    def __post_init__(self):
        if self.platforms is None:
            self.platforms = ["android", "ios", "web"]
        if self.lint_rules is None:
            self.lint_rules = {
                "rules": [
                    "prefer_const_constructors",
                    "prefer_const_declarations",
                    "avoid_print",
                    "use_key_in_widget_constructors"
                ],
                "exclude": ["generated_plugin_registrant.dart"]
            }

class FlutterDeveloper(Role):
    """
    Represents a Flutter developer role responsible for generating Flutter code.
    This implementation follows a more flexible approach similar to the Engineer role.

    Attributes:
        name (str): Name of the Flutter developer.
        profile (str): Role profile, default is 'Flutter Developer'.
        goal (str): Goal of the Flutter developer.
        constraints (str): Constraints for the Flutter developer.
        use_code_review (bool): Whether to use code review.
        test_coverage (float): Target test coverage percentage.
        platforms (List[str]): Target platforms for the Flutter app.
    """
    name: str = "Flutter Developer"
    profile: str = "Flutter Developer"
    goal: str = "write elegant, readable, extensible, efficient Flutter code"
    constraints: str = (
        "the code should follow Flutter best practices, be modular, maintainable, and use appropriate architecture. "
        "Use same language as user requirement"
    )
    use_code_review: bool = False
    test_coverage: float = 80.0
    platforms: List[str] = ["android", "ios", "web"]
    code_todos: list = []
    summarize_todos: list = []
    next_todo_action: str = ""
    n_summarize: int = 0

    def __init__(self, **kwargs) -> None:
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
            llm.max_retries = 5  # Set max_retries before using it
            llm.cost_manager = CostManager()  # Initialize cost manager
            kwargs['llm'] = llm
            
        super().__init__(**kwargs)
        
        # Initialize project configuration
        self.project_config: Optional[FlutterProjectConfig] = None
        
        # Initialize Flutter-specific actions with proper context
        context_dict = self.context.dict() if hasattr(self.context, 'dict') else {}
        
        # Initialize WriteFlutterCode with Flutter-specific context
        self.write_flutter_code = WriteFlutterCode(
            context={
                **context_dict,
                "architecture": "clean",
                "state_management": "provider",
                "platforms": ["android", "ios", "web"],
                "test_coverage": 80.0
            }
        )
        
        # Initialize other Flutter-specific actions
        self.write_flutter_tests = WriteFlutterTests(context=context_dict)
        self.write_documentation = WriteFlutterDocumentation(context=context_dict)
        
        # Set actions - only Flutter-specific actions
        self.set_actions([self.write_flutter_code, self.write_flutter_tests, self.write_documentation])
        self._watch([WriteFlutterCode, WriteFlutterTests, WriteFlutterDocumentation])
        
        print("FlutterDeveloper initialized")
        print(f"class:{self.__class__.__name__}({self.name}), llm: {self.llm},")
        
        self.code_todos = []
        self.summarize_todos = []
        self.next_todo_action = any_to_name(WriteFlutterCode)
    
    async def initialize_flutter_project(self, project_path: Path) -> bool:
        """Initialize a new Flutter project with proper configuration."""
        try:
            # Create Flutter project
            subprocess.run(["flutter", "create", "--org", "com.example", str(project_path)], check=True)
            
            # Update pubspec.yaml with common dependencies
            pubspec_path = project_path / "pubspec.yaml"
            if pubspec_path.exists():
                with open(pubspec_path, "r") as f:
                    pubspec_content = f.read()
                
                # Add common dependencies
                dependencies = {
                    "provider": "^6.0.5",
                    "get_it": "^7.6.0",
                    "dio": "^5.3.2",
                    "flutter_bloc": "^8.1.3",
                    "equatable": "^2.0.5",
                    "json_annotation": "^4.8.1",
                    "freezed_annotation": "^2.4.1",
                    "flutter_secure_storage": "^8.0.0",
                    "shared_preferences": "^2.2.0",
                }
                
                # Add dev dependencies
                dev_dependencies = {
                    "build_runner": "^2.4.6",
                    "json_serializable": "^6.7.1",
                    "freezed": "^2.4.5",
                    "flutter_test": "sdk",
                    "integration_test": "sdk",
                }
                
                # Update pubspec.yaml
                updated_content = await self._update_pubspec_dependencies(pubspec_content, dependencies, dev_dependencies)
                with open(pubspec_path, "w") as f:
                    f.write(updated_content)
                
                return True
        except Exception as e:
            logger.error(f"Failed to initialize Flutter project: {str(e)}")
            return False

    async def _update_pubspec_dependencies(self, content: str, dependencies: Dict[str, str], dev_dependencies: Dict[str, str]) -> str:
        """Update pubspec.yaml with new dependencies using proper YAML parsing."""
        try:
            # Parse existing YAML
            pubspec = yaml.safe_load(content)
            
            # Update dependencies
            if "dependencies" not in pubspec:
                pubspec["dependencies"] = {}
            pubspec["dependencies"].update(dependencies)
            
            # Update dev_dependencies
            if "dev_dependencies" not in pubspec:
                pubspec["dev_dependencies"] = {}
            pubspec["dev_dependencies"].update(dev_dependencies)
            
            # Add Flutter SDK dependency if not present
            if "flutter" not in pubspec["dependencies"]:
                pubspec["dependencies"]["flutter"] = "sdk"
            
            # Convert back to YAML
            return yaml.dump(pubspec, default_flow_style=False)
        except Exception as e:
            raise DependencyError(f"Failed to update pubspec.yaml: {str(e)}")

    async def configure_build(self, project_path: Path) -> bool:
        """Configure build settings for different platforms."""
        try:
            # Configure Android build
            android_path = project_path / "android"
            if android_path.exists():
                # Update Android configuration
                gradle_path = android_path / "build.gradle"
                if gradle_path.exists():
                    with open(gradle_path, "r") as f:
                        gradle_content = f.read()
                    
                    # Update Gradle configuration
                    updated_content = await self._aask(await self._update_android_gradle(gradle_content))
                    with open(gradle_path, "w") as f:
                        f.write(updated_content)
            
            # Configure iOS build
            ios_path = project_path / "ios"
            if ios_path.exists():
                # Update iOS configuration
                podfile_path = ios_path / "Podfile"
                if podfile_path.exists():
                    with open(podfile_path, "r") as f:
                        podfile_content = f.read()
                    
                    # Update Podfile configuration
                    updated_content = await self._aask(await self._update_ios_podfile(podfile_content))
                    with open(podfile_path, "w") as f:
                        f.write(updated_content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to configure build: {str(e)}")
            return False

    async def _update_android_gradle(self, content: str) -> str:
        """Update Android Gradle configuration based on project requirements.
        
        Args:
            content: Original Gradle configuration content
            
        Returns:
            Updated Gradle configuration content
        """
        try:
            # Get project requirements from context
            requirements = self.context.get("requirements", "")
            design_doc = self.context.get("design_doc", "")
            
            # Generate configuration using LLM
            prompt = f"""Based on the following project requirements, generate an Android Gradle configuration:

Requirements:
{requirements}

Design Document:
{design_doc if design_doc else 'No design document provided'}

Please provide the following configurations in JSON format:
1. SDK versions (minSdkVersion, targetSdkVersion, compileSdkVersion)
2. Dependencies (core, networking, database, UI, testing, etc.)
3. Build types (debug, release, staging)
4. Signing configurations
5. Product flavors (if needed)
6. Build features and options

Format the response as a JSON object with the following structure:
{{
    "sdk_versions": {{
        "minSdkVersion": "version",
        "targetSdkVersion": "version",
        "compileSdkVersion": "version"
    }},
    "dependencies": {{
        "core": ["dependency1", "dependency2"],
        "networking": ["dependency1", "dependency2"],
        "database": ["dependency1", "dependency2"],
        "ui": ["dependency1", "dependency2"],
        "testing": ["dependency1", "dependency2"]
    }},
    "build_types": {{
        "debug": {{
            "minifyEnabled": "true/false",
            "debuggable": "true/false",
            "applicationIdSuffix": "suffix"
        }},
        "release": {{
            "minifyEnabled": "true/false",
            "proguardFiles": "files",
            "signingConfig": "config"
        }}
    }},
    "signing_configs": {{
        "debug": {{
            "storeFile": "file",
            "storePassword": "password",
            "keyAlias": "alias",
            "keyPassword": "password"
        }},
        "release": {{
            "storeFile": "file",
            "storePassword": "env_var",
            "keyAlias": "env_var",
            "keyPassword": "env_var"
        }}
    }},
    "product_flavors": {{
        "dev": {{
            "applicationIdSuffix": "suffix",
            "versionNameSuffix": "suffix"
        }},
        "prod": {{
            "applicationIdSuffix": "suffix",
            "versionNameSuffix": "suffix"
        }}
    }},
    "build_features": {{
        "viewBinding": "true/false",
        "dataBinding": "true/false"
    }},
    "packaging_options": {{
        "excludes": ["file1", "file2"]
    }}
}}
"""
            
            # Get configuration from LLM
            config_response = await self._aask(prompt)
            config = json.loads(config_response)
            
            # Update build.gradle with generated configurations
            updates = {
                "compileSdkVersion": config["sdk_versions"]["compileSdkVersion"],
                "targetSdkVersion": config["sdk_versions"]["targetSdkVersion"],
                "minSdkVersion": config["sdk_versions"]["minSdkVersion"],
                "dependencies": "\n    " + "\n    ".join([
                    f"implementation '{dep}'" for dep in 
                    config["dependencies"]["core"] +
                    config["dependencies"]["networking"] +
                    config["dependencies"]["database"] +
                    config["dependencies"]["ui"] +
                    config["dependencies"]["testing"]
                ]),
                "buildTypes": "\n    buildTypes {\n" + "\n".join([
                    f"        {type} {{\n" + "\n".join([
                        f"            {key} {value}"
                        for key, value in config["build_types"][type].items()
                    ]) + "\n        }"
                    for type in config["build_types"]
                ]) + "\n    }",
                "signingConfigs": "\n    signingConfigs {\n" + "\n".join([
                    f"        {type} {{\n" + "\n".join([
                        f"            {key} {value}"
                        for key, value in config["signing_configs"][type].items()
                    ]) + "\n        }"
                    for type in config["signing_configs"]
                ]) + "\n    }",
                "productFlavors": "\n    productFlavors {\n" + "\n".join([
                    f"        {type} {{\n" + "\n".join([
                        f"            {key} {value}"
                        for key, value in config["product_flavors"][type].items()
                    ]) + "\n        }"
                    for type in config["product_flavors"]
                ]) + "\n    }" if config["product_flavors"] else "",
                "android": f"""
    android {{
        namespace 'com.example.app'
        defaultConfig {{
            applicationId "com.example.app"
            versionCode 1
            versionName "1.0"
            testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
        }}
        
        buildFeatures {{
            {chr(10).join(f"            {key} {value}" for key, value in config["build_features"].items())}
        }}
        
        packagingOptions {{
            resources {{
                excludes += {config["packaging_options"]["excludes"]}
            }}
        }}
    }}
"""
            }
            
            # Apply updates to content
            for key, value in updates.items():
                if key in content:
                    pattern = f"{key}.*?(?=\n\w|$)"
                    content = re.sub(pattern, f"{key} {value}", content, flags=re.DOTALL)
                else:
                    content += f"\n{key} {value}"
            
            return content
        except Exception as e:
            logger.error(f"Failed to update Android Gradle configuration: {str(e)}")
            return content

    async def _update_ios_podfile(self, content: str) -> str:
        """Update iOS Podfile configuration based on project requirements.
        
        Args:
            content: Original Podfile configuration content
            
        Returns:
            Updated Podfile configuration content
        """
        try:
            # Get project requirements from context
            requirements = self.context.get("requirements", "")
            design_doc = self.context.get("design_doc", "")
            
            # Generate configuration using LLM
            prompt = f"""Based on the following project requirements, generate an iOS Podfile configuration:

Requirements:
{requirements}

Design Document:
{design_doc if design_doc else 'No design document provided'}

Please provide the following configurations in JSON format:
1. iOS version
2. Pods (core, networking, database, UI, testing, etc.)
3. Build configurations
4. Post-install settings

Format the response as a JSON object with the following structure:
{{
    "ios_version": "version",
    "pods": {{
        "core": ["pod1", "pod2"],
        "networking": ["pod1", "pod2"],
        "database": ["pod1", "pod2"],
        "ui": ["pod1", "pod2"],
        "testing": ["pod1", "pod2"]
    }},
    "configurations": {{
        "workspace": "name",
        "project": "name",
        "build_settings": {{
            "ENABLE_BITCODE": "YES/NO",
            "SWIFT_VERSION": "version",
            "CLANG_WARN_STRICT_PROTOTYPES": "YES/NO",
            "CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER": "YES/NO"
        }}
    }},
    "post_install": {{
        "code_signing": {{
            "CODE_SIGN_IDENTITY": "identity",
            "DEVELOPMENT_TEAM": "team_id"
        }},
        "swift_package_manager": "YES/NO",
        "swift_lint": "YES/NO"
    }}
}}
"""
            
            # Get configuration from LLM
            config_response = await self._aask(prompt)
            config = json.loads(config_response)
            
            # Update Podfile with generated configurations
            updates = {
                "platform": f"platform :ios, '{config['ios_version']}'",
                "pods": "\n  " + "\n  ".join([
                    f"# {category}\n  " + "\n  ".join(config["pods"][category])
                    for category in config["pods"]
                ]),
                "configurations": f"""
  # Configurations
  configurations: ['Debug', 'Release', 'Staging']
  workspace '{config["configurations"]["workspace"]}'
  project '{config["configurations"]["project"]}'
""",
                "post_install": f"""
post_install do |installer|
  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '{config["ios_version"]}'
      {chr(10).join(f"      config.build_settings['{key}'] = '{value}'" for key, value in config["configurations"]["build_settings"].items())}
      
      # Enable arm64 architecture for simulators
      config.build_settings['EXCLUDED_ARCHS[sdk=iphonesimulator*]'] = 'arm64'
      
      # Code signing
      {chr(10).join(f"      config.build_settings['{key}'] = '{value}'" for key, value in config["post_install"]["code_signing"].items())}
      
      # Swift Package Manager
      config.build_settings['SWIFT_PACKAGE_MANAGER'] = '{config["post_install"]["swift_package_manager"]}'
      
      # Swift Lint
      config.build_settings['SWIFT_LINT'] = '{config["post_install"]["swift_lint"]}'
    end
  end
end
"""
            }
            
            # Apply updates to content
            for key, value in updates.items():
                if key in content:
                    pattern = f"{key}.*?(?=\n\w|$)"
                    content = re.sub(pattern, f"{key} {value}", content, flags=re.DOTALL)
                else:
                    content += f"\n{key} {value}"
            
            return content
        except Exception as e:
            logger.error(f"Failed to update iOS Podfile configuration: {str(e)}")
            return content
    
    async def validate_project_structure(self, project_path: Path) -> bool:
        """Validate the Flutter project structure."""
        try:
            required_dirs = [
                "lib",
                "test",
                "android",
                "ios",
                "web",
                "lib/core",
                "lib/features",
                "lib/shared"
            ]
            
            required_files = [
                "pubspec.yaml",
                "lib/main.dart",
                "test/widget_test.dart",
                "analysis_options.yaml"
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
            
            # Validate pubspec.yaml
            pubspec_path = project_path / "pubspec.yaml"
            with open(pubspec_path, "r") as f:
                pubspec = yaml.safe_load(f)
                if not pubspec.get("name") or not pubspec.get("dependencies"):
                    raise ProjectValidationError("Invalid pubspec.yaml structure")
            
            return True
        except Exception as e:
            logger.error(f"Project validation failed: {str(e)}")
            return False

    async def setup_code_quality(self, project_path: Path) -> bool:
        """Set up code quality tools and linting rules."""
        try:
            # Create analysis_options.yaml
            analysis_options = {
                "include": "package:flutter_lints/flutter.yaml",
                "analyzer": {
                    "exclude": self.project_config.lint_rules["exclude"],
                    "errors": {
                        "missing_required_param": "error",
                        "missing_return": "error",
                        "must_be_immutable": "error"
                    }
                },
                "linter": {
                    "rules": self.project_config.lint_rules["rules"]
                }
            }
            
            analysis_path = project_path / "analysis_options.yaml"
            with open(analysis_path, "w") as f:
                yaml.dump(analysis_options, f)
            
            # Add flutter_lints to dev_dependencies
            pubspec_path = project_path / "pubspec.yaml"
            with open(pubspec_path, "r") as f:
                pubspec = yaml.safe_load(f)
            
            if "dev_dependencies" not in pubspec:
                pubspec["dev_dependencies"] = {}
            
            pubspec["dev_dependencies"]["flutter_lints"] = "^2.0.0"
            
            with open(pubspec_path, "w") as f:
                yaml.dump(pubspec, f)
            
            # Run flutter analyze
            subprocess.run(["flutter", "analyze"], cwd=project_path, check=True)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set up code quality: {str(e)}")
            return False

    async def generate_documentation(self, project_path: Path) -> bool:
        """Generate project documentation."""
        try:
            if not self.project_config.documentation:
                return True
            
            # Generate API documentation
            self.write_documentation.context.update({
                "project_path": str(project_path),
                "project_config": self.project_config.__dict__
            })
            
            doc_message = await self.write_documentation.run()
            if not doc_message or "Failed" in doc_message.content:
                raise Exception("Failed to generate documentation")
            
            # Parse and save documentation
            doc_blocks = CodeParser.parse_code(block="", text=doc_message.content)
            if isinstance(doc_blocks, dict):
                for file_path, content in doc_blocks.items():
                    full_path = project_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_path, "w") as f:
                        f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate documentation: {str(e)}")
            return False

    async def _act(self) -> Message | None:
        """Determines the mode of action based on whether code review is used."""
        if self.rc.todo is None:
            return None
            
        if isinstance(self.rc.todo, WriteFlutterCode):
            self.next_todo_action = any_to_name(WriteFlutterTests)
            return await self._act_write_code()
            
        if isinstance(self.rc.todo, WriteFlutterTests):
            self.next_todo_action = any_to_name(WriteFlutterDocumentation)
            return await self._act_write_tests()
            
        if isinstance(self.rc.todo, WriteFlutterDocumentation):
            self.next_todo_action = any_to_name(WriteFlutterCode)
            return await self._act_write_documentation()
            
        return None

    async def _act_write_code(self):
        """Handle Flutter code writing."""
        changed_files = set()
        for todo in self.code_todos:
            coding_context = await todo.run()
            
            # Code review if enabled
            if self.use_code_review:
                action = WriteFlutterCode(i_context=coding_context, context=self.context, llm=self.llm)
                self._init_action(action)
                coding_context = await action.run()

            # Save the generated code
            await self.project_repo.srcs.save(
                filename=coding_context.filename,
                dependencies=coding_context.dependencies,
                content=coding_context.code_doc.content,
            )
            
            msg = Message(
                content=coding_context.model_dump_json(),
                instruct_content=coding_context,
                role=self.profile,
                cause_by=WriteFlutterCode,
            )
            self.rc.memory.add(msg)
            changed_files.add(coding_context.code_doc.filename)

        if not changed_files:
            logger.info("Nothing has changed.")
            
        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=WriteFlutterCodeReview if self.use_code_review else WriteFlutterCode,
            send_to=self,
            sent_from=self,
        )

    async def _act_write_tests(self):
        """Handle Flutter test writing."""
        changed_files = set()
        for todo in self.code_todos:
            test_context = await todo.run()
            
            # Save the generated tests
            await self.project_repo.tests.save(
                filename=test_context.filename,
                dependencies=test_context.dependencies,
                content=test_context.test_doc.content,
            )
            
            msg = Message(
                content=test_context.model_dump_json(),
                instruct_content=test_context,
                role=self.profile,
                cause_by=WriteFlutterTests,
            )
            self.rc.memory.add(msg)
            changed_files.add(test_context.test_doc.filename)

        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=WriteFlutterTests,
            send_to=self,
            sent_from=self,
        )

    async def _act_write_documentation(self):
        """Handle Flutter documentation writing."""
        changed_files = set()
        for todo in self.code_todos:
            doc_context = await todo.run()
            
            # Save the generated documentation
            await self.project_repo.docs.save(
                filename=doc_context.filename,
                dependencies=doc_context.dependencies,
                content=doc_context.doc_doc.content,
            )
            
            msg = Message(
                content=doc_context.model_dump_json(),
                instruct_content=doc_context,
                role=self.profile,
                cause_by=WriteFlutterDocumentation,
            )
            self.rc.memory.add(msg)
            changed_files.add(doc_context.doc_doc.filename)

        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=WriteFlutterDocumentation,
            send_to=self,
            sent_from=self,
        )

    async def _think(self) -> Action | None:
        """Determine the next action based on incoming messages."""
        if not self.rc.news:
            return None
            
        msg = self.rc.news[0]
        
        # Handle code writing tasks
        if msg.cause_by in any_to_str_set([WriteFlutterCode]):
            logger.debug(f"TODO WriteFlutterCode:{msg.model_dump_json()}")
            await self._new_code_actions()
            return self.rc.todo
            
        # Handle test writing tasks
        if msg.cause_by in any_to_str_set([WriteFlutterTests]):
            logger.debug(f"TODO WriteFlutterTests:{msg.model_dump_json()}")
            await self._new_test_actions()
            return self.rc.todo
            
        # Handle documentation tasks
        if msg.cause_by in any_to_str_set([WriteFlutterDocumentation]):
            logger.debug(f"TODO WriteFlutterDocumentation:{msg.model_dump_json()}")
            await self._new_documentation_actions()
            return self.rc.todo
            
        return None

    async def _new_code_actions(self):
        """Create new Flutter code writing actions."""
        changed_files = self.project_repo.srcs.changed_files
        for filename in changed_files:
            coding_doc = await self._new_coding_doc(filename)
            self.code_todos.append(WriteFlutterCode(i_context=coding_doc, context=self.context, llm=self.llm))
            
        if self.code_todos:
            self.set_todo(self.code_todos[0])

    async def _new_test_actions(self):
        """Create new Flutter test writing actions."""
        changed_files = self.project_repo.tests.changed_files
        for filename in changed_files:
            test_doc = await self._new_test_doc(filename)
            self.code_todos.append(WriteFlutterTests(i_context=test_doc, context=self.context, llm=self.llm))
            
        if self.code_todos:
            self.set_todo(self.code_todos[0])

    async def _new_documentation_actions(self):
        """Create new Flutter documentation writing actions."""
        changed_files = self.project_repo.docs.changed_files
        for filename in changed_files:
            doc_doc = await self._new_doc_doc(filename)
            self.code_todos.append(WriteFlutterDocumentation(i_context=doc_doc, context=self.context, llm=self.llm))
            
        if self.code_todos:
            self.set_todo(self.code_todos[0])

    @property
    def action_description(self) -> str:
        """AgentStore uses this attribute to display to the user what actions the current role should take."""
        return self.next_todo_action