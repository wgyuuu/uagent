"""
UAgent Context Isolation Manager

上下文隔离管理器 - 确保角色间的上下文完全隔离
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from ...models.base import IsolatedRoleContext, HandoffContext, RoleResult
from ...models.workflow import WorkflowExecution

logger = structlog.get_logger(__name__)


class ContextIsolationManager:
    """
    上下文隔离管理器
    
    确保每个角色在完全隔离的上下文中执行，避免角色间的相互干扰
    """
    
    def __init__(self):
        """初始化上下文隔离管理器"""
        self.active_contexts: Dict[str, IsolatedRoleContext] = {}
        self.context_history: List[Dict[str, Any]] = []
        self.isolation_rules: Dict[str, List[str]] = {}
        
        logger.info("上下文隔离管理器初始化完成")
    
    async def create_isolated_context(self, 
                                    workflow_id: str,
                                    role: str,
                                    handoff_context: Optional[HandoffContext] = None) -> IsolatedRoleContext:
        """
        创建隔离的上下文
        
        Args:
            workflow_id: 工作流ID
            role: 角色名称
            handoff_context: 交接上下文
            
        Returns:
            IsolatedRoleContext: 隔离的上下文
        """
        try:
            logger.info(f"创建隔离上下文: 工作流={workflow_id}, 角色={role}")
            
            # 创建新的隔离上下文
            isolated_context = IsolatedRoleContext(
                role=role,
                workflow_id=workflow_id
            )
            
            # 如果有交接上下文，填充相关信息
            if handoff_context:
                await self._populate_from_handoff(isolated_context, handoff_context)
            
            # 应用隔离规则
            await self._apply_isolation_rules(isolated_context, role)
            
            # 注册上下文
            context_key = f"{workflow_id}_{role}"
            self.active_contexts[context_key] = isolated_context
            
            # 记录上下文创建
            await self._record_context_creation(isolated_context)
            
            logger.info(f"隔离上下文创建完成: {context_key}")
            return isolated_context
            
        except Exception as e:
            logger.error(f"创建隔离上下文失败: {e}")
            raise
    
    async def get_isolated_context(self, workflow_id: str, role: str) -> Optional[IsolatedRoleContext]:
        """获取隔离上下文"""
        context_key = f"{workflow_id}_{role}"
        return self.active_contexts.get(context_key)
    
    async def update_context_section(self, 
                                   workflow_id: str,
                                   role: str,
                                   section_name: str,
                                   content: str,
                                   importance_score: float = 0.5):
        """更新上下文段落"""
        context = await self.get_isolated_context(workflow_id, role)
        if context:
            context.update_section(section_name, content, importance_score)
            logger.debug(f"上下文段落已更新: {workflow_id}_{role}, {section_name}")
    
    async def finalize_context(self, workflow_id: str, role: str) -> IsolatedRoleContext:
        """完成上下文，准备交接"""
        context = await self.get_isolated_context(workflow_id, role)
        if not context:
            raise ValueError(f"上下文不存在: {workflow_id}_{role}")
        
        # 压缩上下文
        await self._compress_context(context)
        
        # 标记为已完成
        context.is_compressed = True
        
        logger.info(f"上下文已完成: {workflow_id}_{role}")
        return context
    
    async def cleanup_context(self, workflow_id: str, role: str):
        """清理上下文"""
        context_key = f"{workflow_id}_{role}"
        if context_key in self.active_contexts:
            context = self.active_contexts[context_key]
            
            # 记录清理历史
            await self._record_context_cleanup(context)
            
            # 从活跃上下文中移除
            del self.active_contexts[context_key]
            
            logger.info(f"上下文已清理: {context_key}")
    
    async def get_context_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        total_contexts = len(self.active_contexts)
        total_sections = sum(len(ctx.sections) for ctx in self.active_contexts.values())
        compressed_contexts = sum(1 for ctx in self.active_contexts.values() if ctx.is_compressed)
        
        return {
            "active_contexts": total_contexts,
            "total_sections": total_sections,
            "compressed_contexts": compressed_contexts,
            "context_history_size": len(self.context_history)
        }
    
    # ===== 私有方法 =====
    
    async def _populate_from_handoff(self, 
                                   isolated_context: IsolatedRoleContext,
                                   handoff_context: HandoffContext):
        """从交接上下文填充隔离上下文"""
        # 填充主要请求和意图
        isolated_context.update_section(
            "Primary Request and Intent",
            handoff_context.original_task,
            0.9
        )
        
        # 填充当前工作
        isolated_context.update_section(
            "Current Work",
            f"执行角色: {isolated_context.role}, 阶段: {handoff_context.current_stage}",
            0.8
        )
        
        # 填充问题解决
        if handoff_context.handoff_message:
            isolated_context.update_section(
                "Problem Solving",
                handoff_context.handoff_message,
                0.7
            )
        
        # 填充下一步操作
        if handoff_context.next_steps:
            isolated_context.update_section(
                "Pending Tasks",
                "; ".join(handoff_context.next_steps),
                0.8
            )
        
        # 填充技术上下文
        if handoff_context.technical_context:
            isolated_context.update_section(
                "Key Technical Concepts",
                str(handoff_context.technical_context),
                0.7
            )
        
        # 填充交付物
        if handoff_context.deliverables:
            isolated_context.update_section(
                "Files and Code Sections",
                str(handoff_context.deliverables),
                0.6
            )
    
    async def _apply_isolation_rules(self, context: IsolatedRoleContext, role: str):
        """应用隔离规则"""
        # 基于角色的隔离规则
        role_isolation_rules = {
            "方案规划师": ["architecture_design", "requirements_analysis"],
            "编码专家": ["implementation_details", "code_structure"],
            "测试工程师": ["test_cases", "quality_metrics"],
            "代码审查员": ["code_review", "quality_standards"],
            "数据分析师": ["data_insights", "analysis_methods"],
            "股票分析师": ["financial_analysis", "investment_recommendations"],
            "技术写作专家": ["content_structure", "writing_guidelines"],
            "调研分析师": ["research_methods", "market_insights"],
            "文档阅读专家": ["document_analysis", "information_extraction"],
            "知识整理专家": ["knowledge_organization", "content_categorization"]
        }
        
        # 应用角色特定的隔离规则
        if role in role_isolation_rules:
            rules = role_isolation_rules[role]
            context.metadata["isolation_rules"] = rules
            
            # 为每个规则创建相应的上下文段落
            for rule in rules:
                if rule not in context.sections:
                    context.sections[rule] = {
                        "name": rule,
                        "content": "",
                        "importance_score": 0.5,
                        "last_updated": datetime.now(),
                        "content_type": "text",
                        "metadata": {}
                    }
    
    async def _compress_context(self, context: IsolatedRoleContext):
        """压缩上下文"""
        # 计算压缩比例
        original_length = context.get_total_content_length()
        
        # 基于重要性分数过滤内容
        compressed_sections = {}
        for name, section in context.sections.items():
            if section.importance_score >= 0.3:  # 保留重要性分数>=0.3的内容
                compressed_sections[name] = section
        
        # 更新压缩后的上下文
        context.sections = compressed_sections
        
        # 计算压缩比例
        compressed_length = context.get_total_content_length()
        if original_length > 0:
            context.compression_ratio = compressed_length / original_length
        
        logger.info(f"上下文已压缩: 原始长度={original_length}, 压缩后长度={compressed_length}, 比例={context.compression_ratio}")
    
    async def _record_context_creation(self, context: IsolatedRoleContext):
        """记录上下文创建"""
        record = {
            "context_id": context.context_id,
            "workflow_id": context.workflow_id,
            "role": context.role,
            "created_at": context.created_at.isoformat(),
            "sections_count": len(context.sections),
            "action": "created"
        }
        
        self.context_history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self.context_history) > 10000:
            self.context_history = self.context_history[-5000:]
    
    async def _record_context_cleanup(self, context: IsolatedRoleContext):
        """记录上下文清理"""
        record = {
            "context_id": context.context_id,
            "workflow_id": context.workflow_id,
            "role": context.role,
            "created_at": context.created_at.isoformat(),
            "last_updated": context.last_updated.isoformat(),
            "sections_count": len(context.sections),
            "is_compressed": context.is_compressed,
            "compression_ratio": context.compression_ratio,
            "action": "cleaned"
        }
        
        self.context_history.append(record)
