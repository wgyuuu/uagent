# UAgent MCP工具集成架构

## 1. 概述

MCP (Model Context Protocol) 工具集成架构是UAgent系统的工具支撑层，提供了标准化的工具接入、管理和调用机制。该架构支持第三方工具的动态集成，为各角色提供丰富的工具支持。

## 2. 设计理念

### 2.1 统一工具接口
- **标准化协议**: 基于MCP协议的统一工具接口
- **插件化架构**: 支持工具的动态加载和卸载
- **版本兼容**: 向后兼容不同版本的MCP工具
- **类型安全**: 强类型的工具参数和返回值定义

### 2.2 共享资源池
- **并发安全**: 支持多个角色同时访问工具
- **资源复用**: 高效的连接池和资源管理
- **负载均衡**: 智能的工具实例分配
- **故障恢复**: 自动的故障检测和恢复机制

### 2.3 用户交互集成
- **用户提问MCP**: 将用户交互也作为MCP服务
- **实时通信**: 支持实时的用户问答和确认
- **会话管理**: 维护用户交互的上下文和状态
- **多模态支持**: 支持文本、图片等多种交互方式

## 3. MCP工具集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                MCP Tool Integration Layer                   │
├─────────────────────────────────────────────────────────────┤
│  Tool Registry (工具注册表)                                │
│  ├── MCP Server Discovery (MCP服务发现)                   │
│  ├── Tool Metadata Manager (工具元数据管理器)             │
│  └── Version Compatibility Checker (版本兼容性检查器)     │
├─────────────────────────────────────────────────────────────┤
│  Shared MCP Pool (共享MCP资源池)                           │
│  ├── Connection Pool Manager (连接池管理器)               │
│  ├── Load Balancer (负载均衡器)                           │
│  └── Health Monitor (健康监控器)                          │
├─────────────────────────────────────────────────────────────┤
│  Tool Access Controller (工具访问控制器)                   │
│  ├── Permission Manager (权限管理器)                      │
│  ├── Rate Limiter (速率限制器)                            │
│  └── Audit Logger (审计日志器)                            │
├─────────────────────────────────────────────────────────────┤
│  User Question MCP (用户提问MCP)                           │
│  ├── Question Router (问题路由器)                         │
│  ├── Session Manager (会话管理器)                         │
│  └── Response Formatter (响应格式化器)                    │
├─────────────────────────────────────────────────────────────┤
│  Tool Execution Engine (工具执行引擎)                      │
│  ├── Parameter Validator (参数验证器)                     │
│  ├── Execution Coordinator (执行协调器)                   │
│  └── Result Processor (结果处理器)                        │
└─────────────────────────────────────────────────────────────┘
```

## 4. 工具注册表

### 4.1 MCP服务发现
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import aiohttp

@dataclass
class MCPServerInfo:
    """MCP服务器信息"""
    name: str
    url: str
    version: str
    description: str
    capabilities: List[str]
    tools: List[str]
    health_check_url: str
    authentication: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

@dataclass 
class MCPToolInfo:
    """MCP工具信息"""
    name: str
    server_name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    is_concurrency_safe: bool = True
    requires_authentication: bool = False
    rate_limit: Optional[int] = None
    tags: List[str] = None

class MCPServerDiscovery:
    """MCP服务发现"""
    
    def __init__(self):
        self.discovered_servers: Dict[str, MCPServerInfo] = {}
        self.discovery_sources = [
            "http://localhost:8080",  # 本地开发服务
            "https://mcp-registry.example.com",  # 公共注册表
        ]
    
    async def discover_servers(self) -> List[MCPServerInfo]:
        """发现可用的MCP服务器"""
        discovered = []
        
        for source in self.discovery_sources:
            try:
                servers = await self._discover_from_source(source)
                discovered.extend(servers)
            except Exception as e:
                logger.warning(f"Failed to discover from {source}: {e}")
        
        # 更新已发现服务器列表
        for server in discovered:
            self.discovered_servers[server.name] = server
        
        return discovered
    
    async def _discover_from_source(self, source_url: str) -> List[MCPServerInfo]:
        """从指定源发现服务器"""
        async with aiohttp.ClientSession() as session:
            # 尝试标准MCP发现端点
            discovery_endpoints = [
                f"{source_url}/mcp/servers",
                f"{source_url}/.well-known/mcp-servers",
                f"{source_url}/api/v1/servers"
            ]
            
            for endpoint in discovery_endpoints:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_server_list(data)
                except Exception:
                    continue
        
        return []
    
    async def register_server_manually(self, server_info: MCPServerInfo):
        """手动注册MCP服务器"""
        # 验证服务器可访问性
        if await self._validate_server_connection(server_info):
            self.discovered_servers[server_info.name] = server_info
            logger.info(f"Manually registered MCP server: {server_info.name}")
        else:
            raise ValueError(f"Cannot connect to MCP server: {server_info.url}")
    
    async def _validate_server_connection(self, server_info: MCPServerInfo) -> bool:
        """验证服务器连接"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(server_info.health_check_url or f"{server_info.url}/health") as response:
                    return response.status == 200
        except Exception:
            return False
```

### 4.2 工具元数据管理器
```python
class ToolMetadataManager:
    """工具元数据管理器"""
    
    def __init__(self):
        self.tool_registry: Dict[str, MCPToolInfo] = {}
        self.server_tools: Dict[str, List[str]] = {}
        self.tool_categories: Dict[str, List[str]] = {
            "file_operations": [],
            "web_services": [],
            "data_processing": [],
            "user_interaction": [],
            "development_tools": [],
            "system_utilities": []
        }
    
    async def register_server_tools(self, server_info: MCPServerInfo):
        """注册服务器的所有工具"""
        try:
            # 获取服务器工具列表
            tools = await self._fetch_server_tools(server_info)
            
            # 注册每个工具
            for tool_data in tools:
                tool_info = self._create_tool_info(tool_data, server_info.name)
                await self.register_tool(tool_info)
            
            self.server_tools[server_info.name] = [tool.name for tool in tools]
            logger.info(f"Registered {len(tools)} tools from server {server_info.name}")
            
        except Exception as e:
            logger.error(f"Failed to register tools from {server_info.name}: {e}")
    
    async def _fetch_server_tools(self, server_info: MCPServerInfo) -> List[Dict[str, Any]]:
        """从服务器获取工具列表"""
        async with aiohttp.ClientSession() as session:
            tools_url = f"{server_info.url}/tools"
            
            headers = {}
            if server_info.authentication:
                headers.update(self._build_auth_headers(server_info.authentication))
            
            async with session.get(tools_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("tools", [])
                else:
                    raise Exception(f"Failed to fetch tools: HTTP {response.status}")
    
    async def register_tool(self, tool_info: MCPToolInfo):
        """注册单个工具"""
        tool_key = f"{tool_info.server_name}::{tool_info.name}"
        self.tool_registry[tool_key] = tool_info
        
        # 按类别分类工具
        category = self._categorize_tool(tool_info)
        if category in self.tool_categories:
            self.tool_categories[category].append(tool_key)
    
    def _categorize_tool(self, tool_info: MCPToolInfo) -> str:
        """对工具进行分类"""
        tool_name = tool_info.name.lower()
        description = tool_info.description.lower()
        
        # 基于工具名称和描述进行简单分类
        if any(keyword in tool_name or keyword in description 
               for keyword in ["file", "read", "write", "directory"]):
            return "file_operations"
        elif any(keyword in tool_name or keyword in description 
                for keyword in ["http", "web", "api", "request"]):
            return "web_services"
        elif any(keyword in tool_name or keyword in description 
                for keyword in ["user", "question", "input", "ask"]):
            return "user_interaction"
        elif any(keyword in tool_name or keyword in description 
                for keyword in ["git", "code", "compile", "test"]):
            return "development_tools"
        elif any(keyword in tool_name or keyword in description 
                for keyword in ["data", "process", "transform", "parse"]):
            return "data_processing"
        else:
            return "system_utilities"
    
    def get_tools_by_category(self, category: str) -> List[MCPToolInfo]:
        """按类别获取工具"""
        tool_keys = self.tool_categories.get(category, [])
        return [self.tool_registry[key] for key in tool_keys if key in self.tool_registry]
    
    def get_tools_by_server(self, server_name: str) -> List[MCPToolInfo]:
        """按服务器获取工具"""
        return [tool for key, tool in self.tool_registry.items() 
                if tool.server_name == server_name]
    
    def search_tools(self, query: str, categories: List[str] = None) -> List[MCPToolInfo]:
        """搜索工具"""
        results = []
        query_lower = query.lower()
        
        for tool_info in self.tool_registry.values():
            # 检查类别过滤
            if categories:
                tool_category = self._categorize_tool(tool_info)
                if tool_category not in categories:
                    continue
            
            # 检查名称和描述匹配
            if (query_lower in tool_info.name.lower() or 
                query_lower in tool_info.description.lower() or
                any(query_lower in tag.lower() for tag in (tool_info.tags or []))):
                results.append(tool_info)
        
        return results
```

## 5. 共享MCP资源池

### 5.1 连接池管理器
```python
class MCPConnectionPool:
    """MCP连接池"""
    
    def __init__(self, server_info: MCPServerInfo, 
                 min_connections: int = 2, 
                 max_connections: int = 10):
        self.server_info = server_info
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        self.available_connections: asyncio.Queue = asyncio.Queue()
        self.active_connections: Dict[str, MCPConnection] = {}
        self.connection_count = 0
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """初始化连接池"""
        async with self.lock:
            for _ in range(self.min_connections):
                connection = await self._create_connection()
                await self.available_connections.put(connection)
    
    async def get_connection(self) -> 'MCPConnection':
        """获取连接"""
        try:
            # 尝试从池中获取可用连接
            connection = self.available_connections.get_nowait()
            
            # 检查连接健康状态
            if await connection.is_healthy():
                return connection
            else:
                # 连接不健康，创建新连接
                await connection.close()
                return await self._create_connection()
                
        except asyncio.QueueEmpty:
            # 池中没有可用连接
            async with self.lock:
                if self.connection_count < self.max_connections:
                    return await self._create_connection()
                else:
                    # 等待连接释放
                    return await self.available_connections.get()
    
    async def return_connection(self, connection: 'MCPConnection'):
        """归还连接"""
        if await connection.is_healthy():
            await self.available_connections.put(connection)
        else:
            await connection.close()
            async with self.lock:
                self.connection_count -= 1
    
    async def _create_connection(self) -> 'MCPConnection':
        """创建新连接"""
        connection = MCPConnection(self.server_info)
        await connection.connect()
        
        async with self.lock:
            self.connection_count += 1
            connection_id = f"conn_{self.connection_count}"
            self.active_connections[connection_id] = connection
        
        return connection

class SharedMCPPool:
    """共享MCP资源池"""
    
    def __init__(self):
        self.connection_pools: Dict[str, MCPConnectionPool] = {}
        self.load_balancer = MCPLoadBalancer()
        self.health_monitor = MCPHealthMonitor()
    
    async def add_server(self, server_info: MCPServerInfo):
        """添加MCP服务器到资源池"""
        pool = MCPConnectionPool(server_info)
        await pool.initialize()
        
        self.connection_pools[server_info.name] = pool
        await self.health_monitor.add_server(server_info)
        
        logger.info(f"Added MCP server to pool: {server_info.name}")
    
    async def call_tool(self, 
                       server_name: str, 
                       tool_name: str, 
                       parameters: Dict[str, Any],
                       timeout: int = 30) -> Any:
        """调用工具"""
        if server_name not in self.connection_pools:
            raise ValueError(f"Server not found in pool: {server_name}")
        
        pool = self.connection_pools[server_name]
        connection = await pool.get_connection()
        
        try:
            # 执行工具调用
            result = await connection.call_tool(tool_name, parameters, timeout)
            return result
            
        finally:
            # 归还连接
            await pool.return_connection(connection)
    
    async def call_tool_with_load_balancing(self, 
                                          tool_name: str,
                                          parameters: Dict[str, Any],
                                          preferred_servers: List[str] = None) -> Any:
        """使用负载均衡调用工具"""
        # 选择最优服务器
        server_name = await self.load_balancer.select_server(
            tool_name, preferred_servers, self.connection_pools.keys()
        )
        
        return await self.call_tool(server_name, tool_name, parameters)
```

### 5.2 负载均衡器
```python
class MCPLoadBalancer:
    """MCP负载均衡器"""
    
    def __init__(self):
        self.server_metrics: Dict[str, ServerMetrics] = {}
        self.balancing_strategy = "least_connections"
    
    async def select_server(self, 
                          tool_name: str,
                          preferred_servers: List[str] = None,
                          available_servers: List[str] = None) -> str:
        """选择最优服务器"""
        
        # 过滤可用服务器
        candidates = self._filter_candidate_servers(
            tool_name, preferred_servers, available_servers
        )
        
        if not candidates:
            raise ValueError(f"No servers available for tool: {tool_name}")
        
        # 根据策略选择服务器
        if self.balancing_strategy == "least_connections":
            return self._select_by_least_connections(candidates)
        elif self.balancing_strategy == "round_robin":
            return self._select_by_round_robin(candidates)
        elif self.balancing_strategy == "response_time":
            return self._select_by_response_time(candidates)
        else:
            return candidates[0]  # 默认选择第一个
    
    def _select_by_least_connections(self, candidates: List[str]) -> str:
        """基于最少连接数选择"""
        min_connections = float('inf')
        selected_server = candidates[0]
        
        for server in candidates:
            metrics = self.server_metrics.get(server)
            if metrics and metrics.active_connections < min_connections:
                min_connections = metrics.active_connections
                selected_server = server
        
        return selected_server
    
    def _select_by_response_time(self, candidates: List[str]) -> str:
        """基于响应时间选择"""
        min_response_time = float('inf')
        selected_server = candidates[0]
        
        for server in candidates:
            metrics = self.server_metrics.get(server)
            if metrics and metrics.avg_response_time < min_response_time:
                min_response_time = metrics.avg_response_time
                selected_server = server
        
        return selected_server
    
    async def update_server_metrics(self, server_name: str, metrics: 'ServerMetrics'):
        """更新服务器指标"""
        self.server_metrics[server_name] = metrics
```

## 6. 用户提问MCP

### 6.1 用户提问服务设计
```python
class UserQuestionMCP:
    """用户提问MCP服务"""
    
    def __init__(self):
        self.question_router = QuestionRouter()
        self.session_manager = SessionManager()
        self.response_formatter = ResponseFormatter()
        self.active_questions: Dict[str, PendingQuestion] = {}
    
    async def ask_user(self, 
                      question: str,
                      options: List[str] = None,
                      question_type: str = "text",
                      timeout: int = 300,
                      context: Dict[str, Any] = None) -> str:
        """向用户提问"""
        
        question_id = f"q_{uuid4().hex[:8]}"
        
        # 创建问题对象
        pending_question = PendingQuestion(
            id=question_id,
            question=question,
            options=options,
            question_type=question_type,
            created_at=datetime.now(),
            timeout=timeout,
            context=context or {}
        )
        
        self.active_questions[question_id] = pending_question
        
        try:
            # 路由问题到适当的UI界面
            await self.question_router.route_question(pending_question)
            
            # 等待用户回答
            answer = await self._wait_for_answer(question_id, timeout)
            
            # 格式化响应
            formatted_response = await self.response_formatter.format_response(
                answer, pending_question
            )
            
            return formatted_response
            
        finally:
            # 清理问题记录
            if question_id in self.active_questions:
                del self.active_questions[question_id]
    
    async def _wait_for_answer(self, question_id: str, timeout: int) -> str:
        """等待用户回答"""
        start_time = datetime.now()
        
        while True:
            question = self.active_questions.get(question_id)
            if not question:
                raise ValueError(f"Question not found: {question_id}")
            
            if question.answer is not None:
                return question.answer
            
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(f"User question timeout: {question_id}")
            
            await asyncio.sleep(0.5)  # 轮询间隔
    
    async def answer_question(self, question_id: str, answer: str) -> bool:
        """回答问题（由UI调用）"""
        if question_id in self.active_questions:
            question = self.active_questions[question_id]
            question.answer = answer
            question.answered_at = datetime.now()
            
            # 验证答案格式
            if question.options and answer not in question.options:
                return False
            
            return True
        
        return False
    
    async def ask_confirmation(self, message: str, context: Dict[str, Any] = None) -> bool:
        """请求用户确认"""
        answer = await self.ask_user(
            question=f"{message}\n\n请确认：",
            options=["是", "否", "取消"],
            question_type="confirmation",
            context=context
        )
        
        return answer in ["是", "确认", "yes", "y"]
    
    async def ask_choice(self, 
                        question: str, 
                        choices: List[str],
                        context: Dict[str, Any] = None) -> str:
        """请求用户选择"""
        return await self.ask_user(
            question=question,
            options=choices,
            question_type="choice",
            context=context
        )
    
    async def ask_recovery_action(self, 
                                failed_role: str,
                                error: Exception,
                                recovery_options: List['RecoveryOption']) -> str:
        """请求错误恢复操作"""
        
        question = f"""
角色 "{failed_role}" 执行失败：
错误信息：{str(error)}

请选择恢复操作：
        """
        
        options = [option.description for option in recovery_options]
        
        choice = await self.ask_choice(
            question=question,
            choices=options,
            context={
                "failed_role": failed_role,
                "error_type": type(error).__name__,
                "recovery_context": True
            }
        )
        
        # 返回对应的恢复选项ID
        for option in recovery_options:
            if option.description == choice:
                return option.action_id
        
        return recovery_options[0].action_id  # 默认第一个选项
```

### 6.2 会话管理器
```python
class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.user_sessions: Dict[str, UserSession] = {}
        self.session_timeout = 3600  # 1小时
    
    async def create_session(self, user_id: str, workflow_id: str) -> str:
        """创建用户会话"""
        session_id = f"session_{uuid4().hex[:8]}"
        
        session = UserSession(
            id=session_id,
            user_id=user_id,
            workflow_id=workflow_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            context={}
        )
        
        self.user_sessions[session_id] = session
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话"""
        session = self.user_sessions.get(session_id)
        
        if session:
            # 检查会话是否过期
            elapsed = (datetime.now() - session.last_activity).total_seconds()
            if elapsed > self.session_timeout:
                await self.cleanup_session(session_id)
                return None
            
            # 更新最后活动时间
            session.last_activity = datetime.now()
        
        return session
    
    async def update_session_context(self, 
                                   session_id: str, 
                                   context_update: Dict[str, Any]) -> bool:
        """更新会话上下文"""
        session = await self.get_session(session_id)
        if session:
            session.context.update(context_update)
            return True
        return False
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.user_sessions.items():
            elapsed = (current_time - session.last_activity).total_seconds()
            if elapsed > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
    
    async def cleanup_session(self, session_id: str):
        """清理会话"""
        if session_id in self.user_sessions:
            del self.user_sessions[session_id]
```

## 7. 工具访问控制器

### 7.1 权限管理器
```python
class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.role_permissions = self._load_role_permissions()
        self.tool_security_levels = self._load_tool_security_levels()
    
    def _load_role_permissions(self) -> Dict[str, List[str]]:
        """加载角色权限配置"""
        return {
            "方案规划师": [
                "user_interaction:*",
                "web_services:search",
                "web_services:documentation",
                "data_processing:analysis"
            ],
            "编码专家": [
                "file_operations:*",
                "development_tools:*",
                "web_services:api_call",
                "system_utilities:*"
            ],
            "测试工程师": [
                "file_operations:read",
                "development_tools:test",
                "development_tools:build",
                "system_utilities:monitor"
            ],
            "代码审查员": [
                "file_operations:read",
                "development_tools:analysis",
                "web_services:documentation",
                "data_processing:analysis"
            ]
        }
    
    def _load_tool_security_levels(self) -> Dict[str, str]:
        """加载工具安全级别"""
        return {
            "file_operations:write": "high",
            "file_operations:delete": "critical", 
            "system_utilities:execute": "high",
            "web_services:api_call": "medium",
            "user_interaction:ask": "low",
            "development_tools:test": "medium"
        }
    
    async def check_permission(self, 
                             role: str, 
                             tool_category: str, 
                             tool_name: str) -> bool:
        """检查角色是否有权限使用工具"""
        
        role_perms = self.role_permissions.get(role, [])
        
        # 检查具体工具权限
        specific_perm = f"{tool_category}:{tool_name}"
        if specific_perm in role_perms:
            return True
        
        # 检查类别通配符权限
        category_perm = f"{tool_category}:*"
        if category_perm in role_perms:
            return True
        
        # 检查全局权限
        if "*:*" in role_perms:
            return True
        
        return False
    
    async def validate_tool_access(self, 
                                 role: str,
                                 tool_info: MCPToolInfo,
                                 parameters: Dict[str, Any]) -> ValidationResult:
        """验证工具访问权限"""
        
        # 基础权限检查
        tool_category = self._get_tool_category(tool_info)
        has_permission = await self.check_permission(role, tool_category, tool_info.name)
        
        if not has_permission:
            return ValidationResult(
                is_valid=False,
                error_message=f"Role {role} does not have permission to use {tool_info.name}"
            )
        
        # 安全级别检查
        security_level = self.tool_security_levels.get(f"{tool_category}:{tool_info.name}", "low")
        
        if security_level == "critical":
            # 关键工具需要额外验证
            additional_validation = await self._validate_critical_tool_usage(
                role, tool_info, parameters
            )
            if not additional_validation.is_valid:
                return additional_validation
        
        return ValidationResult(is_valid=True)
```

### 7.2 速率限制器
```python
class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        self.rate_limits = {
            "user_interaction": {"requests": 10, "window": 60},  # 10次/分钟
            "web_services": {"requests": 100, "window": 60},     # 100次/分钟
            "file_operations": {"requests": 50, "window": 60},   # 50次/分钟
            "default": {"requests": 30, "window": 60}            # 默认30次/分钟
        }
        self.usage_tracking: Dict[str, List[datetime]] = {}
    
    async def check_rate_limit(self, 
                             role: str,
                             tool_category: str,
                             tool_name: str) -> bool:
        """检查速率限制"""
        
        # 获取限制配置
        limit_config = self.rate_limits.get(tool_category, self.rate_limits["default"])
        max_requests = limit_config["requests"]
        time_window = limit_config["window"]
        
        # 生成跟踪键
        tracking_key = f"{role}:{tool_category}:{tool_name}"
        
        # 清理过期记录
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=time_window)
        
        if tracking_key in self.usage_tracking:
            self.usage_tracking[tracking_key] = [
                timestamp for timestamp in self.usage_tracking[tracking_key]
                if timestamp > cutoff_time
            ]
        else:
            self.usage_tracking[tracking_key] = []
        
        # 检查是否超出限制
        current_usage = len(self.usage_tracking[tracking_key])
        
        if current_usage >= max_requests:
            return False
        
        # 记录本次使用
        self.usage_tracking[tracking_key].append(current_time)
        return True
    
    async def get_remaining_quota(self, 
                                role: str,
                                tool_category: str,
                                tool_name: str) -> Dict[str, Any]:
        """获取剩余配额"""
        
        limit_config = self.rate_limits.get(tool_category, self.rate_limits["default"])
        max_requests = limit_config["requests"]
        time_window = limit_config["window"]
        
        tracking_key = f"{role}:{tool_category}:{tool_name}"
        
        # 计算当前使用量
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=time_window)
        
        current_usage = len([
            timestamp for timestamp in self.usage_tracking.get(tracking_key, [])
            if timestamp > cutoff_time
        ])
        
        remaining = max(0, max_requests - current_usage)
        
        # 计算重置时间
        if tracking_key in self.usage_tracking and self.usage_tracking[tracking_key]:
            oldest_request = min(self.usage_tracking[tracking_key])
            reset_time = oldest_request + timedelta(seconds=time_window)
        else:
            reset_time = current_time + timedelta(seconds=time_window)
        
        return {
            "remaining": remaining,
            "total": max_requests,
            "reset_time": reset_time.isoformat(),
            "window_seconds": time_window
        }
```

## 8. 工具执行引擎

### 8.1 参数验证器
```python
class ParameterValidator:
    """参数验证器"""
    
    def __init__(self):
        self.schema_validator = JSONSchemaValidator()
    
    async def validate_parameters(self, 
                                tool_info: MCPToolInfo,
                                parameters: Dict[str, Any]) -> ValidationResult:
        """验证工具参数"""
        
        try:
            # JSON Schema验证
            if tool_info.input_schema:
                schema_result = await self.schema_validator.validate(
                    parameters, tool_info.input_schema
                )
                if not schema_result.is_valid:
                    return schema_result
            
            # 业务逻辑验证
            business_result = await self._validate_business_logic(tool_info, parameters)
            if not business_result.is_valid:
                return business_result
            
            # 安全性验证
            security_result = await self._validate_security(tool_info, parameters)
            if not security_result.is_valid:
                return security_result
            
            return ValidationResult(is_valid=True)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Parameter validation error: {str(e)}"
            )
    
    async def _validate_business_logic(self, 
                                     tool_info: MCPToolInfo,
                                     parameters: Dict[str, Any]) -> ValidationResult:
        """业务逻辑验证"""
        
        # 文件路径安全检查
        if "file_path" in parameters:
            file_path = parameters["file_path"]
            if not self._is_safe_file_path(file_path):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsafe file path: {file_path}"
                )
        
        # URL安全检查
        if "url" in parameters:
            url = parameters["url"]
            if not self._is_safe_url(url):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsafe URL: {url}"
                )
        
        return ValidationResult(is_valid=True)
    
    def _is_safe_file_path(self, file_path: str) -> bool:
        """检查文件路径安全性"""
        # 禁止路径遍历
        if ".." in file_path or file_path.startswith("/"):
            return False
        
        # 禁止访问系统敏感目录
        sensitive_dirs = ["/etc", "/sys", "/proc", "/dev"]
        for sensitive_dir in sensitive_dirs:
            if file_path.startswith(sensitive_dir):
                return False
        
        return True
    
    def _is_safe_url(self, url: str) -> bool:
        """检查URL安全性"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        
        # 只允许HTTP和HTTPS
        if parsed.scheme not in ["http", "https"]:
            return False
        
        # 禁止访问本地地址
        if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
            return False
        
        return True
```

### 8.2 执行协调器
```python
class ToolExecutionCoordinator:
    """工具执行协调器"""
    
    def __init__(self, 
                 shared_pool: SharedMCPPool,
                 permission_manager: PermissionManager,
                 rate_limiter: RateLimiter,
                 parameter_validator: ParameterValidator):
        self.shared_pool = shared_pool
        self.permission_manager = permission_manager
        self.rate_limiter = rate_limiter
        self.parameter_validator = parameter_validator
        self.execution_history = []
    
    async def execute_tool(self, 
                         role: str,
                         tool_info: MCPToolInfo,
                         parameters: Dict[str, Any],
                         context: Dict[str, Any] = None) -> ToolExecutionResult:
        """执行工具调用"""
        
        execution_id = f"exec_{uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # 1. 权限检查
            permission_result = await self.permission_manager.validate_tool_access(
                role, tool_info, parameters
            )
            if not permission_result.is_valid:
                return ToolExecutionResult(
                    execution_id=execution_id,
                    success=False,
                    error=permission_result.error_message,
                    execution_time=0
                )
            
            # 2. 速率限制检查
            tool_category = self._get_tool_category(tool_info)
            rate_ok = await self.rate_limiter.check_rate_limit(
                role, tool_category, tool_info.name
            )
            if not rate_ok:
                return ToolExecutionResult(
                    execution_id=execution_id,
                    success=False,
                    error="Rate limit exceeded",
                    execution_time=0
                )
            
            # 3. 参数验证
            param_result = await self.parameter_validator.validate_parameters(
                tool_info, parameters
            )
            if not param_result.is_valid:
                return ToolExecutionResult(
                    execution_id=execution_id,
                    success=False,
                    error=param_result.error_message,
                    execution_time=0
                )
            
            # 4. 执行工具调用
            result = await self.shared_pool.call_tool(
                tool_info.server_name,
                tool_info.name,
                parameters
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 5. 处理结果
            processed_result = await self._process_tool_result(
                tool_info, result, context
            )
            
            # 6. 记录执行历史
            await self._record_execution(
                execution_id, role, tool_info, parameters, processed_result, execution_time
            )
            
            return ToolExecutionResult(
                execution_id=execution_id,
                success=True,
                result=processed_result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_result = ToolExecutionResult(
                execution_id=execution_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
            # 记录错误
            await self._record_execution(
                execution_id, role, tool_info, parameters, None, execution_time, str(e)
            )
            
            return error_result
```

## 9. 监控和优化

### 9.1 性能监控
```python
class MCPPerformanceMonitor:
    """MCP性能监控"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_analyzer = PerformanceAnalyzer()
    
    async def monitor_tool_performance(self):
        """监控工具性能"""
        while True:
            try:
                # 收集性能指标
                metrics = await self.metrics_collector.collect_mcp_metrics()
                
                # 分析性能趋势
                analysis = await self.performance_analyzer.analyze_trends(metrics)
                
                # 检测异常
                anomalies = await self._detect_performance_anomalies(metrics)
                
                if anomalies:
                    await self._handle_performance_issues(anomalies)
                
                await asyncio.sleep(30)  # 30秒监控间隔
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)  # 错误时延长间隔
```

## 10. 总结

MCP工具集成架构通过以下核心能力，为UAgent系统提供了强大的工具支持：

1. **标准化工具接入**: 基于MCP协议的统一工具接口
2. **高效资源管理**: 共享连接池和智能负载均衡
3. **完善的权限控制**: 角色权限管理和安全验证
4. **智能用户交互**: 用户提问MCP和会话管理
5. **全面的监控优化**: 性能监控和自动优化

该架构确保了工具的高效使用、安全访问和良好的用户体验，是UAgent系统功能实现的重要基础。
