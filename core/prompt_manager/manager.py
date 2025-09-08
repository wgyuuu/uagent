"""
Runtime Prompt Manager

运行时prompt管理器 - 动态构建和组装运行时prompt
"""

from typing import Dict, List, Optional, Any
import structlog

from models.base import ExecutionContext, ExecutionState
from models.roles import RoleConfig
from prompts.role_prompts import RolePromptManager
from prompts.templates.template_manager import TemplateManager
from prompts.reminders.system_reminder import SystemReminder

from .dto.prompt_request import PromptBuildRequest
from .builders.base_builder import BasePromptBuilder
from .builders.role_identity_builder import RoleIdentityBuilder
from .builders.context_builder import ContextBuilder
from .builders.tool_builder import ToolBuilder
from .builders.guidance_builder import GuidanceBuilder
from .processors.context_processor import ContextProcessor

logger = structlog.get_logger(__name__)


class RuntimePromptManager:
    """运行时prompt管理器 - core模块的独立组件"""
    
    def __init__(self):
        # 依赖静态资源管理器
        self.role_prompt_manager = RolePromptManager()
        self.template_manager = TemplateManager()
        self.reminder_engine = SystemReminder()
        
        # 初始化处理器（必须在构建器之前）
        self.context_processor = ContextProcessor()
        
        # 初始化构建器
        self.builders = self._initialize_builders()
        
        logger.info("RuntimePromptManager初始化完成")
    
    def _initialize_builders(self) -> Dict[str, BasePromptBuilder]:
        """初始化所有构建器"""
        builders = {
            'role_identity': RoleIdentityBuilder(),
            'context': ContextBuilder(),
            'tools': ToolBuilder(),  # 移除tool_cache参数
            'guidance': GuidanceBuilder()
        }
        
        logger.info(f"初始化了 {len(builders)} 个prompt构建器")
        return builders
    
    async def build_complete_prompt(self, request: PromptBuildRequest) -> str:
        """构建完整prompt - 统一入口点"""
        
        try:
            logger.info(f"开始构建角色 {request.role} 的完整prompt")
            
            # 1. 按优先级顺序构建各个section
            sections = {}
            
            # 获取构建器并按优先级排序
            sorted_builders = sorted(
                self.builders.items(),
                key=lambda x: x[1].get_priority()
            )
            
            for section_name, builder in sorted_builders:
                try:
                    section_content = await builder.build(request)
                    if section_content and section_content.strip():
                        sections[section_name] = section_content
                        logger.debug(f"构建section完成: {section_name}")
                except Exception as e:
                    logger.error(f"构建section失败 {section_name}: {e}")
                    # 继续构建其他section
            
            # 2. 添加自定义sections
            if request.custom_sections:
                sections.update(request.custom_sections)
            
            # 3. 组装最终prompt
            final_prompt = await self._assemble_final_prompt(sections)
            
            logger.info(f"角色 {request.role} 的prompt构建完成，总长度: {len(final_prompt)}")
            return final_prompt
            
        except Exception as e:
            logger.error(f"构建完整prompt失败: {e}")
            # 返回基础prompt作为降级方案
            return await self._build_fallback_prompt(request)
    
    async def build_section(self, section_type: str, request: PromptBuildRequest) -> str:
        """构建特定section"""
        
        if section_type not in self.builders:
            logger.warning(f"未知的section类型: {section_type}")
            return ""
        
        try:
            builder = self.builders[section_type]
            return await builder.build(request)
        except Exception as e:
            logger.error(f"构建section {section_type} 失败: {e}")
            return ""
    
    def get_available_builders(self) -> List[str]:
        """获取可用的构建器列表"""
        return list(self.builders.keys())
    
    async def validate_prompt_structure(self, prompt: str) -> Dict[str, Any]:
        """验证prompt结构的完整性"""
        
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'sections_found': [],
            'total_length': len(prompt)
        }
        
        # 检查必要的sections
        required_sections = ['角色身份', '执行上下文', '可用工具', '执行状态']
        for section in required_sections:
            if section in prompt:
                validation_result['sections_found'].append(section)
            else:
                validation_result['warnings'].append(f"缺少必要section: {section}")
        
        # 检查prompt长度
        if len(prompt) < 100:
            validation_result['errors'].append("Prompt长度过短")
            validation_result['is_valid'] = False
        elif len(prompt) > 10000:
            validation_result['warnings'].append("Prompt长度较长，可能影响性能")
        
        return validation_result
    
    async def _assemble_final_prompt(self, sections: Dict[str, str]) -> str:
        """组装最终prompt"""
        
        # 定义section顺序
        section_order = [
            'role_identity',
            'context', 
            'tools',
            'state',
            'guidance'
        ]
        
        # 按顺序组装
        prompt_parts = []
        
        for section_name in section_order:
            if section_name in sections and sections[section_name]:
                prompt_parts.append(sections[section_name])
        
        # 添加其他自定义sections
        for section_name, content in sections.items():
            if section_name not in section_order and content:
                prompt_parts.append(content)
        
        # 添加执行开始指令
        prompt_parts.append("""
## 开始执行
基于以上完整信息，请开始执行你的专业任务。
""")
        
        return "\n\n".join(prompt_parts).strip()
    
    async def _build_fallback_prompt(self, request: PromptBuildRequest) -> str:
        """构建降级prompt"""
        
        logger.warning(f"使用降级prompt构建方案")
        
        fallback_prompt = f"""
{request.role_config.prompt_template}

## 可用工具
{', '.join(request.available_tools) if request.available_tools else '当前没有可用的工具'}

## 开始执行
请开始执行你的任务。
"""
        
        return fallback_prompt.strip()
