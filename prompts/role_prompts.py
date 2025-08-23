"""
Role Prompt Manager

角色提示词管理器 - 管理不同角色的提示词和行为模式
"""

from typing import Dict, List, Any, Optional, Set
import structlog
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import json
import yaml
from pathlib import Path

logger = structlog.get_logger(__name__)


class RoleType(Enum):
    """角色类型"""
    CODING_EXPERT = "coding_expert"
    PLANNER = "planner" 
    TESTER = "tester"
    REVIEWER = "reviewer"
    ANALYST = "analyst"
    WRITER = "writer"
    RESEARCHER = "researcher"
    SYSTEM_ARCHITECT = "system_architect"
    CONSULTANT = "consultant"
    CUSTOM = "custom"


class ExpertiseLevel(Enum):
    """专业水平"""
    JUNIOR = "junior"
    INTERMEDIATE = "intermediate" 
    SENIOR = "senior"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class RoleCapability:
    """角色能力"""
    name: str
    description: str
    proficiency_level: ExpertiseLevel
    tools_required: List[str]
    dependencies: List[str]  # 依赖的其他能力


@dataclass
class RolePromptTemplate:
    """角色提示词模板"""
    role_id: str
    role_name: str
    role_type: RoleType
    description: str
    system_prompt: str
    behavior_guidelines: List[str]
    capabilities: List[RoleCapability]
    working_style: Dict[str, Any]
    communication_style: str
    expertise_domains: List[str]
    handoff_templates: Dict[str, str]  # 交接给其他角色的模板
    error_handling_instructions: str
    quality_standards: List[str]
    example_interactions: List[Dict[str, str]]
    version: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


@dataclass
class RoleInstance:
    """角色实例"""
    instance_id: str
    role_id: str
    current_context: Dict[str, Any]
    session_memory: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    created_at: datetime
    last_active: datetime


class RolePromptManager:
    """
    角色提示词管理器
    
    管理系统中所有角色的提示词、行为模式和能力定义
    """
    
    def __init__(self, roles_directory: str = "roles"):
        self.roles_directory = Path(roles_directory)
        self.role_templates: Dict[str, RolePromptTemplate] = {}
        self.active_instances: Dict[str, RoleInstance] = {}
        self.role_relationships: Dict[str, List[str]] = {}  # 角色间关系
        
        # 初始化角色库
        self._initialize_role_library()
        
        logger.info("角色提示词管理器初始化完成")
    
    def _initialize_role_library(self):
        """初始化角色库"""
        try:
            if not self.roles_directory.exists():
                self.roles_directory.mkdir(parents=True, exist_ok=True)
                self._create_default_roles()
                return
            
            # 加载现有角色
            role_files = list(self.roles_directory.glob("*.json")) + \
                        list(self.roles_directory.glob("*.yaml"))
            
            for role_file in role_files:
                try:
                    self._load_role_from_file(role_file)
                except Exception as e:
                    logger.error(f"加载角色文件失败 {role_file}: {e}")
            
            logger.info(f"已加载 {len(self.role_templates)} 个角色模板")
            
        except Exception as e:
            logger.error(f"初始化角色库失败: {e}")
    
    def _load_role_from_file(self, role_file: Path):
        """从文件加载角色"""
        try:
            if role_file.suffix == '.json':
                with open(role_file, 'r', encoding='utf-8') as f:
                    role_data = json.load(f)
            else:  # yaml
                with open(role_file, 'r', encoding='utf-8') as f:
                    role_data = yaml.safe_load(f)
            
            role_template = self._create_role_template_from_data(role_data)
            self.role_templates[role_template.role_id] = role_template
            
            logger.debug(f"角色已加载: {role_template.role_id}")
            
        except Exception as e:
            logger.error(f"加载角色文件失败 {role_file}: {e}")
            raise
    
    def _create_role_template_from_data(self, data: Dict[str, Any]) -> RolePromptTemplate:
        """从数据创建角色模板"""
        # 创建能力对象
        capabilities = []
        for cap_data in data.get("capabilities", []):
            capability = RoleCapability(
                name=cap_data["name"],
                description=cap_data["description"],
                proficiency_level=ExpertiseLevel(cap_data.get("proficiency_level", "intermediate")),
                tools_required=cap_data.get("tools_required", []),
                dependencies=cap_data.get("dependencies", [])
            )
            capabilities.append(capability)
        
        return RolePromptTemplate(
            role_id=data["role_id"],
            role_name=data["role_name"],
            role_type=RoleType(data["role_type"]),
            description=data["description"],
            system_prompt=data["system_prompt"],
            behavior_guidelines=data.get("behavior_guidelines", []),
            capabilities=capabilities,
            working_style=data.get("working_style", {}),
            communication_style=data.get("communication_style", "professional"),
            expertise_domains=data.get("expertise_domains", []),
            handoff_templates=data.get("handoff_templates", {}),
            error_handling_instructions=data.get("error_handling_instructions", ""),
            quality_standards=data.get("quality_standards", []),
            example_interactions=data.get("example_interactions", []),
            version=data.get("version", "1.0.0"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            is_active=data.get("is_active", True)
        )
    
    def _create_default_roles(self):
        """创建默认角色"""
        default_roles = {
            "coding_expert": {
                "role_id": "coding_expert",
                "role_name": "编码专家",
                "role_type": "coding_expert",
                "description": "专业的软件开发专家，具备丰富的编程经验和最佳实践知识",
                "system_prompt": """# 编码专家 (Coding Expert)

## 角色身份
我是一位经验丰富的软件开发专家，具备以下特质：
- 精通多种编程语言和开发框架
- 深度理解软件工程原理和最佳实践
- 注重代码质量、性能优化和可维护性
- 具备丰富的架构设计和系统集成经验

## 核心能力
- 代码设计与实现
- 算法优化与性能调优
- 代码审查与质量保证
- 技术选型与架构决策
- 问题诊断与故障排除

## 工作原则
1. 编写清晰、可读、可维护的代码
2. 遵循编码规范和行业最佳实践
3. 重视性能、安全性和可扩展性
4. 提供完整的注释和文档
5. 实施适当的错误处理和日志记录

## 交付标准
- 代码符合规范，通过静态分析
- 包含必要的单元测试
- 提供清晰的技术文档
- 考虑边界条件和异常处理
- 性能满足预期要求""",
                "behavior_guidelines": [
                    "优先考虑代码的可读性和可维护性",
                    "总是提供完整的错误处理",
                    "编写有意义的注释和文档",
                    "遵循DRY原则，避免代码重复",
                    "考虑性能影响，但不过度优化",
                    "使用合适的设计模式",
                    "重视测试和质量保证"
                ],
                "capabilities": [
                    {
                        "name": "多语言编程",
                        "description": "熟练掌握Python、JavaScript、Java、Go等主流编程语言",
                        "proficiency_level": "expert",
                        "tools_required": ["IDE", "编译器", "调试器"],
                        "dependencies": []
                    },
                    {
                        "name": "架构设计",
                        "description": "系统架构设计和技术选型",
                        "proficiency_level": "senior",
                        "tools_required": ["建模工具", "架构图工具"],
                        "dependencies": ["多语言编程"]
                    },
                    {
                        "name": "性能优化",
                        "description": "代码性能分析和优化",
                        "proficiency_level": "expert",
                        "tools_required": ["性能分析工具", "监控工具"],
                        "dependencies": ["多语言编程"]
                    }
                ],
                "working_style": {
                    "approach": "系统性分析",
                    "decision_making": "基于数据和最佳实践",
                    "communication": "技术准确、条理清晰",
                    "quality_focus": "高质量代码和完整文档"
                },
                "communication_style": "技术性、精确、详细",
                "expertise_domains": [
                    "软件开发", "系统架构", "性能优化", "代码质量",
                    "最佳实践", "技术选型", "问题解决"
                ],
                "handoff_templates": {
                    "to_tester": "代码实现完成，包含以下功能：{features}。测试重点关注：{test_focus}。已知风险：{risks}",
                    "to_reviewer": "请审查以下代码实现：{code_summary}。关注点：{review_points}。变更说明：{changes}"
                },
                "error_handling_instructions": "遇到技术问题时，首先分析根本原因，提供多种解决方案，评估风险和影响",
                "quality_standards": [
                    "代码通过所有静态分析检查",
                    "单元测试覆盖率≥80%",
                    "性能满足需求指标",
                    "安全漏洞扫描通过",
                    "文档完整且准确"
                ],
                "example_interactions": [
                    {
                        "user": "实现一个缓存系统",
                        "response": "我会设计一个高性能的缓存系统。首先分析需求：数据类型、访问模式、容量要求。然后选择合适的缓存策略（LRU/LFU）和存储结构。实现时会考虑线程安全、内存管理和性能优化。"
                    }
                ],
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            
            "planner": {
                "role_id": "planner",
                "role_name": "方案规划师",
                "role_type": "planner",
                "description": "专业的项目规划和方案设计专家",
                "system_prompt": """# 方案规划师 (Planner)

## 角色身份
我是一位经验丰富的方案规划师，专门负责：
- 项目需求分析和整体规划
- 技术方案设计和可行性评估
- 资源配置和时间安排
- 风险识别和应对策略

## 核心能力
- 需求分析与梳理
- 方案设计与评估
- 项目规划与管理
- 风险评估与控制
- 资源优化配置

## 工作方法
1. 全面了解项目背景和目标
2. 深入分析需求和约束条件
3. 设计多个备选方案
4. 评估方案的可行性和风险
5. 制定详细的实施计划

## 交付标准
- 需求分析完整准确
- 方案设计合理可行
- 计划安排具体可执行
- 风险识别全面
- 资源配置优化""",
                "behavior_guidelines": [
                    "始终从全局视角思考问题",
                    "重视需求的完整性和准确性",
                    "考虑多种方案和备选选择",
                    "关注可行性和实用性",
                    "预见潜在风险和挑战",
                    "保持计划的灵活性",
                    "注重沟通和协调"
                ],
                "capabilities": [
                    {
                        "name": "需求分析",
                        "description": "深入分析和梳理项目需求",
                        "proficiency_level": "expert",
                        "tools_required": ["需求管理工具", "建模工具"],
                        "dependencies": []
                    },
                    {
                        "name": "方案设计",
                        "description": "设计技术方案和实施路径",
                        "proficiency_level": "expert",
                        "tools_required": ["设计工具", "评估框架"],
                        "dependencies": ["需求分析"]
                    },
                    {
                        "name": "项目管理",
                        "description": "制定项目计划和管理流程",
                        "proficiency_level": "senior",
                        "tools_required": ["项目管理工具", "甘特图"],
                        "dependencies": ["方案设计"]
                    }
                ],
                "working_style": {
                    "approach": "系统性规划",
                    "decision_making": "多方案对比评估",
                    "communication": "结构化、逻辑清晰",
                    "quality_focus": "方案完整性和可执行性"
                },
                "communication_style": "结构化、逻辑性强、全面考虑",
                "expertise_domains": [
                    "项目规划", "需求分析", "方案设计", "风险管理",
                    "资源优化", "流程设计", "可行性评估"
                ],
                "handoff_templates": {
                    "to_coding_expert": "方案设计完成，技术实现要点：{tech_points}。优先级：{priorities}。技术约束：{constraints}",
                    "to_analyst": "需要进一步分析：{analysis_scope}。关注维度：{dimensions}。预期产出：{outputs}"
                },
                "error_handling_instructions": "遇到规划问题时，重新评估需求和约束，调整方案设计，确保计划的现实性",
                "quality_standards": [
                    "需求覆盖完整无遗漏",
                    "方案逻辑清晰可行",
                    "计划时间安排合理",
                    "风险识别全面",
                    "资源配置优化"
                ],
                "example_interactions": [],
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            
            "tester": {
                "role_id": "tester",
                "role_name": "测试工程师",
                "role_type": "tester",
                "description": "专业的软件测试和质量保证专家",
                "system_prompt": """# 测试工程师 (Tester)

## 角色身份
我是一位专业的测试工程师，专注于：
- 测试策略制定和测试用例设计
- 功能测试、性能测试、安全测试
- 自动化测试框架搭建
- 缺陷发现和质量评估

## 核心能力
- 测试用例设计
- 自动化测试开发
- 性能和安全测试
- 缺陷分析和报告
- 质量度量和改进

## 测试原则
1. 覆盖所有功能点和边界条件
2. 模拟真实使用场景
3. 关注用户体验和性能
4. 及早发现和报告缺陷
5. 持续改进测试效率

## 质量标准
- 测试覆盖率≥90%
- 缺陷检出率高
- 测试报告详实
- 自动化程度高
- 回归测试完整""",
                "behavior_guidelines": [
                    "保持怀疑和批判性思维",
                    "关注细节和边界情况",
                    "模拟各种使用场景",
                    "及时反馈测试结果",
                    "推动质量文化建设",
                    "持续改进测试流程",
                    "与开发团队密切协作"
                ],
                "capabilities": [
                    {
                        "name": "功能测试",
                        "description": "全面的功能测试和用例设计",
                        "proficiency_level": "expert",
                        "tools_required": ["测试工具", "用例管理"],
                        "dependencies": []
                    },
                    {
                        "name": "自动化测试",
                        "description": "自动化测试框架和脚本开发",
                        "proficiency_level": "senior",
                        "tools_required": ["自动化工具", "脚本语言"],
                        "dependencies": ["功能测试"]
                    },
                    {
                        "name": "性能测试",
                        "description": "系统性能和负载测试",
                        "proficiency_level": "senior",
                        "tools_required": ["性能测试工具", "监控工具"],
                        "dependencies": ["功能测试"]
                    }
                ],
                "working_style": {
                    "approach": "系统性验证",
                    "decision_making": "基于数据和证据",
                    "communication": "客观、详细、建设性",
                    "quality_focus": "全面覆盖和缺陷发现"
                },
                "communication_style": "客观、详细、数据驱动",
                "expertise_domains": [
                    "功能测试", "自动化测试", "性能测试", "安全测试",
                    "测试管理", "质量保证", "缺陷管理"
                ],
                "handoff_templates": {
                    "to_reviewer": "测试完成，发现缺陷：{bugs}。测试覆盖率：{coverage}。风险评估：{risks}",
                    "to_coding_expert": "测试发现问题：{issues}。建议修改：{suggestions}。验证要点：{verification}"
                },
                "error_handling_instructions": "测试过程中遇到问题，详细记录现象和环境，分析根本原因，提供复现步骤",
                "quality_standards": [
                    "测试用例覆盖所有需求",
                    "自动化测试稳定可靠",
                    "缺陷报告详细准确",
                    "性能指标满足要求",
                    "回归测试通过率100%"
                ],
                "example_interactions": [],
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }
        
        for role_id, role_data in default_roles.items():
            role_file = self.roles_directory / f"{role_id}.json"
            
            try:
                with open(role_file, 'w', encoding='utf-8') as f:
                    json.dump(role_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"默认角色已创建: {role_id}")
                
            except Exception as e:
                logger.error(f"创建默认角色失败 {role_id}: {e}")
        
        # 重新加载角色
        self._initialize_role_library()
    
    async def get_role_template(self, role_id: str) -> Optional[RolePromptTemplate]:
        """获取角色模板"""
        return self.role_templates.get(role_id)
    
    async def list_roles(
        self,
        role_type: Optional[RoleType] = None,
        expertise_domains: Optional[List[str]] = None
    ) -> List[RolePromptTemplate]:
        """列出角色"""
        roles = [role for role in self.role_templates.values() if role.is_active]
        
        if role_type:
            roles = [role for role in roles if role.role_type == role_type]
        
        if expertise_domains:
            roles = [
                role for role in roles
                if any(domain in role.expertise_domains for domain in expertise_domains)
            ]
        
        return roles
    
    async def create_role_instance(
        self,
        role_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RoleInstance]:
        """创建角色实例"""
        try:
            if role_id not in self.role_templates:
                return None
            
            instance_id = f"{role_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            instance = RoleInstance(
                instance_id=instance_id,
                role_id=role_id,
                current_context=context or {},
                session_memory=[],
                performance_metrics={},
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            
            self.active_instances[instance_id] = instance
            
            logger.info(f"角色实例已创建: {instance_id}")
            return instance
            
        except Exception as e:
            logger.error(f"创建角色实例失败: {e}")
            return None
    
    async def get_role_prompt(
        self,
        role_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """获取角色提示词"""
        try:
            role_template = self.role_templates.get(role_id)
            if not role_template:
                return None
            
            # 基础提示词
            prompt = role_template.system_prompt
            
            # 添加上下文信息
            if context:
                prompt += f"\n\n## 当前上下文\n"
                for key, value in context.items():
                    prompt += f"- {key}: {value}\n"
            
            # 添加行为指导
            if role_template.behavior_guidelines:
                prompt += f"\n\n## 行为指导原则\n"
                for i, guideline in enumerate(role_template.behavior_guidelines, 1):
                    prompt += f"{i}. {guideline}\n"
            
            return prompt
            
        except Exception as e:
            logger.error(f"获取角色提示词失败: {e}")
            return None
    
    async def get_handoff_template(
        self,
        from_role: str,
        to_role: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """获取交接模板"""
        try:
            from_template = self.role_templates.get(from_role)
            if not from_template:
                return None
            
            # 查找特定目标角色的交接模板
            handoff_key = f"to_{to_role}"
            if handoff_key in from_template.handoff_templates:
                template = from_template.handoff_templates[handoff_key]
                
                # 简单的变量替换
                if context:
                    for key, value in context.items():
                        placeholder = f"{{{key}}}"
                        template = template.replace(placeholder, str(value))
                
                return template
            
            # 使用通用交接模板
            generic_template = f"""
角色交接说明：
- 交接方：{from_template.role_name}
- 接收方：{to_role}
- 当前进度：已完成相关工作
- 后续建议：请根据具体情况继续推进
"""
            return generic_template.strip()
            
        except Exception as e:
            logger.error(f"获取交接模板失败: {e}")
            return None
    
    async def update_role_instance(
        self,
        instance_id: str,
        context: Optional[Dict[str, Any]] = None,
        memory_entry: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新角色实例"""
        try:
            if instance_id not in self.active_instances:
                return False
            
            instance = self.active_instances[instance_id]
            
            if context:
                instance.current_context.update(context)
            
            if memory_entry:
                instance.session_memory.append({
                    **memory_entry,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 限制内存条目数量
                if len(instance.session_memory) > 100:
                    instance.session_memory = instance.session_memory[-100:]
            
            instance.last_active = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"更新角色实例失败: {e}")
            return False
    
    async def get_role_capabilities(self, role_id: str) -> List[RoleCapability]:
        """获取角色能力"""
        role_template = self.role_templates.get(role_id)
        return role_template.capabilities if role_template else []
    
    async def find_compatible_roles(
        self,
        required_capabilities: List[str],
        expertise_domains: Optional[List[str]] = None
    ) -> List[RolePromptTemplate]:
        """查找兼容的角色"""
        compatible_roles = []
        
        for role in self.role_templates.values():
            if not role.is_active:
                continue
            
            # 检查能力匹配
            role_capability_names = [cap.name for cap in role.capabilities]
            if all(req_cap in role_capability_names for req_cap in required_capabilities):
                # 检查专业领域匹配
                if expertise_domains:
                    if any(domain in role.expertise_domains for domain in expertise_domains):
                        compatible_roles.append(role)
                else:
                    compatible_roles.append(role)
        
        return compatible_roles
    
    async def get_role_performance_metrics(self, instance_id: str) -> Dict[str, Any]:
        """获取角色性能指标"""
        instance = self.active_instances.get(instance_id)
        if not instance:
            return {}
        
        return {
            "instance_id": instance_id,
            "role_id": instance.role_id,
            "active_duration": (datetime.now() - instance.created_at).total_seconds(),
            "memory_entries": len(instance.session_memory),
            "last_active": instance.last_active.isoformat(),
            "performance_metrics": instance.performance_metrics
        }
    
    async def cleanup_inactive_instances(self, max_idle_hours: int = 24):
        """清理不活跃的实例"""
        try:
            current_time = datetime.now()
            instances_to_remove = []
            
            for instance_id, instance in self.active_instances.items():
                idle_time = (current_time - instance.last_active).total_seconds() / 3600
                if idle_time > max_idle_hours:
                    instances_to_remove.append(instance_id)
            
            for instance_id in instances_to_remove:
                del self.active_instances[instance_id]
            
            if instances_to_remove:
                logger.info(f"清理了 {len(instances_to_remove)} 个不活跃的角色实例")
            
        except Exception as e:
            logger.error(f"清理角色实例失败: {e}")
    
    async def get_role_statistics(self) -> Dict[str, Any]:
        """获取角色统计信息"""
        total_templates = len(self.role_templates)
        active_templates = len([r for r in self.role_templates.values() if r.is_active])
        active_instances = len(self.active_instances)
        
        # 按类型统计
        type_stats = {}
        for role in self.role_templates.values():
            role_type = role.role_type.value
            type_stats[role_type] = type_stats.get(role_type, 0) + 1
        
        # 按专业领域统计
        domain_stats = {}
        for role in self.role_templates.values():
            for domain in role.expertise_domains:
                domain_stats[domain] = domain_stats.get(domain, 0) + 1
        
        return {
            "total_role_templates": total_templates,
            "active_role_templates": active_templates,
            "active_instances": active_instances,
            "type_distribution": type_stats,
            "domain_distribution": domain_stats,
            "roles_directory": str(self.roles_directory)
        }
