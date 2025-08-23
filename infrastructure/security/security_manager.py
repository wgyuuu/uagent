"""
Security Manager

安全管理器 - 管理系统安全、认证、授权和加密
"""

from typing import Dict, List, Any, Optional, Callable, Union
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import hashlib
import secrets
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)


@dataclass
class SecurityConfig:
    """安全配置"""
    enabled: bool = True
    authentication_required: bool = True
    authorization_enabled: bool = True
    encryption_enabled: bool = True
    session_timeout: int = 3600  # 秒
    max_login_attempts: int = 5
    password_min_length: int = 8
    jwt_secret: Optional[str] = None
    encryption_key: Optional[str] = None


@dataclass
class User:
    """用户信息"""
    user_id: str
    username: str
    email: str
    password_hash: str
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    status: str  # "active", "inactive", "locked"
    metadata: Dict[str, Any]


@dataclass
class Session:
    """会话信息"""
    session_id: str
    user_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_active: bool
    metadata: Dict[str, Any]


class AuthenticationService:
    """认证服务"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.login_attempts: Dict[str, List[datetime]] = {}
        
        # 初始化默认用户
        self._initialize_default_users()
        
        logger.info("认证服务初始化完成")
    
    def _initialize_default_users(self):
        """初始化默认用户"""
        try:
            # 创建管理员用户
            admin_user = User(
                user_id="admin",
                username="admin",
                email="admin@uagent.local",
                password_hash=self._hash_password("admin123"),
                roles=["admin"],
                permissions=["*"],
                created_at=datetime.now(),
                status="active",
                metadata={}
            )
            
            self.users["admin"] = admin_user
            logger.info("默认管理员用户已创建")
            
        except Exception as e:
            logger.error(f"初始化默认用户失败: {e}")
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, hash_part = password_hash.split(":", 1)
            expected_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return expected_hash == hash_part
        except Exception:
            return False
    
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None
    ) -> Optional[User]:
        """注册用户"""
        try:
            # 验证输入
            if len(password) < self.config.password_min_length:
                raise ValueError(f"密码长度必须至少为 {self.config.password_min_length} 个字符")
            
            if username in [u.username for u in self.users.values()]:
                raise ValueError("用户名已存在")
            
            if email in [u.email for u in self.users.values()]:
                raise ValueError("邮箱已存在")
            
            # 创建用户
            user_id = f"user_{secrets.token_hex(8)}"
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=self._hash_password(password),
                roles=roles or ["user"],
                permissions=permissions or ["read"],
                created_at=datetime.now(),
                status="active",
                metadata={}
            )
            
            self.users[user_id] = user
            logger.info(f"用户已注册: {username}")
            
            return user
            
        except Exception as e:
            logger.error(f"注册用户失败: {e}")
            raise
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[Session]:
        """用户认证"""
        try:
            # 查找用户
            user = None
            for u in self.users.values():
                if u.username == username:
                    user = u
                    break
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                return None
            
            # 检查用户状态
            if user.status != "active":
                logger.warning(f"用户状态异常: {username}, 状态: {user.status}")
                return None
            
            # 检查登录尝试次数
            if self._is_account_locked(username):
                logger.warning(f"账户已锁定: {username}")
                return None
            
            # 验证密码
            if not self._verify_password(password, user.password_hash):
                await self._record_failed_login(username)
                logger.warning(f"密码错误: {username}")
                return None
            
            # 创建会话
            session = await self._create_session(user, ip_address, user_agent)
            
            # 更新用户最后登录时间
            user.last_login = datetime.now()
            
            # 清除失败的登录尝试
            if username in self.login_attempts:
                del self.login_attempts[username]
            
            logger.info(f"用户认证成功: {username}")
            return session
            
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            return None
    
    def _is_account_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        if username not in self.login_attempts:
            return False
        
        attempts = self.login_attempts[username]
        recent_attempts = [
            attempt for attempt in attempts
            if datetime.now() - attempt < timedelta(minutes=15)
        ]
        
        return len(recent_attempts) >= self.config.max_login_attempts
    
    async def _record_failed_login(self, username: str):
        """记录失败的登录"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []
        
        self.login_attempts[username].append(datetime.now())
        
        # 清理旧的尝试记录
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.login_attempts[username] = [
            attempt for attempt in self.login_attempts[username]
            if attempt > cutoff_time
        ]
    
    async def _create_session(
        self,
        user: User,
        ip_address: str,
        user_agent: str
    ) -> Session:
        """创建会话"""
        session_id = f"session_{secrets.token_hex(16)}"
        token = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            token=token,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.config.session_timeout),
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            metadata={}
        )
        
        self.sessions[session_id] = session
        return session
    
    async def validate_session(self, token: str) -> Optional[User]:
        """验证会话"""
        try:
            # 查找会话
            session = None
            for s in self.sessions.values():
                if s.token == token and s.is_active:
                    session = s
                    break
            
            if not session:
                return None
            
            # 检查会话是否过期
            if datetime.now() > session.expires_at:
                session.is_active = False
                return None
            
            # 获取用户信息
            user = self.users.get(session.user_id)
            if not user or user.status != "active":
                session.is_active = False
                return None
            
            # 延长会话
            session.expires_at = datetime.now() + timedelta(seconds=self.config.session_timeout)
            
            return user
            
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None
    
    async def logout(self, token: str) -> bool:
        """用户登出"""
        try:
            for session in self.sessions.values():
                if session.token == token:
                    session.is_active = False
                    logger.info(f"用户已登出: {session.user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            return False
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        return self.users.get(user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    async def update_user_roles(self, user_id: str, roles: List[str]) -> bool:
        """更新用户角色"""
        try:
            if user_id not in self.users:
                return False
            
            self.users[user_id].roles = roles
            logger.info(f"用户角色已更新: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户角色失败: {e}")
            return False
    
    async def update_user_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """更新用户权限"""
        try:
            if user_id not in self.users:
                return False
            
            self.users[user_id].permissions = permissions
            logger.info(f"用户权限已更新: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户权限失败: {e}")
            return False
    
    async def get_active_sessions(self) -> List[Session]:
        """获取活跃会话"""
        return [
            session for session in self.sessions.values()
            if session.is_active and datetime.now() <= session.expires_at
        ]
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session in self.sessions.items():
                if current_time > session.expires_at:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
            
            if expired_sessions:
                logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
                
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
    
    async def get_authentication_statistics(self) -> Dict[str, Any]:
        """获取认证统计信息"""
        total_users = len(self.users)
        active_users = len([u for u in self.users.values() if u.status == "active"])
        total_sessions = len(self.sessions)
        active_sessions = len(await self.get_active_sessions())
        
        # 按角色统计用户
        role_stats = {}
        for user in self.users.values():
            for role in user.roles:
                role_stats[role] = role_stats.get(role, 0) + 1
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "role_distribution": role_stats,
            "locked_accounts": len([u for u in self.users.values() if u.status == "locked"])
        }


class AuthorizationService:
    """授权服务"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.role_permissions: Dict[str, List[str]] = {}
        self.resource_permissions: Dict[str, Dict[str, List[str]]] = {}
        
        # 初始化默认权限
        self._initialize_default_permissions()
        
        logger.info("授权服务初始化完成")
    
    def _initialize_default_permissions(self):
        """初始化默认权限"""
        # 角色权限映射
        self.role_permissions = {
            "admin": ["*"],  # 管理员拥有所有权限
            "user": ["read", "write"],
            "guest": ["read"]
        }
        
        # 资源权限映射
        self.resource_permissions = {
            "tasks": {
                "read": ["user", "admin"],
                "write": ["admin"],
                "delete": ["admin"]
            },
            "workflows": {
                "read": ["user", "admin"],
                "write": ["admin"],
                "execute": ["user", "admin"]
            },
            "system": {
                "read": ["admin"],
                "write": ["admin"],
                "admin": ["admin"]
            }
        }
    
    async def check_permission(
        self,
        user: User,
        resource: str,
        action: str
    ) -> bool:
        """检查权限"""
        try:
            # 管理员拥有所有权限
            if "admin" in user.roles:
                return True
            
            # 检查用户直接权限
            if "*" in user.permissions:
                return True
            
            if action in user.permissions:
                return True
            
            # 检查角色权限
            for role in user.roles:
                if role in self.role_permissions:
                    role_perms = self.role_permissions[role]
                    if "*" in role_perms or action in role_perms:
                        return True
            
            # 检查资源特定权限
            if resource in self.resource_permissions:
                resource_perms = self.resource_permissions[resource]
                if action in resource_perms:
                    allowed_roles = resource_perms[action]
                    if any(role in user.roles for role in allowed_roles):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return False


class EncryptionService:
    """加密服务"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.encryption_key = config.encryption_key or secrets.token_hex(32)
        
        logger.info("加密服务初始化完成")
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            # 简单的加密实现（生产环境应使用更安全的加密库如cryptography）
            import base64
            
            # 使用异或加密
            encrypted = ""
            for i, char in enumerate(data):
                key_char = self.encryption_key[i % len(self.encryption_key)]
                encrypted_char = chr(ord(char) ^ ord(key_char))
                encrypted += encrypted_char
            
            # Base64编码
            return base64.b64encode(encrypted.encode('latin-1')).decode()
            
        except Exception as e:
            logger.error(f"加密数据失败: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            import base64
            
            # Base64解码
            decoded = base64.b64decode(encrypted_data.encode()).decode('latin-1')
            
            # 异或解密
            decrypted = ""
            for i, char in enumerate(decoded):
                key_char = self.encryption_key[i % len(self.encryption_key)]
                decrypted_char = chr(ord(char) ^ ord(key_char))
                decrypted += decrypted_char
            
            return decrypted
            
        except Exception as e:
            logger.error(f"解密数据失败: {e}")
            raise
    
    def hash_data(self, data: str) -> str:
        """哈希数据"""
        try:
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"哈希数据失败: {e}")
            raise
    
    def generate_token(self, length: int = 32) -> str:
        """生成令牌"""
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            logger.error(f"生成令牌失败: {e}")
            raise


class SecurityManager:
    """
    安全管理器
    
    管理系统安全、认证、授权和加密
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.authentication_service: Optional[AuthenticationService] = None
        self.authorization_service: Optional[AuthorizationService] = None
        self.encryption_service: Optional[EncryptionService] = None
        
        # 初始化安全服务
        self._initialize_security_services()
        
        # 启动清理任务
        self.cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("安全管理器初始化完成")
    
    def _initialize_security_services(self):
        """初始化安全服务"""
        try:
            self.authentication_service = AuthenticationService(self.config)
            self.authorization_service = AuthorizationService(self.config)
            self.encryption_service = EncryptionService(self.config)
            
            logger.info("安全服务初始化完成")
            
        except Exception as e:
            logger.error(f"初始化安全服务失败: {e}")
            raise
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    if self.authentication_service:
                        await self.authentication_service.cleanup_expired_sessions()
                    await asyncio.sleep(300)  # 每5分钟清理一次
                except Exception as e:
                    logger.error(f"清理任务出错: {e}")
                    await asyncio.sleep(300)
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("安全清理任务已启动")
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[Session]:
        """用户认证"""
        if not self.authentication_service:
            return None
        
        return await self.authentication_service.authenticate_user(username, password, ip_address, user_agent)
    
    async def validate_session(self, token: str) -> Optional[User]:
        """验证会话"""
        if not self.authentication_service:
            return None
        
        return await self.authentication_service.validate_session(token)
    
    async def check_permission(
        self,
        user: User,
        resource: str,
        action: str
    ) -> bool:
        """检查权限"""
        if not self.authorization_service:
            return False
        
        return await self.authorization_service.check_permission(user, resource, action)
    
    async def encrypt_data(self, data: str) -> str:
        """加密数据"""
        if not self.encryption_service:
            return data
        
        return self.encryption_service.encrypt_data(data)
    
    async def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        if not self.encryption_service:
            return encrypted_data
        
        return self.encryption_service.decrypt_data(encrypted_data)
    
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None
    ) -> Optional[User]:
        """注册用户"""
        if not self.authentication_service:
            return None
        
        return await self.authentication_service.register_user(username, email, password, roles, permissions)
    
    async def logout(self, token: str) -> bool:
        """用户登出"""
        if not self.authentication_service:
            return False
        
        return await self.authentication_service.logout(token)
    
    async def get_security_status(self) -> Dict[str, Any]:
        """获取安全状态"""
        try:
            status = {
                "enabled": self.config.enabled,
                "authentication_required": self.config.authentication_required,
                "authorization_enabled": self.config.authorization_enabled,
                "encryption_enabled": self.config.encryption_enabled,
                "session_timeout": self.config.session_timeout,
                "max_login_attempts": self.config.max_login_attempts
            }
            
            # 添加认证统计
            if self.authentication_service:
                auth_stats = await self.authentication_service.get_authentication_statistics()
                status["authentication"] = auth_stats
            
            return status
            
        except Exception as e:
            logger.error(f"获取安全状态失败: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """关闭安全管理器"""
        try:
            # 停止清理任务
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("安全管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭安全管理器失败: {e}")
            raise
