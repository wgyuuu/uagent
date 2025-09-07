"""
UAgent MCP Tool Registry

MCP工具注册表 - 统一管理所有MCP工具
"""

from typing import Dict, List, Optional, Any
import structlog

from models.base import MCPToolDefinition

logger = structlog.get_logger(__name__)


class MCPToolRegistry:
    """
    MCP工具注册表
    
    统一管理所有MCP工具的注册、发现和查询，不负责工具执行
    职责：
    - 工具注册和注销
    - 工具发现和查询
    - 工具元数据管理
    - 工具统计信息
    """
    
    def __init__(self, config_file_path: Optional[str] = None):
        """初始化MCP工具注册表"""
        self.config_file_path = config_file_path
        self.registered_tools: Dict[str, MCPToolDefinition] = {}
        
        # MCP服务管理器实例（将在initialize中初始化）
        self.builtin_manager = None
        self.configurable_manager = None
        
        logger.info("MCP工具注册表初始化完成")
    
    async def initialize(self):
        """异步初始化MCP服务并自动注册工具"""
        try:
            await self._initialize_mcp_services()
            await self._auto_register_all_tools()
            logger.info("MCP工具注册表异步初始化完成")
        except Exception as e:
            logger.error(f"MCP工具注册表初始化失败: {e}")
            raise
    
    async def _initialize_mcp_services(self):
        """初始化所有MCP服务"""
        try:
            # 避免循环导入，在方法内部导入
            from .builtin_mcp import BuiltInMCPServerManager
            from .configurable_mcp import ConfigurableMCPServerManager
            
            # 初始化内置MCP服务器管理器
            self.builtin_manager = BuiltInMCPServerManager()
            
            # 初始化可配置MCP服务器管理器
            self.configurable_manager = ConfigurableMCPServerManager()
            if self.config_file_path:
                await self.configurable_manager.load_config(self.config_file_path)
            
            logger.info("所有MCP服务初始化完成")
            
        except Exception as e:
            logger.error(f"MCP服务初始化失败: {e}")
            raise
    
    async def _auto_register_all_tools(self):
        """自动从所有MCP服务发现和注册工具"""
        try:
            # 注册内置工具
            await self._register_builtin_tools()
            
            # 注册可配置MCP工具
            await self._register_configurable_tools()
            
            logger.info(f"自动注册完成，共注册 {len(self.registered_tools)} 个工具")
            
        except Exception as e:
            logger.error(f"自动注册工具失败: {e}")
            raise
    
    async def _register_builtin_tools(self):
        """注册内置工具"""
        if not self.builtin_manager:
            return
        
        try:
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
                    is_concurrency_safe=True,
                    requires_authentication=False,
                    timeout=30,
                    allowed_roles=["*"],
                    security_level="low"
                )
                
                await self.register_tool(mcp_tool)
            
            logger.info(f"已注册 {len(builtin_tools)} 个内置工具")
            
        except Exception as e:
            logger.error(f"注册内置工具失败: {e}")
            raise
    
    async def _register_configurable_tools(self):
        """注册可配置MCP工具"""
        if not self.configurable_manager:
            return
        
        try:
            configurable_tools = await self.configurable_manager.get_all_tools()
            
            for tool_info in configurable_tools:
                # 创建MCP工具定义
                mcp_tool = MCPToolDefinition(
                    name=tool_info.name,
                    server_name=tool_info.server_id,
                    server_type="configurable",
                    description=tool_info.description,
                    category="configurable",
                    tags=["configurable", "http"],
                    input_schema=tool_info.input_schema,
                    output_schema=tool_info.output_schema,
                    is_concurrency_safe=False,  # HTTP工具可能不是并发安全的
                    requires_authentication=True,
                    timeout=tool_info.timeout,
                    allowed_roles=["*"],
                    security_level="medium"
                )
                
                await self.register_tool(mcp_tool)
            
            logger.info(f"已注册 {len(configurable_tools)} 个可配置工具")
            
        except Exception as e:
            logger.error(f"注册可配置工具失败: {e}")
            # 不抛出异常，因为这是可选的
    
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """直接通过相应的MCP服务执行工具"""
        try:
            tool = await self.get_tool(tool_name)
            if not tool:
                raise ValueError(f"工具不存在: {tool_name}")
            
            # 根据工具类型路由到相应的MCP服务
            if tool.server_type == "builtin":
                return await self.builtin_manager.execute_tool(tool_name, parameters)
            elif tool.server_type == "configurable":
                return await self.configurable_manager.execute_tool(tool_name, parameters)
            else:
                raise ValueError(f"未知的工具类型: {tool.server_type}")
                
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            raise
    
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
    
    async def search_tools(self, query: str) -> List[MCPToolDefinition]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        
        for tool in self.registered_tools.values():
            # 搜索名称、描述、标签
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                results.append(tool)
        
        return results
    
    async def get_tools_by_tags(self, tags: List[str]) -> List[MCPToolDefinition]:
        """按标签获取工具"""
        results = []
        tags_lower = [tag.lower() for tag in tags]
        
        for tool in self.registered_tools.values():
            if any(tag.lower() in tags_lower for tag in tool.tags):
                results.append(tool)
        
        return results
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = set()
        for tool in self.registered_tools.values():
            categories.add(tool.category)
        return list(categories)
    
    def get_servers(self) -> List[str]:
        """获取所有服务器"""
        servers = set()
        for tool in self.registered_tools.values():
            servers.add(tool.server_name)
        return list(servers)


    
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
            "server_distribution": server_counts
        }
