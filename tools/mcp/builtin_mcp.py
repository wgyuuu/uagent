"""
Built-in MCP Server Manager

内置MCP服务器管理器 - 管理直接实现的函数调用MCP服务
"""

from typing import Dict, List, Any, Optional
import structlog
import asyncio
from datetime import datetime
import traceback

from models.base import ToolExecutionResult
from .builtin_tools import (
    FileReadTool, FileWriteTool, CodeAnalyzeTool, 
    TextSummarizeTool, SystemInfoTool, DataValidateTool
)

logger = structlog.get_logger(__name__)


class BuiltInMCPServerManager:
    """
    内置MCP服务器管理器
    
    管理直接实现的函数调用MCP服务，提供常用功能的本地实现
    """
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.categories: Dict[str, List[str]] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # 注册默认工具
        self._register_default_tools()
        
        logger.info("内置MCP服务器管理器初始化完成")
    
    def _register_default_tools(self):
        """注册默认内置工具"""
        # 创建工具实例
        tools = [
            FileReadTool(),
            FileWriteTool(),
            CodeAnalyzeTool(),
            TextSummarizeTool(),
            SystemInfoTool(),
            DataValidateTool()
        ]
        
        # 注册所有工具
        for tool in tools:
            self._register_tool_instance(tool)
    
    def _register_tool_instance(self, tool_instance):
        """注册工具实例"""
        try:
            tool_id = tool_instance.tool_id
            tool_info = tool_instance.get_tool_info()
            
            # 注册工具
            self.tools[tool_id] = tool_instance
            
            # 更新分类
            category = tool_info["category"]
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(tool_id)
            
            # 初始化执行统计
            self.execution_stats[tool_id] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "last_called": None,
                "error_history": []
            }
            
            logger.info(f"内置工具已注册: {tool_info['name']} ({tool_id})")
            
        except Exception as e:
            logger.error(f"注册内置工具失败: {e}")
            raise
    
    def register_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        function: callable,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        category: str,
        tags: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """注册内置工具（向后兼容）"""
        logger.warning("此方法已废弃，请使用工具类注册")
        # 这里可以保留向后兼容性，或者抛出异常
        raise NotImplementedError("请使用工具类注册方法")
    
    def unregister_tool(self, tool_id: str):
        """注销内置工具"""
        try:
            if tool_id not in self.tools:
                logger.warning(f"工具 {tool_id} 不存在")
                return
            
            tool = self.tools[tool_id]
            
            # 从分类中移除
            if tool.category in self.categories:
                self.categories[tool.category].remove(tool_id)
                if not self.categories[tool.category]:
                    del self.categories[tool.category]
            
            # 移除工具和统计
            del self.tools[tool_id]
            if tool_id in self.execution_stats:
                del self.execution_stats[tool_id]
            
            logger.info(f"内置工具已注销: {tool_id}")
            
        except Exception as e:
            logger.error(f"注销内置工具失败: {e}")
            raise
    
    async def execute_tool(
        self,
        tool_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        执行内置工具
        
        Args:
            tool_id: 工具ID
            input_data: 输入数据
            timeout: 超时时间
            
        Returns:
            工具执行结果
        """
        try:
            if tool_id not in self.tools:
                raise ValueError(f"工具 {tool_id} 不存在")
            
            tool = self.tools[tool_id]
            
            # 更新执行统计
            self.execution_stats[tool_id]["total_calls"] += 1
            self.execution_stats[tool_id]["last_called"] = datetime.now().isoformat()
            
            # 验证输入数据
            tool.validate_input(input_data)
            
            # 执行工具
            start_time = datetime.now()
            
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**input_data)
            else:
                # 如果是同步函数，在线程池中执行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, tool.execute, **input_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新成功统计
            self.execution_stats[tool_id]["successful_calls"] += 1
            self.execution_stats[tool_id]["total_execution_time"] += execution_time
            
            # 构建结果
            tool_result = ToolExecutionResult(
                tool_id=tool_id,
                success=True,
                output=result,
                execution_time=execution_time,
                metadata={
                    "category": tool.category,
                    "tags": tool.tags,
                    "input_schema": tool.schema.input_schema,
                    "output_schema": tool.schema.output_schema
                }
            )
            
            logger.info(f"内置工具 {tool_id} 执行成功，耗时: {execution_time:.3f}s")
            return tool_result
            
        except Exception as e:
            # 更新失败统计
            if tool_id in self.execution_stats:
                self.execution_stats[tool_id]["failed_calls"] += 1
                self.execution_stats[tool_id]["error_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                # 保持错误历史在合理范围内
                if len(self.execution_stats[tool_id]["error_history"]) > 10:
                    self.execution_stats[tool_id]["error_history"] = \
                        self.execution_stats[tool_id]["error_history"][-10:]
            
            logger.error(f"内置工具 {tool_id} 执行失败: {e}")
            
            # 构建错误结果
            error_result = ToolExecutionResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                execution_time=0,
                metadata={
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            )
            
            return error_result
    
    def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        if tool_id not in self.tools:
            return None
        return self.tools[tool_id].get_tool_info()
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具信息"""
        return [tool.get_tool_info() for tool in self.tools.values()]
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """获取指定分类的工具信息"""
        if category not in self.categories:
            return []
        
        return [
            self.tools[tool_id].get_tool_info() 
            for tool_id in self.categories[category]
        ]
    
    def get_tools_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """获取指定标签的工具信息"""
        return [
            tool.get_tool_info() for tool in self.tools.values()
            if tag in tool.tags
        ]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.categories.keys())
    
    def get_execution_stats(self, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计"""
        if tool_id:
            return self.execution_stats.get(tool_id, {})
        
        return {
            "total_tools": len(self.tools),
            "total_calls": sum(stats["total_calls"] for stats in self.execution_stats.values()),
            "successful_calls": sum(stats["successful_calls"] for stats in self.execution_stats.values()),
            "failed_calls": sum(stats["failed_calls"] for stats in self.execution_stats.values()),
            "tools_stats": self.execution_stats
        }
