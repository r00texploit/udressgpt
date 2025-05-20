#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : design_interface.py
"""

from typing import Dict, Any

from metagpt.actions import Action
from metagpt.schema import Message


class DesignInterface(Action):
    """Action for designing user interfaces and creating mockups."""

    name: str = "DesignInterface"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the interface design action.
        
        Returns:
            Message: A message containing the design specifications and mockups.
        """
        framework = self.context.get("ui_framework", "react").lower()
        
        # Framework-specific prompts
        framework_prompts = {
            "react": """
            As a React UI/UX designer, create a detailed interface design based on the following requirements:
            
            {context}
            
            Please provide:
            1. A high-level design overview
            2. React component specifications
            3. Layout guidelines
            4. Color scheme and typography
            5. Responsive design considerations
            6. Accessibility guidelines
            """,
            
            "flutter": """
            As a Flutter UI/UX designer, create a detailed interface design based on the following requirements:
            
            {context}
            
            Please provide:
            1. A high-level design overview
            2. Flutter widget specifications
            3. Material/Cupertino design guidelines
            4. Color scheme and typography
            5. Responsive layout considerations
            6. Accessibility guidelines
            """,
            
            "python": """
            As a Python UI/UX designer, create a detailed interface design based on the following requirements:
            
            {context}
            
            Please provide:
            1. A high-level design overview
            2. UI component specifications (Tkinter/PyQt/etc.)
            3. Layout guidelines
            4. Color scheme and typography
            5. Responsive design considerations
            6. Accessibility guidelines
            """,
            
            "vue": """
            As a Vue.js UI/UX designer, create a detailed interface design based on the following requirements:
            
            {context}
            
            Please provide:
            1. A high-level design overview
            2. Vue component specifications
            3. Layout guidelines
            4. Color scheme and typography
            5. Responsive design considerations
            6. Accessibility guidelines
            """,
            
            "angular": """
            As an Angular UI/UX designer, create a detailed interface design based on the following requirements:
            
            {context}
            
            Please provide:
            1. A high-level design overview
            2. Angular component specifications
            3. Layout guidelines
            4. Color scheme and typography
            5. Responsive design considerations
            6. Accessibility guidelines
            """
        }
        
        # Get the appropriate prompt for the framework
        prompt = framework_prompts.get(framework, """
        As a UI/UX designer, create a detailed interface design based on the following requirements:
        
        {context}
        
        Please provide:
        1. A high-level design overview
        2. Component specifications
        3. Layout guidelines
        4. Color scheme and typography
        5. Responsive design considerations
        6. Accessibility guidelines
        """)
        
        # TODO: Implement actual design generation logic using LLM
        design_spec = await self._aask(prompt.format(context=self.context))
        
        return Message(
            content=design_spec,
            role="UI/UX Developer",
            cause_by=self.name
        ) 