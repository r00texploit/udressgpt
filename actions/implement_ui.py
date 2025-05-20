#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : implement_ui.py
"""

from typing import Dict, Any

from metagpt.actions import Action
from metagpt.schema import Message


class ImplementUI(Action):
    """Action for implementing UI components based on design specifications."""

    name: str = "ImplementUI"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the UI implementation action.
        
        Returns:
            Message: A message containing the implemented UI code and components.
        """
        framework = self.context.get("ui_framework", "react").lower()
        
        # Framework-specific prompts
        framework_prompts = {
            "react": """
            As a React developer, implement the following interface design:
            
            {context}
            
            Please provide:
            1. React component code
            2. Component structure and hierarchy
            3. Styling (CSS/SCSS)
            4. State management
            5. Responsive design implementation
            6. Accessibility features
            """,
            
            "flutter": """
            As a Flutter developer, implement the following interface design:
            
            {context}
            
            Please provide:
            1. Flutter widget code
            2. Widget tree structure
            3. Material/Cupertino design implementation
            4. State management
            5. Responsive layout
            6. Accessibility features
            """,
            
            "python": """
            As a Python UI developer, implement the following interface design:
            
            {context}
            
            Please provide:
            1. Python UI code (e.g., Tkinter, PyQt, or other specified framework)
            2. Component structure
            3. Layout implementation
            4. Event handling
            5. Responsive design considerations
            6. Accessibility features
            """,
            
            "vue": """
            As a Vue.js developer, implement the following interface design:
            
            {context}
            
            Please provide:
            1. Vue component code
            2. Component structure and hierarchy
            3. Styling (CSS/SCSS)
            4. Vuex/Pinia state management
            5. Responsive design implementation
            6. Accessibility features
            """,
            
            "angular": """
            As an Angular developer, implement the following interface design:
            
            {context}
            
            Please provide:
            1. Angular component code
            2. Component structure and hierarchy
            3. Styling (CSS/SCSS)
            4. NgRx/Service state management
            5. Responsive design implementation
            6. Accessibility features
            """
        }
        
        # Get the appropriate prompt for the framework
        prompt = framework_prompts.get(framework, """
        As a UI developer, implement the following interface design:
        
        {context}
        
        Please provide:
        1. UI component code
        2. Component structure and hierarchy
        3. Styling and layout implementation
        4. State management
        5. Responsive design implementation
        6. Accessibility features
        """)
        
        # TODO: Implement actual UI implementation logic using LLM
        implementation = await self._aask(prompt.format(context=self.context))
        
        return Message(
            content=implementation,
            role="UI/UX Developer",
            cause_by=self.name
        ) 