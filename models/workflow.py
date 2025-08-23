"""
UAgent Workflow Models

定义工作流相关的数据模型和状态管理
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import BaseModel, Field, validator
from .base import (
    WorkflowStatus, RoleStatus, TaskStatus, ComplexityLevel,
    Task, TaskAnalysis, RoleResult, HandoffContext,
    generate_id, current_timestamp
)


# ===== 工作流定义模型 =====

class WorkflowTemplate(BaseModel):
    """工作流模板模型"""
    template_id: str = Field(default_factory=lambda: f"template_{generate_id()}", description="模板ID")
    
    # 基本信息
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    category: str = Field(..., description="模板类别")
    
    # 角色配置
    role_sequence: List[str] = Field(..., description="角色序列")
    optional_roles: List[str] = Field(default_factory=list, description="可选角色")
    parallel_roles: Dict[str, List[str]] = Field(default_factory=dict, description="并行角色组")
    
    # 适用条件
    applicable_domains: List[str] = Field(default_factory=list, description="适用领域")
    applicable_task_types: List[str] = Field(default_factory=list, description="适用任务类型")
    complexity_range: List[str] = Field(default_factory=list, description="复杂度范围")
    
    # 质量控制
    quality_gates: Dict[str, List[str]] = Field(default_factory=dict, description="质量门禁")
    success_criteria: List[str] = Field(default_factory=list, description="成功标准")
    
    # 配置参数
    default_timeout_minutes: int = Field(default=60, description="默认超时时间")
    max_retry_attempts: int = Field(default=3, description="最大重试次数")
    allow_skip_optional: bool = Field(default=True, description="允许跳过可选角色")
    
    # 元数据
    version: str = Field(default="1.0.0", description="模板版本")
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(default_factory=current_timestamp, description="创建时间")
    updated_at: datetime = Field(default_factory=current_timestamp, description="更新时间")
    is_active: bool = Field(default=True, description="是否激活")
    usage_count: int = Field(default=0, description="使用次数")
    
    def is_applicable(self, task_analysis: TaskAnalysis) -> bool:
        """检查模板是否适用于任务"""
        # 检查领域匹配
        if self.applicable_domains:
            domain_match = task_analysis.primary_domain.value in self.applicable_domains
            if not domain_match:
                return False
        
        # 检查任务类型匹配
        if self.applicable_task_types:
            type_match = task_analysis.task_type.value in self.applicable_task_types
            if not type_match:
                return False
        
        # 检查复杂度匹配
        if self.complexity_range:
            complexity_match = task_analysis.complexity_level.value in self.complexity_range
            if not complexity_match:
                return False
        
        return True


class WorkflowDefinition(BaseModel):
    """工作流定义模型"""
    workflow_id: str = Field(default_factory=lambda: f"workflow_{generate_id()}", description="工作流ID")
    
    # 基本信息
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    template_id: Optional[str] = Field(None, description="基于的模板ID")
    
    # 任务关联
    task: Task = Field(..., description="关联任务")
    task_analysis: TaskAnalysis = Field(..., description="任务分析结果")
    
    # 角色配置
    roles: List[str] = Field(..., description="角色序列")
    role_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="角色配置")
    
    # 执行配置
    execution_mode: str = Field(default="sequential", description="执行模式")  # sequential, parallel, hybrid
    timeout_minutes: int = Field(default=60, description="超时时间")
    max_retry_attempts: int = Field(default=3, description="最大重试次数")
    allow_skip_optional: bool = Field(default=True, description="允许跳过可选角色")
    
    # 质量控制
    quality_gates: Dict[str, List[str]] = Field(default_factory=dict, description="质量门禁")
    success_criteria: List[str] = Field(default_factory=list, description="成功标准")
    
    # 错误处理
    error_handling_strategy: str = Field(default="auto_recovery", description="错误处理策略")
    critical_roles: List[str] = Field(default_factory=list, description="关键角色")
    
    # 用户交互
    user_interaction_points: List[str] = Field(default_factory=list, description="用户交互点")
    approval_required_roles: List[str] = Field(default_factory=list, description="需要批准的角色")
    
    # 元数据
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(default_factory=current_timestamp, description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class WorkflowStep(BaseModel):
    """工作流步骤模型"""
    step_id: str = Field(default_factory=lambda: f"step_{generate_id()}", description="步骤ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 步骤信息
    step_index: int = Field(..., description="步骤索引")
    role: str = Field(..., description="执行角色")
    step_type: str = Field(default="role_execution", description="步骤类型")
    
    # 状态信息
    status: RoleStatus = Field(default=RoleStatus.PENDING, description="步骤状态")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")
    
    # 输入输出
    input_context: Optional[HandoffContext] = Field(None, description="输入上下文")
    output_result: Optional[RoleResult] = Field(None, description="输出结果")
    
    # 错误处理
    error_count: int = Field(default=0, description="错误次数")
    last_error: Optional[str] = Field(None, description="最后错误")
    recovery_actions: List[Dict[str, Any]] = Field(default_factory=list, description="恢复操作")
    
    # 质量评估
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="质量分数")
    user_satisfaction: Optional[float] = Field(None, ge=0.0, le=1.0, description="用户满意度")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    def mark_started(self):
        """标记步骤开始"""
        self.status = RoleStatus.RUNNING
        self.started_at = current_timestamp()
    
    def mark_completed(self, result: RoleResult):
        """标记步骤完成"""
        self.status = RoleStatus.COMPLETED
        self.completed_at = current_timestamp()
        self.output_result = result
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error: str):
        """标记步骤失败"""
        self.status = RoleStatus.FAILED
        self.completed_at = current_timestamp()
        self.last_error = error
        self.error_count += 1
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()


# ===== 执行监控模型 =====

class ExecutionMetrics(BaseModel):
    """执行指标模型"""
    workflow_id: str = Field(..., description="工作流ID")
    
    # 时间指标
    total_execution_time: float = Field(default=0.0, description="总执行时间(秒)")
    average_step_time: float = Field(default=0.0, description="平均步骤时间(秒)")
    waiting_time: float = Field(default=0.0, description="等待时间(秒)")
    
    # 资源指标
    peak_memory_usage: float = Field(default=0.0, description="峰值内存使用(MB)")
    average_cpu_usage: float = Field(default=0.0, description="平均CPU使用率")
    disk_io_operations: int = Field(default=0, description="磁盘IO操作次数")
    network_requests: int = Field(default=0, description="网络请求次数")
    
    # 质量指标
    overall_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="整体质量分数")
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="完整性分数")
    accuracy_score: float = Field(default=0.0, ge=0.0, le=1.0, description="准确性分数")
    
    # 错误指标
    total_errors: int = Field(default=0, description="总错误数")
    recovered_errors: int = Field(default=0, description="已恢复错误数")
    critical_errors: int = Field(default=0, description="严重错误数")
    
    # 用户交互指标
    user_questions: int = Field(default=0, description="用户问题数")
    user_interventions: int = Field(default=0, description="用户干预次数")
    average_response_time: float = Field(default=0.0, description="平均用户响应时间(秒)")
    
    # 更新时间
    last_updated: datetime = Field(default_factory=current_timestamp, description="最后更新时间")
    
    def update_from_step(self, step: WorkflowStep):
        """从步骤更新指标"""
        if step.execution_time:
            self.total_execution_time += step.execution_time
        
        if step.error_count > 0:
            self.total_errors += step.error_count
        
        if step.quality_score:
            # 更新质量分数（简单平均）
            current_steps = 1  # 这里应该从上下文获取当前步骤数
            self.overall_quality_score = (
                self.overall_quality_score * (current_steps - 1) + step.quality_score
            ) / current_steps
        
        self.last_updated = current_timestamp()


# ===== 工作流事件模型 =====

class WorkflowEvent(BaseModel):
    """工作流事件模型"""
    event_id: str = Field(default_factory=lambda: f"event_{generate_id()}", description="事件ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 事件信息
    event_type: str = Field(..., description="事件类型")
    event_name: str = Field(..., description="事件名称")
    description: str = Field(default="", description="事件描述")
    
    # 事件数据
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    context: Dict[str, Any] = Field(default_factory=dict, description="事件上下文")
    
    # 来源信息
    source_role: Optional[str] = Field(None, description="来源角色")
    source_step_id: Optional[str] = Field(None, description="来源步骤ID")
    
    # 时间信息
    timestamp: datetime = Field(default_factory=current_timestamp, description="事件时间")
    
    # 处理状态
    is_processed: bool = Field(default=False, description="是否已处理")
    processed_at: Optional[datetime] = Field(None, description="处理时间")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class WorkflowEventHandler(BaseModel):
    """工作流事件处理器模型"""
    handler_id: str = Field(default_factory=lambda: f"handler_{generate_id()}", description="处理器ID")
    
    # 处理器信息
    name: str = Field(..., description="处理器名称")
    description: str = Field(..., description="处理器描述")
    event_types: List[str] = Field(..., description="处理的事件类型")
    
    # 处理逻辑
    handler_function: str = Field(..., description="处理函数名称")
    handler_config: Dict[str, Any] = Field(default_factory=dict, description="处理器配置")
    
    # 执行配置
    is_async: bool = Field(default=True, description="是否异步处理")
    timeout_seconds: int = Field(default=30, description="处理超时时间")
    retry_attempts: int = Field(default=3, description="重试次数")
    
    # 状态
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(default_factory=current_timestamp, description="创建时间")


# ===== 工作流状态管理 =====

class WorkflowState(BaseModel):
    """工作流状态模型"""
    workflow_id: str = Field(..., description="工作流ID")
    
    # 当前状态
    current_status: WorkflowStatus = Field(..., description="当前状态")
    current_step_index: int = Field(default=0, description="当前步骤索引")
    current_role: Optional[str] = Field(None, description="当前角色")
    
    # 状态历史
    status_history: List[Dict[str, Any]] = Field(default_factory=list, description="状态历史")
    
    # 暂停和恢复
    is_paused: bool = Field(default=False, description="是否暂停")
    paused_at: Optional[datetime] = Field(None, description="暂停时间")
    pause_reason: Optional[str] = Field(None, description="暂停原因")
    
    # 检查点
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list, description="检查点")
    last_checkpoint: Optional[datetime] = Field(None, description="最后检查点时间")
    
    # 更新时间
    last_updated: datetime = Field(default_factory=current_timestamp, description="最后更新时间")
    
    def transition_to(self, new_status: WorkflowStatus, reason: str = ""):
        """状态转换"""
        old_status = self.current_status
        self.current_status = new_status
        
        # 记录状态历史
        self.status_history.append({
            "from_status": old_status.value,
            "to_status": new_status.value,
            "reason": reason,
            "timestamp": current_timestamp().isoformat()
        })
        
        self.last_updated = current_timestamp()
    
    def pause(self, reason: str = ""):
        """暂停工作流"""
        if not self.is_paused:
            self.is_paused = True
            self.paused_at = current_timestamp()
            self.pause_reason = reason
            self.transition_to(WorkflowStatus.PAUSED, reason)
    
    def resume(self):
        """恢复工作流"""
        if self.is_paused:
            self.is_paused = False
            self.paused_at = None
            self.pause_reason = None
            self.transition_to(WorkflowStatus.RUNNING, "resumed")
    
    def create_checkpoint(self, data: Dict[str, Any]):
        """创建检查点"""
        checkpoint = {
            "checkpoint_id": generate_id("checkpoint"),
            "step_index": self.current_step_index,
            "current_role": self.current_role,
            "status": self.current_status.value,
            "data": data,
            "timestamp": current_timestamp().isoformat()
        }
        
        self.checkpoints.append(checkpoint)
        self.last_checkpoint = current_timestamp()
        
        # 保持检查点数量在合理范围内
        if len(self.checkpoints) > 20:
            self.checkpoints = self.checkpoints[-10:]


# ===== 工作流执行计划 =====

class ExecutionPlan(BaseModel):
    """执行计划模型"""
    plan_id: str = Field(default_factory=lambda: f"plan_{generate_id()}", description="计划ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 计划信息
    planned_steps: List[WorkflowStep] = Field(..., description="计划步骤")
    estimated_total_time: int = Field(..., description="预估总时间(分钟)")
    
    # 资源规划
    required_resources: Dict[str, Any] = Field(default_factory=dict, description="所需资源")
    resource_allocation: Dict[str, Any] = Field(default_factory=dict, description="资源分配")
    
    # 风险评估
    identified_risks: List[Dict[str, Any]] = Field(default_factory=list, description="识别的风险")
    mitigation_strategies: Dict[str, str] = Field(default_factory=dict, description="缓解策略")
    
    # 质量计划
    quality_checkpoints: List[str] = Field(default_factory=list, description="质量检查点")
    testing_strategy: Optional[str] = Field(None, description="测试策略")
    
    # 创建信息
    created_at: datetime = Field(default_factory=current_timestamp, description="创建时间")
    created_by: str = Field(..., description="创建者")
    
    def get_step_by_role(self, role: str) -> Optional[WorkflowStep]:
        """根据角色获取步骤"""
        for step in self.planned_steps:
            if step.role == role:
                return step
        return None
    
    def get_next_step(self, current_step_index: int) -> Optional[WorkflowStep]:
        """获取下一步骤"""
        next_index = current_step_index + 1
        if next_index < len(self.planned_steps):
            return self.planned_steps[next_index]
        return None
    
    def estimate_remaining_time(self, current_step_index: int) -> int:
        """估算剩余时间"""
        remaining_steps = self.planned_steps[current_step_index + 1:]
        return sum(step.estimated_duration or 30 for step in remaining_steps)


# ===== 工作流监控模型 =====

class WorkflowMonitoringData(BaseModel):
    """工作流监控数据模型"""
    workflow_id: str = Field(..., description="工作流ID")
    
    # 实时状态
    current_metrics: ExecutionMetrics = Field(..., description="当前指标")
    health_status: str = Field(default="healthy", description="健康状态")
    
    # 性能监控
    cpu_usage_history: List[float] = Field(default_factory=list, description="CPU使用历史")
    memory_usage_history: List[float] = Field(default_factory=list, description="内存使用历史")
    response_time_history: List[float] = Field(default_factory=list, description="响应时间历史")
    
    # 异常监控
    error_rate: float = Field(default=0.0, description="错误率")
    warning_count: int = Field(default=0, description="警告数量")
    alert_count: int = Field(default=0, description="告警数量")
    
    # 用户体验监控
    user_satisfaction_trend: List[float] = Field(default_factory=list, description="用户满意度趋势")
    interaction_response_times: List[float] = Field(default_factory=list, description="交互响应时间")
    
    # 更新时间
    last_updated: datetime = Field(default_factory=current_timestamp, description="最后更新时间")
    
    def add_cpu_usage(self, usage: float):
        """添加CPU使用率"""
        self.cpu_usage_history.append(usage)
        if len(self.cpu_usage_history) > 100:  # 保持最近100个数据点
            self.cpu_usage_history = self.cpu_usage_history[-50:]
    
    def add_memory_usage(self, usage: float):
        """添加内存使用率"""
        self.memory_usage_history.append(usage)
        if len(self.memory_usage_history) > 100:
            self.memory_usage_history = self.memory_usage_history[-50:]
    
    def calculate_health_status(self) -> str:
        """计算健康状态"""
        if self.error_rate > 0.5:
            return "critical"
        elif self.error_rate > 0.2 or self.warning_count > 10:
            return "warning"
        elif self.alert_count > 0:
            return "attention"
        else:
            return "healthy"


# ===== 工作流优化模型 =====

class WorkflowOptimizationSuggestion(BaseModel):
    """工作流优化建议模型"""
    suggestion_id: str = Field(default_factory=lambda: f"opt_{generate_id()}", description="建议ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 优化建议
    optimization_type: str = Field(..., description="优化类型")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="详细描述")
    
    # 影响评估
    expected_improvement: Dict[str, float] = Field(default_factory=dict, description="预期改进")
    implementation_effort: str = Field(..., description="实施难度")  # low, medium, high
    risk_level: str = Field(..., description="风险级别")  # low, medium, high
    
    # 实施信息
    implementation_steps: List[str] = Field(default_factory=list, description="实施步骤")
    required_resources: List[str] = Field(default_factory=list, description="所需资源")
    estimated_time: int = Field(..., description="预估实施时间(小时)")
    
    # 验证标准
    success_metrics: List[str] = Field(default_factory=list, description="成功指标")
    validation_criteria: List[str] = Field(default_factory=list, description="验证标准")
    
    # 元数据
    generated_at: datetime = Field(default_factory=current_timestamp, description="生成时间")
    generated_by: str = Field(default="system", description="生成者")
    priority: int = Field(default=5, ge=1, le=10, description="优先级")


# ===== 工作流分析模型 =====

class WorkflowAnalysisResult(BaseModel):
    """工作流分析结果模型"""
    analysis_id: str = Field(default_factory=lambda: f"analysis_{generate_id()}", description="分析ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 性能分析
    performance_summary: Dict[str, Any] = Field(default_factory=dict, description="性能摘要")
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list, description="性能瓶颈")
    optimization_opportunities: List[Dict[str, Any]] = Field(default_factory=list, description="优化机会")
    
    # 质量分析
    quality_assessment: Dict[str, float] = Field(default_factory=dict, description="质量评估")
    quality_issues: List[str] = Field(default_factory=list, description="质量问题")
    
    # 用户体验分析
    user_experience_score: float = Field(default=0.0, ge=0.0, le=1.0, description="用户体验分数")
    interaction_analysis: Dict[str, Any] = Field(default_factory=dict, description="交互分析")
    
    # 成本效益分析
    resource_utilization: Dict[str, float] = Field(default_factory=dict, description="资源利用率")
    cost_effectiveness: float = Field(default=0.0, description="成本效益")
    
    # 改进建议
    improvement_suggestions: List[WorkflowOptimizationSuggestion] = Field(
        default_factory=list, description="改进建议"
    )
    
    # 分析元数据
    analyzed_at: datetime = Field(default_factory=current_timestamp, description="分析时间")
    analysis_method: str = Field(default="automated", description="分析方法")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="分析置信度")


# ===== 预定义工作流模板 =====

class StandardWorkflowTemplates:
    """标准工作流模板"""
    
    @staticmethod
    def software_development_template() -> WorkflowTemplate:
        """软件开发工作流模板"""
        return WorkflowTemplate(
            name="软件开发标准流程",
            description="适用于软件开发项目的标准工作流",
            category="software_development",
            role_sequence=["方案规划师", "编码专家", "测试工程师", "代码审查员"],
            optional_roles=["代码审查员"],
            applicable_domains=["software_development"],
            applicable_task_types=["new_development", "enhancement", "refactoring"],
            complexity_range=["simple", "moderate", "complex", "enterprise"],
            quality_gates={
                "方案规划师": ["technical_specification_complete", "architecture_approved"],
                "编码专家": ["code_implemented", "basic_tests_pass"],
                "测试工程师": ["test_coverage_80_percent", "all_tests_pass"],
                "代码审查员": ["code_quality_approved", "security_validated"]
            },
            success_criteria=[
                "All functional requirements implemented",
                "Code quality standards met",
                "Test coverage above 80%",
                "Security requirements satisfied"
            ],
            created_by="system"
        )
    
    @staticmethod
    def data_analysis_template() -> WorkflowTemplate:
        """数据分析工作流模板"""
        return WorkflowTemplate(
            name="数据分析标准流程",
            description="适用于数据分析任务的标准工作流",
            category="data_analysis",
            role_sequence=["数据分析师", "技术写作专家"],
            optional_roles=["知识整理专家"],
            applicable_domains=["data_analysis"],
            applicable_task_types=["data_analysis", "trend_analysis"],
            complexity_range=["moderate", "complex", "enterprise"],
            quality_gates={
                "数据分析师": ["data_quality_validated", "analysis_complete"],
                "技术写作专家": ["report_comprehensive", "insights_clear"]
            },
            success_criteria=[
                "Data analysis completed with statistical significance",
                "Clear insights and recommendations provided",
                "Professional report generated"
            ],
            created_by="system"
        )
    
    @staticmethod
    def financial_analysis_template() -> WorkflowTemplate:
        """金融分析工作流模板"""
        return WorkflowTemplate(
            name="金融分析标准流程",
            description="适用于股票和投资分析的标准工作流",
            category="financial_analysis",
            role_sequence=["调研分析师", "股票分析师", "技术写作专家"],
            optional_roles=["数据分析师"],
            applicable_domains=["financial_analysis"],
            applicable_task_types=["financial_analysis", "market_research"],
            complexity_range=["moderate", "complex", "enterprise"],
            quality_gates={
                "调研分析师": ["market_research_complete", "competitive_analysis_done"],
                "股票分析师": ["financial_analysis_complete", "investment_recommendation_ready"],
                "技术写作专家": ["investment_report_complete", "risk_disclosure_included"]
            },
            success_criteria=[
                "Comprehensive financial analysis completed",
                "Clear investment recommendation provided",
                "Risk factors properly disclosed",
                "Professional investment report generated"
            ],
            created_by="system"
        )
    
    @staticmethod
    def content_creation_template() -> WorkflowTemplate:
        """内容创作工作流模板"""
        return WorkflowTemplate(
            name="内容创作标准流程",
            description="适用于技术文档和报告创作的标准工作流",
            category="content_creation",
            role_sequence=["调研分析师", "技术写作专家", "知识整理专家"],
            optional_roles=["文档阅读专家"],
            applicable_domains=["content_creation", "technical_writing"],
            applicable_task_types=["content_writing", "documentation", "report_generation"],
            complexity_range=["simple", "moderate", "complex"],
            quality_gates={
                "调研分析师": ["research_complete", "sources_validated"],
                "技术写作专家": ["content_complete", "quality_reviewed"],
                "知识整理专家": ["content_organized", "structure_optimized"]
            },
            success_criteria=[
                "Comprehensive research conducted",
                "High-quality content created",
                "Information well-organized and accessible"
            ],
            created_by="system"
        )
    
    @staticmethod
    def document_processing_template() -> WorkflowTemplate:
        """文档处理工作流模板"""
        return WorkflowTemplate(
            name="文档处理标准流程",
            description="适用于文档分析和信息提取的标准工作流",
            category="information_processing",
            role_sequence=["文档阅读专家", "知识整理专家"],
            optional_roles=["技术写作专家"],
            applicable_domains=["information_processing"],
            applicable_task_types=["document_reading", "information_extraction", "knowledge_organization"],
            complexity_range=["simple", "moderate", "complex"],
            quality_gates={
                "文档阅读专家": ["document_analyzed", "key_information_extracted"],
                "知识整理专家": ["information_structured", "relationships_identified"]
            },
            success_criteria=[
                "Document thoroughly analyzed",
                "Key information accurately extracted",
                "Information properly structured and organized"
            ],
            created_by="system"
        )


# ===== 工作流工厂 =====

class WorkflowFactory:
    """工作流工厂"""
    
    _templates = {
        "software_development": StandardWorkflowTemplates.software_development_template,
        "data_analysis": StandardWorkflowTemplates.data_analysis_template,
        "financial_analysis": StandardWorkflowTemplates.financial_analysis_template,
        "content_creation": StandardWorkflowTemplates.content_creation_template,
        "document_processing": StandardWorkflowTemplates.document_processing_template,
    }
    
    @classmethod
    def create_workflow_from_template(cls, 
                                    template_name: str, 
                                    task: Task,
                                    task_analysis: TaskAnalysis,
                                    customizations: Dict[str, Any] = None) -> WorkflowDefinition:
        """基于模板创建工作流"""
        template_creator = cls._templates.get(template_name)
        if not template_creator:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = template_creator()
        
        # 应用自定义配置
        if customizations:
            if "roles" in customizations:
                template.role_sequence = customizations["roles"]
            if "timeout" in customizations:
                template.default_timeout_minutes = customizations["timeout"]
        
        # 创建工作流定义
        workflow = WorkflowDefinition(
            name=f"{task.title} - {template.name}",
            description=f"基于{template.name}的工作流执行",
            template_id=template.template_id,
            task=task,
            task_analysis=task_analysis,
            roles=template.role_sequence,
            timeout_minutes=template.default_timeout_minutes,
            max_retry_attempts=template.max_retry_attempts,
            allow_skip_optional=template.allow_skip_optional,
            quality_gates=template.quality_gates,
            success_criteria=template.success_criteria,
            created_by=task.created_by
        )
        
        return workflow
    
    @classmethod
    def get_available_templates(cls) -> List[str]:
        """获取可用模板列表"""
        return list(cls._templates.keys())
    
    @classmethod
    def register_template(cls, name: str, template_creator: Callable[[], WorkflowTemplate]):
        """注册新模板"""
        cls._templates[name] = template_creator
    
    @classmethod
    def create_custom_workflow(cls, 
                             task: Task,
                             task_analysis: TaskAnalysis,
                             roles: List[str],
                             config: Dict[str, Any] = None) -> WorkflowDefinition:
        """创建自定义工作流"""
        config = config or {}
        
        workflow = WorkflowDefinition(
            name=task.title,
            description=task.description,
            task=task,
            task_analysis=task_analysis,
            roles=roles,
            timeout_minutes=config.get("timeout_minutes", 60),
            max_retry_attempts=config.get("max_retry_attempts", 3),
            allow_skip_optional=config.get("allow_skip_optional", True),
            quality_gates=config.get("quality_gates", {}),
            success_criteria=config.get("success_criteria", []),
            created_by=task.created_by
        )
        
        return workflow


# ===== 工具函数 =====

def validate_workflow_definition(workflow: WorkflowDefinition) -> List[str]:
    """验证工作流定义"""
    errors = []
    
    # 检查角色序列不为空
    if not workflow.roles:
        errors.append("角色序列不能为空")
    
    # 检查角色是否存在
    available_roles = RoleFactory.get_available_roles()
    for role in workflow.roles:
        if role not in available_roles:
            errors.append(f"角色不存在: {role}")
    
    # 检查质量门禁配置
    for role, gates in workflow.quality_gates.items():
        if role not in workflow.roles:
            errors.append(f"质量门禁配置的角色不在工作流中: {role}")
    
    return errors


def estimate_workflow_duration(workflow: WorkflowDefinition) -> int:
    """估算工作流执行时间"""
    total_minutes = 0
    
    # 基于角色和任务复杂度估算
    complexity_multipliers = {
        ComplexityLevel.SIMPLE: 1.0,
        ComplexityLevel.MODERATE: 1.5,
        ComplexityLevel.COMPLEX: 2.5,
        ComplexityLevel.ENTERPRISE: 4.0
    }
    
    role_base_times = {
        "方案规划师": 60,    # 1小时
        "编码专家": 180,     # 3小时
        "测试工程师": 90,    # 1.5小时
        "代码审查员": 45,    # 45分钟
        "数据分析师": 120,   # 2小时
        "股票分析师": 90,    # 1.5小时
        "技术写作专家": 75,  # 1.25小时
        "调研分析师": 105,   # 1.75小时
        "文档阅读专家": 45,  # 45分钟
        "知识整理专家": 60,  # 1小时
    }
    
    multiplier = complexity_multipliers.get(workflow.task_analysis.complexity_level, 1.5)
    
    for role in workflow.roles:
        base_time = role_base_times.get(role, 60)  # 默认1小时
        total_minutes += int(base_time * multiplier)
    
    return total_minutes
