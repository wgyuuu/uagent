# UAgent Tool Layer 详细设计

## 1. 概述

Tool Layer是UAgent系统的工具支撑层，负责提供三种类型的MCP服务：
1. **配置式MCP Server** - 通过配置文件动态添加的外部HTTP MCP服务
2. **内置MCP Server** - 直接代码实现的函数调用形式MCP服务
3. **用户互动MCP** - 作为系统核心功能的用户对话能力

该设计确保系统具有高度的灵活性和扩展性，同时将用户互动作为核心功能，实现真正的智能化协作。

## 2. 设计理念

### 2.1 配置化优先
- **零代码扩展**: 通过配置文件即可添加新的MCP服务
- **动态加载**: 支持运行时动态加载和配置MCP服务
- **版本管理**: 支持MCP服务的版本控制和兼容性管理

### 2.2 内置服务基础
- **常用功能**: 提供文件操作、代码分析、系统管理等基础功能
- **性能优化**: 直接代码实现，避免网络开销
- **安全可控**: 内置服务经过严格测试，安全可靠

### 2.3 用户互动核心
- **对话优先**: 用户对话是系统的核心功能，不是辅助功能
- **实时响应**: 支持实时的用户问答和确认
- **上下文感知**: 维护用户交互的上下文和状态

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Layer Architecture                  │
├─────────────────────────────────────────────────────────────┤
│  Tool Registry (工具注册表)                                │
│  ├── Configurable MCP Manager (配置式MCP管理器)            │
│  ├── Built-in MCP Manager (内置MCP管理器)                  │
│  └── User Interaction MCP Manager (用户互动MCP管理器)      │
├─────────────────────────────────────────────────────────────┤
│  MCP Service Providers (MCP服务提供者)                     │
│  ├── HTTP MCP Clients (HTTP MCP客户端)                    │
│  ├── Built-in MCP Services (内置MCP服务)                   │
│  └── User Interaction Services (用户互动服务)              │
├─────────────────────────────────────────────────────────────┤
│  Service Discovery & Health Check (服务发现与健康检查)     │
│  ├── Dynamic Service Discovery (动态服务发现)              │
│  ├── Health Monitoring (健康监控)                          │
│  └── Failover Management (故障转移管理)                    │
├─────────────────────────────────────────────────────────────┤
│  Tool Access Control (工具访问控制)                        │
│  ├── Role-based Permission (基于角色的权限控制)            │
│  ├── Rate Limiting (速率限制)                              │
│  └── Audit Logging (审计日志)                              │
└─────────────────────────────────────────────────────────────┘
```

## 4. 配置式MCP Server

### 4.1 配置文件格式
```yaml
# config/mcp_servers.yaml
mcp_servers:
  # 外部HTTP MCP服务
  external_services:
    - name: "github_tools"
      url: "https://api.github.com/mcp"
      version: "1.0.0"
      description: "GitHub相关工具服务"
      authentication:
        type: "bearer_token"
        token_env: "GITHUB_TOKEN"
      health_check:
        endpoint: "/health"
        interval: 30
        timeout: 5
      tools:
        - name: "create_repository"
          description: "创建GitHub仓库"
          input_schema:
            type: "object"
            properties:
              name: {"type": "string"}
              description: {"type": "string"}
              private: {"type": "boolean"}
        - name: "search_code"
          description: "搜索GitHub代码"
          input_schema:
            type: "object"
            properties:
              query: {"type": "string"}
              language: {"type": "string"}
    
    - name: "openai_tools"
      url: "https://api.openai.com/mcp"
      version: "1.0.0"
      description: "OpenAI API工具服务"
      authentication:
        type: "api_key"
        key_env: "OPENAI_API_KEY"
      rate_limit: 100  # 每分钟请求数
      tools:
        - name: "generate_text"
          description: "生成文本内容"
        - name: "analyze_sentiment"
          description: "情感分析"
  
  # 本地MCP服务
  local_services:
    - name: "file_manager"
      socket_path: "/tmp/file_manager.sock"
      description: "本地文件管理服务"
      tools:
        - name: "read_file"
        - name: "write_file"
        - name: "list_directory"
```

### 4.2 配置式MCP管理器
```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml
import aiohttp
import asyncio
from pathlib import Path

@dataclass
class MCPConfig:
    """MCP配置信息"""
    name: str
    url: str
    version: str
    description: str
    authentication: Optional[Dict[str, Any]] = None
    health_check: Optional[Dict[str, Any]] = None
    tools: List[Dict[str, Any]] = None
    rate_limit: Optional[int] = None
    metadata: Dict[str, Any] = None

class ConfigurableMCPServerManager:
    """配置式MCP服务器管理器"""
    
    def __init__(self, config_path: str = "config/mcp_servers.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.active_servers: Dict[str, 'MCPClient'] = {}
        self.health_checkers: Dict[str, asyncio.Task] = {}
        
    async def load_configuration(self) -> bool:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"MCP配置文件不存在: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 初始化外部服务
            await self._initialize_external_services()
            
            # 初始化本地服务
            await self._initialize_local_services()
            
            return True
            
        except Exception as e:
            logger.error(f"加载MCP配置失败: {e}")
            return False
    
    async def _initialize_external_services(self):
        """初始化外部HTTP MCP服务"""
        external_services = self.config.get("external_services", [])
        
        for service_config in external_services:
            try:
                mcp_config = MCPConfig(**service_config)
                client = await self._create_http_mcp_client(mcp_config)
                
                if client:
                    self.active_servers[mcp_config.name] = client
                    await self._start_health_checker(mcp_config.name, mcp_config)
                    
                    logger.info(f"成功初始化外部MCP服务: {mcp_config.name}")
                    
            except Exception as e:
                logger.error(f"初始化外部MCP服务失败 {service_config.get('name', 'unknown')}: {e}")
    
    async def _create_http_mcp_client(self, config: MCPConfig) -> Optional['MCPClient']:
        """创建HTTP MCP客户端"""
        try:
            # 处理认证
            headers = await self._build_auth_headers(config.authentication)
            
            # 创建客户端
            client = HTTPMCPClient(
                name=config.name,
                base_url=config.url,
                headers=headers,
                rate_limit=config.rate_limit
            )
            
            # 验证连接
            if await client.health_check():
                return client
            else:
                logger.warning(f"MCP服务健康检查失败: {config.name}")
                return None
                
        except Exception as e:
            logger.error(f"创建HTTP MCP客户端失败: {e}")
            return None
    
    async def _build_auth_headers(self, auth_config: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """构建认证头"""
        headers = {}
        
        if not auth_config:
            return headers
        
        auth_type = auth_config.get("type")
        
        if auth_type == "bearer_token":
            token = os.getenv(auth_config.get("token_env", ""))
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            api_key = os.getenv(auth_config.get("key_env", ""))
            if api_key:
                headers["X-API-Key"] = api_key
        
        elif auth_type == "basic":
            username = os.getenv(auth_config.get("username_env", ""))
            password = os.getenv(auth_config.get("password_env", ""))
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def _start_health_checker(self, server_name: str, config: MCPConfig):
        """启动健康检查器"""
        if not config.health_check:
            return
        
        async def health_check_loop():
            while True:
                try:
                    client = self.active_servers.get(server_name)
                    if client:
                        is_healthy = await client.health_check()
                        if not is_healthy:
                            logger.warning(f"MCP服务不健康: {server_name}")
                            # 可以触发故障转移或重试逻辑
                    
                    await asyncio.sleep(config.health_check.get("interval", 30))
                    
                except Exception as e:
                    logger.error(f"健康检查失败 {server_name}: {e}")
                    await asyncio.sleep(60)  # 错误时延长间隔
        
        task = asyncio.create_task(health_check_loop())
        self.health_checkers[server_name] = task
    
    async def reload_configuration(self) -> bool:
        """重新加载配置"""
        # 停止现有服务
        await self._stop_all_services()
        
        # 重新加载配置
        return await self.load_configuration()
    
    async def _stop_all_services(self):
        """停止所有服务"""
        # 停止健康检查器
        for task in self.health_checkers.values():
            task.cancel()
        
        # 关闭客户端连接
        for client in self.active_servers.values():
            await client.close()
        
        self.active_servers.clear()
        self.health_checkers.clear()
```

### 4.3 HTTP MCP客户端
```python
class HTTPMCPClient:
    """HTTP MCP客户端"""
    
    def __init__(self, 
                 name: str,
                 base_url: str,
                 headers: Dict[str, str] = None,
                 rate_limit: Optional[int] = None):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.rate_limit = rate_limit
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit else None
    
    async def connect(self):
        """建立连接"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                base_url=self.base_url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def call_tool(self, 
                       tool_name: str, 
                       parameters: Dict[str, Any],
                       timeout: int = 30) -> Any:
        """调用工具"""
        await self.connect()
        
        # 速率限制检查
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        
        try:
            # 构建请求
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            
            async with self.session.post(
                "/tools/call",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get("result")
                else:
                    error_text = await response.text()
                    raise MCPCallError(f"HTTP {response.status}: {error_text}")
                    
        except asyncio.TimeoutError:
            raise MCPCallError(f"调用超时: {tool_name}")
        except Exception as e:
            raise MCPCallError(f"调用失败: {e}")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.connect()
            
            health_endpoint = "/health"
            async with self.session.get(health_endpoint, timeout=5) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        try:
            await self.connect()
            
            async with self.session.get("/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("tools", [])
                else:
                    return []
                    
        except Exception:
            return []
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
```

## 5. 内置MCP Server

### 5.1 内置服务管理器
```python
class BuiltInMCPServerManager:
    """内置MCP服务器管理器"""
    
    def __init__(self):
        self.built_in_services: Dict[str, 'BuiltInMCPService'] = {}
        self.service_registry: Dict[str, Dict[str, Any]] = {}
        
        # 注册内置服务
        self._register_built_in_services()
    
    def _register_built_in_services(self):
        """注册内置服务"""
        # 文件操作服务
        self._register_service(FileOperationsService())
        
        # 代码分析服务
        self._register_service(CodeAnalysisService())
        
        # 系统管理服务
        self._register_service(SystemManagementService())
        
        # 数据查询服务
        self._register_service(DataQueryService())
        
        # 网络工具服务
        self._register_service(NetworkToolsService())
    
    def _register_service(self, service: 'BuiltInMCPService'):
        """注册单个服务"""
        service_name = service.get_service_name()
        self.built_in_services[service_name] = service
        
        # 注册工具信息
        tools = service.get_available_tools()
        self.service_registry[service_name] = {
            "description": service.get_service_description(),
            "tools": tools,
            "service": service
        }
        
        logger.info(f"注册内置MCP服务: {service_name} ({len(tools)} 个工具)")
    
    async def call_tool(self, 
                       service_name: str,
                       tool_name: str,
                       parameters: Dict[str, Any]) -> Any:
        """调用内置工具"""
        if service_name not in self.built_in_services:
            raise ValueError(f"内置服务不存在: {service_name}")
        
        service = self.built_in_services[service_name]
        return await service.call_tool(tool_name, parameters)
    
    def get_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有可用工具"""
        tools = {}
        for service_name, service_info in self.service_registry.items():
            tools[service_name] = service_info["tools"]
        return tools
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务信息"""
        return self.service_registry.get(service_name)
```

### 5.2 内置服务基类
```python
from abc import ABC, abstractmethod

class BuiltInMCPService(ABC):
    """内置MCP服务基类"""
    
    @abstractmethod
    def get_service_name(self) -> str:
        """获取服务名称"""
        pass
    
    @abstractmethod
    def get_service_description(self) -> str:
        """获取服务描述"""
        pass
    
    @abstractmethod
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """调用工具"""
        pass
    
    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        # 基础参数验证逻辑
        return True
```

### 5.3 文件操作服务示例
```python
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

class FileOperationsService(BuiltInMCPService):
    """文件操作服务"""
    
    def get_service_name(self) -> str:
        return "file_operations"
    
    def get_service_description(self) -> str:
        return "提供文件系统操作功能，包括读写、复制、移动等"
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "读取文件内容",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "文件路径"},
                        "encoding": {"type": "string", "default": "utf-8"},
                        "max_size": {"type": "integer", "default": 1048576}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "写入文件内容",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"},
                        "encoding": {"type": "string", "default": "utf-8"},
                        "mode": {"type": "string", "enum": ["w", "a"], "default": "w"}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": "列出目录内容",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "目录路径"},
                        "include_hidden": {"type": "boolean", "default": False},
                        "file_types": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["directory_path"]
                }
            },
            {
                "name": "copy_file",
                "description": "复制文件",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "源文件路径"},
                        "destination_path": {"type": "string", "description": "目标文件路径"},
                        "overwrite": {"type": "boolean", "default": False}
                    },
                    "required": ["source_path", "destination_path"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self._validate_parameters(tool_name, parameters):
            raise ValueError(f"参数验证失败: {tool_name}")
        
        if tool_name == "read_file":
            return await self._read_file(parameters)
        elif tool_name == "write_file":
            return await self._write_file(parameters)
        elif tool_name == "list_directory":
            return await self._list_directory(parameters)
        elif tool_name == "copy_file":
            return await self._copy_file(parameters)
        else:
            raise ValueError(f"未知工具: {tool_name}")
    
    async def _read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件"""
        file_path = parameters["file_path"]
        encoding = parameters.get("encoding", "utf-8")
        max_size = parameters.get("max_size", 1048576)  # 1MB
        
        try:
            file_path = Path(file_path)
            
            # 安全检查
            if not self._is_safe_path(file_path):
                raise ValueError(f"不安全的文件路径: {file_path}")
            
            # 检查文件大小
            if file_path.stat().st_size > max_size:
                raise ValueError(f"文件过大: {file_path.stat().st_size} bytes")
            
            # 读取文件
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "file_size": len(content),
                "encoding": encoding
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件"""
        file_path = parameters["file_path"]
        content = parameters["content"]
        encoding = parameters.get("encoding", "utf-8")
        mode = parameters.get("mode", "w")
        
        try:
            file_path = Path(file_path)
            
            # 安全检查
            if not self._is_safe_path(file_path):
                raise ValueError(f"不安全的文件路径: {file_path}")
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "bytes_written": len(content.encode(encoding))
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _is_safe_path(self, file_path: Path) -> bool:
        """检查路径安全性"""
        # 禁止路径遍历
        if ".." in str(file_path):
            return False
        
        # 禁止访问系统敏感目录
        sensitive_dirs = ["/etc", "/sys", "/proc", "/dev", "/boot"]
        for sensitive_dir in sensitive_dirs:
            if str(file_path).startswith(sensitive_dir):
                return False
        
        return True
```

## 6. 用户互动MCP

### 6.1 用户互动服务管理器
```python
class UserInteractionMCPService(BuiltInMCPService):
    """用户互动MCP服务"""
    
    def __init__(self):
        self.active_sessions: Dict[str, 'UserSession'] = {}
        self.question_queue: asyncio.Queue = asyncio.Queue()
        self.response_handlers: Dict[str, asyncio.Future] = {}
        
    def get_service_name(self) -> str:
        return "user_interaction"
    
    def get_service_description(self) -> str:
        return "用户互动核心服务，支持实时问答、确认、选择等交互功能"
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "ask_question",
                "description": "向用户提问",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "问题内容"},
                        "question_type": {"type": "string", "enum": ["text", "choice", "confirmation"], "default": "text"},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "选项列表（用于choice类型）"},
                        "timeout": {"type": "integer", "default": 300, "description": "超时时间（秒）"},
                        "context": {"type": "object", "description": "上下文信息"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "get_user_input",
                "description": "获取用户输入",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "提示信息"},
                        "input_type": {"type": "string", "enum": ["text", "number", "file"], "default": "text"},
                        "validation_rules": {"type": "object", "description": "验证规则"},
                        "default_value": {"type": "string", "description": "默认值"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "confirm_action",
                "description": "确认用户操作",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_description": {"type": "string", "description": "操作描述"},
                        "risk_level": {"type": "string", "enum": ["low", "medium", "high"], "default": "low"},
                        "alternatives": {"type": "array", "items": {"type": "string"}, "description": "替代方案"}
                    },
                    "required": ["action_description"]
                }
            },
            {
                "name": "get_user_preference",
                "description": "获取用户偏好",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "preference_type": {"type": "string", "description": "偏好类型"},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "allow_custom": {"type": "boolean", "default": False}
                    },
                    "required": ["preference_type", "options"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """调用工具"""
        if tool_name == "ask_question":
            return await self._ask_question(parameters)
        elif tool_name == "get_user_input":
            return await self._get_user_input(parameters)
        elif tool_name == "confirm_action":
            return await self._confirm_action(parameters)
        elif tool_name == "get_user_preference":
            return await self._get_user_preference(parameters)
        else:
            raise ValueError(f"未知工具: {tool_name}")
    
    async def _ask_question(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """向用户提问"""
        question = parameters["question"]
        question_type = parameters.get("question_type", "text")
        options = parameters.get("options", [])
        timeout = parameters.get("timeout", 300)
        context = parameters.get("context", {})
        
        # 生成问题ID
        question_id = f"q_{uuid4().hex[:8]}"
        
        # 创建问题对象
        user_question = UserQuestion(
            id=question_id,
            question=question,
            question_type=question_type,
            options=options,
            timeout=timeout,
            context=context,
            created_at=datetime.now()
        )
        
        # 创建响应处理器
        response_future = asyncio.Future()
        self.response_handlers[question_id] = response_future
        
        try:
            # 发送问题到UI
            await self._send_question_to_ui(user_question)
            
            # 等待用户回答
            response = await asyncio.wait_for(response_future, timeout=timeout)
            
            return {
                "success": True,
                "question_id": question_id,
                "response": response,
                "response_time": (datetime.now() - user_question.created_at).total_seconds()
            }
            
        except asyncio.TimeoutError:
            # 超时处理
            response_future.cancel()
            return {
                "success": False,
                "error": "用户回答超时",
                "question_id": question_id
            }
        
        finally:
            # 清理资源
            if question_id in self.response_handlers:
                del self.response_handlers[question_id]
    
    async def _send_question_to_ui(self, question: 'UserQuestion'):
        """发送问题到UI界面"""
        # 这里应该实现具体的UI通知逻辑
        # 可以是WebSocket、HTTP API、消息队列等
        
        # 示例：通过消息队列发送
        message = {
            "type": "user_question",
            "question": question.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送到UI消息队列
        await self._send_to_ui_queue(message)
    
    async def handle_user_response(self, question_id: str, response: str) -> bool:
        """处理用户回答"""
        if question_id in self.response_handlers:
            future = self.response_handlers[question_id]
            if not future.done():
                future.set_result(response)
                return True
        
        return False
    
    async def _send_to_ui_queue(self, message: Dict[str, Any]):
        """发送消息到UI队列"""
        # 实现具体的UI通知逻辑
        # 这里可以集成WebSocket、Server-Sent Events等
        pass
```

### 6.2 用户会话管理
```python
@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: str
    workflow_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    question_history: List[Dict[str, Any]] = field(default_factory=list)

class UserSessionManager:
    """用户会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.session_timeout = 3600  # 1小时
    
    async def create_session(self, user_id: str, workflow_id: Optional[str] = None) -> str:
        """创建用户会话"""
        session_id = f"session_{uuid4().hex[:8]}"
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            workflow_id=workflow_id
        )
        
        self.sessions[session_id] = session
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话"""
        session = self.sessions.get(session_id)
        
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
    
    async def add_question_to_history(self, 
                                    session_id: str, 
                                    question: Dict[str, Any]):
        """添加问题到历史记录"""
        session = await self.get_session(session_id)
        if session:
            session.question_history.append({
                "timestamp": datetime.now().isoformat(),
                "question": question
            })
            
            # 保持历史记录在合理范围内
            if len(session.question_history) > 100:
                session.question_history = session.question_history[-50:]
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            elapsed = (current_time - session.last_activity).total_seconds()
            if elapsed > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
    
    async def cleanup_session(self, session_id: str):
        """清理会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
```

## 7. 工具访问控制

### 7.1 基于角色的权限管理
```python
class ToolAccessController:
    """工具访问控制器"""
    
    def __init__(self):
        self.role_permissions = self._load_role_permissions()
        self.tool_security_levels = self._load_tool_security_levels()
        self.audit_logger = AuditLogger()
    
    def _load_role_permissions(self) -> Dict[str, List[str]]:
        """加载角色权限配置"""
        return {
            "方案规划师": [
                "user_interaction:*",
                "file_operations:read",
                "web_services:search",
                "data_processing:analysis"
            ],
            "编码专家": [
                "file_operations:*",
                "code_analysis:*",
                "git_operations:*",
                "user_interaction:ask_question"
            ],
            "测试工程师": [
                "file_operations:read",
                "code_analysis:test",
                "system_management:monitor",
                "user_interaction:get_user_input"
            ],
            "代码审查员": [
                "file_operations:read",
                "code_analysis:review",
                "security_analysis:*",
                "user_interaction:confirm_action"
            ]
        }
    
    async def check_permission(self, 
                             role: str, 
                             service_name: str, 
                             tool_name: str) -> bool:
        """检查权限"""
        role_perms = self.role_permissions.get(role, [])
        
        # 检查具体工具权限
        specific_perm = f"{service_name}:{tool_name}"
        if specific_perm in role_perms:
            return True
        
        # 检查服务级权限
        service_perm = f"{service_name}:*"
        if service_perm in role_perms:
            return True
        
        # 检查全局权限
        if "*:*" in role_perms:
            return True
        
        return False
    
    async def validate_tool_access(self, 
                                 role: str,
                                 service_name: str,
                                 tool_name: str,
                                 parameters: Dict[str, Any]) -> ValidationResult:
        """验证工具访问"""
        
        # 基础权限检查
        has_permission = await self.check_permission(role, service_name, tool_name)
        
        if not has_permission:
            return ValidationResult(
                is_valid=False,
                error_message=f"角色 {role} 没有权限使用 {service_name}.{tool_name}"
            )
        
        # 安全检查
        security_result = await self._security_check(service_name, tool_name, parameters)
        if not security_result.is_valid:
            return security_result
        
        # 记录审计日志
        await self.audit_logger.log_tool_access(
            role=role,
            service_name=service_name,
            tool_name=tool_name,
            parameters=parameters,
            timestamp=datetime.now()
        )
        
        return ValidationResult(is_valid=True)
    
    async def _security_check(self, 
                            service_name: str,
                            tool_name: str,
                            parameters: Dict[str, Any]) -> ValidationResult:
        """安全检查"""
        
        # 文件路径安全检查
        if "file_path" in parameters:
            file_path = parameters["file_path"]
            if not self._is_safe_file_path(file_path):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"不安全的文件路径: {file_path}"
                )
        
        # URL安全检查
        if "url" in parameters:
            url = parameters["url"]
            if not self._is_safe_url(url):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"不安全的URL: {url}"
                )
        
        # 命令注入检查
        if "command" in parameters:
            command = parameters["command"]
            if not self._is_safe_command(command):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"不安全的命令: {command}"
                )
        
        return ValidationResult(is_valid=True)
```

## 8. 配置热重载

### 8.1 配置监控器
```python
class ConfigurationMonitor:
    """配置监控器"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.last_modified = 0
        self.file_watcher = None
        self.reload_callbacks: List[Callable] = []
    
    async def start_monitoring(self):
        """开始监控配置变化"""
        if self.file_watcher:
            return
        
        # 使用watchdog监控文件变化
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ConfigChangeHandler(FileSystemEventHandler):
                def __init__(self, monitor):
                    self.monitor = monitor
                
                def on_modified(self, event):
                    if event.src_path == str(self.monitor.config_path):
                        asyncio.create_task(self.monitor._handle_config_change())
            
            self.file_watcher = Observer()
            handler = ConfigChangeHandler(self)
            self.file_watcher.schedule(handler, str(self.config_path.parent), recursive=False)
            self.file_watcher.start()
            
            logger.info(f"开始监控配置文件: {self.config_path}")
            
        except ImportError:
            logger.warning("watchdog未安装，使用轮询方式监控配置")
            asyncio.create_task(self._poll_config_changes())
    
    async def _poll_config_changes(self):
        """轮询配置变化"""
        while True:
            try:
                current_modified = self.config_path.stat().st_mtime
                if current_modified > self.last_modified:
                    await self._handle_config_change()
                    self.last_modified = current_modified
                
                await asyncio.sleep(5)  # 5秒检查一次
                
            except Exception as e:
                logger.error(f"配置监控错误: {e}")
                await asyncio.sleep(30)
    
    async def _handle_config_change(self):
        """处理配置变化"""
        logger.info("检测到配置文件变化，准备重新加载")
        
        # 通知所有回调函数
        for callback in self.reload_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"配置重载回调执行失败: {e}")
    
    def add_reload_callback(self, callback: Callable):
        """添加重载回调函数"""
        self.reload_callbacks.append(callback)
    
    async def stop_monitoring(self):
        """停止监控"""
        if self.file_watcher:
            self.file_watcher.stop()
            self.file_watcher.join()
            self.file_watcher = None
```

## 9. 总结

Tool Layer的详细设计通过以下三个核心功能，为UAgent系统提供了强大的工具支持：

### 1. **配置式MCP Server**
- 支持通过YAML/JSON配置文件动态添加外部HTTP MCP服务
- 自动服务发现、健康检查和故障转移
- 灵活的认证配置和速率限制

### 2. **内置MCP Server**  
- 提供常用功能的直接代码实现，如文件操作、代码分析等
- 高性能、安全可控的内置服务
- 标准化的服务接口和工具定义

### 3. **用户互动MCP**
- 将用户对话作为系统核心功能，不是辅助功能
- 支持实时问答、确认、选择等多种交互方式
- 完整的会话管理和上下文维护

该设计确保了UAgent系统具有高度的灵活性和扩展性，同时将用户互动作为核心功能，实现了真正的智能化协作。通过配置化管理和内置服务相结合，系统能够适应各种不同的使用场景和需求。
