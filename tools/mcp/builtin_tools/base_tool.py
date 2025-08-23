"""
Base Tool Class

基础工具类 - 定义所有内置工具的共同接口和属性
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolSchema:
    """工具模式定义"""
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class BaseTool(ABC):
    """基础工具类"""
    
    def __init__(self):
        self.tool_id: str = self.get_tool_id()
        self.name: str = self.get_name()
        self.description: str = self.get_description()
        self.category: str = self.get_category()
        self.tags: List[str] = self.get_tags()
        self.metadata: Dict[str, Any] = self.get_metadata()
        self.schema: ToolSchema = self.get_schema()
        
        logger.debug(f"工具 {self.name} ({self.tool_id}) 已初始化")
    
    @abstractmethod
    def get_tool_id(self) -> str:
        """获取工具ID"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """获取工具分类"""
        pass
    
    @abstractmethod
    def get_tags(self) -> List[str]:
        """获取工具标签"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """获取工具元数据"""
        pass
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """获取工具模式定义"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具功能"""
        pass
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
            "input_schema": self.schema.input_schema,
            "output_schema": self.schema.output_schema
        }
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        # 基本验证：检查必需字段
        required_fields = self.schema.input_schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"缺少必需字段: {field}")
        return True
