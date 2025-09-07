"""
State Builder

执行状态构建器 - 构建当前执行状态信息
"""

import structlog
from typing import TYPE_CHECKING

from .base_builder import BasePromptBuilder

if TYPE_CHECKING:
    from ..dto.prompt_request import PromptBuildRequest

logger = structlog.get_logger(__name__)


class StateBuilder(BasePromptBuilder):
    """执行状态构建器"""
    
    async def build(self, request: 'PromptBuildRequest') -> str:
        """构建执行状态section"""
        
        try:
            execution_state = request.execution_state
            
            state_section = "## 当前执行状态\n"
            
            # 基础执行信息
            state_section += f"- 执行轮次: 第 {execution_state.iteration} 轮\n"
            state_section += f"- 当前角色: {execution_state.role}\n"
            state_section += f"- 迭代计数: {execution_state.iteration_count}\n"
            state_section += f"- 质量评分: {execution_state.quality_score:.2f}\n"
            
            # 工具执行统计
            if execution_state.tool_execution_stats:
                stats = execution_state.tool_execution_stats
                state_section += f"\n### 工具执行统计\n"
                state_section += f"- 总调用次数: {stats.get('total_calls', 0)}\n"
                state_section += f"- 成功次数: {stats.get('successful_calls', 0)}\n"
                state_section += f"- 失败次数: {stats.get('failed_calls', 0)}\n"
                
                if stats.get('success_rate') is not None:
                    state_section += f"- 成功率: {stats['success_rate']:.2%}\n"
            
            # 执行历史信息
            if execution_state.previous_actions:
                state_section += f"\n### 执行历史\n"
                recent_actions = execution_state.previous_actions[-3:]  # 只显示最近3个动作
                for i, action in enumerate(recent_actions, 1):
                    state_section += f"{i}. {action}\n"
            
            # 完成信号
            if execution_state.completion_signals:
                state_section += f"\n### 完成信号\n"
                for signal in execution_state.completion_signals:
                    state_section += f"- {signal}\n"
            
            # 性能指标
            if execution_state.execution_time or execution_state.memory_usage:
                state_section += f"\n### 性能指标\n"
                if execution_state.execution_time:
                    state_section += f"- 执行时间: {execution_state.execution_time:.2f}秒\n"
                if execution_state.memory_usage:
                    state_section += f"- 内存使用: {execution_state.memory_usage:.2f}MB\n"
            
            # 最终迭代标识
            if execution_state.is_final_iteration:
                state_section += f"\n⚠️ **这是最终迭代轮次，请确保完成所有任务**\n"
            
            logger.debug(f"构建执行状态section完成")
            return state_section.strip()
            
        except Exception as e:
            logger.error(f"构建执行状态section失败: {e}")
            # 降级处理
            return await self._build_basic_state_section(request.execution_state)
    
    async def _build_basic_state_section(self, execution_state) -> str:
        """构建基本状态section（降级方案）"""
        
        try:
            state_section = "## 当前执行状态\n"
            state_section += f"- 执行轮次: 第 {getattr(execution_state, 'iteration', 1)} 轮\n"
            state_section += f"- 当前角色: {getattr(execution_state, 'role', '未知')}\n"
            state_section += f"- 质量评分: {getattr(execution_state, 'quality_score', 0.0):.2f}\n"
            
            return state_section.strip()
            
        except Exception as e:
            logger.error(f"构建基本状态section也失败: {e}")
            return "## 当前执行状态\n- 状态信息获取失败"
    
    def get_section_name(self) -> str:
        return "state"
    
    def get_priority(self) -> int:
        return 40
    
    def is_required(self) -> bool:
        return True
    
    async def validate_input(self, request: 'PromptBuildRequest') -> bool:
        """验证输入参数"""
        return (request.execution_state is not None and
                hasattr(request.execution_state, 'iteration') and
                hasattr(request.execution_state, 'role'))
