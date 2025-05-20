#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : ui_ux_developer.py
"""

from __future__ import annotations

from typing import Set, List, Optional, Dict, Any

from metagpt.actions import Action
from metagpt.actions.design_interface import DesignInterface
from metagpt.actions.implement_ui import ImplementUI
from metagpt.actions.review_ui import ReviewUI
from metagpt.roles import Role
from metagpt.schema import Message


class UIUXDeveloper(Role):
    """
    Represents a UI/UX Developer role responsible for creating user interfaces and ensuring good user experience.

    Attributes:
        name (str): Name of the UI/UX developer.
        profile (str): Role profile, default is 'UI/UX Developer'.
        goal (str): Goal of the UI/UX developer.
        constraints (str): Constraints for the UI/UX developer.
        design_todos (List[DesignInterface]): List of design tasks to be completed.
        implementation_todos (List[ImplementUI]): List of implementation tasks to be completed.
        review_todos (List[ReviewUI]): List of review tasks to be completed.
        ui_framework (str): The UI framework to use (e.g., 'react', 'vue', 'angular', 'flutter').
        enable_review (bool): Whether to enable UI/UX review process.
    """

    name: str = "Sarah"
    profile: str = "UI/UX Developer"
    goal: str = "create intuitive, accessible, and visually appealing user interfaces"
    constraints: str = (
        "designs should follow modern UI/UX principles, be responsive, accessible, "
        "and maintain consistency across the application"
    )
    ui_framework: str = "react"
    enable_review: bool = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.design_todos: List[DesignInterface] = []
        self.implementation_todos: List[ImplementUI] = []
        self.review_todos: List[ReviewUI] = []
        
        # Initialize actions with proper context
        self._init_actions()

    def _init_actions(self) -> None:
        """Initialize actions with proper context."""
        context = {"ui_framework": self.ui_framework, "enable_review": self.enable_review}
        
        design_action = DesignInterface(context=context)
        implement_action = ImplementUI(context=context)
        review_action = ReviewUI(context=context)
        
        self.set_actions([design_action, implement_action, review_action])
        self._watch([design_action, implement_action, review_action])

    def _update_context(self, context: Dict[str, Any]) -> None:
        """Update the role's context with framework and review settings."""
        if "ui_framework" in context:
            self.ui_framework = context["ui_framework"]
        if "enable_review" in context:
            self.enable_review = context["enable_review"]
        
        # Reinitialize actions with updated context
        self._init_actions()

    async def _act(self) -> Message | None:
        """Execute the UI/UX development tasks."""
        if self.rc.todo is None:
            return None

        if isinstance(self.rc.todo, DesignInterface):
            return await self._act_design()
        elif isinstance(self.rc.todo, ImplementUI):
            return await self._act_implement()
        elif isinstance(self.rc.todo, ReviewUI) and self.enable_review:
            return await self._act_review()
        
        return None

    async def _act_design(self) -> Message:
        """Execute design tasks."""
        changed_files = set()
        for todo in self.design_todos:
            todo.context = {"ui_framework": self.ui_framework, "enable_review": self.enable_review}
            design_spec = await todo.run()
            # TODO: Save design specifications to appropriate location
            changed_files.add(design_spec.content)
        
        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=DesignInterface,
            send_to=self,
            sent_from=self,
        )

    async def _act_implement(self) -> Message:
        """Execute implementation tasks."""
        changed_files = set()
        for todo in self.implementation_todos:
            todo.context = {"ui_framework": self.ui_framework, "enable_review": self.enable_review}
            implementation = await todo.run()
            # TODO: Save implementation code to appropriate location
            changed_files.add(implementation.content)
        
        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=ImplementUI,
            send_to=self,
            sent_from=self,
        )

    async def _act_review(self) -> Message:
        """Execute review tasks."""
        if not self.enable_review:
            return None
            
        changed_files = set()
        for todo in self.review_todos:
            todo.context = {"ui_framework": self.ui_framework, "enable_review": self.enable_review}
            review = await todo.run()
            # TODO: Save review results to appropriate location
            changed_files.add(review.content)
        
        return Message(
            content="\n".join(changed_files),
            role=self.profile,
            cause_by=ReviewUI,
            send_to=self,
            sent_from=self,
        )

    async def _think(self) -> Action | None:
        """Determine the next action to take."""
        if not self.rc.todo:
            return None
        
        # Prioritize actions: Design -> Implement -> Review
        if self.design_todos:
            return self.design_todos[0]
        elif self.implementation_todos:
            return self.implementation_todos[0]
        elif self.review_todos and self.enable_review:
            return self.review_todos[0]
        
        return None

    @property
    def action_description(self) -> str:
        """Return the action description for the UI/UX Developer role."""
        return f"I am a UI/UX Developer responsible for creating user interfaces using {self.ui_framework} and ensuring good user experience." 