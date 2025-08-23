"""
Authorization Service

授权服务 - 处理权限检查、角色管理和资源访问控制
"""

from typing import Dict, List, Any, Optional, Set
import structlog
from datetime import datetime
from dataclasses import dataclass

from .security_manager import SecurityConfig, User

logger = structlog.get_logger(__name__)


@dataclass
class Permission:
    """权限定义"""
    name: str
    description: str
    resource: str
    action: str
    created_at: datetime


@dataclass
class Role:
    """角色定义"""
    name: str
    description: str
    permissions: List[str]
    created_at: datetime
    is_system_role: bool = False


class AuthorizationService:
    """
    授权服务
    
    管理用户权限、角色分配和资源访问控制
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.permissions: Dict[str, Permission] = {}
        self.roles: Dict[str, Role] = {}
        self.role_permissions: Dict[str, List[str]] = {}
        self.resource_permissions: Dict[str, Dict[str, List[str]]] = {}
        
        # 初始化默认权限和角色
        self._initialize_default_permissions()
        self._initialize_default_roles()
        
        logger.info("授权服务初始化完成")
    
    def _initialize_default_permissions(self):
        """初始化默认权限"""
        default_permissions = [
            # 系统权限
            Permission("system.admin", "系统管理员权限", "system", "*", datetime.now()),
            Permission("system.read", "系统读取权限", "system", "read", datetime.now()),
            Permission("system.write", "系统写入权限", "system", "write", datetime.now()),
            
            # 任务权限
            Permission("task.create", "创建任务权限", "tasks", "create", datetime.now()),
            Permission("task.read", "读取任务权限", "tasks", "read", datetime.now()),
            Permission("task.update", "更新任务权限", "tasks", "update", datetime.now()),
            Permission("task.delete", "删除任务权限", "tasks", "delete", datetime.now()),
            Permission("task.execute", "执行任务权限", "tasks", "execute", datetime.now()),
            
            # 工作流权限
            Permission("workflow.create", "创建工作流权限", "workflows", "create", datetime.now()),
            Permission("workflow.read", "读取工作流权限", "workflows", "read", datetime.now()),
            Permission("workflow.update", "更新工作流权限", "workflows", "update", datetime.now()),
            Permission("workflow.delete", "删除工作流权限", "workflows", "delete", datetime.now()),
            Permission("workflow.execute", "执行工作流权限", "workflows", "execute", datetime.now()),
            
            # 用户权限
            Permission("user.create", "创建用户权限", "users", "create", datetime.now()),
            Permission("user.read", "读取用户权限", "users", "read", datetime.now()),
            Permission("user.update", "更新用户权限", "users", "update", datetime.now()),
            Permission("user.delete", "删除用户权限", "users", "delete", datetime.now()),
            
            # 角色权限
            Permission("role.create", "创建角色权限", "roles", "create", datetime.now()),
            Permission("role.read", "读取角色权限", "roles", "read", datetime.now()),
            Permission("role.update", "更新角色权限", "roles", "update", datetime.now()),
            Permission("role.delete", "删除角色权限", "roles", "delete", datetime.now()),
        ]
        
        for perm in default_permissions:
            self.permissions[perm.name] = perm
        
        logger.info(f"初始化了 {len(default_permissions)} 个默认权限")
    
    def _initialize_default_roles(self):
        """初始化默认角色"""
        # 超级管理员角色
        admin_role = Role(
            name="admin",
            description="系统管理员",
            permissions=["system.admin"],
            created_at=datetime.now(),
            is_system_role=True
        )
        
        # 普通用户角色
        user_role = Role(
            name="user",
            description="普通用户",
            permissions=[
                "task.read", "task.create", "task.update", "task.execute",
                "workflow.read", "workflow.execute",
                "user.read"
            ],
            created_at=datetime.now(),
            is_system_role=True
        )
        
        # 访客角色
        guest_role = Role(
            name="guest",
            description="访客用户",
            permissions=["task.read", "workflow.read"],
            created_at=datetime.now(),
            is_system_role=True
        )
        
        # 任务管理员角色
        task_admin_role = Role(
            name="task_admin",
            description="任务管理员",
            permissions=[
                "task.create", "task.read", "task.update", "task.delete", "task.execute",
                "workflow.read", "workflow.execute"
            ],
            created_at=datetime.now(),
            is_system_role=True
        )
        
        # 工作流管理员角色
        workflow_admin_role = Role(
            name="workflow_admin",
            description="工作流管理员",
            permissions=[
                "workflow.create", "workflow.read", "workflow.update", 
                "workflow.delete", "workflow.execute",
                "task.read", "task.execute"
            ],
            created_at=datetime.now(),
            is_system_role=True
        )
        
        default_roles = [admin_role, user_role, guest_role, task_admin_role, workflow_admin_role]
        
        for role in default_roles:
            self.roles[role.name] = role
            self.role_permissions[role.name] = role.permissions
        
        # 初始化资源权限映射
        self.resource_permissions = {
            "system": {
                "read": ["admin", "user"],
                "write": ["admin"],
                "admin": ["admin"]
            },
            "tasks": {
                "create": ["admin", "user", "task_admin"],
                "read": ["admin", "user", "guest", "task_admin", "workflow_admin"],
                "update": ["admin", "user", "task_admin"],
                "delete": ["admin", "task_admin"],
                "execute": ["admin", "user", "task_admin", "workflow_admin"]
            },
            "workflows": {
                "create": ["admin", "workflow_admin"],
                "read": ["admin", "user", "guest", "task_admin", "workflow_admin"],
                "update": ["admin", "workflow_admin"],
                "delete": ["admin", "workflow_admin"],
                "execute": ["admin", "user", "task_admin", "workflow_admin"]
            },
            "users": {
                "create": ["admin"],
                "read": ["admin", "user"],
                "update": ["admin"],
                "delete": ["admin"]
            },
            "roles": {
                "create": ["admin"],
                "read": ["admin"],
                "update": ["admin"],
                "delete": ["admin"]
            }
        }
        
        logger.info(f"初始化了 {len(default_roles)} 个默认角色")
    
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
            
            # 检查具体权限
            permission_name = f"{resource}.{action}"
            if permission_name in user.permissions:
                return True
            
            # 检查系统权限
            if "system.admin" in user.permissions:
                return True
            
            # 检查角色权限
            for role in user.roles:
                if role in self.role_permissions:
                    role_perms = self.role_permissions[role]
                    if "system.admin" in role_perms or permission_name in role_perms:
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
    
    async def grant_permission_to_user(
        self,
        user: User,
        permission: str
    ) -> bool:
        """授予用户权限"""
        try:
            if permission not in user.permissions:
                user.permissions.append(permission)
                logger.info(f"权限已授予: {user.user_id} -> {permission}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"授予权限失败: {e}")
            return False
    
    async def revoke_permission_from_user(
        self,
        user: User,
        permission: str
    ) -> bool:
        """从用户撤销权限"""
        try:
            if permission in user.permissions:
                user.permissions.remove(permission)
                logger.info(f"权限已撤销: {user.user_id} -> {permission}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"撤销权限失败: {e}")
            return False
    
    async def assign_role_to_user(
        self,
        user: User,
        role: str
    ) -> bool:
        """分配角色给用户"""
        try:
            if role not in self.roles:
                raise ValueError(f"角色不存在: {role}")
            
            if role not in user.roles:
                user.roles.append(role)
                logger.info(f"角色已分配: {user.user_id} -> {role}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"分配角色失败: {e}")
            return False
    
    async def remove_role_from_user(
        self,
        user: User,
        role: str
    ) -> bool:
        """从用户移除角色"""
        try:
            if role in user.roles:
                user.roles.remove(role)
                logger.info(f"角色已移除: {user.user_id} -> {role}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"移除角色失败: {e}")
            return False
    
    async def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str]
    ) -> bool:
        """创建角色"""
        try:
            if name in self.roles:
                raise ValueError(f"角色已存在: {name}")
            
            # 验证权限是否存在
            for perm in permissions:
                if perm not in self.permissions and perm != "system.admin":
                    raise ValueError(f"权限不存在: {perm}")
            
            role = Role(
                name=name,
                description=description,
                permissions=permissions,
                created_at=datetime.now(),
                is_system_role=False
            )
            
            self.roles[name] = role
            self.role_permissions[name] = permissions
            
            logger.info(f"角色已创建: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建角色失败: {e}")
            return False
    
    async def update_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> bool:
        """更新角色"""
        try:
            if name not in self.roles:
                raise ValueError(f"角色不存在: {name}")
            
            role = self.roles[name]
            
            # 系统角色不能修改
            if role.is_system_role:
                raise ValueError(f"系统角色不能修改: {name}")
            
            if description is not None:
                role.description = description
            
            if permissions is not None:
                # 验证权限是否存在
                for perm in permissions:
                    if perm not in self.permissions and perm != "system.admin":
                        raise ValueError(f"权限不存在: {perm}")
                
                role.permissions = permissions
                self.role_permissions[name] = permissions
            
            logger.info(f"角色已更新: {name}")
            return True
            
        except Exception as e:
            logger.error(f"更新角色失败: {e}")
            return False
    
    async def delete_role(self, name: str) -> bool:
        """删除角色"""
        try:
            if name not in self.roles:
                raise ValueError(f"角色不存在: {name}")
            
            role = self.roles[name]
            
            # 系统角色不能删除
            if role.is_system_role:
                raise ValueError(f"系统角色不能删除: {name}")
            
            del self.roles[name]
            del self.role_permissions[name]
            
            logger.info(f"角色已删除: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            return False
    
    async def get_user_permissions(self, user: User) -> List[str]:
        """获取用户所有权限"""
        try:
            permissions = set(user.permissions)
            
            # 添加角色权限
            for role in user.roles:
                if role in self.role_permissions:
                    permissions.update(self.role_permissions[role])
            
            return list(permissions)
            
        except Exception as e:
            logger.error(f"获取用户权限失败: {e}")
            return []
    
    async def get_role_info(self, role_name: str) -> Optional[Role]:
        """获取角色信息"""
        return self.roles.get(role_name)
    
    async def list_all_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self.roles.values())
    
    async def list_all_permissions(self) -> List[Permission]:
        """列出所有权限"""
        return list(self.permissions.values())
    
    async def get_authorization_statistics(self) -> Dict[str, Any]:
        """获取授权统计信息"""
        total_roles = len(self.roles)
        system_roles = len([r for r in self.roles.values() if r.is_system_role])
        custom_roles = total_roles - system_roles
        total_permissions = len(self.permissions)
        
        # 按资源统计权限
        resource_stats = {}
        for perm in self.permissions.values():
            resource_stats[perm.resource] = resource_stats.get(perm.resource, 0) + 1
        
        return {
            "total_roles": total_roles,
            "system_roles": system_roles,
            "custom_roles": custom_roles,
            "total_permissions": total_permissions,
            "resource_permission_distribution": resource_stats,
            "resources_managed": len(self.resource_permissions)
        }
