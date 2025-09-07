"""
Core Prompt Manager Module

独立的prompt管理模块，提供统一的prompt构建和管理功能
"""

from .manager import RuntimePromptManager
from .dto.prompt_request import PromptBuildRequest
from .processors.context_processor import ContextProcessor

# 提供便捷的工厂方法
def create_prompt_manager() -> RuntimePromptManager:
    """创建RuntimePromptManager实例"""
    return RuntimePromptManager()

def create_build_request(role: str, 
                        role_config,
                        context, 
                        execution_state,
                        available_tools: list[str]) -> PromptBuildRequest:
    """创建PromptBuildRequest"""
    return PromptBuildRequest(
        role=role,
        role_config=role_config,
        context=context,
        execution_state=execution_state,
        available_tools=available_tools
    )

__all__ = [
    'RuntimePromptManager',
    'PromptBuildRequest', 
    'ContextProcessor',
    'create_prompt_manager',
    'create_build_request'
]
