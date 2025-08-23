"""
UAgent MCP Tool Registry

MCP工具注册表 - 统一管理所有MCP工具
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from models.base import MCPToolDefinition, ToolExecutionResult

logger = structlog.get_logger(__name__)


class MCPToolRegistry:
    """
    MCP工具注册表
    
    统一管理所有MCP工具，提供工具发现、注册和调用接口
    """
    
    def __init__(self):
        """初始化MCP工具注册表"""
        self.registered_tools: Dict[str, MCPToolDefinition] = {}
        self.tool_servers: Dict[str, Any] = {}
        self.tool_execution_history: List[ToolExecutionResult] = []
        
        logger.info("MCP工具注册表初始化完成")
    
    async def register_tool(self, tool: MCPToolDefinition) -> bool:
        """注册MCP工具"""
        try:
            if tool.name in self.registered_tools:
                logger.warning(f"工具已存在，将覆盖: {tool.name}")
            
            self.registered_tools[tool.name] = tool
            logger.info(f"MCP工具已注册: {tool.name}")
            return True
            
        except Exception as e:
            logger.error(f"工具注册失败: {tool.name}, 错误: {e}")
            return False
    
    async def unregister_tool(self, tool_name: str) -> bool:
        """注销MCP工具"""
        if tool_name in self.registered_tools:
            del self.registered_tools[tool_name]
            logger.info(f"MCP工具已注销: {tool_name}")
            return True
        return False
    
    async def get_tool(self, tool_name: str) -> Optional[MCPToolDefinition]:
        """获取工具定义"""
        return self.registered_tools.get(tool_name)
    
    async def get_all_tools(self) -> List[MCPToolDefinition]:
        """获取所有工具"""
        return list(self.registered_tools.values())
    
    async def get_tools_by_category(self, category: str) -> List[MCPToolDefinition]:
        """按类别获取工具"""
        return [tool for tool in self.registered_tools.values() if tool.category == category]
    
    async def get_tools_by_server(self, server_name: str) -> List[MCPToolDefinition]:
        """按服务器获取工具"""
        return [tool for tool in self.registered_tools.values() if tool.server_name == server_name]
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], role: str = "unknown") -> Any:
        """调用工具"""
        tool = await self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"工具不存在: {tool_name}")
        
        start_time = datetime.now()
        
        try:
            # 这里应该根据工具类型调用相应的执行器
            # 暂时返回模拟结果
            result = await self._execute_tool(tool, parameters)
            
            # 记录执行历史
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_result = ToolExecutionResult(
                tool_name=tool_name,
                server_name=tool.server_name,
                role=role,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
            self.tool_execution_history.append(execution_result)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_result = ToolExecutionResult(
                tool_name=tool_name,
                server_name=tool.server_name,
                role=role,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
            self.tool_execution_history.append(execution_result)
            raise
    
    async def _execute_tool(self, tool: MCPToolDefinition, parameters: Dict[str, Any]) -> Any:
        """执行工具（模拟实现）"""
        # 这里应该根据工具类型调用相应的执行器
        await asyncio.sleep(0.1)  # 模拟执行时间
        
        # 返回模拟结果
        return {
            "tool_name": tool.name,
            "parameters": parameters,
            "result": f"模拟执行结果: {tool.description}",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        # 按类别统计工具数量
        category_counts = {}
        for tool in self.registered_tools.values():
            category = tool.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 按服务器统计工具数量
        server_counts = {}
        for tool in self.registered_tools.values():
            server = tool.server_name
            server_counts[server] = server_counts.get(server, 0) + 1
        
        return {
            "total_tools": len(self.registered_tools),
            "category_distribution": category_counts,
            "server_distribution": server_counts,
            "execution_history_size": len(self.tool_execution_history)
        }
