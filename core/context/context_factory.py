"""
Context Factory

上下文工厂 - 创建和管理角色上下文
"""

from typing import Dict, List, Any, Optional, Type
import structlog
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass

from ...models.base import IsolatedRoleContext, HandoffContext
from ...models.roles import RoleDefinition

logger = structlog.get_logger(__name__)


@dataclass
class ContextTemplate:
    """上下文模板"""
    template_id: str
    role_type: str
    required_fields: List[str]
    optional_fields: List[str]
    default_values: Dict[str, Any]
    validation_rules: Dict[str, Any]
    metadata: Dict[str, Any]


class ContextFactory:
    """
    上下文工厂
    
    负责创建、配置和管理角色上下文，确保每个角色都有合适的执行环境
    """
    
    def __init__(self):
        self.context_templates: Dict[str, ContextTemplate] = {}
        self.active_contexts: Dict[str, IsolatedRoleContext] = {}
        self.context_history: List[Dict[str, Any]] = []
        
        # 初始化默认模板
        self._initialize_default_templates()
        
        logger.info("上下文工厂初始化完成")
    
    def _initialize_default_templates(self):
        """初始化默认上下文模板"""
        # 编码专家模板
        self.context_templates["coding_expert"] = ContextTemplate(
            template_id="coding_expert",
            role_type="coding_expert",
            required_fields=[
                "primary_request",
                "technical_requirements",
                "code_files",
                "dependencies"
            ],
            optional_fields=[
                "performance_requirements",
                "security_considerations",
                "testing_guidelines"
            ],
            default_values={
                "environment": "development",
                "language": "python",
                "framework": "standard"
            },
            validation_rules={
                "min_code_files": 1,
                "max_context_size": 10000
            },
            metadata={
                "description": "编码专家上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 方案规划师模板
        self.context_templates["planner"] = ContextTemplate(
            template_id="planner",
            role_type="planner",
            required_fields=[
                "primary_request",
                "business_requirements",
                "technical_constraints",
                "success_criteria"
            ],
            optional_fields=[
                "budget_constraints",
                "timeline_requirements",
                "risk_factors"
            ],
            default_values={
                "planning_approach": "agile",
                "documentation_level": "detailed"
            },
            validation_rules={
                "min_requirements": 3,
                "max_context_size": 15000
            },
            metadata={
                "description": "方案规划师上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 测试工程师模板
        self.context_templates["tester"] = ContextTemplate(
            template_id="tester",
            role_type="tester",
            required_fields=[
                "primary_request",
                "test_requirements",
                "code_to_test",
                "test_environment"
            ],
            optional_fields=[
                "performance_benchmarks",
                "security_testing",
                "automation_preferences"
            ],
            default_values={
                "testing_approach": "comprehensive",
                "reporting_level": "detailed"
            },
            validation_rules={
                "min_test_requirements": 2,
                "max_context_size": 12000
            },
            metadata={
                "description": "测试工程师上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 代码审查员模板
        self.context_templates["reviewer"] = ContextTemplate(
            template_id="reviewer",
            role_type="reviewer",
            required_fields=[
                "primary_request",
                "code_to_review",
                "review_standards",
                "quality_metrics"
            ],
            optional_fields=[
                "performance_considerations",
                "security_review",
                "documentation_review"
            ],
            default_values={
                "review_depth": "thorough",
                "feedback_style": "constructive"
            },
            validation_rules={
                "min_code_size": 100,
                "max_context_size": 10000
            },
            metadata={
                "description": "代码审查员上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 数据分析师模板
        self.context_templates["data_analyst"] = ContextTemplate(
            template_id="data_analyst",
            role_type="data_analyst",
            required_fields=[
                "primary_request",
                "data_sources",
                "analysis_objectives",
                "output_requirements"
            ],
            optional_fields=[
                "data_quality_requirements",
                "visualization_preferences",
                "statistical_methods"
            ],
            default_values={
                "analysis_approach": "exploratory",
                "output_format": "comprehensive_report"
            },
            validation_rules={
                "min_data_sources": 1,
                "max_context_size": 20000
            },
            metadata={
                "description": "数据分析师上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 内容创作者模板
        self.context_templates["content_creator"] = ContextTemplate(
            template_id="content_creator",
            role_type="content_creator",
            required_fields=[
                "primary_request",
                "content_type",
                "target_audience",
                "key_messages"
            ],
            optional_fields=[
                "style_guidelines",
                "format_requirements",
                "reference_materials"
            ],
            default_values={
                "writing_style": "professional",
                "tone": "informative"
            },
            validation_rules={
                "min_key_messages": 1,
                "max_context_size": 15000
            },
            metadata={
                "description": "内容创作者上下文模板",
                "version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        )
    
    async def create_context(
        self,
        role_id: str,
        role_type: str,
        primary_request: str,
        context_data: Dict[str, Any],
        workflow_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> IsolatedRoleContext:
        """
        创建角色上下文
        
        Args:
            role_id: 角色ID
            role_type: 角色类型
            primary_request: 主要请求
            context_data: 上下文数据
            workflow_id: 工作流ID
            task_id: 任务ID
            
        Returns:
            隔离的角色上下文对象
        """
        try:
            logger.info(f"为角色 {role_id} 创建上下文")
            
            # 获取角色模板
            template = self.context_templates.get(role_type)
            if not template:
                template = self.context_templates.get("planner")  # 使用默认模板
            
            # 验证必要字段
            await self._validate_context_data(template, context_data)
            
            # 创建上下文ID
            context_id = f"ctx_{role_id}_{uuid.uuid4().hex[:8]}"
            
            # 构建完整上下文数据
            full_context_data = await self._build_full_context(
                template, 
                primary_request, 
                context_data
            )
            
            # 创建IsolatedRoleContext对象
            isolated_context = IsolatedRoleContext(
                context_id=context_id,
                role_id=role_id,
                role_type=role_type,
                primary_request=primary_request,
                context_data=full_context_data,
                workflow_id=workflow_id,
                task_id=task_id,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                metadata={
                    "template_id": template.template_id,
                    "template_version": template.metadata.get("version", "1.0"),
                    "validation_status": "validated",
                    "compression_applied": False
                }
            )
            
            # 存储到活跃上下文
            self.active_contexts[context_id] = isolated_context
            
            # 记录到历史
            self.context_history.append({
                "context_id": context_id,
                "role_id": role_id,
                "role_type": role_type,
                "workflow_id": workflow_id,
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            })
            
            logger.info(f"角色 {role_id} 上下文创建完成: {context_id}")
            return isolated_context
            
        except Exception as e:
            logger.error(f"创建角色上下文失败: {e}")
            raise
    
    async def _validate_context_data(
        self, 
        template: ContextTemplate, 
        context_data: Dict[str, Any]
    ):
        """验证上下文数据"""
        missing_fields = []
        
        for field in template.required_fields:
            if field not in context_data or not context_data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"缺少必要字段: {', '.join(missing_fields)}")
        
        # 应用验证规则
        for rule_name, rule_value in template.validation_rules.items():
            if rule_name == "min_code_files" and "code_files" in context_data:
                if len(context_data["code_files"]) < rule_value:
                    raise ValueError(f"代码文件数量不足: 需要至少 {rule_value} 个")
            
            elif rule_name == "max_context_size":
                context_size = len(str(context_data))
                if context_size > rule_value:
                    raise ValueError(f"上下文大小超出限制: {context_size} > {rule_value}")
    
    async def _build_full_context(
        self,
        template: ContextTemplate,
        primary_request: str,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建完整上下文数据"""
        full_context = {
            "primary_request": primary_request,
            "role_type": template.role_type,
            "template_info": {
                "template_id": template.template_id,
                "version": template.metadata.get("version", "1.0"),
                "description": template.metadata.get("description", "")
            }
        }
        
        # 添加必要字段
        for field in template.required_fields:
            if field in context_data:
                full_context[field] = context_data[field]
            else:
                full_context[field] = f"待补充: {field}"
        
        # 添加可选字段
        for field in template.optional_fields:
            if field in context_data:
                full_context[field] = context_data[field]
        
        # 添加默认值
        for field, default_value in template.default_values.items():
            if field not in full_context:
                full_context[field] = default_value
        
        # 添加元数据
        full_context["_metadata"] = {
            "created_at": datetime.now().isoformat(),
            "template_used": template.template_id,
            "validation_status": "validated"
        }
        
        return full_context
    
    async def get_context(self, context_id: str) -> Optional[IsolatedRoleContext]:
        """获取上下文"""
        if context_id in self.active_contexts:
            context = self.active_contexts[context_id]
            context.last_accessed = datetime.now()
            context.access_count += 1
            return context
        
        return None
    
    async def update_context(
        self,
        context_id: str,
        updates: Dict[str, Any]
    ) -> Optional[IsolatedRoleContext]:
        """更新上下文"""
        if context_id not in self.active_contexts:
            return None
        
        context = self.active_contexts[context_id]
        
        # 更新上下文数据
        for key, value in updates.items():
            if key in context.context_data:
                context.context_data[key] = value
        
        # 更新元数据
        context.last_accessed = datetime.now()
        context.metadata["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"上下文 {context_id} 已更新")
        return context
    
    async def close_context(self, context_id: str) -> bool:
        """关闭上下文"""
        if context_id not in self.active_contexts:
            return False
        
        context = self.active_contexts[context_id]
        
        # 更新历史记录
        for record in self.context_history:
            if record["context_id"] == context_id:
                record["status"] = "closed"
                record["closed_at"] = datetime.now().isoformat()
                break
        
        # 从活跃上下文移除
        del self.active_contexts[context_id]
        
        logger.info(f"上下文 {context_id} 已关闭")
        return True
    
    async def get_contexts_by_role(self, role_id: str) -> List[IsolatedRoleContext]:
        """获取指定角色的所有上下文"""
        return [
            context for context in self.active_contexts.values()
            if context.role_id == role_id
        ]
    
    async def get_contexts_by_workflow(self, workflow_id: str) -> List[IsolatedRoleContext]:
        """获取指定工作流的所有上下文"""
        return [
            context for context in self.active_contexts.values()
            if context.workflow_id == workflow_id
        ]
    
    async def create_context_from_handoff(
        self,
        handoff_context: HandoffContext,
        role_id: str
    ) -> IsolatedRoleContext:
        """
        从交接上下文创建角色上下文
        
        Args:
            handoff_context: 交接上下文
            role_id: 目标角色ID
            
        Returns:
            新的角色上下文
        """
        try:
            logger.info(f"从交接上下文创建角色 {role_id} 的上下文")
            
            # 提取交接内容
            handoff_content = handoff_context.content
            
            # 确定角色类型（可以从交接内容推断或使用默认值）
            role_type = self._infer_role_type_from_handoff(handoff_content, role_id)
            
            # 构建上下文数据
            context_data = {
                "primary_request": handoff_content.get("task_summary", "处理交接任务"),
                "handoff_source": handoff_context.from_role_id,
                "handoff_id": handoff_context.handoff_id,
                "key_findings": handoff_content.get("key_findings", []),
                "deliverables": handoff_content.get("deliverables", []),
                "next_steps": handoff_content.get("next_steps", []),
                "context_notes": handoff_content.get("context_notes", {}),
                "handoff_metadata": handoff_content.get("metadata", {})
            }
            
            # 创建新上下文
            new_context = await self.create_context(
                role_id=role_id,
                role_type=role_type,
                primary_request=context_data["primary_request"],
                context_data=context_data,
                workflow_id=handoff_context.workflow_id,
                task_id=handoff_context.task_id
            )
            
            # 添加交接相关信息到元数据
            new_context.metadata["handoff_source"] = handoff_context.from_role_id
            new_context.metadata["handoff_id"] = handoff_context.handoff_id
            new_context.metadata["created_from_handoff"] = True
            
            logger.info(f"从交接上下文创建角色 {role_id} 上下文完成")
            return new_context
            
        except Exception as e:
            logger.error(f"从交接上下文创建角色上下文失败: {e}")
            raise
    
    def _infer_role_type_from_handoff(
        self, 
        handoff_content: Dict[str, Any], 
        role_id: str
    ) -> str:
        """从交接内容推断角色类型"""
        # 基于角色ID推断
        if "coding" in role_id.lower():
            return "coding_expert"
        elif "plan" in role_id.lower():
            return "planner"
        elif "test" in role_id.lower():
            return "tester"
        elif "review" in role_id.lower():
            return "reviewer"
        elif "data" in role_id.lower() or "analysis" in role_id.lower():
            return "data_analyst"
        elif "content" in role_id.lower() or "write" in role_id.lower():
            return "content_creator"
        else:
            return "planner"  # 默认使用规划师模板
    
    async def get_context_statistics(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        total_contexts = len(self.active_contexts)
        total_history = len(self.context_history)
        
        # 按角色类型统计
        role_stats = {}
        for context in self.active_contexts.values():
            role_type = context.role_type
            role_stats[role_type] = role_stats.get(role_type, 0) + 1
        
        # 按工作流统计
        workflow_stats = {}
        for context in self.active_contexts.values():
            if context.workflow_id:
                workflow_stats[context.workflow_id] = workflow_stats.get(context.workflow_id, 0) + 1
        
        return {
            "active_contexts": total_contexts,
            "total_history": total_history,
            "role_distribution": role_stats,
            "workflow_distribution": workflow_stats,
            "templates_available": len(self.context_templates)
        }
    
    async def cleanup_expired_contexts(self, max_age_hours: int = 24):
        """清理过期的上下文"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            expired_contexts = []
            
            for context_id, context in self.active_contexts.items():
                if context.last_accessed < cutoff_time:
                    expired_contexts.append(context_id)
            
            for context_id in expired_contexts:
                await self.close_context(context_id)
            
            logger.info(f"清理了 {len(expired_contexts)} 个过期上下文")
            
        except Exception as e:
            logger.error(f"清理过期上下文失败: {e}")
            raise
    
    async def register_custom_template(self, template: ContextTemplate):
        """注册自定义上下文模板"""
        try:
            if template.template_id in self.context_templates:
                logger.warning(f"模板 {template.template_id} 已存在，将被覆盖")
            
            self.context_templates[template.template_id] = template
            logger.info(f"自定义模板 {template.template_id} 注册成功")
            
        except Exception as e:
            logger.error(f"注册自定义模板失败: {e}")
            raise
