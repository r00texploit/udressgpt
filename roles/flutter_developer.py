from metagpt.roles import Role
from metagpt.schema import Message, Document
from metagpt.utils.common import CodeParser
from typing import ClassVar, Set
from metagpt.logs import logger
from pathlib import Path
from metagpt.actions import WriteCode, WriteCodeReview
from pydantic import Field, ConfigDict

from metagpt.provider.base_llm import BaseLLM

class FlutterDeveloper(Role):

    """
    Represents a Flutter developer role responsible for generating Flutter code.

    Attributes:
        name (str): Name of the Flutter developer.
        profile (str): Role profile, default is 'Flutter Developer'.
        goal (str): Goal of the Flutter developer.
        constraints (str): Constraints for the Flutter developer.
        use_code_review (bool): Whether to use code review.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = "Senior Flutter Developer"
    profile: str = "Expert in Flutter, Dart, Clean Architecture, and State Management"
    goal: str = "Generate a production-ready Flutter app with best practices"
    constraints: str = (
        "the code should follow Flutter best practices, be modular, maintainable, and use Clean Architecture. "
        "Use same language as user requirement"
    )
    use_code_review: bool = True
    # llm: BaseLLM = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs) -> None:
        # self.llm = kwargs.get("llm", None)
        super().__init__(**kwargs)
        self.set_actions([WriteCode])
        self._watch([WriteCode, WriteCodeReview])
        print("FlutterDeveloper initialized")
        print(f"class:{self.__class__.__name__}({self.name}), llm: {self.llm},")
    
    async def _act(self) -> Message:
        # Get the latest message from the news
        news = self.rc.news[0]
        
        # Initialize project structure
        project_name = news.content.split(":")[0].strip()
        project_path = self.project_repo.workdir / project_name
        
        # Set up source directory
        self.project_repo.with_src_path(project_path)
        
        # Get system design if available
        design_doc = None
        try:
            design_doc = await self.project_repo.docs.system_design.get("system_design.md")
        except Exception as e:
            logger.warning(f"No system design found: {e}")
        
        # Generate code using LLM
        prompt = f"""Generate a Flutter app for: {news.content}
        
        Follow these requirements:
        1. Use Clean Architecture with the following structure:
           - lib/
             - core/
               - error/
               - network/
               - utils/
             - features/
               - auth/
               - photos/
             - presentation/
               - screens/
               - widgets/
        2. Implement proper state management using Provider
        3. Include error handling in core/error
        4. Follow Flutter best practices
        5. Generate all necessary files including pubspec.yaml
        
        For each file, use this format:
        ```dart:lib/main.dart
        // File content here
        ```
        make sure to Generate all necessary files
        
        Start with pubspec.yaml and then generate all other files."""
        
        if design_doc:
            prompt += f"\n\nSystem Design:\n{design_doc.content}"
        
        rsp = await self.llm.aask(prompt)
        
        # Parse and save files
        code_blocks = CodeParser.parse_code(block="", text=rsp)
        saved_files = []
        failed_files = []
        
        if isinstance(code_blocks, dict):
            # First create the project structure
            for file_path in code_blocks.keys():
                full_path = self.project_repo.workdir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Then save each file
            for file_path, content in code_blocks.items():
                try:
                    # Create coding context
                    old_code_doc = await self.project_repo.srcs.get(file_path)
                    if not old_code_doc:
                        old_code_doc = Document(
                            root_path=str(self.project_repo.src_relative_path),
                            filename=file_path,
                            content=""
                        )
                    
                    # Save the file with dependencies
                    dependencies = []
                    if design_doc:
                        dependencies.append(str(design_doc.root_relative_path))
                    
                    await self.project_repo.srcs.save(
                        filename=file_path,
                        content=content,
                        dependencies=dependencies
                    )
                    saved_files.append(file_path)
                    logger.info(f"Successfully saved file: {file_path}")
                    
                    # Add to memory for tracking
                    msg = Message(
                        content=content,
                        role=self.profile,
                        cause_by=WriteCode
                    )
                    self.rc.memory.add(msg)
                    
                except Exception as e:
                    logger.error(f"Failed to save file {file_path}: {str(e)}")
                    failed_files.append(file_path)
        else:
            logger.error("Failed to parse code blocks from LLM response")
            return Message(content="Failed to parse generated code into files. Please check the LLM response format.")
        
        # Return status message
        if saved_files:
            return Message(
                content=f"Successfully generated Flutter project with {len(saved_files)} files.\n"
                       f"Files created: {', '.join(saved_files)}\n"
                       f"Failed files: {', '.join(failed_files) if failed_files else 'None'}"
            )
        else:
            return Message(
                content="Failed to generate Flutter project. No files were created."
            )