"""
Configurable MCP Server Manager

可配置MCP服务器管理器 - 管理通过配置方式添加的HTTP MCP服务
"""

from typing import Dict, List, Any, Optional, Tuple
import structlog
import aiohttp
import asyncio
import json
import yaml
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import time

from models.base import MCPToolDefinition, ToolExecutionResult

logger = structlog.get_logger(__name__)


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    server_id: str
    name: str
    description: str
    base_url: str
    api_key: Optional[str] = None
    auth_type: str = "none"  # "none", "api_key", "bearer", "basic"
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_enabled: bool = False  # 是否启用重试
    rate_limit: Optional[int] = None  # 每分钟请求数
    enabled: bool = True
    metadata: Dict[str, Any] = None


@dataclass
class MCPToolInfo:
    """MCP工具信息"""
    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    server_id: str
    endpoint: str
    method: str
    timeout: int
    retry_config: Dict[str, Any]
    metadata: Dict[str, Any]


class ConfigurableMCPServerManager:
    """
    可配置MCP服务器管理器
    
    管理通过配置文件定义的HTTP MCP服务，支持动态加载、认证、限流和可选重试
    """
    
    def __init__(self):
        self.config_file_path: Optional[str] = None
        self.servers: Dict[str, MCPServerConfig] = {}
        self.tools: Dict[str, MCPToolInfo] = {}
        self.server_sessions: Dict[str, aiohttp.ClientSession] = {}
        self.rate_limit_trackers: Dict[str, List[float]] = {}
        
        logger.info("可配置MCP服务器管理器初始化完成")
    
    async def load_config(self, config_file_path: str):
        """从配置文件加载MCP服务器配置"""
        try:
            self.config_file_path = config_file_path
            logger.info(f"加载MCP配置: {config_file_path}")
            
            with open(config_file_path, 'r', encoding='utf-8') as f:
                if config_file_path.endswith('.yaml') or config_file_path.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # 加载服务器配置
            servers_config = config_data.get('servers', [])
            for server_config in servers_config:
                server = MCPServerConfig(**server_config)
                self.servers[server.server_id] = server
                logger.info(f"加载MCP服务器: {server.name} ({server.server_id})")
            
            # 加载工具配置
            tools_config = config_data.get('tools', [])
            for tool_config in tools_config:
                tool = MCPToolInfo(**tool_config)
                self.tools[tool.tool_id] = tool
                logger.info(f"加载MCP工具: {tool.name} ({tool.tool_id})")
            
            logger.info(f"配置加载完成: {len(self.servers)} 个服务器, {len(self.tools)} 个工具")
            
        except Exception as e:
            logger.error(f"加载MCP配置失败: {e}")
            raise
    
    def save_config(self, config_file_path: Optional[str] = None):
        """保存配置到文件"""
        try:
            save_path = config_file_path or self.config_file_path
            if not save_path:
                raise ValueError("未指定配置文件路径")
            
            config_data = {
                'servers': [asdict(server) for server in self.servers.values()],
                'tools': [asdict(tool) for tool in self.tools.values()]
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith('.yaml') or save_path.endswith('.yml'):
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"保存MCP配置失败: {e}")
            raise
    
    async def add_server(self, server_config: MCPServerConfig):
        """添加MCP服务器"""
        try:
            if server_config.server_id in self.servers:
                logger.warning(f"服务器 {server_config.server_id} 已存在，将被覆盖")
            
            self.servers[server_config.server_id] = server_config
            
            # 创建HTTP会话
            await self._create_server_session(server_config.server_id)
            
            # 初始化限流跟踪器
            self.rate_limit_trackers[server_config.server_id] = []
            
            logger.info(f"MCP服务器已添加: {server_config.name} ({server_config.server_id})")
            
        except Exception as e:
            logger.error(f"添加MCP服务器失败: {e}")
            raise
    
    async def remove_server(self, server_id: str):
        """移除MCP服务器"""
        try:
            if server_id not in self.servers:
                logger.warning(f"服务器 {server_id} 不存在")
                return
            
            # 关闭HTTP会话
            if server_id in self.server_sessions:
                await self.server_sessions[server_id].close()
                del self.server_sessions[server_id]
            
            # 移除相关工具
            tools_to_remove = [
                tool_id for tool_id, tool in self.tools.items()
                if tool.server_id == server_id
            ]
            
            for tool_id in tools_to_remove:
                del self.tools[tool_id]
            
            # 清理其他状态
            del self.servers[server_id]
            if server_id in self.rate_limit_trackers:
                del self.rate_limit_trackers[server_id]
            
            logger.info(f"MCP服务器已移除: {server_id}")
            
        except Exception as e:
            logger.error(f"移除MCP服务器失败: {e}")
            raise
    
    async def add_tool(self, tool_info: MCPToolInfo):
        """添加MCP工具"""
        try:
            if tool_info.tool_id in self.tools:
                logger.warning(f"工具 {tool_info.tool_id} 已存在，将被覆盖")
            
            # 验证服务器存在
            if tool_info.server_id not in self.servers:
                raise ValueError(f"服务器 {tool_info.server_id} 不存在")
            
            self.tools[tool_info.tool_id] = tool_info
            logger.info(f"MCP工具已添加: {tool_info.name} ({tool_info.tool_id})")
            
        except Exception as e:
            logger.error(f"添加MCP工具失败: {e}")
            raise
    
    async def remove_tool(self, tool_id: str):
        """移除MCP工具"""
        try:
            if tool_id not in self.tools:
                logger.warning(f"工具 {tool_id} 不存在")
                return
            
            del self.tools[tool_id]
            logger.info(f"MCP工具已移除: {tool_id}")
            
        except Exception as e:
            logger.error(f"移除MCP工具失败: {e}")
            raise
    
    async def execute_tool(
        self,
        tool_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ToolExecutionResult:
        """
        执行MCP工具
        
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
            
            tool_info = self.tools[tool_id]
            server_id = tool_info.server_id
            
            # 检查限流
            if not await self._check_rate_limit(server_id):
                raise RuntimeError(f"服务器 {server_id} 达到限流阈值")
            
            # 准备请求
            url = f"{self.servers[server_id].base_url.rstrip('/')}/{tool_info.endpoint.lstrip('/')}"
            headers = await self._prepare_headers(server_id)
            
            # 执行请求
            start_time = time.time()
            response = await self._make_request(
                method=tool_info.method,
                url=url,
                headers=headers,
                data=input_data,
                timeout=timeout or tool_info.timeout,
                server_id=server_id
            )
            execution_time = time.time() - start_time
            
            # 构建结果
            result = ToolExecutionResult(
                tool_id=tool_id,
                success=True,
                output=response,
                execution_time=execution_time,
                metadata={
                    "server_id": server_id,
                    "endpoint": tool_info.endpoint,
                    "method": tool_info.method,
                    "response_size": len(str(response))
                }
            )
            
            logger.info(f"工具 {tool_id} 执行成功，耗时: {execution_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"工具 {tool_id} 执行失败: {e}")
            
            # 构建错误结果
            result = ToolExecutionResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                execution_time=0,
                metadata={
                    "server_id": tool_info.server_id if 'tool_info' in locals() else "unknown",
                    "error_type": type(e).__name__
                }
            )
            
            return result
    
    async def _create_server_session(self, server_id: str):
        """为服务器创建HTTP会话"""
        try:
            server_config = self.servers[server_id]
            
            # 创建连接器
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            # 创建会话
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=server_config.timeout)
            )
            
            self.server_sessions[server_id] = session
            logger.info(f"为服务器 {server_id} 创建HTTP会话")
            
        except Exception as e:
            logger.error(f"为服务器 {server_id} 创建HTTP会话失败: {e}")
            raise
    
    async def _prepare_headers(self, server_id: str) -> Dict[str, str]:
        """准备请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "UAgent-MCP-Client/2.0.0"
        }
        
        server_config = self.servers[server_id]
        
        if server_config.auth_type == "api_key" and server_config.api_key:
            headers["X-API-Key"] = server_config.api_key
        elif server_config.auth_type == "bearer" and server_config.api_key:
            headers["Authorization"] = f"Bearer {server_config.api_key}"
        elif server_config.auth_type == "basic" and server_config.username and server_config.password:
            import base64
            credentials = base64.b64encode(
                f"{server_config.username}:{server_config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
        timeout: int,
        server_id: str
    ) -> Any:
        """发送HTTP请求"""
        session = self.server_sessions[server_id]
        server_config = self.servers[server_id]
        
        # 如果未启用重试，直接执行一次请求
        if not server_config.retry_enabled:
            return await self._execute_single_request(method, url, headers, data, timeout, session)
        
        # 启用重试逻辑
        for attempt in range(server_config.max_retries + 1):
            try:
                return await self._execute_single_request(method, url, headers, data, timeout, session)
            except asyncio.TimeoutError:
                if attempt < server_config.max_retries:
                    logger.warning(f"请求超时，重试 {attempt + 1}/{server_config.max_retries}")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise RuntimeError(f"请求超时，已重试 {server_config.max_retries} 次")
            except Exception as e:
                if attempt < server_config.max_retries:
                    logger.warning(f"请求失败，重试 {attempt + 1}/{server_config.max_retries}: {e}")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise
        
        raise RuntimeError("所有重试都失败了")
    
    async def _execute_single_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
        timeout: int,
        session: aiohttp.ClientSession
    ) -> Any:
        """执行单次HTTP请求"""
        if method.upper() == "GET":
            async with session.get(url, headers=headers, timeout=timeout) as response:
                return await self._handle_response(response)
        elif method.upper() == "POST":
            async with session.post(url, headers=headers, json=data, timeout=timeout) as response:
                return await self._handle_response(response)
        elif method.upper() == "PUT":
            async with session.put(url, headers=headers, json=data, timeout=timeout) as response:
                return await self._handle_response(response)
        elif method.upper() == "DELETE":
            async with session.delete(url, headers=headers, timeout=timeout) as response:
                return await self._handle_response(response)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """处理HTTP响应"""
        if response.status >= 400:
            error_text = await response.text()
            raise RuntimeError(f"HTTP {response.status}: {error_text}")
        
        content_type = response.headers.get("Content-Type", "")
        
        if "application/json" in content_type:
            return await response.json()
        elif "text/" in content_type:
            return await response.text()
        else:
            return await response.read()
    
    async def _check_rate_limit(self, server_id: str) -> bool:
        """检查限流"""
        if server_id not in self.rate_limit_trackers:
            return True
        
        server_config = self.servers[server_id]
        if not server_config.rate_limit:
            return True
        
        current_time = time.time()
        tracker = self.rate_limit_trackers[server_id]
        
        # 清理过期的请求记录
        cutoff_time = current_time - 60  # 1分钟窗口
        tracker[:] = [t for t in tracker if t > cutoff_time]
        
        # 检查是否超过限流
        if len(tracker) >= server_config.rate_limit:
            return False
        
        # 记录当前请求
        tracker.append(current_time)
        return True
    
    async def get_tool_info(self, tool_id: str) -> Optional[MCPToolInfo]:
        """获取工具信息"""
        return self.tools.get(tool_id)
    
    async def get_all_tools(self) -> List[MCPToolInfo]:
        """获取所有工具"""
        return list(self.tools.values())
    
    async def get_tools_by_server(self, server_id: str) -> List[MCPToolInfo]:
        """获取指定服务器的工具"""
        return [
            tool for tool in self.tools.values()
            if tool.server_id == server_id
        ]
    
    async def shutdown(self):
        """关闭管理器"""
        try:
            # 关闭所有HTTP会话
            for session in self.server_sessions.values():
                await session.close()
            
            logger.info("可配置MCP服务器管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭管理器失败: {e}")
            raise
