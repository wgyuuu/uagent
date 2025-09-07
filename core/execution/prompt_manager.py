"""
Prompt Manager

提示词管理器 - 构建角色专用的提示词
"""

from typing import Dict, List, Optional, Any
import structlog

from .execution_controller import ExecutionContext
from models.roles import RoleConfig

logger = structlog.get_logger(__name__)

class PromptManager:
    """提示词管理器 - 构建角色专用的提示词"""
    
    def __init__(self):
        pass
    
    async def build_role_prompt(self, role: str, role_config: RoleConfig, context: ExecutionContext) -> str:
        """构建角色专用的完整提示词"""
        
        # 1. 获取角色模板（从RoleConfig）
        role_template = role_config.prompt_template
        
        # 2. 构建8段式上下文摘要
        context_summary = await self._build_context_summary(context)
        
        # 3. 构建工具使用指南
        tool_guide = await self._build_tool_guide(context.isolated_context.available_tools if hasattr(context.isolated_context, 'available_tools') else [])
        
        # 4. 构建执行指导
        execution_guide = await self._build_execution_guide(role_config)
        
        # 5. 组装完整提示词（整合所有内容）
        full_prompt = f"""
{role_template}

## 当前执行上下文
{context_summary}

## 可用工具
{tool_guide}

## 工具调用格式约定

请使用以下XML格式调用工具：

<tool_name>
    <!-- 工具调用的目标，说明要使用这个工具达到什么目的 -->
    <target>创建配置文件</target>
    
    <!-- 参数列表，每个 arg 元素表示一个参数 -->
    <args>
        <arg name="param1" type="string" value="value1"/>
        <arg name="param2" type="int" value="42"/>
    </args>
</tool_name>

## 工具使用原则
1. 明确说明使用工具的目的和目标
2. 提供必要的参数和上下文信息
3. 一次调用一个工具，避免复杂嵌套
4. 等待工具执行结果后再进行下一步

## 执行指导
{execution_guide}

## 任务执行指导
1. **分析阶段**: 理解任务需求，制定执行计划
2. **执行阶段**: 使用合适的工具逐步完成任务
3. **验证阶段**: 检查任务完成情况，确保质量
4. **总结阶段**: 提供任务完成状态和关键信息

## 重要提醒
<system-reminder>
你是一个专业的{role}，专注于完成当前任务。请遵循以下原则：

**执行原则：**
1. 使用可用的工具来完成任务
2. 每轮执行后评估是否完成
3. 如果任务完成，明确说明完成状态和交付物
4. 如果任务未完成，说明下一步计划和所需信息
5. 保持专业性和效率性

**任务完成标识：**
当任务完成时，请明确说明：
- 任务完成状态（完成/部分完成/需要更多信息）
- 主要交付物和成果
- 下一步建议或注意事项
</system-reminder>

请开始执行你的任务。
        """
        
        return full_prompt
    
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
