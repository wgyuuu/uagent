"""
Permission Manager

权限管理器 - 负责工具访问权限控制
"""

from typing import Dict, List, Optional, Any
import structlog

logger = structlog.get_logger(__name__)


class PermissionManager:
    """
    权限管理器
    
    负责工具访问权限控制，包括：
    - 角色权限管理
    - 工具安全级别控制
    - 动态权限验证
    """
    
    def __init__(self):
        """初始化权限管理器"""
        # 角色权限配置
        self.role_permissions = self._load_default_role_permissions()
        
        # 工具安全级别配置
        self.tool_security_levels = self._load_default_tool_security_levels()
        
        # 动态权限规则
        self.dynamic_rules: List[callable] = []
        
        logger.info("权限管理器初始化完成")
    
    def _load_default_role_permissions(self) -> Dict[str, List[str]]:
        """加载默认角色权限配置"""
        return {
            "方案规划师": [
                "user_interaction:*",
                "web_services:search",
                "web_services:documentation",
                "data_processing:analysis",
                "file_operations:read"
            ],
            "编码专家": [
                "file_operations:*",
                "development_tools:*",
                "web_services:api_call",
                "system_utilities:*",
                "user_interaction:ask"
            ],
            "测试工程师": [
                "file_operations:read",
                "development_tools:test",
                "development_tools:build",
                "system_utilities:monitor",
                "user_interaction:ask"
            ],
            "代码审查员": [
                "file_operations:read",
                "development_tools:analysis",
                "web_services:documentation",
                "data_processing:analysis",
                "user_interaction:ask"
            ],
            "系统管理员": [
                "*:*"  # 所有权限
            ],
            "访客": [
                "user_interaction:ask",
                "web_services:search"
            ]
        }
    
    def _load_default_tool_security_levels(self) -> Dict[str, str]:
        """加载默认工具安全级别配置"""
        return {
            "file_operations:write": "high",
            "file_operations:delete": "critical",
            "system_utilities:execute": "high",
            "system_utilities:shutdown": "critical",
            "web_services:api_call": "medium",
            "user_interaction:ask": "low",
            "development_tools:test": "medium",
            "development_tools:deploy": "high"
        }
    
    async def check_permission(self, 
                             role: str, 
                             tool_category: str, 
                             tool_name: str) -> bool:
        """
        检查角色是否有权限使用工具
        
        Args:
            role: 角色名称
            tool_category: 工具类别
            tool_name: 工具名称
            
        Returns:
            是否有权限
        """
        try:
            # 获取角色权限
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
            
            # 检查动态权限规则
            if await self._check_dynamic_rules(role, tool_category, tool_name):
                return True
            
            logger.debug(f"角色 {role} 没有权限使用工具 {tool_category}:{tool_name}")
            return False
            
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return False
    
    async def validate_tool_access(self, 
                                 role: str,
                                 tool_info: Any,
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具访问权限
        
        Args:
            role: 角色名称
            tool_info: 工具信息
            parameters: 工具参数
            
        Returns:
            验证结果
        """
        try:
            # 基础权限检查
            tool_category = getattr(tool_info, 'category', 'unknown')
            tool_name = getattr(tool_info, 'name', 'unknown')
            
            has_permission = await self.check_permission(role, tool_category, tool_name)
            
            if not has_permission:
                return {
                    "is_valid": False,
                    "error_message": f"角色 {role} 没有权限使用工具 {tool_name}",
                    "error_code": "PERMISSION_DENIED"
                }
            
            # 安全级别检查
            security_level = self._get_tool_security_level(tool_category, tool_name)
            
            if security_level == "critical":
                # 关键工具需要额外验证
                additional_validation = await self._validate_critical_tool_usage(
                    role, tool_info, parameters
                )
                if not additional_validation["is_valid"]:
                    return additional_validation
            
            # 参数安全检查
            param_validation = await self._validate_tool_parameters(tool_info, parameters)
            if not param_validation["is_valid"]:
                return param_validation
            
            return {
                "is_valid": True,
                "security_level": security_level,
                "permissions_granted": [f"{tool_category}:{tool_name}"]
            }
            
        except Exception as e:
            logger.error(f"验证工具访问权限失败: {e}")
            return {
                "is_valid": False,
                "error_message": f"权限验证失败: {str(e)}",
                "error_code": "VALIDATION_ERROR"
            }
    
    def _get_tool_security_level(self, tool_category: str, tool_name: str) -> str:
        """获取工具安全级别"""
        # 检查具体工具的安全级别
        specific_key = f"{tool_category}:{tool_name}"
        if specific_key in self.tool_security_levels:
            return self.tool_security_levels[specific_key]
        
        # 检查类别默认安全级别
        category_key = f"{tool_category}:*"
        if category_key in self.tool_security_levels:
            return self.tool_security_levels[category_key]
        
        # 默认安全级别
        return "medium"
    
    async def _validate_critical_tool_usage(self, 
                                          role: str,
                                          tool_info: Any,
                                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证关键工具使用权限"""
        try:
            # 这里可以添加额外的验证逻辑
            # 例如：需要管理员确认、审计日志等
            
            # 检查角色是否有管理员权限
            if role in ["系统管理员", "超级用户"]:
                return {"is_valid": True}
            
            # 检查是否有特殊授权
            if await self._check_special_authorization(role, tool_info):
                return {"is_valid": True}
            
            return {
                "is_valid": False,
                "error_message": f"关键工具 {tool_info.name} 需要管理员权限或特殊授权",
                "error_code": "CRITICAL_TOOL_ACCESS_DENIED"
            }
            
        except Exception as e:
            logger.error(f"验证关键工具使用权限失败: {e}")
            return {
                "is_valid": False,
                "error_message": f"关键工具权限验证失败: {str(e)}",
                "error_code": "CRITICAL_VALIDATION_ERROR"
            }
    
    async def _validate_tool_parameters(self, 
                                      tool_info: Any,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具参数安全性"""
        try:
            # 检查文件路径安全性
            if "file_path" in parameters:
                file_path = parameters["file_path"]
                if not self._is_safe_file_path(file_path):
                    return {
                        "is_valid": False,
                        "error_message": f"不安全的文件路径: {file_path}",
                        "error_code": "UNSAFE_FILE_PATH"
                    }
            
            # 检查URL安全性
            if "url" in parameters:
                url = parameters["url"]
                if not self._is_safe_url(url):
                    return {
                        "is_valid": False,
                        "error_message": f"不安全的URL: {url}",
                        "error_code": "UNSAFE_URL"
                    }
            
            # 检查命令执行安全性
            if "command" in parameters:
                command = parameters["command"]
                if not self._is_safe_command(command):
                    return {
                        "is_valid": False,
                        "error_message": f"不安全的命令: {command}",
                        "error_code": "UNSAFE_COMMAND"
                    }
            
            return {"is_valid": True}
            
        except Exception as e:
            logger.error(f"验证工具参数失败: {e}")
            return {
                "is_valid": False,
                "error_message": f"参数验证失败: {str(e)}",
                "error_code": "PARAMETER_VALIDATION_ERROR"
            }
    
    def _is_safe_file_path(self, file_path: str) -> bool:
        """检查文件路径安全性"""
        if not file_path:
            return False
        
        # 禁止路径遍历
        if ".." in file_path or file_path.startswith("/"):
            return False
        
        # 禁止访问系统敏感目录
        sensitive_dirs = ["/etc", "/sys", "/proc", "/dev", "/boot", "/root"]
        for sensitive_dir in sensitive_dirs:
            if file_path.startswith(sensitive_dir):
                return False
        
        # 禁止访问用户主目录之外的文件
        if file_path.startswith("~") or file_path.startswith("/home"):
            return False
        
        return True
    
    def _is_safe_url(self, url: str) -> bool:
        """检查URL安全性"""
        if not url:
            return False
        
        # 只允许HTTP和HTTPS
        if not url.startswith(("http://", "https://")):
            return False
        
        # 禁止访问本地地址
        local_addresses = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        for local_addr in local_addresses:
            if local_addr in url:
                return False
        
        return True
    
    def _is_safe_command(self, command: str) -> bool:
        """检查命令安全性"""
        if not command:
            return False
        
        # 禁止危险命令
        dangerous_commands = [
            "rm -rf", "format", "dd", "mkfs", "fdisk",
            "shutdown", "reboot", "halt", "poweroff",
            "chmod 777", "chown root", "su -", "sudo"
        ]
        
        for dangerous_cmd in dangerous_commands:
            if dangerous_cmd in command.lower():
                return False
        
        return True
    
    async def _check_special_authorization(self, role: str, tool_info: Any) -> bool:
        """检查特殊授权"""
        # 这里可以实现特殊的授权逻辑
        # 例如：临时授权、紧急情况授权等
        return False
    
    async def _check_dynamic_rules(self, role: str, tool_category: str, tool_name: str) -> bool:
        """检查动态权限规则"""
        try:
            for rule in self.dynamic_rules:
                if await rule(role, tool_category, tool_name):
                    return True
            return False
            
        except Exception as e:
            logger.error(f"检查动态权限规则失败: {e}")
            return False
    
    def add_dynamic_rule(self, rule: callable):
        """添加动态权限规则"""
        self.dynamic_rules.append(rule)
        logger.info("动态权限规则已添加")
    
    def remove_dynamic_rule(self, rule: callable):
        """移除动态权限规则"""
        if rule in self.dynamic_rules:
            self.dynamic_rules.remove(rule)
            logger.info("动态权限规则已移除")
    
    def update_role_permissions(self, role: str, permissions: List[str]):
        """更新角色权限"""
        self.role_permissions[role] = permissions
        logger.info(f"角色 {role} 权限已更新")
    
    def update_tool_security_level(self, tool_key: str, security_level: str):
        """更新工具安全级别"""
        self.tool_security_levels[tool_key] = security_level
        logger.info(f"工具 {tool_key} 安全级别已更新为 {security_level}")
    
    def get_role_permissions(self, role: str) -> List[str]:
        """获取角色权限"""
        return self.role_permissions.get(role, [])
    
    def get_all_roles(self) -> List[str]:
        """获取所有角色"""
        return list(self.role_permissions.keys())
    
    def get_tool_security_info(self) -> Dict[str, str]:
        """获取工具安全级别信息"""
        return self.tool_security_levels.copy()
