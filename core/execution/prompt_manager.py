"""
Prompt Manager

提示词管理器 - 构建角色专用的提示词
"""

from typing import Dict, List, Optional, Any
import structlog

from .tool_manager import UnifiedToolManager
from .execution_controller import ExecutionContext
from models.roles import RoleConfig

logger = structlog.get_logger(__name__)

class PromptManager:
    """提示词管理器 - 构建角色专用的提示词"""
    
    def __init__(self, tool_manager: UnifiedToolManager = None):
        self.base_templates = self._load_base_templates()
        self.role_templates = self._load_role_templates()
        self.tool_manager = tool_manager
    
    async def build_role_prompt(self, role: str, role_config: RoleConfig, context: ExecutionContext) -> str:
        """构建角色专用的完整提示词"""
        
        # 1. 获取角色基础模板
        base_template = self.role_templates.get(role, self.base_templates["default"])
        
        # 2. 构建8段式上下文摘要
        context_summary = await self._build_context_summary(context)
        
        # 3. 构建工具使用指南
        tool_guide = await self._build_tool_guide(context.isolated_context.available_tools if hasattr(context.isolated_context, 'available_tools') else [])
        
        # 4. 构建执行指导
        execution_guide = await self._build_execution_guide(role_config)
        
        # 5. 组装完整提示词
        full_prompt = f"""
{base_template}

## 当前执行上下文
{context_summary}

## 可用工具
{tool_guide}

## 执行指导
{execution_guide}

## 重要提醒
<system-reminder>
你是一个专业的{role}，专注于完成当前任务。请遵循以下原则：
1. 使用可用的工具来完成任务
2. 每轮执行后评估是否完成
3. 如果任务完成，明确说明完成状态和交付物
4. 如果任务未完成，说明下一步计划和所需信息
5. 保持专业性和效率性
</system-reminder>

请开始执行你的任务。
        """
        
        return full_prompt
    
    def _load_base_templates(self) -> Dict[str, str]:
        """加载基础模板"""
        return {
            "default": """
# 角色执行指导

你是一个专业的AI助手，负责执行特定的角色任务。请按照以下指导原则执行任务：

## 核心原则
1. **专注性**: 专注于当前角色的专业领域
2. **效率性**: 高效完成任务，避免不必要的重复
3. **质量性**: 确保输出质量达到专业标准
4. **协作性**: 为后续角色提供清晰的交接信息

## 执行流程
1. 分析当前任务和可用资源
2. 制定执行计划
3. 使用工具完成任务
4. 评估完成状态
5. 准备交接信息

## 输出要求
- 清晰的任务状态说明
- 具体的交付物描述
- 详细的交接信息
- 下一步行动建议
            """,
            
            "coding_expert": """
# 编码专家角色

你是一个专业的软件工程师，擅长代码开发、调试和优化。

## 专业能力
- 代码实现和重构
- 问题诊断和修复
- 性能优化
- 代码质量保证

## 工作方式
1. 仔细分析技术需求
2. 设计实现方案
3. 编写高质量代码
4. 进行必要的测试
5. 准备技术文档
            """,
            
            "planner": """
# 方案规划师角色

你是一个专业的项目规划师，擅长需求分析、架构设计和技术规划。

## 专业能力
- 需求分析和分解
- 技术方案设计
- 架构规划
- 风险评估

## 工作方式
1. 深入理解用户需求
2. 分析技术可行性
3. 设计解决方案
4. 制定实施计划
5. 识别潜在风险
            """
        }
    
    def _load_role_templates(self) -> Dict[str, str]:
        """加载角色专用模板"""
        return {
            "coding_expert": self.base_templates["coding_expert"],
            "planner": self.base_templates["planner"],
            "tester": """
# 测试工程师角色

你是一个专业的测试工程师，擅长测试设计、执行和质量保证。

## 专业能力
- 测试用例设计
- 自动化测试
- 性能测试
- 缺陷管理

## 工作方式
1. 分析测试需求
2. 设计测试策略
3. 执行测试用例
4. 报告测试结果
5. 跟踪缺陷修复
            """,
            
            "reviewer": """
# 代码审查员角色

你是一个专业的代码审查员，擅长代码质量评估和安全检查。

## 专业能力
- 代码质量评估
- 安全漏洞检测
- 最佳实践检查
- 性能问题识别

## 工作方式
1. 仔细阅读代码
2. 识别潜在问题
3. 提供改进建议
4. 确保代码标准
5. 安全风险评估
            """
        }
    
    async def _build_context_summary(self, context: ExecutionContext) -> str:
        """构建8段式上下文摘要"""
        
        # 使用Claude Code的8段式压缩思想
        summary_sections = [
            "Primary Request and Intent",
            "Key Technical Concepts", 
            "Files and Code Sections",
            "Errors and fixes",
            "Problem Solving",
            "All user messages",
            "Pending Tasks",
            "Current Work"
        ]
        
        summary = []
        for section in summary_sections:
            content = ""
            if hasattr(context.isolated_context, 'get_section'):
                content = context.isolated_context.get_section(section, "")
            elif hasattr(context.isolated_context, 'sections'):
                content = context.isolated_context.sections.get(section, "")
            
            if content:
                summary.append(f"### {section}\n{content}")
        
        if not summary:
            # 如果没有8段式内容，使用基本信息
            summary.append(f"### 任务描述\n{getattr(context, 'task_description', '未提供任务描述')}")
            summary.append(f"### 工作流ID\n{context.workflow_id}")
            summary.append(f"### 当前角色\n{context.current_role}")
        
        return "\n\n".join(summary)
    
    async def _build_tool_guide(self, available_tools: List[str]) -> str:
        """构建工具使用指南"""
        
        if not available_tools:
            return "当前没有可用的工具。"
        
        tool_descriptions = []
        for tool in available_tools:
            # 这里应该从工具管理器获取详细信息
            tool_info = await self._get_tool_info(tool)
            tool_descriptions.append(f"- **{tool}**: {tool_info}")
        
        return "\n".join(tool_descriptions)
    
    async def _get_tool_info(self, tool_name: str) -> str:
        """获取工具信息"""
        # 这里应该从工具管理器获取详细信息
        # 暂时返回基本描述
        tool_descriptions = {
            "file_operations": "文件操作工具，支持读取、写入、删除等操作",
            "code_analysis": "代码分析工具，支持语法检查、依赖分析等",
            "testing_tools": "测试工具，支持单元测试、集成测试等",
            "git_operations": "Git操作工具，支持提交、分支、合并等",
            "user_question": "用户交互工具，支持获取用户确认和反馈"
        }
        
        return tool_descriptions.get(tool_name, f"{tool_name} 工具")
    
    async def _build_execution_guide(self, role_config: RoleConfig) -> str:
        """构建执行指导"""
        
        guide = f"""
## 角色信息
- **角色名称**: {role_config.name}
- **专业领域**: {role_config.category}
- **专家级别**: {role_config.expert_level}
- **最大执行时间**: {role_config.max_execution_time} 秒

## 执行要求
"""
        
        if role_config.behavior_rules:
            guide += "\n### 行为规则\n"
            for rule in role_config.behavior_rules:
                guide += f"- {rule}\n"
        
        if role_config.capabilities and role_config.capabilities.output_types:
            guide += f"\n### 输出要求\n"
            for output_type in role_config.capabilities.output_types:
                guide += f"- {output_type}\n"
        
        guide += """
## 质量标准
- 确保输出符合专业标准
- 保持代码和文档的一致性
- 遵循最佳实践和行业标准
- 及时识别和报告问题

## 交接要求
当任务完成时，请提供详细的交接信息，包括：
1. 完成状态总结
2. 关键交付物说明
3. 技术要点和注意事项
4. 下一步行动建议
5. 潜在风险和缓解措施
        """
        
        return guide
