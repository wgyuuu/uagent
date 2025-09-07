"""
Handoff Orchestrator

交接编排器 - 管理角色间的上下文交接
"""

from typing import Dict, List, Any, Optional, Tuple
import structlog
from datetime import datetime
import json
from dataclasses import dataclass, asdict

from models.base import HandoffContext, IsolatedRoleContext, RoleResult

logger = structlog.get_logger(__name__)


@dataclass
class HandoffRequest:
    """交接请求"""
    from_role_id: str
    to_role_id: str
    workflow_id: str
    task_id: str
    handoff_type: str  # "success", "failure", "partial", "manual"
    priority: str  # "high", "medium", "low"
    context_data: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class HandoffResponse:
    """交接响应"""
    handoff_id: str
    status: str  # "accepted", "rejected", "pending"
    message: str
    context_validation: Dict[str, Any]


class HandoffOrchestrator:
    """
    交接编排器
    
    负责管理角色间的上下文交接，确保信息传递的完整性和有效性
    """
    
    def __init__(self):
        self.active_handoffs: Dict[str, HandoffRequest] = {}
        self.handoff_history: List[Dict[str, Any]] = []
        self.handoff_templates: Dict[str, Dict[str, Any]] = {}
        self.validation_rules: Dict[str, List[str]] = {}
        
        # 初始化交接模板
        self._initialize_handoff_templates()
        
        # 初始化验证规则
        self._initialize_validation_rules()
        
        logger.info("交接编排器初始化完成")
    
    def _initialize_handoff_templates(self):
        """初始化交接模板"""
        self.handoff_templates = {
            "coding_expert_to_tester": {
                "required_fields": ["code_files", "test_requirements", "implementation_notes"],
                "optional_fields": ["performance_notes", "security_considerations"],
                "format": "structured",
                "priority": "high"
            },
            "planner_to_coding_expert": {
                "required_fields": ["architecture_design", "technical_specs", "constraints"],
                "optional_fields": ["alternative_approaches", "risk_assessment"],
                "format": "structured",
                "priority": "high"
            },
            "tester_to_reviewer": {
                "required_fields": ["test_results", "bug_reports", "test_coverage"],
                "optional_fields": ["performance_metrics", "security_findings"],
                "format": "structured",
                "priority": "medium"
            },
            "general_handoff": {
                "required_fields": ["task_summary", "key_findings", "next_steps"],
                "optional_fields": ["context_notes", "user_feedback"],
                "format": "flexible",
                "priority": "medium"
            }
        }
    
    def _initialize_validation_rules(self):
        """初始化验证规则"""
        self.validation_rules = {
            "content_completeness": [
                "检查必要字段是否完整",
                "验证数据格式是否正确",
                "确认上下文信息是否充分"
            ],
            "data_quality": [
                "检查数据一致性",
                "验证逻辑关系",
                "确认无重复或冲突信息"
            ],
            "context_relevance": [
                "检查信息相关性",
                "验证时效性",
                "确认对下一角色的有用性"
            ]
        }
    
    async def initiate_handoff(
        self,
        from_role_id: str,
        to_role_id: str,
        workflow_id: str,
        task_id: str,
        context_data: Dict[str, Any],
        handoff_type: str = "success",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> HandoffRequest:
        """
        发起交接请求
        
        Args:
            from_role_id: 发起角色ID
            to_role_id: 接收角色ID
            workflow_id: 工作流ID
            task_id: 任务ID
            context_data: 上下文数据
            handoff_type: 交接类型
            priority: 优先级
            metadata: 元数据
            
        Returns:
            交接请求对象
        """
        try:
            logger.info(f"发起交接: {from_role_id} -> {to_role_id}")
            
            # 创建交接请求
            handoff_request = HandoffRequest(
                from_role_id=from_role_id,
                to_role_id=to_role_id,
                workflow_id=workflow_id,
                task_id=task_id,
                handoff_type=handoff_type,
                priority=priority,
                context_data=context_data,
                metadata=metadata or {}
            )
            
            # 生成交接ID
            handoff_id = f"handoff_{workflow_id}_{from_role_id}_{to_role_id}_{int(datetime.now().timestamp())}"
            
            # 存储到活跃交接列表
            self.active_handoffs[handoff_id] = handoff_request
            
            # 记录到历史
            self.handoff_history.append({
                "handoff_id": handoff_id,
                "timestamp": datetime.now().isoformat(),
                "request": asdict(handoff_request)
            })
            
            logger.info(f"交接请求已创建: {handoff_id}")
            return handoff_request
            
        except Exception as e:
            logger.error(f"发起交接失败: {e}")
            raise
    
    async def process_handoff(
        self,
        handoff_id: str,
        to_role_id: str,
        acceptance: bool = True,
        feedback: Optional[str] = None
    ) -> HandoffResponse:
        """
        处理交接请求
        
        Args:
            handoff_id: 交接ID
            to_role_id: 接收角色ID
            acceptance: 是否接受
            feedback: 反馈信息
            
        Returns:
            交接响应对象
        """
        try:
            if handoff_id not in self.active_handoffs:
                raise ValueError(f"交接请求不存在: {handoff_id}")
            
            handoff_request = self.active_handoffs[handoff_id]
            
            if handoff_request.to_role_id != to_role_id:
                raise ValueError(f"角色ID不匹配: {to_role_id}")
            
            logger.info(f"处理交接请求: {handoff_id}")
            
            # 验证上下文数据
            validation_result = await self._validate_handoff_context(handoff_request)
            
            # 创建响应
            status = "accepted" if acceptance and validation_result["is_valid"] else "rejected"
            
            handoff_response = HandoffResponse(
                handoff_id=handoff_id,
                status=status,
                message=feedback or f"交接{'接受' if status == 'accepted' else '拒绝'}",
                context_validation=validation_result
            )
            
            # 更新交接状态
            if status == "accepted":
                # 从活跃列表移除
                del self.active_handoffs[handoff_id]
                
                # 更新历史记录
                for record in self.handoff_history:
                    if record["handoff_id"] == handoff_id:
                        record["response"] = asdict(handoff_response)
                        record["completed_at"] = datetime.now().isoformat()
                        break
            
            logger.info(f"交接处理完成: {handoff_id}, 状态: {status}")
            return handoff_response
            
        except Exception as e:
            logger.error(f"处理交接失败: {e}")
            raise
    
    async def _validate_handoff_context(self, handoff_request: HandoffRequest) -> Dict[str, Any]:
        """
        验证交接上下文
        
        Args:
            handoff_request: 交接请求
            
        Returns:
            验证结果
        """
        try:
            validation_result = {
                "is_valid": True,
                "score": 0.0,
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # 获取交接模板
            template_key = f"{handoff_request.from_role_id}_to_{handoff_request.to_role_id}"
            template = self.handoff_templates.get(template_key, self.handoff_templates["general_handoff"])
            
            # 检查必要字段
            required_fields = template.get("required_fields", [])
            missing_fields = []
            
            for field in required_fields:
                if field not in handoff_request.context_data or not handoff_request.context_data[field]:
                    missing_fields.append(field)
                    validation_result["is_valid"] = False
            
            if missing_fields:
                validation_result["issues"].append(f"缺少必要字段: {', '.join(missing_fields)}")
            
            # 检查数据质量
            data_quality_score = await self._assess_data_quality(handoff_request.context_data)
            validation_result["score"] = data_quality_score
            
            if data_quality_score < 0.7:
                validation_result["warnings"].append("数据质量较低，建议优化")
            
            # 检查上下文相关性
            relevance_score = await self._assess_context_relevance(
                handoff_request.context_data,
                handoff_request.to_role_id
            )
            
            if relevance_score < 0.6:
                validation_result["warnings"].append("上下文相关性较低")
            
            # 生成建议
            if missing_fields:
                validation_result["recommendations"].append(f"补充缺失字段: {', '.join(missing_fields)}")
            
            if data_quality_score < 0.7:
                validation_result["recommendations"].append("提高数据质量和完整性")
            
            if relevance_score < 0.6:
                validation_result["recommendations"].append("增强上下文的相关性和实用性")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"验证交接上下文失败: {e}")
            return {
                "is_valid": False,
                "score": 0.0,
                "issues": [f"验证过程出错: {str(e)}"],
                "warnings": [],
                "recommendations": ["检查系统状态并重试"]
            }
    
    async def _assess_data_quality(self, context_data: Dict[str, Any]) -> float:
        """评估数据质量"""
        try:
            score = 0.0
            total_checks = 0
            
            # 检查数据完整性
            if context_data:
                score += 1.0
                total_checks += 1
            
            # 检查数据深度
            if len(str(context_data)) > 100:
                score += 1.0
                total_checks += 1
            
            # 检查结构化程度
            structured_fields = 0
            for value in context_data.values():
                if isinstance(value, (dict, list)) or (isinstance(value, str) and len(value) > 10):
                    structured_fields += 1
            
            if structured_fields > 0:
                score += min(structured_fields / len(context_data), 1.0)
                total_checks += 1
            
            return score / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            logger.error(f"评估数据质量失败: {e}")
            return 0.0
    
    async def _assess_context_relevance(
        self, 
        context_data: Dict[str, Any], 
        target_role_id: str
    ) -> float:
        """评估上下文相关性"""
        try:
            # 基于角色类型评估相关性
            role_keywords = {
                "coding_expert": ["code", "implementation", "algorithm", "function", "class"],
                "tester": ["test", "bug", "coverage", "quality", "validation"],
                "reviewer": ["review", "analysis", "feedback", "improvement", "standards"],
                "planner": ["design", "architecture", "plan", "strategy", "requirements"]
            }
            
            target_keywords = role_keywords.get(target_role_id, [])
            if not target_keywords:
                return 0.5  # 默认中等相关性
            
            # 计算关键词匹配度
            context_text = str(context_data).lower()
            matches = sum(1 for keyword in target_keywords if keyword in context_text)
            
            relevance_score = min(matches / len(target_keywords), 1.0)
            return relevance_score
            
        except Exception as e:
            logger.error(f"评估上下文相关性失败: {e}")
            return 0.5
    
    async def get_handoff_template(
        self, 
        from_role_id: str, 
        to_role_id: str
    ) -> Dict[str, Any]:
        """获取交接模板"""
        template_key = f"{from_role_id}_to_{to_role_id}"
        return self.handoff_templates.get(template_key, self.handoff_templates["general_handoff"])
    
    async def create_handoff_context(
        self,
        handoff_request: HandoffRequest,
        role_result: RoleResult
    ) -> HandoffContext:
        """
        创建交接上下文
        
        Args:
            handoff_request: 交接请求
            role_result: 角色执行结果
            
        Returns:
            交接上下文对象
        """
        try:
            logger.info(f"创建交接上下文: {handoff_request.handoff_id}")
            
            # 构建交接内容
            handoff_content = {
                "task_summary": role_result.summary,
                "key_findings": role_result.key_findings or [],
                "deliverables": role_result.deliverables or [],
                "next_steps": role_result.next_steps or [],
                "context_notes": handoff_request.context_data,
                "metadata": {
                    "from_role": handoff_request.from_role_id,
                    "to_role": handoff_request.to_role_id,
                    "handoff_type": handoff_request.handoff_type,
                    "priority": handoff_request.priority,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # 创建HandoffContext对象
            handoff_context = HandoffContext(
                handoff_id=handoff_request.handoff_id,
                from_role_id=handoff_request.from_role_id,
                to_role_id=handoff_request.to_role_id,
                workflow_id=handoff_request.workflow_id,
                task_id=handoff_request.task_id,
                content=handoff_content,
                status="pending",
                created_at=datetime.now(),
                metadata=handoff_request.metadata
            )
            
            logger.info(f"交接上下文创建完成: {handoff_request.handoff_id}")
            return handoff_context
            
        except Exception as e:
            logger.error(f"创建交接上下文失败: {e}")
            raise
    
    async def get_handoff_status(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """获取交接状态"""
        if handoff_id in self.active_handoffs:
            handoff_request = self.active_handoffs[handoff_id]
            return {
                "handoff_id": handoff_id,
                "status": "active",
                "from_role": handoff_request.from_role_id,
                "to_role": handoff_request.to_role_id,
                "created_at": handoff_request.metadata.get("timestamp", "unknown"),
                "priority": handoff_request.priority
            }
        
        # 检查历史记录
        for record in self.handoff_history:
            if record["handoff_id"] == handoff_id:
                return {
                    "handoff_id": handoff_id,
                    "status": "completed",
                    "from_role": record["request"]["from_role_id"],
                    "to_role": record["request"]["to_role_id"],
                    "created_at": record["timestamp"],
                    "completed_at": record.get("completed_at", "unknown")
                }
        
        return None
    
    async def get_active_handoffs(self, role_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取活跃的交接列表"""
        active_list = []
        
        for handoff_id, handoff_request in self.active_handoffs.items():
            if role_id is None or handoff_request.to_role_id == role_id:
                active_list.append({
                    "handoff_id": handoff_id,
                    "from_role": handoff_request.from_role_id,
                    "to_role": handoff_request.to_role_id,
                    "workflow_id": handoff_request.workflow_id,
                    "task_id": handoff_request.task_id,
                    "handoff_type": handoff_request.handoff_type,
                    "priority": handoff_request.priority,
                    "created_at": handoff_request.metadata.get("timestamp", "unknown")
                })
        
        return active_list
    
    async def get_handoff_statistics(self) -> Dict[str, Any]:
        """获取交接统计信息"""
        total_handoffs = len(self.handoff_history)
        active_handoffs = len(self.active_handoffs)
        completed_handoffs = total_handoffs - active_handoffs
        
        # 按类型统计
        type_stats = {}
        for record in self.handoff_history:
            handoff_type = record["request"]["handoff_type"]
            type_stats[handoff_type] = type_stats.get(handoff_type, 0) + 1
        
        return {
            "total_handoffs": total_handoffs,
            "active_handoffs": active_handoffs,
            "completed_handoffs": completed_handoffs,
            "type_distribution": type_stats,
            "success_rate": completed_handoffs / total_handoffs if total_handoffs > 0 else 0.0
        }
