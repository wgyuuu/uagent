"""
Base Prompt Builder

Prompt构建器基类 - 定义所有构建器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

# 使用TYPE_CHECKING避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest


class BasePromptBuilder(ABC):
    """Prompt构建器基类"""
    
    @abstractmethod
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建prompt section
        
        Args:
            request: Prompt构建请求
            
        Returns:
            str: 构建的prompt section内容
        """
        pass
    
    @abstractmethod
    def get_section_name(self) -> str:
        """获取section名称
        
        Returns:
            str: section的标识名称
        """
        pass
    
    def get_priority(self) -> int:
        """获取构建优先级（数字越小优先级越高）
        
        Returns:
            int: 优先级数值，默认为100
        """
        return 100
    
    def is_required(self) -> bool:
        """是否为必需的section
        
        Returns:
            bool: True表示必需，False表示可选
        """
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数
        
        Args:
            request: Prompt构建请求
            
        Returns:
            bool: True表示输入有效，False表示无效
        """
        return True
    
    def get_dependencies(self) -> list[str]:
        """获取依赖的其他section
        
        Returns:
            List[str]: 依赖的section名称列表
        """
        return []
