"""
Authentication Service

认证服务 - 处理用户认证、会话管理和用户管理
"""

from typing import Dict, List, Any, Optional, Set
import structlog
from datetime import datetime, timedelta
import hashlib
import secrets
from dataclasses import dataclass

from .security_manager import SecurityConfig, User, Session

logger = structlog.get_logger(__name__)


class AuthenticationService:
    """
    认证服务
    
    提供用户注册、登录、会话管理等功能
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.login_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Set[str] = set()
        
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
            
            # 创建普通用户
            user = User(
                user_id="user_001",
                username="user",
                email="user@uagent.local",
                password_hash=self._hash_password("user123"),
                roles=["user"],
                permissions=["read", "write"],
                created_at=datetime.now(),
                status="active",
                metadata={}
            )
            
            self.users["user_001"] = user
            logger.info("默认普通用户已创建")
            
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
    
    def _is_ip_blocked(self, ip_address: str) -> bool:
        """检查IP是否被阻止"""
        return ip_address in self.blocked_ips
    
    def _block_ip(self, ip_address: str):
        """阻止IP"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"IP已被阻止: {ip_address}")
    
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
            # 检查IP是否被阻止
            if self._is_ip_blocked(ip_address):
                logger.warning(f"阻止的IP尝试登录: {ip_address}")
                return None
            
            # 查找用户
            user = None
            for u in self.users.values():
                if u.username == username:
                    user = u
                    break
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                await self._record_failed_login(username)
                return None
            
            # 检查用户状态
            if user.status != "active":
                logger.warning(f"用户状态异常: {username}, 状态: {user.status}")
                return None
            
            # 检查登录尝试次数
            if self._is_account_locked(username):
                logger.warning(f"账户已锁定: {username}")
                # 如果尝试次数过多，阻止IP
                if len(self.login_attempts.get(username, [])) > self.config.max_login_attempts * 2:
                    self._block_ip(ip_address)
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
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """更新用户密码"""
        try:
            if user_id not in self.users:
                return False
            
            # 验证密码长度
            if len(new_password) < self.config.password_min_length:
                raise ValueError(f"密码长度必须至少为 {self.config.password_min_length} 个字符")
            
            self.users[user_id].password_hash = self._hash_password(new_password)
            logger.info(f"用户密码已更新: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户密码失败: {e}")
            return False
    
    async def update_user_status(self, user_id: str, status: str) -> bool:
        """更新用户状态"""
        try:
            if user_id not in self.users:
                return False
            
            if status not in ["active", "inactive", "locked"]:
                raise ValueError("无效的用户状态")
            
            self.users[user_id].status = status
            logger.info(f"用户状态已更新: {user_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户状态失败: {e}")
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
            "inactive_users": len([u for u in self.users.values() if u.status == "inactive"]),
            "locked_users": len([u for u in self.users.values() if u.status == "locked"]),
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "role_distribution": role_stats,
            "blocked_ips": len(self.blocked_ips),
            "failed_login_attempts": len(self.login_attempts)
        }
