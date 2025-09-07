"""
Context Builder

上下文构建器 - 构建执行上下文信息，支持8段式上下文处理
"""

import structlog
from typing import TYPE_CHECKING

from .base_builder import BasePromptBuilder

if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class ContextBuilder(BasePromptBuilder):
    """上下文构建器"""
    
    # 8段式上下文标准sections
    STANDARD_SECTIONS = [
        "Primary Request and Intent",
        "Key Technical Concepts", 
        "Files and Code Sections",
        "Errors and Fixes",
        "Problem Solving Progress",
        "All User Messages",
        "Pending Tasks",
        "Current Work Status"
    ]
    
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建执行上下文section"""
        
        try:
            context = request.context
            
            # 处理8段式上下文
            context_sections = await self._process_eight_segment_context(context)
            
            if not context_sections:
                # 降级处理：使用基本上下文信息
                return await self._build_basic_context(context, request)
            
            # 构建8段式上下文section
            context_section = "## 当前执行上下文\n"
            
            for section_name, content in context_sections.items():
                if content and content.strip():
                    context_section += f"\n### {section_name}\n{content}\n"
            
            logger.debug(f"构建8段式上下文section完成，包含 {len(context_sections)} 个sections")
            return context_section.strip()
            
        except Exception as e:
            logger.error(f"构建上下文section失败: {e}")
            # 降级处理
            return await self._build_basic_context(request.context, request)
    
    async def _process_eight_segment_context(self, context) -> dict[str, str]:
        """处理8段式上下文"""
        
        context_sections = {}
        
        try:
            # 尝试从isolated_context获取8段式sections
            if hasattr(context, 'isolated_context') and context.isolated_context:
                isolated = context.isolated_context
                
                if hasattr(isolated, 'sections') and isolated.sections:
                    # 直接使用已有的8段式sections
                    for section_name, section_obj in isolated.sections.items():
                        if section_obj and hasattr(section_obj, 'content'):
                            content = section_obj.content
                            if content and content.strip():
                                # 限制内容长度，避免过长
                                if len(content) > 500:
                                    content = content[:500] + "..."
                                context_sections[section_name] = content
                
                elif hasattr(isolated, 'get_section'):
                    # 使用get_section方法获取
                    for section_name in self.STANDARD_SECTIONS:
                        content = isolated.get_section(section_name, "")
                        if content and content.strip():
                            if len(content) > 500:
                                content = content[:500] + "..."
                            context_sections[section_name] = content
            
            # 如果没有获取到8段式内容，尝试其他方式
            if not context_sections:
                context_sections = await self._extract_context_from_attributes(context)
            
        except Exception as e:
            logger.warning(f"处理8段式上下文失败: {e}")
        
        return context_sections
    
    async def _extract_context_from_attributes(self, context) -> dict[str, str]:
        """从context属性中提取信息"""
        
        sections = {}
        
        try:
            # 提取基本信息
            if hasattr(context, 'task_description') and context.task_description:
                sections["Primary Request and Intent"] = context.task_description
            
            if hasattr(context, 'workflow_id') and context.workflow_id:
                sections["Current Work Status"] = f"工作流ID: {context.workflow_id}"
            
            if hasattr(context, 'current_role') and context.current_role:
                current_work = sections.get("Current Work Status", "")
                sections["Current Work Status"] = f"{current_work}\n当前角色: {context.current_role}".strip()
            
            # 尝试获取其他可能的属性
            for attr_name in ['files', 'errors', 'messages', 'tasks']:
                if hasattr(context, attr_name):
                    attr_value = getattr(context, attr_name)
                    if attr_value:
                        section_name = self._map_attribute_to_section(attr_name)
                        if section_name:
                            sections[section_name] = str(attr_value)[:300] + "..." if len(str(attr_value)) > 300 else str(attr_value)
        
        except Exception as e:
            logger.warning(f"从属性提取上下文失败: {e}")
        
        return sections
    
    def _map_attribute_to_section(self, attr_name: str) -> str:
        """将属性名映射到8段式section名"""
        
        mapping = {
            'files': 'Files and Code Sections',
            'errors': 'Errors and Fixes', 
            'messages': 'All User Messages',
            'tasks': 'Pending Tasks'
        }
        
        return mapping.get(attr_name, "")
    
    async def _build_basic_context(self, context, request: 'PromptBuildRequest') -> str:
        """构建基本上下文信息（降级方案）"""
        
        basic_context = "## 当前执行上下文\n"
        
        # 添加基本任务信息
        if hasattr(context, 'task_description') and context.task_description:
            basic_context += f"### 任务描述\n{context.task_description}\n\n"
        
        # 添加工作流信息
        if hasattr(context, 'workflow_id') and context.workflow_id:
            basic_context += f"### 工作流信息\n工作流ID: {context.workflow_id}\n\n"
        
        # 添加当前角色信息
        basic_context += f"### 当前工作\n正在执行角色: {request.role}\n"
        
        return basic_context.strip()
    
    def get_section_name(self) -> str:
        return "context"
    
    def get_priority(self) -> int:
        return 20
    
    def is_required(self) -> bool:
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数"""
        return request.context is not None
