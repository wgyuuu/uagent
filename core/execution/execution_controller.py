"""
Execution Controller

执行控制器 - 控制Agent执行的各种条件
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import structlog
import logging

from models.base import (
    HandoffContext, 
    IsolatedRoleContext, 
    RoleResult,
    ExecutionContext,
    AgentEnvironment,
    ExecutionConfig
)

logger = structlog.get_logger(__name__)

@dataclass
class ExecutionMetrics:
    """执行指标"""
    iteration_count: int
    total_execution_time: float
    tool_execution_count: int
    success_rate: float
    quality_score: float
    context_size: int

@dataclass
class ControlDecision:
    """控制决策"""
    can_continue: bool
    reason: str
    suggested_action: str
    priority: str  # "high", "medium", "low"

class ExecutionController:
    """执行控制器 - 控制Agent执行的各种条件"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.iteration_metrics: Dict[int, ExecutionMetrics] = {}
        self.control_history: List[ControlDecision] = []
    
    def can_continue(self, iteration: int, agent_env: AgentEnvironment) -> bool:
        """检查是否可以继续执行"""
        
        # 1. 检查最大轮数限制
        if iteration >= self.config.max_iterations:
            logger.info(f"达到最大执行轮数限制: {self.config.max_iterations}")
            self._record_control_decision(iteration, False, "达到最大执行轮数限制", "停止执行", "high")
            return False
        
        # 2. 检查质量阈值
        if hasattr(agent_env, 'quality_score') and agent_env.quality_score >= self.config.quality_threshold:
            logger.info(f"达到质量阈值: {agent_env.quality_score}")
            self._record_control_decision(iteration, False, "达到质量阈值", "停止执行", "medium")
            return False
        
        # 3. 检查上下文大小
        if self._is_context_too_large(agent_env):
            logger.info("上下文过大，需要压缩")
            self._record_control_decision(iteration, True, "上下文过大", "压缩上下文", "medium")
            return True
        
        # 4. 检查是否有明确的停止信号
        if self._has_stop_signal(agent_env):
            logger.info("检测到停止信号")
            self._record_control_decision(iteration, False, "检测到停止信号", "停止执行", "high")
            return False
        
        # 5. 检查执行效率
        if self._is_execution_inefficient(iteration, agent_env):
            logger.info("执行效率低下，建议优化")
            self._record_control_decision(iteration, True, "执行效率低下", "优化执行策略", "medium")
            return True
        
        # 6. 检查资源使用
        if self._is_resource_exhausted(agent_env):
            logger.info("资源使用过高，需要调整")
            self._record_control_decision(iteration, False, "资源使用过高", "停止执行", "high")
            return False
        
        # 可以继续执行
        self._record_control_decision(iteration, True, "执行条件正常", "继续执行", "low")
        return True
    
    def _is_context_too_large(self, agent_env: AgentEnvironment) -> bool:
        """检查上下文是否过大"""
        
        if not hasattr(agent_env, 'context'):
            return False
        
        context_size = len(str(agent_env.context))
        max_size = 10000  # 可配置的最大上下文大小
        
        return context_size > max_size
    
    def _has_stop_signal(self, agent_env: AgentEnvironment) -> bool:
        """检查是否有停止信号"""
        
        # 检查LLM响应中是否包含完成信号
        if hasattr(agent_env, 'last_response') and agent_env.last_response:
            response = agent_env.last_response.lower()
            stop_signals = [
                "task completed", "任务完成", "已完成", "完成",
                "work finished", "工作完成", "执行完毕", "任务结束",
                "mission accomplished", "目标达成", "需求满足"
            ]
            
            return any(signal in response for signal in stop_signals)
        
        return False
    
    def _is_execution_inefficient(self, iteration: int, agent_env: AgentEnvironment) -> bool:
        """检查执行是否效率低下"""
        
        if iteration < 3:
            return False  # 前几轮不检查效率
        
        # 检查工具执行效率
        if hasattr(agent_env, 'tool_execution_count'):
            tool_count = agent_env.tool_execution_count
            if tool_count > 0 and tool_count < iteration * 0.5:
                return True  # 工具使用率过低
        
        # 检查质量提升速度
        if hasattr(agent_env, 'quality_score'):
            current_quality = agent_env.quality_score
            if iteration > 5 and current_quality < 0.3:
                return True  # 质量提升过慢
        
        return False
    
    def _is_resource_exhausted(self, agent_env: AgentEnvironment) -> bool:
        """检查资源是否耗尽"""
        
        # 检查内存使用（模拟）
        if hasattr(agent_env, 'context'):
            context_size = len(str(agent_env.context))
            if context_size > 50000:  # 50KB限制
                return True
        
        # 检查执行时间
        if hasattr(agent_env, 'total_execution_time'):
            if agent_env.total_execution_time > self.config.max_execution_time:
                return True
        
        return False
    
    def _record_control_decision(self, iteration: int, can_continue: bool, reason: str, action: str, priority: str):
        """记录控制决策"""
        
        decision = ControlDecision(
            can_continue=can_continue,
            reason=reason,
            suggested_action=action,
            priority=priority
        )
        
        self.control_history.append(decision)
        
        # 记录到日志
        log_level = logging.INFO if can_continue else logging.WARNING
        logger.log(log_level, f"执行控制决策 [轮次{iteration}]: {reason} -> {action}")
    
    def get_control_summary(self) -> Dict[str, Any]:
        """获取控制摘要"""
        
        if not self.control_history:
            return {"message": "暂无控制决策记录"}
        
        # 统计决策类型
        continue_count = sum(1 for d in self.control_history if d.can_continue)
        stop_count = len(self.control_history) - continue_count
        
        # 按优先级统计
        priority_stats = {}
        for decision in self.control_history:
            priority = decision.priority
            if priority not in priority_stats:
                priority_stats[priority] = {"continue": 0, "stop": 0}
            
            if decision.can_continue:
                priority_stats[priority]["continue"] += 1
            else:
                priority_stats[priority]["stop"] += 1
        
        return {
            "total_decisions": len(self.control_history),
            "continue_decisions": continue_count,
            "stop_decisions": stop_count,
            "priority_statistics": priority_stats,
            "recent_decisions": [
                {
                    "iteration": i,
                    "can_continue": d.can_continue,
                    "reason": d.reason,
                    "action": d.suggested_action,
                    "priority": d.priority
                }
                for i, d in enumerate(self.control_history[-5:])  # 最近5个决策
            ]
        }
    
    def suggest_optimization(self, iteration: int, agent_env: AgentEnvironment) -> List[str]:
        """建议优化措施"""
        
        suggestions = []
        
        # 基于当前状态提供优化建议
        if hasattr(agent_env, 'quality_score'):
            if agent_env.quality_score < 0.5:
                suggestions.append("质量分数较低，建议重新评估任务理解")
                suggestions.append("考虑使用更多相关工具来提升输出质量")
        
        if hasattr(agent_env, 'context'):
            context_size = len(str(agent_env.context))
            if context_size > 8000:
                suggestions.append("上下文过大，建议进行压缩")
                suggestions.append("考虑移除不相关的历史信息")
        
        if iteration > 5:
            suggestions.append("执行轮次较多，建议检查是否有循环依赖")
            suggestions.append("考虑简化任务分解，减少迭代次数")
        
        # 基于控制历史提供建议
        recent_stops = [d for d in self.control_history[-3:] if not d.can_continue]
        if recent_stops:
            for decision in recent_stops:
                if "效率" in decision.reason:
                    suggestions.append("检测到效率问题，建议优化执行策略")
                elif "资源" in decision.reason:
                    suggestions.append("资源使用过高，建议优化内存管理")
        
        return suggestions
    
    def update_metrics(self, iteration: int, metrics: ExecutionMetrics):
        """更新执行指标"""
        
        self.iteration_metrics[iteration] = metrics
        
        # 基于指标调整控制策略
        if iteration > 1:
            prev_metrics = self.iteration_metrics.get(iteration - 1)
            if prev_metrics:
                # 检查质量提升
                quality_improvement = metrics.quality_score - prev_metrics.quality_score
                if quality_improvement < 0.1 and iteration > 3:
                    logger.warning(f"轮次 {iteration} 质量提升不明显: {quality_improvement:.3f}")
                
                # 检查执行效率
                time_per_tool = metrics.total_execution_time / max(metrics.tool_execution_count, 1)
                if time_per_tool > 10.0:  # 每个工具超过10秒
                    logger.warning(f"轮次 {iteration} 工具执行时间过长: {time_per_tool:.2f}s")
    
    def get_execution_health(self) -> Dict[str, Any]:
        """获取执行健康状态"""
        
        if not self.iteration_metrics:
            return {"status": "unknown", "message": "暂无执行指标"}
        
        # 计算健康分数
        total_iterations = len(self.iteration_metrics)
        avg_quality = sum(m.quality_score for m in self.iteration_metrics.values()) / total_iterations
        avg_success_rate = sum(m.success_rate for m in self.iteration_metrics.values()) / total_iterations
        
        # 判断健康状态
        if avg_quality > 0.8 and avg_success_rate > 0.9:
            status = "healthy"
        elif avg_quality > 0.6 and avg_success_rate > 0.7:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "total_iterations": total_iterations,
            "average_quality": avg_quality,
            "average_success_rate": avg_success_rate,
            "latest_metrics": self.iteration_metrics.get(max(self.iteration_metrics.keys())),
            "control_decisions": len(self.control_history)
        }
