from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.utils.common import CodeParser, any_to_name, any_to_str, get_project_srcs_path
from metagpt.actions import WriteCode, WriteCodeReview, SummarizeCode
from metagpt.actions.write_code import WriteCodeAction
from metagpt.roles.di.role_zero import RoleZero
from metagpt.tools.libs.editor import Editor
from metagpt.tools.libs.terminal import Terminal
from metagpt.utils.common import tool2name
from metagpt.utils.project_repo import ProjectRepo
from pydantic import Field, BaseModel
from typing import Optional, Set
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class FlutterDeveloper(RoleZero):
    """
    Represents a Flutter Developer role responsible for creating Flutter applications.

    Attributes:
        name (str): Name of the developer.
        profile (str): Role profile, default is 'Senior Flutter Developer'.
        goal (str): Goal of the developer.
        constraints (str): Constraints for the developer.
        instruction (str): Instructions for the role.
        tools (list[str]): List of tools available to the role.
        use_code_review (bool): Whether to use code review.
        repo (ProjectRepo): Project repository instance.
        input_args (BaseModel): Input arguments for the role.
    """
    
    name: str = "FlutterDev"
    profile: str = "Senior Flutter Developer"
    goal: str = "Generate a production-ready Flutter app with best practices"
    constraints: str = (
        "Follow Flutter best practices, use Clean Architecture, implement proper state management, "
        "and ensure code is maintainable and scalable. Use same language as user requirement"
    )
    instruction: str = """Use WriteCode tool to generate Flutter code following Clean Architecture principles"""
    tools: list[str] = [
        "Editor:write,read,similarity_search",
        "RoleZero",
        "Terminal:run_command",
        "WriteCode",
        "WriteCodeReview",
        "SummarizeCode"
    ]
    terminal: Terminal = Field(default_factory=Terminal, exclude=True)
    use_code_review: bool = True
    repo: Optional[ProjectRepo] = Field(default=None, exclude=True)
    input_args: Optional[BaseModel] = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.enable_memory = False
        self.set_actions([WriteCode, WriteCodeReview, SummarizeCode])
        self._watch([WriteCode, WriteCodeReview, SummarizeCode])
    
    def _update_tool_execution(self):
        """Update the tool execution map with available tools."""
        wc = WriteCode()
        wcr = WriteCodeReview()
        sc = SummarizeCode()
        self.tool_execution_map.update({
            "WriteCode.run": wc.run,
            "WriteCode": wc.run,  # alias
            "WriteCodeReview.run": wcr.run,
            "WriteCodeReview": wcr.run,  # alias
            "SummarizeCode.run": sc.run,
            "SummarizeCode": sc.run,  # alias
            "Terminal.run_command": self.terminal.run_command
        })
    
    async def _save_code_to_file(self, filename: str, content: str, dependencies: list[str] = None) -> None:
        """Save generated code to a file in the project repository."""
        if not self.repo:
            logger.warning("No repository initialized. Cannot save code.")
            return
            
        await self.repo.srcs.save(
            filename=filename,
            dependencies=dependencies or [],
            content=content
        )
        logger.info(f"Saved code to {filename}")
    
    async def _init_flutter_project(self, project_name: str) -> None:
        """Initialize a new Flutter project structure."""
        if not self.repo:
            logger.warning("No repository initialized. Cannot create Flutter project.")
            return
            
        # Create basic Flutter project structure
        project_structure = {
            "lib": {
                "main.dart": "",
                "presentation": {
                    "screens": {},
                    "widgets": {}
                },
                "data": {
                    "repositories": {}
                },
                "domain": {
                    "models": {}
                }
            },
            "test": {},
            "pubspec.yaml": ""
        }
        
        # Create directories and files
        for path, content in self._flatten_structure(project_structure):
            full_path = self.repo.workdir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                await self._save_code_to_file(str(path), content)
    
    def _flatten_structure(self, structure: dict, prefix: str = "") -> list[tuple[str, str]]:
        """Flatten nested directory structure into a list of (path, content) tuples."""
        result = []
        for key, value in structure.items():
            path = f"{prefix}/{key}" if prefix else key
            if isinstance(value, dict):
                result.extend(self._flatten_structure(value, path))
            else:
                result.append((path, value))
        return result
    
    async def _act(self, msg: Message) -> Message:
        """Act on the received message to generate Flutter code."""
        # Initialize project if needed
        if not self.repo:
            self.repo = ProjectRepo(self.config.project_path)
            if self.repo.src_relative_path is None:
                path = get_project_srcs_path(self.repo.workdir)
                self.repo.with_src_path(path)
            await self._init_flutter_project(self.config.project_name)
        
        prompt = f"""
        You are a senior Flutter developer. Follow these instructions strictly:
        
        1. **Project Structure**: Use Clean Architecture (data/domain/presentation layers).
        2. **State Management**: Use Riverpod or Bloc.
        3. **Required Files**:
           - main.dart (MaterialApp setup)
           - presentation/screens/ (HomeScreen, CartScreen, etc.)
           - presentation/widgets/ (reusable components)
           - data/repositories/ (API and local data sources)
           - domain/models/ (data classes)
           - pubspec.yaml (with necessary packages: http, riverpod, etc.)
        4. **Code Quality**: Add comments, null safety, and error handling.
        
        Product Spec:
        {msg.content}
        
        Output the full project structure with code for each file.
        """
        
        rsp = self.llm(prompt)
        code = CodeParser.parse_code(rsp)
        
        # Save generated code to files
        if isinstance(code, dict):
            for filename, content in code.items():
                await self._save_code_to_file(filename, content)
        
        return Message(content=code)
    
    async def _think(self) -> bool:
        """Think about what action to take next."""
        if not self.rc.news:
            return False
            
        msg = self.rc.news[0]
        if msg.cause_by == any_to_str(WriteCode):
            self._set_state(0)  # Set state to WriteCode
            return True
        elif msg.cause_by == any_to_str(WriteCodeReview) and self.use_code_review:
            self._set_state(1)  # Set state to WriteCodeReview
            return True
        elif msg.cause_by == any_to_str(SummarizeCode):
            self._set_state(2)  # Set state to SummarizeCode
            return True
            
        return False