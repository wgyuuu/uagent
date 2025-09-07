"""
Context Processor

上下文处理器 - 统一处理8段式上下文和执行状态信息
"""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)


class ContextProcessor:
    """上下文处理器 - 统一处理8段式上下文"""
    
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
    
    def __init__(self):
        self.cache_ttl = 300  # 缓存5分钟
        self._processed_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def normalize_context(self, context: Any) -> Dict[str, str]:
        """标准化上下文信息为8段式格式"""
        
        try:
            # 生成缓存key
            cache_key = self._generate_cache_key(context)
            
            # 检查缓存
            if self._is_cache_valid(cache_key):
                logger.debug("使用缓存的上下文处理结果")
                return self._processed_cache[cache_key]
            
            # 处理上下文
            normalized_sections = {}
            
            # 尝试从isolated_context获取
            if hasattr(context, 'isolated_context') and context.isolated_context:
                normalized_sections = await self._extract_from_isolated_context(context.isolated_context)
            
            # 如果没有获取到，尝试从其他属性提取
            if not normalized_sections:
                normalized_sections = await self._extract_from_context_attributes(context)
            
            # 缓存结果
            self._processed_cache[cache_key] = normalized_sections
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.debug(f"上下文标准化完成，包含 {len(normalized_sections)} 个sections")
            return normalized_sections
            
        except Exception as e:
            logger.error(f"标准化上下文失败: {e}")
            return {}
    
    async def merge_execution_state(self, 
                                  context_sections: Dict[str, str],
                                  execution_state: Any) -> Dict[str, str]:
        """将执行状态信息合并到上下文中"""
        
        try:
            merged_sections = context_sections.copy()
            
            # 更新Current Work Status
            current_work = merged_sections.get("Current Work Status", "")
            
            # 添加执行状态信息
            state_info = f"正在执行角色: {getattr(execution_state, 'role', '未知')}"
            if hasattr(execution_state, 'iteration'):
                state_info += f"，第{execution_state.iteration}轮迭代"
            
            if current_work:
                merged_sections["Current Work Status"] = f"{current_work}\n{state_info}"
            else:
                merged_sections["Current Work Status"] = state_info
            
            # 如果有完成信号，添加到Problem Solving Progress
            if hasattr(execution_state, 'completion_signals') and execution_state.completion_signals:
                progress = merged_sections.get("Problem Solving Progress", "")
                signals_info = "完成信号: " + ", ".join(execution_state.completion_signals)
                
                if progress:
                    merged_sections["Problem Solving Progress"] = f"{progress}\n{signals_info}"
                else:
                    merged_sections["Problem Solving Progress"] = signals_info
            
            logger.debug("执行状态信息合并完成")
            return merged_sections
            
        except Exception as e:
            logger.error(f"合并执行状态失败: {e}")
            return context_sections
    
    async def _extract_from_isolated_context(self, isolated_context: Any) -> Dict[str, str]:
        """从isolated_context提取8段式信息"""
        
        sections = {}
        
        try:
            if hasattr(isolated_context, 'sections') and isolated_context.sections:
                # 直接使用已有的sections
                for section_name, section_obj in isolated_context.sections.items():
                    if section_obj and hasattr(section_obj, 'content'):
                        content = section_obj.content
                        if content and content.strip():
                            # 限制长度
                            if len(content) > 800:
                                content = content[:800] + "..."
                            sections[section_name] = content
            
            elif hasattr(isolated_context, 'get_section'):
                # 使用get_section方法
                for section_name in self.STANDARD_SECTIONS:
                    content = isolated_context.get_section(section_name, "")
                    if content and content.strip():
                        if len(content) > 800:
                            content = content[:800] + "..."
                        sections[section_name] = content
        
        except Exception as e:
            logger.warning(f"从isolated_context提取失败: {e}")
        
        return sections
    
    async def _extract_from_context_attributes(self, context: Any) -> Dict[str, str]:
        """从context属性提取信息"""
        
        sections = {}
        
        try:
            # 基本任务信息
            if hasattr(context, 'task_description') and context.task_description:
                sections["Primary Request and Intent"] = context.task_description
            
            # 工作流信息
            if hasattr(context, 'workflow_id') and context.workflow_id:
                sections["Current Work Status"] = f"工作流ID: {context.workflow_id}"
            
            # 当前角色
            if hasattr(context, 'current_role') and context.current_role:
                current_work = sections.get("Current Work Status", "")
                sections["Current Work Status"] = f"{current_work}\n当前角色: {context.current_role}".strip()
            
            # 其他属性映射
            attribute_mapping = {
                'files': 'Files and Code Sections',
                'errors': 'Errors and Fixes',
                'messages': 'All User Messages', 
                'tasks': 'Pending Tasks',
                'technical_concepts': 'Key Technical Concepts',
                'problem_solving': 'Problem Solving Progress'
            }
            
            for attr_name, section_name in attribute_mapping.items():
                if hasattr(context, attr_name):
                    attr_value = getattr(context, attr_name)
                    if attr_value:
                        content = str(attr_value)
                        if len(content) > 500:
                            content = content[:500] + "..."
                        sections[section_name] = content
        
        except Exception as e:
            logger.warning(f"从属性提取上下文失败: {e}")
        
        return sections
    
    def _generate_cache_key(self, context: Any) -> str:
        """生成缓存key"""
        
        try:
            # 使用context的关键属性生成key
            key_parts = []
            
            if hasattr(context, 'workflow_id'):
                key_parts.append(f"wf_{context.workflow_id}")
            
            if hasattr(context, 'current_role'):
                key_parts.append(f"role_{context.current_role}")
            
            if hasattr(context, 'task_description'):
                # 使用task_description的hash
                key_parts.append(f"task_{hash(context.task_description)}")
            
            if not key_parts:
                key_parts.append(f"ctx_{id(context)}")
            
            return "_".join(key_parts)
            
        except Exception:
            return f"ctx_{id(context)}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        
        if cache_key not in self._processed_cache:
            return False
        
        if cache_key not in self._cache_timestamps:
            return False
        
        # 检查是否过期
        cache_time = self._cache_timestamps[cache_key]
        elapsed = (datetime.now() - cache_time).total_seconds()
        
        return elapsed < self.cache_ttl
    
    def clear_cache(self):
        """清除缓存"""
        self._processed_cache.clear()
        self._cache_timestamps.clear()
        logger.info("上下文处理缓存已清除")
