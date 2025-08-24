"""
Unified Tool Manager

统一工具管理器 - 整合所有MCP工具能力，为execution模块提供统一的工具接口
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import structlog

# 导入现有的MCP组件
from tools.mcp import (
    MCPToolRegistry,
    BuiltInMCPServerManager,
    ConfigurableMCPServerManager,
    UserInteractionMCPService
)
from tools.mcp.builtin_tools import BaseTool
from models.base import MCPToolDefinition, ToolExecutionResult
from .tool_executor import SmartToolExecutor

logger = structlog.get_logger(__name__)


class UnifiedToolManager:
    """
    统一工具管理器
    
    整合所有MCP工具能力，包括：
    - 内置工具（文件操作、代码分析等）
    - 可配置HTTP MCP服务
    - 用户交互服务
    - 简化的工具执行管理
    """
    
    def __init__(self, config_file_path: Optional[str] = None):
        """初始化统一工具管理器"""
        
        # 初始化MCP组件
        self.mcp_registry = MCPToolRegistry()
        self.builtin_manager = BuiltInMCPServerManager()
        self.configurable_manager = ConfigurableMCPServerManager(config_file_path)
        self.user_interaction = UserInteractionMCPService()
        
        self.smart_executor = SmartToolExecutor(
            self.builtin_manager,
            self.configurable_manager,
            self.user_interaction
        )
        
        # 工具缓存和统计
        self.tool_cache: Dict[str, Any] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("统一工具管理器初始化完成")
    
    async def initialize(self):
        """异步初始化"""
        try:
            # 注册内置工具到MCP注册表
            await self._register_builtin_tools()
            
            # 加载可配置MCP服务
            await self._load_configurable_services()
            
            # 初始化用户交互服务
            await self._initialize_user_interaction()
            
            logger.info("统一工具管理器异步初始化完成")
            
        except Exception as e:
            logger.error(f"统一工具管理器初始化失败: {e}")
            raise
    
    async def _register_builtin_tools(self):
        """注册内置工具到MCP注册表"""
        try:
            # 获取所有内置工具
            builtin_tools = self.builtin_manager.get_all_tools()
            
            for tool_info in builtin_tools:
                # 创建MCP工具定义
                mcp_tool = MCPToolDefinition(
                    name=tool_info["name"],
                    server_name="builtin",
                    server_type="builtin",
                    description=tool_info["description"],
                    category=tool_info["category"],
                    tags=tool_info["tags"],
                    input_schema=tool_info["input_schema"],
                    output_schema=tool_info["output_schema"],
                    is_concurrency_safe=True,  # 内置工具通常是并发安全的
                    requires_authentication=False,
                    timeout=30,
                    allowed_roles=["*"],  # 所有角色都可以使用
                    security_level="low"
                )
                
                # 注册到MCP注册表
                await self.mcp_registry.register_tool(mcp_tool)
            
            logger.info(f"已注册 {len(builtin_tools)} 个内置工具")
            
        except Exception as e:
            logger.error(f"注册内置工具失败: {e}")
            raise
    
    async def _load_configurable_services(self):
        """加载可配置MCP服务"""
        try:
            # 这里可以加载配置文件中的MCP服务
            # 暂时跳过，因为需要配置文件
            logger.info("可配置MCP服务加载完成（暂无可配置服务）")
            
        except Exception as e:
            logger.error(f"加载可配置MCP服务失败: {e}")
            # 不抛出异常，因为这是可选的
    
    async def _initialize_user_interaction(self):
        """初始化用户交互服务"""
        try:
            # 用户交互服务已经在构造函数中初始化
            logger.info("用户交互服务初始化完成")
            
        except Exception as e:
            logger.error(f"初始化用户交互服务失败: {e}")
            # 不抛出异常，因为这是可选的
    
    async def get_available_tools(self, category: str = None) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        try:
            tools = []
            
            # 获取MCP注册表中的工具
            mcp_tools = await self.mcp_registry.get_all_tools()
            for tool in mcp_tools:
                # 检查类别过滤
                if category and tool.category != category:
                    continue
                
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
    
    async def execute_tool(self, 
                          tool_name: str, 
                          parameters: Dict[str, Any], 
                          context: Dict[str, Any] = None) -> ToolExecutionResult:
        """执行单个工具"""
        try:
            # 通过智能工具执行器执行工具
            result = await self.smart_executor.execute_single_tool(tool_name, parameters, context)
            
            # 转换结果格式以保持兼容性
            tool_result = ToolExecutionResult(
                success=result.success,
                result=result.result,
                error=result.error,
                execution_time=result.execution_time,
                metadata=result.metadata
            )
            
            # 记录执行统计
            await self._record_execution_stats(tool_name, True, result.execution_time)
            
            return tool_result
            
        except Exception as e:
            # 记录执行统计
            await self._record_execution_stats(tool_name, False, 0)
            raise
    
    async def execute_tools_batch(self, 
                                tool_calls: List[Dict[str, Any]], 
                                context: Dict[str, Any] = None) -> List[ToolExecutionResult]:
        """批量执行工具"""
        try:
            # 使用智能执行器
            results = await self.smart_executor.execute_tool_calls(tool_calls, context)
            
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
    
    async def _record_execution_stats(self, 
                                    tool_name: str, 
                                    success: bool, 
                                    execution_time: float):
        """记录执行统计"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "last_called": None
            }
        
        stats = self.execution_stats[tool_name]
        stats["total_calls"] += 1
        stats["last_called"] = datetime.now().isoformat()
        
        if success:
            stats["successful_calls"] += 1
            stats["total_execution_time"] += execution_time
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["successful_calls"]
        else:
            stats["failed_calls"] += 1
    
    def get_execution_stats(self, tool_name: str = None) -> Dict[str, Any]:
        """获取执行统计"""
        if tool_name:
            return self.execution_stats.get(tool_name, {})
        
        return {
            "total_tools": len(self.execution_stats),
            "total_calls": sum(stats["total_calls"] for stats in self.execution_stats.values()),
            "successful_calls": sum(stats["successful_calls"] for stats in self.execution_stats.values()),
            "failed_calls": sum(stats["failed_calls"] for stats in self.execution_stats.values()),
            "tools_stats": self.execution_stats
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 清理可配置MCP服务
            if hasattr(self.configurable_manager, 'cleanup'):
                await self.configurable_manager.cleanup()
            
            # 清理用户交互服务
            if hasattr(self.user_interaction, 'cleanup'):
                await self.user_interaction.cleanup()
            
            logger.info("统一工具管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
