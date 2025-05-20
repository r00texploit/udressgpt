#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/21
@Author  : MetaGPT
@File    : review_ui.py
"""

from typing import Dict, Any

from metagpt.actions import Action
from metagpt.schema import Message


class ReviewUI(Action):
    """Action for reviewing UI implementations and ensuring quality."""

    name: str = "ReviewUI"
    context: Dict[str, Any] = {}

    async def run(self, *args, **kwargs) -> Message:
        """Run the UI review action.
        
        Returns:
            Message: A message containing the review results and recommendations.
        """
        framework = self.context.get("ui_framework", "react").lower()
        
        # Framework-specific prompts
        framework_prompts = {
            "react": """
            As a React UI/UX reviewer, review the following implementation:
            
            {context}
            
            Please evaluate:
            1. React component structure and best practices
            2. State management implementation
            3. Component reusability
            4. Responsive design implementation
            5. Accessibility compliance
            6. Performance considerations
            
            Provide specific recommendations for improvements.
            """,
            
            "flutter": """
            As a Flutter UI/UX reviewer, review the following implementation:
            
            {context}
            
            Please evaluate:
            1. Flutter widget structure and best practices
            2. State management implementation
            3. Widget reusability
            4. Material/Cupertino design compliance
            5. Responsive layout implementation
            6. Accessibility compliance
            
            Provide specific recommendations for improvements.
            """,
            
            "python": """
            As a Python UI reviewer, review the following implementation:
            
            {context}
            
            Please evaluate:
            1. UI component structure and best practices
            2. Event handling implementation
            3. Component organization
            4. Layout implementation
            5. Responsive design considerations
            6. Accessibility compliance
            
            Provide specific recommendations for improvements.
            """,
            
            "vue": """
            As a Vue.js UI/UX reviewer, review the following implementation:
            
            {context}
            
            Please evaluate:
            1. Vue component structure and best practices
            2. Vuex/Pinia state management
            3. Component reusability
            4. Responsive design implementation
            5. Accessibility compliance
            6. Performance considerations
            
            Provide specific recommendations for improvements.
            """,
            
            "angular": """
            As an Angular UI/UX reviewer, review the following implementation:
            
            {context}
            
            Please evaluate:
            1. Angular component structure and best practices
            2. NgRx/Service state management
            3. Component reusability
            4. Responsive design implementation
            5. Accessibility compliance
            6. Performance considerations
            
            Provide specific recommendations for improvements.
            """
        }
        
        # Get the appropriate prompt for the framework
        prompt = framework_prompts.get(framework, """
        As a UI/UX reviewer, review the following implementation:
        
        {context}
        
        Please evaluate:
        1. Component structure and best practices
        2. State management implementation
        3. Component reusability
        4. Responsive design implementation
        5. Accessibility compliance
        6. Performance considerations
        
        Provide specific recommendations for improvements.
        """)
        
        # TODO: Implement actual UI review logic using LLM
        review = await self._aask(prompt.format(context=self.context))
        
        return Message(
            content=review,
            role="UI/UX Developer",
            cause_by=self.name
        ) 