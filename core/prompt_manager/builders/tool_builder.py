"""
Tool Builder

工具构建器 - 构建工具能力信息和调用规范
"""

import structlog
from typing import TYPE_CHECKING, Optional

from .base_builder import BasePromptBuilder

if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class ToolBuilder(BasePromptBuilder):
    """工具构建器"""
    
    def __init__(self):
        pass
    
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建工具能力section"""
        
        try:
            available_tools = request.available_tools
            
            if not available_tools:
                return "## 可用工具能力\n当前没有可用的工具。"
            
            # 获取详细工具信息
            tools_info = await self._get_tools_detailed_info(available_tools)
            
            # 构建工具section
            tools_section = "## 可用工具能力\n"
            
            for tool_name in available_tools:
                tool_info = tools_info.get(tool_name, {})
                category = tool_info.get('category', '通用')
                description = tool_info.get('description', f'{tool_name} 工具')
                
                tools_section += f"- **{tool_name}** ({category}): {description}\n"
            
            # 添加工具调用格式规范
            tools_section += self._get_tool_format_specification()
            
            logger.debug(f"构建工具section完成，包含 {len(available_tools)} 个工具")
            return tools_section.strip()
            
        except Exception as e:
            logger.error(f"构建工具section失败: {e}")
            # 降级处理
            return await self._build_basic_tools_section(request.available_tools)
    
    async def _get_tools_detailed_info(self, tool_names: list[str]) -> dict[str, dict]:
        """获取工具详细信息"""
        
        tools_info = {}
        
        try:
            # 直接使用默认描述，简化实现
            for tool_name in tool_names:
                tools_info[tool_name] = self._get_default_tool_info(tool_name)
        
        except Exception as e:
            logger.warning(f"获取工具详细信息失败: {e}")
            # 使用默认信息
            for tool_name in tool_names:
                tools_info[tool_name] = self._get_default_tool_info(tool_name)
        
        return tools_info
    
    def _get_default_tool_info(self, tool_name: str) -> dict[str, str]:
        """获取默认工具信息"""
        
        default_descriptions = {
            "file_operations": {
                "category": "文件操作",
                "description": "支持文件读取、写入、删除等操作"
            },
            "code_analysis": {
                "category": "代码分析", 
                "description": "支持语法检查、依赖分析、代码质量评估"
            },
            "testing_tools": {
                "category": "测试工具",
                "description": "支持单元测试、集成测试、性能测试"
            },
            "git_operations": {
                "category": "版本控制",
                "description": "支持Git提交、分支、合并等操作"
            },
            "user_question": {
                "category": "用户交互",
                "description": "支持获取用户确认和反馈"
            },
            "web_search": {
                "category": "信息检索",
                "description": "支持网络搜索和信息收集"
            },
            "documentation": {
                "category": "文档处理",
                "description": "支持文档生成、格式化、转换"
            }
        }
        
        return default_descriptions.get(tool_name, {
            "category": "通用工具",
            "description": f"{tool_name} 工具"
        })
    
    def _get_tool_format_specification(self) -> str:
        """获取工具调用格式规范"""
        
        return """

## 工具调用格式规范

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
4. 等待工具执行结果后再进行下一步"""
    
    async def _build_basic_tools_section(self, available_tools: list[str]) -> str:
        """构建基本工具section（降级方案）"""
        
        if not available_tools:
            return "## 可用工具能力\n当前没有可用的工具。"
        
        tools_section = "## 可用工具能力\n"
        for tool_name in available_tools:
            tools_section += f"- **{tool_name}**: 可用工具\n"
        
        tools_section += self._get_tool_format_specification()
        
        return tools_section.strip()
    
    def get_section_name(self) -> str:
        return "tools"
    
    def get_priority(self) -> int:
        return 30
    
    def is_required(self) -> bool:
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数"""
        return request.available_tools is not None
