"""
Role Identity Builder

角色身份构建器 - 构建角色身份和专业背景信息
"""

import structlog
from typing import TYPE_CHECKING

from .base_builder import BasePromptBuilder

if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class RoleIdentityBuilder(BasePromptBuilder):
    """角色身份构建器"""
    
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建角色身份section"""
        
        try:
            role_config = request.role_config
            
            # 基础角色模板
            identity_section = role_config.prompt_template
            
            # 添加专业背景信息
            if hasattr(role_config, 'category') and hasattr(role_config, 'expert_level'):
                background_info = f"""

## 专业背景
- 角色类别: {role_config.category.value if hasattr(role_config.category, 'value') else role_config.category}
- 专家级别: {role_config.expert_level.value if hasattr(role_config.expert_level, 'value') else role_config.expert_level}"""
                
                # 添加专业领域信息
                if hasattr(role_config, 'capabilities') and role_config.capabilities:
                    if hasattr(role_config.capabilities, 'primary_domains') and role_config.capabilities.primary_domains:
                        domains = [domain.value if hasattr(domain, 'value') else str(domain) 
                                 for domain in role_config.capabilities.primary_domains]
                        background_info += f"\n- 专业领域: {', '.join(domains)}"
                    
                    # 添加核心能力信息
                    if hasattr(role_config.capabilities, 'output_types') and role_config.capabilities.output_types:
                        background_info += f"\n\n## 核心能力"
                        background_info += f"\n- 输出类型: {', '.join(role_config.capabilities.output_types)}"
                    
                    if hasattr(role_config.capabilities, 'deliverable_formats') and role_config.capabilities.deliverable_formats:
                        background_info += f"\n- 交付格式: {', '.join(role_config.capabilities.deliverable_formats)}"
                
                identity_section += background_info
            
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
