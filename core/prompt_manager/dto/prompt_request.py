"""
Prompt Build Request DTO

Prompt构建请求数据传输对象 - 各级模块共享的数据结构
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

# 使用TYPE_CHECKING避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.base import ExecutionContext, ExecutionState
    from models.roles import RoleConfig


@dataclass
class PromptBuildRequest:
    """Prompt构建请求
    
    这个DTO被prompt_manager的各个子模块共享使用：
    - builders/ 模块使用它来构建各个section
    - processors/ 模块使用它来处理上下文信息
    - manager.py 使用它来协调整个构建过程
    """
    role: str
    role_config: 'RoleConfig'
    context: 'ExecutionContext'
    execution_state: 'ExecutionState'
    available_tools: List[str]
    custom_sections: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """初始化后的验证"""
        if not self.role:
            raise ValueError("role不能为空")
        if not self.available_tools:
            self.available_tools = []
        if self.custom_sections is None:
            self.custom_sections = {}
    
    def has_custom_section(self, section_name: str) -> bool:
        """检查是否有自定义section"""
        return section_name in (self.custom_sections or {})
    
    def get_custom_section(self, section_name: str, default: str = "") -> str:
        """获取自定义section内容"""
        return (self.custom_sections or {}).get(section_name, default)
    
    def add_custom_section(self, section_name: str, content: str):
        """添加自定义section"""
        if self.custom_sections is None:
            self.custom_sections = {}
        self.custom_sections[section_name] = content
