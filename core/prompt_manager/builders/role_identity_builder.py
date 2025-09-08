"""
Role Identity Builder

角色身份构建器 - 构建角色身份和专业背景信息
"""

import structlog

from .base_builder import BasePromptBuilder

from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class RoleIdentityBuilder(BasePromptBuilder):
    """角色身份构建器"""
    
    async def build(self, request: PromptBuildRequest) -> str:
        """构建角色身份section"""
        
        try:
            role_config = request.role_config
            
            # 直接使用角色模板，不再追加重复的角色信息
            # 因为prompt_template已经包含了完整的角色信息
            identity_section = role_config.prompt_template
            
            logger.debug(f"构建角色身份section完成: {request.role}")
            return identity_section.strip()
            
        except Exception as e:
            logger.error(f"构建角色身份section失败: {e}")
            # 降级到基础模板
            return request.role_config.prompt_template if request.role_config.prompt_template else f"You are a {request.role}."
    
    def get_section_name(self) -> str:
        return "role_identity"
    
    def get_priority(self) -> int:
        return 10  # 最高优先级
    
    def is_required(self) -> bool:
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数"""
        return (request.role_config is not None and 
                hasattr(request.role_config, 'prompt_template') and
                request.role_config.prompt_template is not None)
