"""
Guidance Builder

系统指导构建器 - 构建执行指导和质量标准信息
"""

import structlog
from typing import TYPE_CHECKING

from .base_builder import BasePromptBuilder

if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class GuidanceBuilder(BasePromptBuilder):
    """系统指导构建器"""
    
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建系统指导section"""
        
        try:
            role_config = request.role_config
            role = request.role
            
            guidance_section = "## 系统执行指导\n"
            
            # 角色特定的执行要求
            guidance_section += await self._build_role_specific_guidance(role_config)
            
            # 行为规则
            if hasattr(role_config, 'behavior_rules') and role_config.behavior_rules:
                guidance_section += "\n### 行为规则\n"
                for rule in role_config.behavior_rules:
                    guidance_section += f"- {rule}\n"
            
            # 质量标准
            guidance_section += await self._build_quality_standards(role_config)
            
            # 任务执行指导
            guidance_section += self._get_task_execution_guidance()
            
            # 系统提醒
            guidance_section += "\n" + await self._build_system_reminder(role)
            
            logger.debug(f"构建系统指导section完成")
            return guidance_section.strip()
            
        except Exception as e:
            logger.error(f"构建系统指导section失败: {e}")
            return ""
    
    async def _build_role_specific_guidance(self, role_config) -> str:
        """构建角色特定的执行指导"""
        
        guidance = ""
        
        try:
            # 输出要求
            if hasattr(role_config, 'capabilities') and role_config.capabilities:
                capabilities = role_config.capabilities
                
                if hasattr(capabilities, 'output_types') and capabilities.output_types:
                    guidance += "### 输出要求\n"
                    for output_type in capabilities.output_types:
                        guidance += f"- {output_type}\n"
                
                if hasattr(capabilities, 'deliverable_formats') and capabilities.deliverable_formats:
                    guidance += "\n### 交付格式\n"
                    for format_type in capabilities.deliverable_formats:
                        guidance += f"- {format_type}\n"
            
            # 最大执行时间
            if hasattr(role_config, 'capabilities') and role_config.capabilities:
                if hasattr(role_config.capabilities, 'average_execution_time') and role_config.capabilities.average_execution_time:
                    guidance += f"\n### 执行时间要求\n- 建议执行时间: {role_config.capabilities.average_execution_time} 分钟内\n"
        
        except Exception as e:
            logger.warning(f"构建角色特定指导失败: {e}")
        
        return guidance
    
    async def _build_quality_standards(self, role_config) -> str:
        """构建质量标准"""
        
        quality_section = "\n### 质量标准\n"
        
        try:
            # 角色特定的质量标准
            if hasattr(role_config, 'quality_gates') and role_config.quality_gates:
                for gate in role_config.quality_gates:
                    quality_section += f"- {gate}\n"
            elif hasattr(role_config, 'success_criteria') and role_config.success_criteria:
                for criteria in role_config.success_criteria:
                    quality_section += f"- {criteria}\n"
            else:
                # 默认质量标准
                quality_section += "- 确保输出符合专业标准\n"
                quality_section += "- 保持代码和文档的一致性\n"
                quality_section += "- 遵循最佳实践和行业标准\n"
                quality_section += "- 及时识别和报告问题\n"
        
        except Exception as e:
            logger.warning(f"构建质量标准失败: {e}")
            # 使用默认标准
            quality_section += "- 确保输出符合专业标准\n"
            quality_section += "- 遵循最佳实践\n"
        
        return quality_section
    
    def _get_task_execution_guidance(self) -> str:
        """获取任务执行指导"""
        
        return """
### 任务执行指导
1. **分析阶段**: 理解任务需求，制定执行计划
2. **执行阶段**: 使用合适的工具逐步完成任务
3. **验证阶段**: 检查任务完成情况，确保质量
4. **总结阶段**: 提供任务完成状态和关键信息"""
    
    async def _build_system_reminder(self, role: str) -> str:
        """构建系统提醒"""
        
        return f"""
### 重要提醒
你是一个专业的{role}，专注于完成当前任务。请遵循以下原则：

**执行原则：**
1. 使用可用的工具来完成任务
2. 每轮执行后评估是否完成
3. 如果任务完成，明确说明完成状态和交付物
4. 如果任务未完成，说明下一步计划和所需信息
5. 保持专业性和效率性

**任务完成标识：**
当任务完成时，请明确说明：
- 任务完成状态（完成/部分完成/需要更多信息）
- 主要交付物和成果
- 下一步建议或注意事项
"""
    
    def get_section_name(self) -> str:
        """获取section名称"""
        return "guidance"
    
    def get_priority(self) -> int:
        """获取构建优先级"""
        return 50  # 较低优先级，在其他核心section之后
    
    def is_required(self) -> bool:
        """是否为必需的section"""
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数"""
        return (request.role_config is not None and 
                request.role is not None)
    
