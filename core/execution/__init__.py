"""
UAgent Execution Module

角色执行模块 - 负责管理每个角色的完整Agent运行过程
"""

from .role_executor import RoleExecutor, ExecutionConfig
from .agent_runner import AgentRunner
from .prompt_manager import PromptManager
from .context_compressor import ContextCompressor
from .execution_controller import ExecutionController
from .result_synthesizer import ResultSynthesizer

# 导入新的mcptools包
from .mcptools import init as init_tool, get_tool_manager

__all__ = [
    'RoleExecutor',
    'ExecutionConfig', 
    'AgentRunner',
    'PromptManager',
    'ContextCompressor',
    'ExecutionController',
    'ResultSynthesizer',
    # 新的mcptools包接口
    'init_tool',
    'get_tool_manager',
]
