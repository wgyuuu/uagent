"""
Tool Manager

工具管理器 - 统一管理所有工具能力，包括内置工具、可配置MCP服务和用户交互服务
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import structlog

# 导入MCP组件
from tools.mcp import MCPToolRegistry
from models.base import MCPToolDefinition, ToolExecutionResult
from .executor import ToolExecutor

logger = structlog.get_logger(__name__)


class ToolManager:
    """
    工具管理器
    
    统一管理所有工具能力，包括：
    - 内置工具（文件操作、代码分析等）
    - 可配置HTTP MCP服务
    - 用户交互服务
    - 工具注册和发现
    """
    
    def __init__(self, tool_registry: MCPToolRegistry):
        """初始化工具管理器"""
        # 工具注册表（依赖注入）
        self.tool_registry: MCPToolRegistry = tool_registry
        
        # 工具执行器
        self.tool_executor: ToolExecutor = ToolExecutor(self.tool_registry)
        
        logger.info("工具管理器初始化完成")
    
    
    async def get_available_tools(self, category: str = None) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        try:
            # 委托给工具注册表
            if category:
                mcp_tools = await self.tool_registry.get_tools_by_category(category)
            else:
                mcp_tools = await self.tool_registry.get_all_tools()
            
            tools = []
            for tool in mcp_tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "tags": tool.tags,
                    "is_concurrency_safe": tool.is_concurrency_safe,
                    "server_type": tool.server_type,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema
                })
            
            return tools
            
        except Exception as e:
            logger.error(f"获取可用工具失败: {e}")
            return []
    
    async def get_tool(self, tool_name: str) -> Optional[MCPToolDefinition]:
        """获取工具定义"""
        return await self.tool_registry.get_tool(tool_name)
    
    async def get_tools_by_category(self, category: str) -> List[MCPToolDefinition]:
        """按类别获取工具"""
        return await self.tool_registry.get_tools_by_category(category)
    
    async def get_tools_by_server(self, server_name: str) -> List[MCPToolDefinition]:
        """按服务器获取工具"""
        return await self.tool_registry.get_tools_by_server(server_name)
    
    async def search_tools(self, query: str) -> List[MCPToolDefinition]:
        """搜索工具"""
        return await self.tool_registry.search_tools(query)
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return self.tool_registry.get_categories()
    
    def get_servers(self) -> List[str]:
        """获取所有服务器"""
        return self.tool_registry.get_servers()
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """获取工具统计信息"""
        return self.tool_registry.get_registry_stats()
    
    async def execute_tool(self, 
                          tool_name: str, 
                          parameters: Dict[str, Any], 
                          context: Dict[str, Any] = None) -> ToolExecutionResult:
        """执行单个工具"""
        try:
            if not self.tool_executor:
                raise RuntimeError("工具执行器未初始化")
            
            # 通过工具执行器执行工具
            result = await self.tool_executor.execute_single_tool(tool_name, parameters, context)
            
            # 转换结果格式以保持兼容性
            tool_result = ToolExecutionResult(
                success=result.success,
                result=result.result,
                error=result.error,
                execution_time=result.execution_time,
                metadata=result.metadata
            )
            
            return tool_result
            
        except Exception as e:
            raise
    
    async def execute_tools_batch(self, 
                                tool_calls: List[Dict[str, Any]], 
                                context: Dict[str, Any] = None) -> List[ToolExecutionResult]:
        """批量执行工具"""
        try:
            if not self.tool_executor:
                raise RuntimeError("工具执行器未初始化")
            
            # 使用工具执行器
            results = await self.tool_executor.execute_tool_calls(tool_calls, context)
            
            # 转换结果格式以保持兼容性
            tool_results = []
            for result in results:
                tool_result = ToolExecutionResult(
                    success=result.success,
                    result=result.result,
                    error=result.error,
                    execution_time=result.execution_time,
                    metadata=result.metadata
                )
                tool_results.append(tool_result)
            
            return tool_results
            
        except Exception as e:
            logger.error(f"批量执行工具失败: {e}")
            raise
    

    
    async def cleanup(self):
        """清理资源"""
        try:
            # 清理工具注册表中的MCP服务
            if self.tool_registry:
                if hasattr(self.tool_registry, 'configurable_manager') and self.tool_registry.configurable_manager:
                    if hasattr(self.tool_registry.configurable_manager, 'shutdown'):
                        await self.tool_registry.configurable_manager.shutdown()
            
            logger.info("工具管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
