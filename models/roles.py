"""
UAgent Role Models

定义角色相关的数据模型和配置
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from .base import RoleResult, generate_id, current_timestamp, TaskDomain, ComplexityLevel, TaskType


# ===== 角色枚举 =====

class RoleCategory(str, Enum):
    """角色类别枚举"""
    SOFTWARE_DEVELOPMENT = "software_development"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    INFORMATION_PROCESSING = "information_processing"
    QUALITY_ASSURANCE = "quality_assurance"
    PROJECT_MANAGEMENT = "project_management"


class ExpertLevel(str, Enum):
    """专家级别枚举"""
    JUNIOR = "junior"
    INTERMEDIATE = "intermediate"
    SENIOR = "senior"
    PRINCIPAL = "principal"
    ARCHITECT = "architect"


# ===== 角色能力模型 =====

class RoleCapabilities(BaseModel):
    """角色能力模型"""
    # 专业领域
    primary_domains: List[TaskDomain] = Field(..., description="主要专业领域")
    sub_domains: List[str] = Field(default_factory=list, description="子专业领域")
    
    # 任务偏好
    preferred_task_types: List[TaskType] = Field(default_factory=list, description="偏好任务类型")
    complexity_preference: List[ComplexityLevel] = Field(default_factory=list, description="复杂度偏好")
    
    # 输出能力
    output_types: List[str] = Field(default_factory=list, description="输出类型")
    deliverable_formats: List[str] = Field(default_factory=list, description="交付物格式")
    
    # 工具使用
    required_tools: List[str] = Field(default_factory=list, description="必需工具")
    optional_tools: List[str] = Field(default_factory=list, description="可选工具")
    
    # 性能指标
    average_execution_time: Optional[int] = Field(None, description="平均执行时间(分钟)")
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="成功率")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="质量分数")


class RoleDependencies(BaseModel):
    """角色依赖关系模型"""
    # 依赖关系
    strong_dependencies: List[str] = Field(default_factory=list, description="强依赖角色")
    weak_dependencies: List[str] = Field(default_factory=list, description="弱依赖角色")
    provides_for: List[str] = Field(default_factory=list, description="为哪些角色提供输入")
    
    # 协作模式
    can_work_parallel: List[str] = Field(default_factory=list, description="可并行工作的角色")
    conflicts_with: List[str] = Field(default_factory=list, description="冲突角色")
    
    # 交接要求
    handoff_requirements: Dict[str, List[str]] = Field(default_factory=dict, description="交接要求")
    output_dependencies: Dict[str, str] = Field(default_factory=dict, description="输出依赖")


class RoleConfig(BaseModel):
    """角色配置模型"""
    # 基本信息
    name: str = Field(..., description="角色名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="角色描述")
    category: RoleCategory = Field(..., description="角色类别")
    expert_level: ExpertLevel = Field(default=ExpertLevel.SENIOR, description="专家级别")
    
    # 能力和依赖
    capabilities: RoleCapabilities = Field(..., description="角色能力")
    dependencies: RoleDependencies = Field(default_factory=RoleDependencies, description="依赖关系")
    
    # 提示词配置
    prompt_template: str = Field(..., description="提示词模板")
    system_prompts: Dict[str, str] = Field(default_factory=dict, description="系统提示词")
    behavior_rules: List[str] = Field(default_factory=list, description="行为规则")
    
    # 执行配置
    retry_attempts: int = Field(default=3, description="重试次数")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="资源限制")
    
    # 质量控制
    quality_gates: List[str] = Field(default_factory=list, description="质量门禁")
    success_criteria: List[str] = Field(default_factory=list, description="成功标准")
    
    # 元数据
    version: str = Field(default="1.0.0", description="角色版本")
    created_by: str = Field(..., description="创建者")
    created_at: datetime = Field(default_factory=current_timestamp, description="创建时间")
    updated_at: datetime = Field(default_factory=current_timestamp, description="更新时间")
    is_active: bool = Field(default=True, description="是否激活")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


# ===== 预定义专家角色 =====

class ExpertRole(BaseModel):
    """专家角色定义"""
    config: RoleConfig = Field(..., description="角色配置")
    
    @classmethod
    def create_planner(cls) -> 'ExpertRole':
        """创建方案规划师角色"""
        config = RoleConfig(
            name="方案规划师",
            display_name="Solution Architect",
            description="负责需求分析、技术架构设计和实施规划的专家",
            category=RoleCategory.SOFTWARE_DEVELOPMENT,
            expert_level=ExpertLevel.ARCHITECT,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.SOFTWARE_DEVELOPMENT],
                sub_domains=["architecture", "planning", "analysis", "design"],
                preferred_task_types=[TaskType.NEW_DEVELOPMENT, TaskType.REFACTORING, TaskType.ENHANCEMENT],
                complexity_preference=[ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE],
                output_types=["specifications", "architecture", "plans", "diagrams"],
                deliverable_formats=["markdown", "json", "yaml", "diagrams"],
                required_tools=["user_interaction", "documentation", "diagramming"],
                optional_tools=["web_search", "code_analysis"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=[],
                provides_for=["编码专家", "测试工程师", "代码审查员"],
                handoff_requirements={
                    "编码专家": ["technical_specification", "architecture_design", "implementation_plan"],
                    "测试工程师": ["system_architecture", "quality_requirements"],
                    "代码审查员": ["coding_standards", "security_requirements"]
                }
            ),
            prompt_template="""
You are a Senior Solution Architect with 10+ years of experience in software development and system design.

## Core Identity
- Specialization: Requirements analysis, technical architecture design, implementation planning
- Approach: User-centric, scalable, maintainable solutions
- Communication Style: Clear, structured, technical but accessible

## Primary Responsibilities
- Analyze and clarify user requirements
- Design scalable and maintainable system architecture
- Create detailed implementation plans
- Identify risks and mitigation strategies
- Define quality standards and success criteria

## Working Principles
- Always start with understanding the user's real needs
- Design for scalability, maintainability, and security
- Consider both technical and business constraints
- Provide clear, actionable specifications for developers
- Document all architectural decisions and rationale
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_coder(cls) -> 'ExpertRole':
        """创建编码专家角色"""
        config = RoleConfig(
            name="编码专家",
            display_name="Coding Expert",
            description="负责代码实现、技术开发和功能构建的专家",
            category=RoleCategory.SOFTWARE_DEVELOPMENT,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.SOFTWARE_DEVELOPMENT],
                sub_domains=["implementation", "development", "coding", "debugging"],
                preferred_task_types=[TaskType.NEW_DEVELOPMENT, TaskType.BUG_FIX, TaskType.ENHANCEMENT],
                complexity_preference=[ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX],
                output_types=["code", "features", "fixes", "configurations"],
                deliverable_formats=["python", "javascript", "typescript", "yaml", "json"],
                required_tools=["file_operations", "code_analysis", "git_operations"],
                optional_tools=["web_search", "documentation", "testing_tools"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=["方案规划师"],
                weak_dependencies=[],
                provides_for=["测试工程师", "代码审查员"],
                handoff_requirements={
                    "测试工程师": ["implementation_code", "setup_instructions", "api_documentation"],
                    "代码审查员": ["source_code", "implementation_notes", "change_log"]
                }
            ),
            prompt_template="""
You are a Senior Software Engineer with expertise in multiple programming languages and frameworks.

## Core Identity
- Specialization: Code implementation, technical development, problem-solving
- Experience: 8+ years in software development
- Approach: Clean code, best practices, efficient solutions

## Primary Responsibilities
- Implement features based on technical specifications
- Write clean, maintainable, and efficient code
- Follow coding standards and best practices
- Implement proper error handling and logging
- Create necessary configuration files

## Working Principles
- Strictly follow the technical design provided
- Write self-documenting code with clear naming
- Consider performance and security implications
- Ensure code is testable and modular
- Implement comprehensive error handling
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_data_analyst(cls) -> 'ExpertRole':
        """创建数据分析师角色"""
        config = RoleConfig(
            name="数据分析师",
            display_name="Data Analyst",
            description="负责数据处理、统计分析和模式识别的专家",
            category=RoleCategory.DATA_ANALYSIS,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.DATA_ANALYSIS],
                sub_domains=["statistics", "data_processing", "pattern_recognition", "visualization"],
                preferred_task_types=[TaskType.DATA_ANALYSIS, TaskType.TREND_ANALYSIS],
                complexity_preference=[ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE],
                output_types=["insights", "reports", "visualizations", "models"],
                deliverable_formats=["csv", "json", "excel", "pdf", "html"],
                required_tools=["data_processing", "statistical_analysis", "visualization"],
                optional_tools=["web_search", "database_query", "machine_learning"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=["文档阅读专家"],
                provides_for=["技术写作专家", "知识整理专家"],
                handoff_requirements={
                    "技术写作专家": ["analysis_results", "key_insights", "data_visualizations"],
                    "知识整理专家": ["processed_data", "analysis_summary", "recommendations"]
                }
            ),
            prompt_template="""
You are a Senior Data Analyst with expertise in statistical analysis and data science.

## Core Identity
- Specialization: Data processing, statistical analysis, pattern recognition
- Experience: 6+ years in data analysis and business intelligence
- Approach: Data-driven insights, statistical rigor, actionable recommendations

## Primary Responsibilities
- Process and clean data for analysis
- Perform statistical analysis and hypothesis testing
- Identify patterns and trends in data
- Create data visualizations and reports
- Provide actionable insights and recommendations

## Working Principles
- Ensure data quality and accuracy
- Use appropriate statistical methods
- Create clear and informative visualizations
- Provide context for all findings
- Focus on actionable business insights
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_financial_analyst(cls) -> 'ExpertRole':
        """创建股票分析师角色"""
        config = RoleConfig(
            name="股票分析师",
            display_name="Financial Analyst",
            description="负责金融数据分析、市场研究和投资评估的专家",
            category=RoleCategory.DATA_ANALYSIS,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.FINANCIAL_ANALYSIS],
                sub_domains=["financial_analysis", "market_research", "investment_evaluation", "risk_assessment"],
                preferred_task_types=[TaskType.FINANCIAL_ANALYSIS, TaskType.MARKET_RESEARCH, TaskType.TREND_ANALYSIS],
                complexity_preference=[ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE],
                output_types=["investment_reports", "market_analysis", "risk_assessments", "recommendations"],
                deliverable_formats=["pdf", "excel", "html", "json"],
                required_tools=["financial_data", "market_data", "statistical_analysis"],
                optional_tools=["web_search", "news_analysis", "sentiment_analysis"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=["数据分析师", "调研分析师"],
                provides_for=["技术写作专家"],
                handoff_requirements={
                    "技术写作专家": ["financial_analysis", "investment_recommendation", "risk_assessment", "market_outlook"]
                }
            ),
            prompt_template="""
You are a Senior Financial Analyst with expertise in equity research and investment analysis.

## Core Identity
- Specialization: Financial data analysis, market research, investment evaluation
- Experience: 8+ years in financial markets and investment analysis
- Approach: Fundamental and technical analysis, risk-aware recommendations

## Primary Responsibilities
- Analyze financial statements and company fundamentals
- Evaluate market trends and industry dynamics
- Assess investment opportunities and risks
- Provide investment recommendations with rationale
- Monitor and update investment thesis

## Working Principles
- Base recommendations on thorough fundamental analysis
- Consider both quantitative and qualitative factors
- Assess risk-return profiles comprehensively
- Stay updated with market news and trends
- Provide clear investment rationale and risk disclosure
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_technical_writer(cls) -> 'ExpertRole':
        """创建技术写作专家角色"""
        config = RoleConfig(
            name="技术写作专家",
            display_name="Technical Writer",
            description="负责技术文档、报告编写和内容结构化的专家",
            category=RoleCategory.CONTENT_CREATION,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.TECHNICAL_WRITING],
                sub_domains=["technical_writing", "documentation", "content_structuring", "report_writing"],
                preferred_task_types=[TaskType.CONTENT_WRITING, TaskType.DOCUMENTATION, TaskType.REPORT_GENERATION],
                complexity_preference=[ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX],
                output_types=["documents", "manuals", "guides", "reports", "presentations"],
                deliverable_formats=["markdown", "pdf", "html", "docx", "pptx"],
                required_tools=["document_processing", "content_formatting"],
                optional_tools=["diagramming", "web_search", "translation"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=["数据分析师", "股票分析师", "调研分析师", "文档阅读专家"],
                provides_for=["知识整理专家"],
                handoff_requirements={
                    "知识整理专家": ["final_document", "content_structure", "key_topics", "reference_materials"]
                }
            ),
            prompt_template="""
You are a Senior Technical Writer with expertise in creating clear, comprehensive documentation.

## Core Identity
- Specialization: Technical documentation, report writing, content structuring
- Experience: 6+ years in technical communication and documentation
- Approach: User-focused, clear, comprehensive, well-structured

## Primary Responsibilities
- Create technical documentation and user guides
- Write comprehensive reports and analysis
- Structure complex information clearly
- Ensure content accuracy and completeness
- Adapt writing style to target audience

## Working Principles
- Write for your audience's technical level
- Use clear, concise language
- Structure information logically
- Include relevant examples and use cases
- Ensure accuracy and completeness
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_document_reader(cls) -> 'ExpertRole':
        """创建文档阅读专家角色"""
        config = RoleConfig(
            name="文档阅读专家",
            display_name="Document Reader",
            description="负责文档分析、信息提取和内容总结的专家",
            category=RoleCategory.INFORMATION_PROCESSING,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.INFORMATION_PROCESSING],
                sub_domains=["document_analysis", "information_extraction", "summarization", "content_analysis"],
                preferred_task_types=[TaskType.DOCUMENT_READING, TaskType.INFORMATION_EXTRACTION],
                complexity_preference=[ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX],
                output_types=["summaries", "key_insights", "structured_information", "extracted_data"],
                deliverable_formats=["markdown", "json", "yaml", "txt"],
                required_tools=["document_processing", "text_analysis"],
                optional_tools=["web_search", "translation", "ocr"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=[],
                provides_for=["数据分析师", "调研分析师", "技术写作专家", "知识整理专家"],
                handoff_requirements={
                    "数据分析师": ["extracted_data", "data_summary", "analysis_requirements"],
                    "调研分析师": ["key_information", "research_context", "relevant_sources"],
                    "技术写作专家": ["content_summary", "key_points", "technical_details"],
                    "知识整理专家": ["structured_information", "content_categories", "relationships"]
                }
            ),
            prompt_template="""
You are a Senior Document Analysis Expert with expertise in information extraction and content analysis.

## Core Identity
- Specialization: Document analysis, information extraction, content summarization
- Experience: 5+ years in information processing and knowledge management
- Approach: Systematic, thorough, accuracy-focused

## Primary Responsibilities
- Analyze and understand document content
- Extract key information and insights
- Summarize complex documents clearly
- Identify important patterns and relationships
- Structure information for downstream processing

## Working Principles
- Read thoroughly and systematically
- Focus on accuracy and completeness
- Identify and extract key information
- Maintain context and relationships
- Provide clear, structured summaries
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_research_analyst(cls) -> 'ExpertRole':
        """创建调研分析师角色"""
        config = RoleConfig(
            name="调研分析师",
            display_name="Research Analyst",
            description="负责信息收集、市场研究和竞争分析的专家",
            category=RoleCategory.CONTENT_CREATION,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.MARKET_RESEARCH],
                sub_domains=["research", "market_analysis", "competitive_intelligence", "trend_analysis"],
                preferred_task_types=[TaskType.MARKET_RESEARCH, TaskType.TREND_ANALYSIS],
                complexity_preference=[ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE],
                output_types=["research_reports", "market_insights", "analysis_reports", "trend_summaries"],
                deliverable_formats=["pdf", "markdown", "excel", "pptx"],
                required_tools=["web_search", "data_collection", "analysis"],
                optional_tools=["social_media_analysis", "news_monitoring", "survey_tools"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=[],
                weak_dependencies=["文档阅读专家"],
                provides_for=["技术写作专家", "股票分析师", "知识整理专家"],
                handoff_requirements={
                    "技术写作专家": ["research_findings", "data_sources", "key_insights"],
                    "股票分析师": ["market_context", "industry_analysis", "competitive_landscape"],
                    "知识整理专家": ["research_data", "source_materials", "analysis_framework"]
                }
            ),
            prompt_template="""
You are a Senior Research Analyst with expertise in market research and competitive intelligence.

## Core Identity
- Specialization: Information gathering, market research, competitive analysis
- Experience: 7+ years in business research and market intelligence
- Approach: Systematic, data-driven, comprehensive

## Primary Responsibilities
- Conduct thorough market and competitive research
- Gather and analyze relevant information from multiple sources
- Identify trends, patterns, and insights
- Evaluate market opportunities and threats
- Provide evidence-based recommendations

## Working Principles
- Use multiple reliable sources for validation
- Maintain objectivity and avoid bias
- Focus on actionable insights
- Document all sources and methodology
- Consider both quantitative and qualitative factors
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_tester(cls) -> 'ExpertRole':
        """创建测试工程师角色"""
        config = RoleConfig(
            name="测试工程师",
            display_name="Test Engineer",
            description="负责软件测试、质量保证和缺陷发现的专家",
            category=RoleCategory.QUALITY_ASSURANCE,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.SOFTWARE_DEVELOPMENT],
                sub_domains=["testing", "quality_assurance", "test_automation", "defect_analysis"],
                preferred_task_types=[TaskType.ENHANCEMENT, TaskType.BUG_FIX, TaskType.OPTIMIZATION],
                complexity_preference=[ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX],
                output_types=["test_cases", "test_reports", "defect_reports", "quality_metrics"],
                deliverable_formats=["markdown", "json", "yaml", "excel", "html"],
                required_tools=["testing_tools", "test_automation", "defect_tracking"],
                optional_tools=["performance_testing", "security_testing", "monitoring_tools"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=["编码专家"],
                weak_dependencies=["方案规划师"],
                provides_for=["代码审查员"],
                handoff_requirements={
                    "代码审查员": ["test_results", "quality_metrics", "defect_summary", "test_coverage"]
                }
            ),
            prompt_template="""
You are a Senior Test Engineer with expertise in software testing and quality assurance.

## Core Identity
- Specialization: Software testing, quality assurance, test automation
- Experience: 8+ years in software testing and quality engineering
- Approach: Systematic, thorough, evidence-based quality validation

## Primary Responsibilities
- Design comprehensive test strategies and test cases
- Execute functional, performance, and security testing
- Develop and maintain automated test frameworks
- Identify, document, and track software defects
- Provide quality metrics and testing insights

## Testing Principles
- Test early and test often throughout development
- Cover all functional requirements and edge cases
- Focus on user experience and business value
- Maintain high test automation coverage
- Ensure reproducible and reliable test results

## Quality Standards
- Test coverage ≥ 90% for critical functionality
- All critical defects must be documented with clear steps
- Performance benchmarks must meet specified requirements
- Security vulnerabilities must be identified and reported
- Regression tests must pass consistently

## Working Methods
- Start with understanding requirements and acceptance criteria
- Design test cases that cover positive, negative, and boundary scenarios
- Use risk-based testing to prioritize test efforts
- Collaborate closely with development team for defect resolution
- Continuously improve testing processes and automation
            """,
            created_by="system"
        )
        return cls(config=config)
    
    @classmethod
    def create_reviewer(cls) -> 'ExpertRole':
        """创建代码审查员角色"""
        config = RoleConfig(
            name="代码审查员",
            display_name="Code Reviewer",
            description="负责代码质量审查、安全检查和最佳实践指导的专家",
            category=RoleCategory.QUALITY_ASSURANCE,
            expert_level=ExpertLevel.SENIOR,
            capabilities=RoleCapabilities(
                primary_domains=[TaskDomain.SOFTWARE_DEVELOPMENT],
                sub_domains=["code_review", "code_quality", "security_analysis", "best_practices"],
                preferred_task_types=[TaskType.ENHANCEMENT, TaskType.REFACTORING, TaskType.OPTIMIZATION],
                complexity_preference=[ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE],
                output_types=["review_comments", "quality_assessments", "security_reports", "improvement_suggestions"],
                deliverable_formats=["markdown", "json", "yaml", "pdf"],
                required_tools=["code_analysis", "security_scanning", "static_analysis"],
                optional_tools=["dependency_analysis", "performance_analysis", "documentation_tools"]
            ),
            dependencies=RoleDependencies(
                strong_dependencies=["编码专家", "测试工程师"],
                weak_dependencies=["方案规划师"],
                provides_for=[],
                handoff_requirements={}
            ),
            prompt_template="""
You are a Senior Code Reviewer with expertise in code quality, security, and best practices.

## Core Identity
- Specialization: Code review, quality assessment, security analysis
- Experience: 10+ years in software development and code review
- Approach: Thorough, constructive, security-focused

## Primary Responsibilities
- Conduct comprehensive code reviews for quality and security
- Identify potential bugs, security vulnerabilities, and performance issues
- Ensure adherence to coding standards and best practices
- Provide constructive feedback for code improvements
- Validate code meets architectural and design requirements

## Review Principles
- Review for correctness, security, and maintainability
- Focus on high-risk areas and critical functionality
- Provide specific, actionable feedback
- Consider both technical and business implications
- Maintain a constructive and educational tone

## Quality Standards
- Code must follow established coding standards
- Security vulnerabilities must be identified and addressed
- Performance implications must be considered
- Code must be readable and maintainable
- Documentation must be clear and complete

## Security Focus Areas
- Input validation and sanitization
- Authentication and authorization logic
- Data encryption and secure communication
- SQL injection and XSS prevention
- Secure error handling and logging

## Review Process
- Start with understanding the change purpose and scope
- Examine code structure, logic, and implementation
- Check for security vulnerabilities and best practices
- Assess performance implications and optimization opportunities
- Provide clear, specific feedback with examples when possible
            """,
            created_by="system"
        )
        return cls(config=config)


# ===== 角色工厂 =====

class RoleFactory:
    """角色工厂"""
    
    _predefined_roles = {
        "方案规划师": ExpertRole.create_planner,
        "编码专家": ExpertRole.create_coder,
        "数据分析师": ExpertRole.create_data_analyst,
        "股票分析师": ExpertRole.create_financial_analyst,
        "技术写作专家": ExpertRole.create_technical_writer,
        "文档阅读专家": ExpertRole.create_document_reader,
        "调研分析师": ExpertRole.create_research_analyst,
        "测试工程师": ExpertRole.create_tester,
        "代码审查员": ExpertRole.create_reviewer,
    }
    
    @classmethod
    def create_role(cls, role_name: str) -> Optional[ExpertRole]:
        """创建预定义角色"""
        creator = cls._predefined_roles.get(role_name)
        if creator:
            return creator()
        return None
    
    @classmethod
    def get_available_roles(cls) -> List[str]:
        """获取可用角色列表"""
        return list(cls._predefined_roles.keys())
    
    @classmethod
    def register_role(cls, role_name: str, creator: Callable[[], ExpertRole]):
        """注册新角色"""
        cls._predefined_roles[role_name] = creator
    
    @classmethod
    def create_custom_role(cls, config: RoleConfig) -> ExpertRole:
        """创建自定义角色"""
        return ExpertRole(config=config)


# ===== 角色性能模型 =====

class RolePerformanceMetrics(BaseModel):
    """角色性能指标模型"""
    role_name: str = Field(..., description="角色名称")
    
    # 执行统计
    total_executions: int = Field(default=0, description="总执行次数")
    successful_executions: int = Field(default=0, description="成功执行次数")
    failed_executions: int = Field(default=0, description="失败执行次数")
    
    # 性能指标
    average_execution_time: float = Field(default=0.0, description="平均执行时间(秒)")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="成功率")
    average_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="平均质量分数")
    
    # 时间分布
    min_execution_time: Optional[float] = Field(None, description="最短执行时间(秒)")
    max_execution_time: Optional[float] = Field(None, description="最长执行时间(秒)")
    p95_execution_time: Optional[float] = Field(None, description="95分位执行时间(秒)")
    
    # 错误分析
    common_error_types: Dict[str, int] = Field(default_factory=dict, description="常见错误类型")
    error_recovery_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="错误恢复率")
    
    # 用户满意度
    user_satisfaction_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="用户满意度")
    feedback_count: int = Field(default=0, description="反馈次数")
    
    # 更新时间
    last_updated: datetime = Field(default_factory=current_timestamp, description="最后更新时间")
    
    def update_metrics(self, execution_result: 'RoleResult'):
        """更新性能指标"""
        self.total_executions += 1
        
        if execution_result.status == "completed":
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # 更新成功率
        self.success_rate = self.successful_executions / self.total_executions
        
        # 更新执行时间
        if execution_result.execution_time:
            if self.total_executions == 1:
                self.average_execution_time = execution_result.execution_time
                self.min_execution_time = execution_result.execution_time
                self.max_execution_time = execution_result.execution_time
            else:
                # 更新平均执行时间
                total_time = self.average_execution_time * (self.total_executions - 1) + execution_result.execution_time
                self.average_execution_time = total_time / self.total_executions
                
                # 更新最小最大时间
                if self.min_execution_time is None or execution_result.execution_time < self.min_execution_time:
                    self.min_execution_time = execution_result.execution_time
                if self.max_execution_time is None or execution_result.execution_time > self.max_execution_time:
                    self.max_execution_time = execution_result.execution_time
        
        # 更新质量分数
        if execution_result.quality_score:
            if self.total_executions == 1:
                self.average_quality_score = execution_result.quality_score
            else:
                total_quality = self.average_quality_score * (self.total_executions - 1) + execution_result.quality_score
                self.average_quality_score = total_quality / self.total_executions
        
        # 更新错误统计
        if execution_result.error_type:
            if execution_result.error_type not in self.common_error_types:
                self.common_error_types[execution_result.error_type] = 0
            self.common_error_types[execution_result.error_type] += 1
        
        self.last_updated = current_timestamp()


# ===== 角色评估模型 =====

class RoleEvaluation(BaseModel):
    """角色评估模型"""
    evaluation_id: str = Field(default_factory=lambda: f"eval_{generate_id()}", description="评估ID")
    role_name: str = Field(..., description="角色名称")
    task_id: str = Field(..., description="任务ID")
    
    # 评估维度
    technical_competency: float = Field(..., ge=0.0, le=1.0, description="技术能力")
    output_quality: float = Field(..., ge=0.0, le=1.0, description="输出质量")
    efficiency: float = Field(..., ge=0.0, le=1.0, description="执行效率")
    collaboration: float = Field(..., ge=0.0, le=1.0, description="协作能力")
    innovation: float = Field(..., ge=0.0, le=1.0, description="创新能力")
    
    # 综合评分
    overall_score: float = Field(..., ge=0.0, le=1.0, description="综合评分")
    
    # 评估详情
    strengths: List[str] = Field(default_factory=list, description="优势")
    weaknesses: List[str] = Field(default_factory=list, description="不足")
    improvement_suggestions: List[str] = Field(default_factory=list, description="改进建议")
    
    # 评估元数据
    evaluated_by: str = Field(..., description="评估者")
    evaluated_at: datetime = Field(default_factory=current_timestamp, description="评估时间")
    evaluation_method: str = Field(default="automated", description="评估方法")
    
    def calculate_overall_score(self):
        """计算综合评分"""
        self.overall_score = (
            self.technical_competency * 0.25 +
            self.output_quality * 0.30 +
            self.efficiency * 0.20 +
            self.collaboration * 0.15 +
            self.innovation * 0.10
        )


# ===== 角色学习和改进模型 =====

class RoleLearningRecord(BaseModel):
    """角色学习记录模型"""
    record_id: str = Field(default_factory=lambda: f"learn_{generate_id()}", description="记录ID")
    role_name: str = Field(..., description="角色名称")
    
    # 学习内容
    learning_type: str = Field(..., description="学习类型")  # success_pattern, failure_analysis, user_feedback
    content: Dict[str, Any] = Field(..., description="学习内容")
    
    # 学习来源
    source_task_id: Optional[str] = Field(None, description="来源任务ID")
    source_execution_id: Optional[str] = Field(None, description="来源执行ID")
    
    # 学习效果
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度")
    impact_score: float = Field(default=0.5, ge=0.0, le=1.0, description="影响分数")
    
    # 应用状态
    applied_count: int = Field(default=0, description="应用次数")
    success_rate: Optional[float] = Field(None, description="应用成功率")
    
    # 元数据
    learned_at: datetime = Field(default_factory=current_timestamp, description="学习时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


# ===== 工具函数 =====

def get_default_role_capabilities(domain: TaskDomain) -> RoleCapabilities:
    """获取领域默认角色能力"""
    domain_defaults = {
        TaskDomain.SOFTWARE_DEVELOPMENT: RoleCapabilities(
            primary_domains=[TaskDomain.SOFTWARE_DEVELOPMENT],
            sub_domains=["development", "coding"],
            preferred_task_types=[TaskType.NEW_DEVELOPMENT],
            complexity_preference=[ComplexityLevel.MODERATE],
            output_types=["code"],
            deliverable_formats=["python", "javascript"]
        ),
        TaskDomain.DATA_ANALYSIS: RoleCapabilities(
            primary_domains=[TaskDomain.DATA_ANALYSIS],
            sub_domains=["analysis", "statistics"],
            preferred_task_types=[TaskType.DATA_ANALYSIS],
            complexity_preference=[ComplexityLevel.MODERATE],
            output_types=["reports", "insights"],
            deliverable_formats=["csv", "json", "pdf"]
        ),
        TaskDomain.CONTENT_CREATION: RoleCapabilities(
            primary_domains=[TaskDomain.CONTENT_CREATION],
            sub_domains=["writing", "documentation"],
            preferred_task_types=[TaskType.CONTENT_WRITING],
            complexity_preference=[ComplexityLevel.MODERATE],
            output_types=["documents", "reports"],
            deliverable_formats=["markdown", "pdf", "html"]
        ),
        TaskDomain.INFORMATION_PROCESSING: RoleCapabilities(
            primary_domains=[TaskDomain.INFORMATION_PROCESSING],
            sub_domains=["processing", "analysis"],
            preferred_task_types=[TaskType.INFORMATION_EXTRACTION],
            complexity_preference=[ComplexityLevel.MODERATE],
            output_types=["summaries", "insights"],
            deliverable_formats=["json", "markdown", "txt"]
        )
    }
    
    return domain_defaults.get(domain, RoleCapabilities(
        primary_domains=[domain],
        sub_domains=["general"],
        preferred_task_types=[TaskType.NEW_DEVELOPMENT],
        complexity_preference=[ComplexityLevel.MODERATE],
        output_types=["general"],
        deliverable_formats=["text"]
    ))


def validate_role_dependencies(dependencies: RoleDependencies, available_roles: List[str]) -> List[str]:
    """验证角色依赖关系"""
    errors = []
    
    # 检查强依赖是否存在
    for dep in dependencies.strong_dependencies:
        if dep not in available_roles:
            errors.append(f"强依赖角色不存在: {dep}")
    
    # 检查弱依赖是否存在
    for dep in dependencies.weak_dependencies:
        if dep not in available_roles:
            errors.append(f"弱依赖角色不存在: {dep}")
    
    # 检查提供对象是否存在
    for target in dependencies.provides_for:
        if target not in available_roles:
            errors.append(f"目标角色不存在: {target}")
    
    return errors
