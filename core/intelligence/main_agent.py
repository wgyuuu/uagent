"""
UAgent Main Agent

主Agent负责整体任务协调和智能决策
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage

from models.base import (
    Task, TaskAnalysis, RoleRecommendation, WorkflowExecution,
    RecoveryDecision, ErrorClassification, ValidationResult
)
from models.workflow import WorkflowDefinition, ExecutionPlan
from .task_analysis import TaskAnalysisEngine
from .role_recommendation import RoleRecommendationEngine
from .dependency_analyzer import DependencyAnalyzer
from .error_recovery import ErrorRecoveryController

logger = structlog.get_logger(__name__)


class MainAgent:
    """
    主Agent - UAgent系统的智能决策中心
    
    负责任务分析、角色推荐、工作流协调和错误处理等核心决策功能
    """
    
    def __init__(self, 
                 llm: BaseLLM,
                 config: Dict[str, Any] = None):
        """
        初始化主Agent
        
        Args:
            llm: 大语言模型实例
            config: 配置参数
        """
        self.llm = llm
        self.config = config or {}
        
        # 初始化子组件
        self.task_analyzer = TaskAnalysisEngine(llm)
        self.role_recommender = RoleRecommendationEngine(llm)
        self.dependency_analyzer = DependencyAnalyzer()
        self.error_recovery = ErrorRecoveryController(llm)
        
        # 决策历史
        self.decision_history: List[Dict[str, Any]] = []
        
        # 性能指标
        self.performance_metrics = {
            "total_decisions": 0,
            "successful_recommendations": 0,
            "average_analysis_time": 0.0,
            "user_satisfaction": 0.0
        }
        
        logger.info("主Agent初始化完成")
    
    async def analyze_and_plan_task(self, task: Task) -> tuple[TaskAnalysis, WorkflowDefinition]:
        """
        分析任务并制定执行计划
        
        Args:
            task: 待分析的任务
            
        Returns:
            tuple: (任务分析结果, 工作流定义)
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始分析任务: {task.task_id}")
            
            # 1. 任务分析
            task_analysis = await self.task_analyzer.analyze_task(task)
            logger.info(f"任务分析完成: 领域={task_analysis.primary_domain}, 类型={task_analysis.task_type}")
            
            # 2. 角色推荐
            role_recommendation = await self.role_recommender.recommend_roles(task_analysis)
            logger.info(f"角色推荐完成: {role_recommendation.recommended_sequence}")
            
            # 3. 依赖关系验证
            dependency_validation = await self.dependency_analyzer.validate_role_sequence(
                role_recommendation.recommended_sequence
            )
            
            if not dependency_validation.is_valid:
                # 调整角色序列以满足依赖关系
                adjusted_sequence = await self.dependency_analyzer.adjust_role_sequence(
                    role_recommendation.recommended_sequence
                )
                role_recommendation.recommended_sequence = adjusted_sequence
                logger.info(f"角色序列已调整: {adjusted_sequence}")
            
            # 4. 创建工作流定义
            workflow_definition = await self._create_workflow_definition(
                task, task_analysis, role_recommendation
            )
            
            # 5. 记录决策
            await self._record_decision("task_analysis_and_planning", {
                "task_id": task.task_id,
                "analysis": task_analysis.dict(),
                "recommendation": role_recommendation.dict(),
                "workflow_id": workflow_definition.workflow_id
            })
            
            # 6. 更新性能指标
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_performance_metrics("analysis", execution_time, True)
            
            return task_analysis, workflow_definition
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_performance_metrics("analysis", execution_time, False)
            
            logger.error(f"任务分析失败: {e}")
            raise
    
    async def handle_workflow_error(self, 
                                  workflow: WorkflowExecution,
                                  failed_role: str,
                                  error: Exception) -> RecoveryDecision:
        """
        处理工作流错误
        
        Args:
            workflow: 工作流执行实例
            failed_role: 失败的角色
            error: 错误信息
            
        Returns:
            RecoveryDecision: 恢复决策
        """
        try:
            logger.warning(f"处理工作流错误: workflow={workflow.workflow_id}, role={failed_role}, error={error}")
            
            # 1. 错误分类
            error_classification = await self.error_recovery.classify_error(
                failed_role, error, {"workflow_id": workflow.workflow_id}
            )
            
            # 2. 影响评估
            impact_assessment = await self.dependency_analyzer.assess_failure_impact(
                failed_role, workflow.get_remaining_roles()
            )
            
            # 3. 生成恢复策略
            recovery_strategies = await self.error_recovery.generate_recovery_strategies(
                error_classification, workflow, impact_assessment
            )
            
            # 4. 制定恢复决策
            recovery_decision = await self.error_recovery.make_recovery_decision(
                error_classification, recovery_strategies, workflow
            )
            
            # 5. 记录决策
            await self._record_decision("error_recovery", {
                "workflow_id": workflow.workflow_id,
                "failed_role": failed_role,
                "error_type": type(error).__name__,
                "decision": recovery_decision.dict()
            })
            
            logger.info(f"错误恢复决策: {recovery_decision.decision_type}")
            return recovery_decision
            
        except Exception as e:
            logger.error(f"错误恢复处理失败: {e}")
            
            # 返回默认的手动干预决策
            return RecoveryDecision(
                decision_type="manual_intervention",
                rationale=f"自动错误恢复失败，需要手动干预: {str(e)}"
            )
    
    async def recommend_workflow_optimization(self, 
                                            workflow: WorkflowExecution) -> List[Dict[str, Any]]:
        """
        推荐工作流优化方案
        
        Args:
            workflow: 工作流执行实例
            
        Returns:
            List[Dict]: 优化建议列表
        """
        try:
            # 分析工作流性能
            performance_analysis = await self._analyze_workflow_performance(workflow)
            
            # 生成优化建议
            optimization_prompt = PromptTemplate(
                template="""
                分析以下工作流执行数据，提供优化建议：
                
                ## 工作流信息
                工作流ID: {workflow_id}
                角色序列: {roles}
                执行时间: {execution_time}
                
                ## 性能数据
                {performance_data}
                
                ## 质量指标
                {quality_metrics}
                
                请提供具体的优化建议，包括：
                1. 角色序列优化
                2. 并发执行机会
                3. 性能瓶颈解决
                4. 质量提升建议
                
                请以JSON格式返回优化建议。
                """,
                input_variables=["workflow_id", "roles", "execution_time", "performance_data", "quality_metrics"]
            )
            
            prompt = optimization_prompt.format(
                workflow_id=workflow.workflow_id,
                roles=", ".join(workflow.roles),
                execution_time=workflow.total_execution_time or 0,
                performance_data=str(workflow.performance_metrics),
                quality_metrics=str(workflow.quality_metrics)
            )
            
            response = await self.llm.agenerate([prompt])
            
            # 解析优化建议
            suggestions = await self._parse_optimization_suggestions(response.generations[0][0].text)
            
            logger.info(f"生成了{len(suggestions)}个优化建议")
            return suggestions
            
        except Exception as e:
            logger.error(f"优化建议生成失败: {e}")
            return []
    
    async def evaluate_task_completion(self, 
                                     workflow: WorkflowExecution) -> Dict[str, Any]:
        """
        评估任务完成质量
        
        Args:
            workflow: 完成的工作流执行实例
            
        Returns:
            Dict: 评估结果
        """
        try:
            evaluation_prompt = PromptTemplate(
                template="""
                评估以下任务的完成质量：
                
                ## 原始任务
                {original_task}
                
                ## 执行结果
                {execution_results}
                
                ## 质量标准
                {quality_criteria}
                
                请从以下维度进行评估：
                1. 完整性 (0-1): 任务是否完全完成
                2. 准确性 (0-1): 结果是否准确
                3. 质量 (0-1): 输出质量如何
                4. 效率 (0-1): 执行效率如何
                5. 用户满意度 (0-1): 预估用户满意度
                
                请以JSON格式返回评估结果，包括各维度分数和详细说明。
                """,
                input_variables=["original_task", "execution_results", "quality_criteria"]
            )
            
            prompt = optimization_prompt.format(
                original_task=workflow.task.description,
                execution_results=str(workflow.role_results),
                quality_criteria=str(workflow.task.quality_standards)
            )
            
            response = await self.llm.agenerate([prompt])
            evaluation = await self._parse_evaluation_result(response.generations[0][0].text)
            
            # 记录评估结果
            await self._record_decision("task_evaluation", {
                "workflow_id": workflow.workflow_id,
                "evaluation": evaluation
            })
            
            return evaluation
            
        except Exception as e:
            logger.error(f"任务评估失败: {e}")
            return {
                "completeness": 0.5,
                "accuracy": 0.5,
                "quality": 0.5,
                "efficiency": 0.5,
                "user_satisfaction": 0.5,
                "error": str(e)
            }
    
    async def get_system_insights(self) -> Dict[str, Any]:
        """
        获取系统运行洞察
        
        Returns:
            Dict: 系统洞察数据
        """
        try:
            # 分析决策历史
            recent_decisions = self.decision_history[-100:]  # 最近100个决策
            
            # 计算成功率
            successful_decisions = sum(1 for d in recent_decisions 
                                     if d.get("outcome", {}).get("success", False))
            success_rate = successful_decisions / len(recent_decisions) if recent_decisions else 0
            
            # 分析常见决策类型
            decision_types = {}
            for decision in recent_decisions:
                decision_type = decision.get("type", "unknown")
                decision_types[decision_type] = decision_types.get(decision_type, 0) + 1
            
            # 分析性能趋势
            performance_trend = await self._analyze_performance_trend()
            
            insights = {
                "system_health": {
                    "decision_success_rate": success_rate,
                    "total_decisions": len(self.decision_history),
                    "recent_decisions": len(recent_decisions)
                },
                "decision_patterns": decision_types,
                "performance_metrics": self.performance_metrics,
                "performance_trend": performance_trend,
                "recommendations": await self._generate_system_recommendations()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"系统洞察生成失败: {e}")
            return {"error": str(e)}
    
    # ===== 私有方法 =====
    
    async def _create_workflow_definition(self, 
                                        task: Task,
                                        task_analysis: TaskAnalysis,
                                        role_recommendation: RoleRecommendation) -> WorkflowDefinition:
        """创建工作流定义"""
        workflow = WorkflowDefinition(
            name=f"{task.title} - 执行计划",
            description=f"基于智能分析的{task.title}执行工作流",
            task=task,
            task_analysis=task_analysis,
            roles=role_recommendation.recommended_sequence,
            timeout_minutes=self.config.get("default_timeout", 60),
            max_retry_attempts=self.config.get("max_retries", 3),
            success_criteria=role_recommendation.success_metrics,
            created_by="main_agent"
        )
        
        return workflow
    
    async def _record_decision(self, decision_type: str, data: Dict[str, Any]):
        """记录决策历史"""
        decision_record = {
            "id": f"decision_{generate_id()}",
            "type": decision_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "agent_version": "2.0.0"
        }
        
        self.decision_history.append(decision_record)
        
        # 保持历史记录在合理范围内
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
    
    async def _update_performance_metrics(self, operation: str, execution_time: float, success: bool):
        """更新性能指标"""
        self.performance_metrics["total_decisions"] += 1
        
        if success:
            self.performance_metrics["successful_recommendations"] += 1
        
        # 更新平均分析时间
        total_decisions = self.performance_metrics["total_decisions"]
        current_avg = self.performance_metrics["average_analysis_time"]
        new_avg = (current_avg * (total_decisions - 1) + execution_time) / total_decisions
        self.performance_metrics["average_analysis_time"] = new_avg
    
    async def _analyze_workflow_performance(self, workflow: WorkflowExecution) -> Dict[str, Any]:
        """分析工作流性能"""
        performance_data = {
            "total_execution_time": workflow.total_execution_time or 0,
            "role_count": len(workflow.roles),
            "error_count": len(workflow.errors),
            "user_intervention_count": len(workflow.user_interventions),
            "quality_scores": workflow.quality_metrics,
            "performance_scores": workflow.performance_metrics
        }
        
        # 计算效率指标
        if workflow.total_execution_time:
            performance_data["efficiency_score"] = min(
                3600 / workflow.total_execution_time,  # 假设理想时间为1小时
                1.0
            )
        
        return performance_data
    
    async def _parse_optimization_suggestions(self, llm_response: str) -> List[Dict[str, Any]]:
        """解析LLM返回的优化建议"""
        try:
            import json
            # 尝试解析JSON响应
            suggestions = json.loads(llm_response)
            
            if isinstance(suggestions, dict) and "suggestions" in suggestions:
                return suggestions["suggestions"]
            elif isinstance(suggestions, list):
                return suggestions
            else:
                return [{"suggestion": llm_response, "type": "general"}]
                
        except json.JSONDecodeError:
            # 如果不是JSON格式，作为文本建议处理
            return [{"suggestion": llm_response, "type": "text"}]
    
    async def _parse_evaluation_result(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM返回的评估结果"""
        try:
            import json
            evaluation = json.loads(llm_response)
            
            # 确保所有必需的评估维度都存在
            required_dimensions = ["completeness", "accuracy", "quality", "efficiency", "user_satisfaction"]
            for dimension in required_dimensions:
                if dimension not in evaluation:
                    evaluation[dimension] = 0.5  # 默认中等分数
            
            return evaluation
            
        except json.JSONDecodeError:
            # 解析失败时返回默认评估
            return {
                "completeness": 0.5,
                "accuracy": 0.5,
                "quality": 0.5,
                "efficiency": 0.5,
                "user_satisfaction": 0.5,
                "note": llm_response
            }
    
    async def _analyze_performance_trend(self) -> Dict[str, Any]:
        """分析性能趋势"""
        recent_decisions = self.decision_history[-50:]  # 最近50个决策
        
        if len(recent_decisions) < 10:
            return {"trend": "insufficient_data"}
        
        # 分析时间趋势
        analysis_times = []
        success_rates = []
        
        for i in range(0, len(recent_decisions), 10):
            batch = recent_decisions[i:i+10]
            
            # 计算这批决策的平均时间和成功率
            avg_time = sum(d.get("execution_time", 0) for d in batch) / len(batch)
            success_rate = sum(1 for d in batch if d.get("outcome", {}).get("success", False)) / len(batch)
            
            analysis_times.append(avg_time)
            success_rates.append(success_rate)
        
        # 计算趋势
        if len(analysis_times) >= 2:
            time_trend = "improving" if analysis_times[-1] < analysis_times[0] else "degrading"
            success_trend = "improving" if success_rates[-1] > success_rates[0] else "degrading"
        else:
            time_trend = "stable"
            success_trend = "stable"
        
        return {
            "trend": "analyzed",
            "time_trend": time_trend,
            "success_trend": success_trend,
            "average_analysis_time": sum(analysis_times) / len(analysis_times),
            "average_success_rate": sum(success_rates) / len(success_rates)
        }
    
    async def _generate_system_recommendations(self) -> List[str]:
        """生成系统优化建议"""
        recommendations = []
        
        # 基于性能指标生成建议
        if self.performance_metrics["average_analysis_time"] > 30:
            recommendations.append("考虑优化LLM调用频率或使用更快的模型")
        
        success_rate = (
            self.performance_metrics["successful_recommendations"] / 
            max(self.performance_metrics["total_decisions"], 1)
        )
        
        if success_rate < 0.8:
            recommendations.append("建议优化角色推荐算法或增加更多训练数据")
        
        if len(self.decision_history) > 500:
            recommendations.append("考虑实施决策历史归档机制")
        
        return recommendations
    
    def get_status(self) -> Dict[str, Any]:
        """获取主Agent状态"""
        return {
            "agent_id": "main_agent",
            "status": "running",
            "performance_metrics": self.performance_metrics,
            "decision_history_size": len(self.decision_history),
            "components": {
                "task_analyzer": "active",
                "role_recommender": "active", 
                "dependency_analyzer": "active",
                "error_recovery": "active"
            },
            "last_updated": datetime.now().isoformat()
        }
