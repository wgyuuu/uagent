"""
UAgent Base Models

定义UAgent系统的核心数据模型和枚举类型
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass, field


# ===== 枚举定义 =====

class TaskDomain(str, Enum):
    """任务领域枚举"""
    SOFTWARE_DEVELOPMENT = "software_development"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    INFORMATION_PROCESSING = "information_processing"
    FINANCIAL_ANALYSIS = "financial_analysis"
    MARKET_RESEARCH = "market_research"
    TECHNICAL_WRITING = "technical_writing"


class TaskType(str, Enum):
    """任务类型枚举"""
    # 开发类型
    NEW_DEVELOPMENT = "new_development"
    BUG_FIX = "bug_fix"
    ENHANCEMENT = "enhancement"
    REFACTORING = "refactoring"
    OPTIMIZATION = "optimization"
    
    # 分析类型
    DATA_ANALYSIS = "data_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    MARKET_RESEARCH = "market_research"
    TREND_ANALYSIS = "trend_analysis"
    
    # 创作类型
    CONTENT_WRITING = "content_writing"
    DOCUMENTATION = "documentation"
    REPORT_GENERATION = "report_generation"
    PRESENTATION = "presentation"
    
    # 处理类型
    DOCUMENT_READING = "document_reading"
    INFORMATION_EXTRACTION = "information_extraction"
    KNOWLEDGE_ORGANIZATION = "knowledge_organization"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    CREATED = "created"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class RoleStatus(str, Enum):
    """角色状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComplexityLevel(str, Enum):
    """复杂度级别枚举"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


class ErrorSeverity(str, Enum):
    """错误严重程度枚举"""
    TRIVIAL = "trivial"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


# ===== 核心数据模型 =====

class Task(BaseModel):
    """任务模型"""
    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:8]}", description="任务ID")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    domain: TaskDomain = Field(..., description="任务领域")
    task_type: TaskType = Field(..., description="任务类型")
    complexity_level: ComplexityLevel = Field(default=ComplexityLevel.MODERATE, description="复杂度级别")
    
    # 需求和约束
    requirements: Dict[str, Any] = Field(default_factory=dict, description="功能需求")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="技术约束")
    quality_standards: Dict[str, Any] = Field(default_factory=dict, description="质量标准")
    
    # 时间和优先级
    priority: int = Field(default=5, ge=1, le=10, description="任务优先级(1-10)")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间(分钟)")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    
    # 元数据
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    # 状态
    status: TaskStatus = Field(default=TaskStatus.CREATED, description="任务状态")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskAnalysis(BaseModel):
    """任务分析结果模型"""
    task_id: str = Field(..., description="任务ID")
    
    # 分类结果
    primary_domain: TaskDomain = Field(..., description="主要领域")
    sub_domains: List[str] = Field(default_factory=list, description="子领域")
    task_type: TaskType = Field(..., description="任务类型")
    complexity_level: ComplexityLevel = Field(..., description="复杂度级别")
    estimated_scope: str = Field(..., description="预估范围")
    
    # 需求分析
    functional_requirements: List[str] = Field(default_factory=list, description="功能需求")
    non_functional_requirements: List[str] = Field(default_factory=list, description="非功能需求")
    technical_constraints: List[str] = Field(default_factory=list, description="技术约束")
    quality_standards: List[str] = Field(default_factory=list, description="质量标准")
    
    # 成功标准
    primary_deliverables: List[str] = Field(default_factory=list, description="主要交付物")
    quality_metrics: List[str] = Field(default_factory=list, description="质量指标")
    acceptance_criteria: List[str] = Field(default_factory=list, description="验收标准")
    
    # 风险评估
    technical_risks: List[str] = Field(default_factory=list, description="技术风险")
    complexity_risks: List[str] = Field(default_factory=list, description="复杂度风险")
    dependency_risks: List[str] = Field(default_factory=list, description="依赖风险")
    
    # 分析元数据
    analyzed_at: datetime = Field(default_factory=datetime.now, description="分析时间")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="分析置信度")
    analysis_method: str = Field(default="llm_based", description="分析方法")


class RoleRecommendation(BaseModel):
    """角色推荐结果模型"""
    task_id: str = Field(..., description="任务ID")
    
    # 推荐结果
    recommended_sequence: List[str] = Field(..., description="推荐角色序列")
    mandatory_roles: List[str] = Field(default_factory=list, description="必需角色")
    optional_roles: List[str] = Field(default_factory=list, description="可选角色")
    
    # 推荐理由
    reasoning: Dict[str, str] = Field(default_factory=dict, description="推荐理由")
    skip_conditions: Dict[str, str] = Field(default_factory=dict, description="跳过条件")
    
    # 时间估算
    estimated_timeline: Dict[str, str] = Field(default_factory=dict, description="时间估算")
    total_estimated_time: Optional[int] = Field(None, description="总预估时间(分钟)")
    
    # 成功指标
    success_metrics: List[str] = Field(default_factory=list, description="成功指标")
    
    # 推荐元数据
    recommended_at: datetime = Field(default_factory=datetime.now, description="推荐时间")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="推荐置信度")
    recommendation_method: str = Field(default="llm_based", description="推荐方法")


class RoleResult(BaseModel):
    """角色执行结果模型"""
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid4().hex[:8]}", description="执行ID")
    role: str = Field(..., description="角色名称")
    task_id: str = Field(..., description="任务ID")
    
    # 执行结果
    status: RoleStatus = Field(..., description="执行状态")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="输出结果")
    deliverables: Dict[str, Any] = Field(default_factory=dict, description="交付物")
    
    # 执行信息
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
    
    # 质量评估
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="质量分数")
    completeness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="完整性分数")
    
    # 交接信息
    handoff_summary: Optional[str] = Field(None, description="交接摘要")
    next_role_guidance: Optional[str] = Field(None, description="下一角色指导")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    class Config:
        use_enum_values = True


class ContextSection(BaseModel):
    """上下文段落模型"""
    name: str = Field(..., description="段落名称")
    content: str = Field(default="", description="段落内容")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性分数")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    content_type: str = Field(default="text", description="内容类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="段落元数据")


class IsolatedRoleContext(BaseModel):
    """隔离的角色上下文模型"""
    context_id: str = Field(default_factory=lambda: f"ctx_{uuid4().hex[:8]}", description="上下文ID")
    role: str = Field(..., description="角色名称")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 8段式上下文结构
    sections: Dict[str, ContextSection] = Field(default_factory=dict, description="上下文段落")
    
    # 上下文状态
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    is_compressed: bool = Field(default=False, description="是否已压缩")
    compression_ratio: Optional[float] = Field(None, description="压缩比例")
    
    # 工具和权限
    available_tools: List[str] = Field(default_factory=list, description="可用工具")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    
    # 预期输出
    expected_outputs: Dict[str, str] = Field(default_factory=dict, description="预期输出")
    
    def __post_init__(self):
        """初始化8段式结构"""
        if not self.sections:
            self._init_eight_segments()
    
    def _init_eight_segments(self):
        """初始化8段式上下文结构"""
        segment_names = [
            "Primary Request and Intent",
            "Key Technical Concepts", 
            "Files and Code Sections",
            "Errors and fixes",
            "Problem Solving",
            "All user messages",
            "Pending Tasks",
            "Current Work"
        ]
        
        for name in segment_names:
            if name not in self.sections:
                self.sections[name] = ContextSection(name=name)
    
    def update_section(self, section_name: str, content: str, importance_score: float = 0.5):
        """更新段落内容"""
        if section_name in self.sections:
            self.sections[section_name].content = content
            self.sections[section_name].importance_score = importance_score
            self.sections[section_name].last_updated = datetime.now()
        else:
            self.sections[section_name] = ContextSection(
                name=section_name,
                content=content,
                importance_score=importance_score
            )
        
        self.last_updated = datetime.now()
    
    def get_total_content_length(self) -> int:
        """获取总内容长度"""
        return sum(len(section.content) for section in self.sections.values())


class HandoffContext(BaseModel):
    """角色交接上下文模型"""
    handoff_id: str = Field(default_factory=lambda: f"handoff_{uuid4().hex[:8]}", description="交接ID")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 角色信息
    from_role: str = Field(..., description="源角色")
    to_role: str = Field(..., description="目标角色")
    current_stage: int = Field(..., description="当前阶段")
    
    # 任务信息
    task_summary: str = Field(..., description="任务摘要")
    original_task: str = Field(..., description="原始任务描述")
    
    # 交接内容
    deliverables: Dict[str, Any] = Field(default_factory=dict, description="交付物")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="需求和约束")
    technical_context: Dict[str, Any] = Field(default_factory=dict, description="技术上下文")
    
    # 指导信息
    handoff_message: str = Field(default="", description="交接说明")
    next_steps: List[str] = Field(default_factory=list, description="下一步操作")
    important_notes: List[str] = Field(default_factory=list, description="重要注意事项")
    
    # 质量和风险
    quality_requirements: List[str] = Field(default_factory=list, description="质量要求")
    risk_warnings: List[str] = Field(default_factory=list, description="风险警告")
    
    # 用户消息历史
    user_messages: List[Dict[str, Any]] = Field(default_factory=list, description="用户消息历史")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class WorkflowExecution(BaseModel):
    """工作流执行实例模型"""
    workflow_id: str = Field(default_factory=lambda: f"workflow_{uuid4().hex[:8]}", description="工作流ID")
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid4().hex[:8]}", description="执行ID")
    
    # 基本信息
    name: str = Field(..., description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    task: Task = Field(..., description="关联任务")
    
    # 执行配置
    roles: List[str] = Field(..., description="角色序列")
    current_role_index: int = Field(default=0, description="当前角色索引")
    
    # 状态管理
    status: WorkflowStatus = Field(default=WorkflowStatus.CREATED, description="工作流状态")
    role_statuses: Dict[str, RoleStatus] = Field(default_factory=dict, description="角色状态")
    role_results: Dict[str, RoleResult] = Field(default_factory=dict, description="角色结果")
    
    # 时间跟踪
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    total_execution_time: Optional[float] = Field(None, description="总执行时间(秒)")
    
    # 错误处理
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误记录")
    retry_counts: Dict[str, int] = Field(default_factory=dict, description="重试次数")
    recovery_actions: List[Dict[str, Any]] = Field(default_factory=list, description="恢复操作")
    
    # 用户交互
    user_interventions: List[Dict[str, Any]] = Field(default_factory=list, description="用户干预记录")
    
    # 质量和性能
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="质量指标")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="性能指标")
    
    # 元数据
    created_by: str = Field(..., description="创建者")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    def get_current_role(self) -> Optional[str]:
        """获取当前执行角色"""
        if 0 <= self.current_role_index < len(self.roles):
            return self.roles[self.current_role_index]
        return None
    
    def get_next_role(self) -> Optional[str]:
        """获取下一个角色"""
        next_index = self.current_role_index + 1
        if next_index < len(self.roles):
            return self.roles[next_index]
        return None
    
    def get_remaining_roles(self) -> List[str]:
        """获取剩余角色"""
        return self.roles[self.current_role_index + 1:]
    
    def add_error(self, role: str, error: Exception, context: Dict[str, Any] = None):
        """添加错误记录"""
        error_record = {
            "role": role,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        self.errors.append(error_record)
    
    def add_user_intervention(self, intervention_type: str, description: str, result: Any = None):
        """添加用户干预记录"""
        intervention_record = {
            "type": intervention_type,
            "description": description,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        self.user_interventions.append(intervention_record)


# ===== 错误和恢复模型 =====

class ErrorClassification(BaseModel):
    """错误分类模型"""
    error_id: str = Field(default_factory=lambda: f"err_{uuid4().hex[:8]}", description="错误ID")
    
    # 错误基本信息
    failed_role: str = Field(..., description="失败角色")
    error_type: str = Field(..., description="错误类型")
    error_message: str = Field(..., description="错误消息")
    
    # 分类结果
    severity: ErrorSeverity = Field(..., description="严重程度")
    category: str = Field(..., description="错误类别")
    recovery_feasibility: str = Field(..., description="恢复可行性")
    workflow_impact: str = Field(..., description="工作流影响")
    
    # 错误修复适用性
    error_recovery_applicable: str = Field(..., description="错误修复适用性")
    
    # 影响分析
    blocked_roles: List[str] = Field(default_factory=list, description="被阻塞角色")
    degraded_roles: List[str] = Field(default_factory=list, description="降级角色")
    
    # 分类元数据
    classified_at: datetime = Field(default_factory=datetime.now, description="分类时间")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="分类置信度")


class RecoveryStrategy(BaseModel):
    """恢复策略模型"""
    strategy_id: str = Field(default_factory=lambda: f"strategy_{uuid4().hex[:8]}", description="策略ID")
    
    # 策略基本信息
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    action_type: str = Field(..., description="操作类型")
    
    # 可行性评估
    feasibility_score: float = Field(..., ge=0.0, le=1.0, description="可行性分数")
    risk_level: str = Field(..., description="风险级别")
    success_probability: float = Field(..., ge=0.0, le=1.0, description="成功概率")
    
    # 资源需求
    estimated_time: int = Field(..., description="预估时间(分钟)")
    required_resources: List[str] = Field(default_factory=list, description="所需资源")
    
    # 执行参数
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    success_criteria: List[str] = Field(default_factory=list, description="成功标准")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class RecoveryDecision(BaseModel):
    """恢复决策模型"""
    decision_id: str = Field(default_factory=lambda: f"decision_{uuid4().hex[:8]}", description="决策ID")
    
    # 决策信息
    decision_type: str = Field(..., description="决策类型")  # automatic, manual_intervention
    selected_strategy: Optional[RecoveryStrategy] = Field(None, description="选择的策略")
    available_options: List[RecoveryStrategy] = Field(default_factory=list, description="可用选项")
    
    # 决策理由
    rationale: str = Field(..., description="决策理由")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="决策置信度")
    
    # 执行信息
    requires_user_approval: bool = Field(default=False, description="是否需要用户批准")
    approved_by_user: Optional[bool] = Field(None, description="用户是否批准")
    
    # 元数据
    decided_at: datetime = Field(default_factory=datetime.now, description="决策时间")
    decided_by: str = Field(default="system", description="决策者")


# ===== 工具和MCP模型 =====

class MCPToolDefinition(BaseModel):
    """MCP工具定义模型"""
    name: str = Field(..., description="工具名称")
    server_name: str = Field(..., description="服务器名称")
    server_type: str = Field(..., description="服务器类型")  # http, builtin, user_interaction
    
    # 工具描述
    description: str = Field(..., description="工具描述")
    category: str = Field(..., description="工具类别")
    tags: List[str] = Field(default_factory=list, description="工具标签")
    
    # 模式定义
    input_schema: Dict[str, Any] = Field(..., description="输入模式")
    output_schema: Dict[str, Any] = Field(..., description="输出模式")
    
    # 执行配置
    is_concurrency_safe: bool = Field(default=True, description="是否并发安全")
    requires_authentication: bool = Field(default=False, description="是否需要认证")
    rate_limit: Optional[int] = Field(None, description="速率限制")
    timeout: int = Field(default=30, description="超时时间(秒)")
    
    # 权限配置
    allowed_roles: List[str] = Field(default_factory=list, description="允许的角色")
    security_level: str = Field(default="medium", description="安全级别")
    
    # 元数据
    version: str = Field(default="1.0.0", description="工具版本")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ToolExecutionResult(BaseModel):
    """工具执行结果模型"""
    execution_id: str = Field(default_factory=lambda: f"tool_exec_{uuid4().hex[:8]}", description="执行ID")
    
    # 工具信息
    tool_name: str = Field(..., description="工具名称")
    server_name: str = Field(..., description="服务器名称")
    role: str = Field(..., description="调用角色")
    
    # 执行结果
    success: bool = Field(..., description="是否成功")
    result: Optional[Any] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    
    # 执行信息
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    execution_time: float = Field(..., description="执行时间(秒)")
    
    # 资源使用
    memory_usage: Optional[float] = Field(None, description="内存使用(MB)")
    cpu_usage: Optional[float] = Field(None, description="CPU使用率")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


# ===== 用户交互模型 =====

class UserQuestion(BaseModel):
    """用户问题模型"""
    question_id: str = Field(default_factory=lambda: f"q_{uuid4().hex[:8]}", description="问题ID")
    
    # 问题内容
    question: str = Field(..., description="问题内容")
    question_type: str = Field(default="text", description="问题类型")  # text, choice, confirmation
    options: List[str] = Field(default_factory=list, description="选项列表")
    
    # 上下文
    workflow_id: Optional[str] = Field(None, description="工作流ID")
    role: Optional[str] = Field(None, description="提问角色")
    context: Dict[str, Any] = Field(default_factory=dict, description="问题上下文")
    
    # 回答信息
    answer: Optional[str] = Field(None, description="用户回答")
    answered_at: Optional[datetime] = Field(None, description="回答时间")
    
    # 时间管理
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    timeout: int = Field(default=300, description="超时时间(秒)")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.dict(exclude_none=True)


class UserSession(BaseModel):
    """用户会话模型"""
    session_id: str = Field(default_factory=lambda: f"session_{uuid4().hex[:8]}", description="会话ID")
    
    # 用户信息
    user_id: str = Field(..., description="用户ID")
    user_name: Optional[str] = Field(None, description="用户名称")
    
    # 会话状态
    workflow_id: Optional[str] = Field(None, description="关联工作流ID")
    current_context: Dict[str, Any] = Field(default_factory=dict, description="当前上下文")
    
    # 交互历史
    question_history: List[UserQuestion] = Field(default_factory=list, description="问题历史")
    interaction_count: int = Field(default=0, description="交互次数")
    
    # 时间管理
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_activity: datetime = Field(default_factory=datetime.now, description="最后活动时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # 会话配置
    timeout_minutes: int = Field(default=60, description="会话超时(分钟)")
    max_questions: int = Field(default=100, description="最大问题数")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        
        # 基于最后活动时间判断
        elapsed_minutes = (datetime.now() - self.last_activity).total_seconds() / 60
        return elapsed_minutes > self.timeout_minutes
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = datetime.now()
    
    def add_question(self, question: UserQuestion):
        """添加问题到历史"""
        self.question_history.append(question)
        self.interaction_count += 1
        self.update_activity()
        
        # 保持历史记录在合理范围内
        if len(self.question_history) > self.max_questions:
            self.question_history = self.question_history[-self.max_questions//2:]


# ===== 配置模型 =====

class SystemConfig(BaseModel):
    """系统配置模型"""
    # 系统基本配置
    system_name: str = Field(default="UAgent", description="系统名称")
    version: str = Field(default="2.0.0", description="系统版本")
    environment: str = Field(default="development", description="运行环境")
    
    # 并发配置
    max_concurrent_workflows: int = Field(default=50, description="最大并发工作流数")
    max_roles_per_workflow: int = Field(default=10, description="每个工作流最大角色数")
    default_timeout_minutes: int = Field(default=60, description="默认超时时间(分钟)")
    
    # 数据库配置
    database_url: str = Field(..., description="数据库连接URL")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis连接URL")
    connection_pool_size: int = Field(default=20, description="连接池大小")
    
    # AI配置
    default_llm_provider: str = Field(default="openai", description="默认LLM提供商")
    llm_api_key: Optional[str] = Field(None, description="LLM API密钥")
    max_tokens: int = Field(default=4000, description="最大token数")
    
    # 缓存配置
    cache_ttl_seconds: int = Field(default=600, description="缓存TTL(秒)")
    compression_ratio: float = Field(default=0.6, ge=0.1, le=0.9, description="压缩比例")
    
    # 监控配置
    enable_metrics: bool = Field(default=True, description="启用指标收集")
    enable_tracing: bool = Field(default=True, description="启用分布式追踪")
    log_level: str = Field(default="INFO", description="日志级别")
    
    # 安全配置
    enable_auth: bool = Field(default=True, description="启用认证")
    secret_key: str = Field(..., description="系统密钥")
    token_expire_hours: int = Field(default=24, description="Token过期时间(小时)")
    
    class Config:
        env_prefix = "UAGENT_"
        case_sensitive = False


# ===== 验证器和工具函数 =====

class ValidationResult(BaseModel):
    """验证结果模型"""
    is_valid: bool = Field(..., description="是否有效")
    error_message: Optional[str] = Field(None, description="错误信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="验证元数据")


def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    if prefix:
        return f"{prefix}_{uuid4().hex[:8]}"
    return uuid4().hex[:8]


def current_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.now()


# ===== 类型别名 =====
TaskID = str
RoleName = str
WorkflowID = str
ContextID = str
UserID = str
SessionID = str

# ===== 执行相关模型 =====

@dataclass
class ExecutionConfig:
    """执行配置"""
    max_iterations: int = 10  # 最大执行轮数
    max_tool_calls_per_iteration: int = 5  # 每轮最大工具调用数
    parallel_tool_execution: bool = True  # 是否并行执行工具
    context_compression_threshold: float = 0.8  # 上下文压缩阈值
    quality_threshold: float = 0.85  # 质量阈值


@dataclass
class AgentEnvironment:
    """Agent运行环境"""
    role: str
    context: Any
    available_tools: List[str]
    prompt: str
    iteration_count: int = 0
    quality_score: float = 0.0
    last_response: Optional[str] = None


@dataclass
class ExecutionContext:
    """执行上下文"""
    workflow_id: str
    current_role: str
    role_index: int
    previous_results: Dict[str, 'RoleResult']
    handoff_context: Optional['HandoffContext']
    isolated_context: 'IsolatedRoleContext'
    metadata: Dict[str, Any]


@dataclass
class IterationResult:
    """单轮执行结果"""
    iteration: int
    prompt: str
    llm_response: str
    tool_calls: List[Any]
    tool_results: List[Any]
    completion_analysis: Any
    is_completed: bool
    next_actions: List[str]
