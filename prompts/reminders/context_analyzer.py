"""
Context Analyzer

上下文分析器 - 分析系统上下文以触发智能提醒
"""

from typing import Dict, List, Any, Optional
import structlog
import re
from datetime import datetime
from dataclasses import dataclass

from .system_reminder import ContextInfo

logger = structlog.get_logger(__name__)


class ContextAnalyzer:
    """
    上下文分析器
    
    分析系统状态和用户行为以生成智能提醒
    """
    
    def __init__(self):
        self.analysis_rules: Dict[str, Dict[str, Any]] = {}
        self.context_history: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, re.Pattern] = {}
        
        # 初始化分析规则
        self._initialize_analysis_rules()
        
        logger.info("上下文分析器初始化完成")
    
    def _initialize_analysis_rules(self):
        """初始化分析规则"""
        self.analysis_rules = {
            "code_quality": {
                "patterns": [
                    r"function\s+\w+\s*\([^)]*\)\s*{[^}]*}",  # 函数定义
                    r"class\s+\w+.*:",  # 类定义
                    r"if\s*\([^)]+\)\s*{",  # 条件语句
                    r"for\s*\([^)]+\)\s*{",  # 循环语句
                ],
                "keywords": ["代码", "函数", "类", "方法", "实现"],
                "complexity_indicators": ["嵌套", "复杂", "循环", "条件"]
            },
            
            "error_detection": {
                "patterns": [
                    r"error|exception|fail|crash",
                    r"null\s+pointer|segmentation\s+fault",
                    r"stack\s+overflow|memory\s+leak"
                ],
                "keywords": ["错误", "异常", "失败", "崩溃", "问题"],
                "severity_indicators": ["critical", "severe", "major"]
            },
            
            "performance_analysis": {
                "patterns": [
                    r"slow|timeout|performance|latency",
                    r"cpu\s+usage|memory\s+usage|disk\s+usage"
                ],
                "keywords": ["性能", "缓慢", "超时", "延迟", "资源"],
                "metrics": ["cpu", "memory", "disk", "network"]
            },
            
            "security_analysis": {
                "patterns": [
                    r"password|secret|key|token",
                    r"sql\s+injection|xss|csrf",
                    r"authentication|authorization|encryption"
                ],
                "keywords": ["安全", "密码", "加密", "认证", "授权"],
                "risk_indicators": ["vulnerability", "exposure", "breach"]
            }
        }
    
    async def analyze_context(self, context: ContextInfo) -> Dict[str, Any]:
        """分析上下文"""
        try:
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "context_summary": self._summarize_context(context),
                "detected_patterns": await self._detect_patterns(context),
                "risk_assessment": await self._assess_risks(context),
                "recommendations": await self._generate_recommendations(context),
                "complexity_score": await self._calculate_complexity(context)
            }
            
            # 记录分析历史
            self.context_history.append(analysis_result)
            
            # 限制历史记录数量
            if len(self.context_history) > 1000:
                self.context_history = self.context_history[-1000:]
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析上下文失败: {e}")
            return {}
    
    def _summarize_context(self, context: ContextInfo) -> Dict[str, Any]:
        """总结上下文"""
        summary = {
            "has_current_role": context.current_role is not None,
            "has_current_task": context.current_task is not None,
            "has_user_input": context.user_input is not None,
            "workflow_stage": context.workflow_stage,
            "recent_errors_count": len(context.recent_errors),
            "system_state_keys": list(context.system_state.keys()) if context.system_state else []
        }
        
        return summary
    
    async def _detect_patterns(self, context: ContextInfo) -> Dict[str, List[str]]:
        """检测模式"""
        detected_patterns = {}
        
        # 分析用户输入中的模式
        if context.user_input:
            for rule_name, rule_config in self.analysis_rules.items():
                patterns = rule_config.get("patterns", [])
                detected = []
                
                for pattern_str in patterns:
                    if pattern_str not in self.pattern_cache:
                        self.pattern_cache[pattern_str] = re.compile(pattern_str, re.IGNORECASE)
                    
                    pattern = self.pattern_cache[pattern_str]
                    matches = pattern.findall(context.user_input)
                    detected.extend(matches)
                
                if detected:
                    detected_patterns[rule_name] = detected
        
        return detected_patterns
    
    async def _assess_risks(self, context: ContextInfo) -> Dict[str, Any]:
        """评估风险"""
        risk_assessment = {
            "overall_risk": "low",
            "risk_factors": [],
            "risk_score": 0
        }
        
        risk_score = 0
        risk_factors = []
        
        # 检查错误历史
        if context.recent_errors:
            error_count = len(context.recent_errors)
            if error_count > 5:
                risk_score += 30
                risk_factors.append(f"高错误频率: {error_count}个错误")
            elif error_count > 2:
                risk_score += 15
                risk_factors.append(f"中等错误频率: {error_count}个错误")
        
        # 检查性能指标
        if context.performance_metrics:
            cpu_usage = context.performance_metrics.get("cpu_usage", 0)
            memory_usage = context.performance_metrics.get("memory_usage", 0)
            
            if cpu_usage > 80:
                risk_score += 20
                risk_factors.append(f"CPU使用率过高: {cpu_usage}%")
            
            if memory_usage > 90:
                risk_score += 25
                risk_factors.append(f"内存使用率过高: {memory_usage}%")
        
        # 确定风险等级
        if risk_score >= 50:
            risk_assessment["overall_risk"] = "high"
        elif risk_score >= 25:
            risk_assessment["overall_risk"] = "medium"
        else:
            risk_assessment["overall_risk"] = "low"
        
        risk_assessment["risk_score"] = risk_score
        risk_assessment["risk_factors"] = risk_factors
        
        return risk_assessment
    
    async def _generate_recommendations(self, context: ContextInfo) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于当前任务的建议
        if context.current_task:
            task_lower = context.current_task.lower()
            
            if any(keyword in task_lower for keyword in ["代码", "编程", "开发"]):
                recommendations.extend([
                    "建议编写单元测试确保代码质量",
                    "注意代码规范和最佳实践",
                    "考虑添加适当的错误处理"
                ])
            
            if any(keyword in task_lower for keyword in ["性能", "优化", "速度"]):
                recommendations.extend([
                    "建议进行性能基准测试",
                    "考虑使用性能分析工具",
                    "关注内存和CPU使用率"
                ])
            
            if any(keyword in task_lower for keyword in ["安全", "加密", "认证"]):
                recommendations.extend([
                    "确保遵循安全最佳实践",
                    "考虑进行安全审计",
                    "注意敏感信息的保护"
                ])
        
        # 基于错误历史的建议
        if context.recent_errors:
            recommendations.append("建议分析最近的错误模式并采取预防措施")
        
        # 基于工作流阶段的建议
        if context.workflow_stage:
            stage_lower = context.workflow_stage.lower()
            
            if "测试" in stage_lower:
                recommendations.append("确保测试覆盖所有关键功能和边界条件")
            elif "部署" in stage_lower:
                recommendations.append("建议进行部署前的最终检查和备份")
            elif "规划" in stage_lower:
                recommendations.append("考虑风险评估和资源分配")
        
        return recommendations
    
    async def _calculate_complexity(self, context: ContextInfo) -> int:
        """计算复杂度分数"""
        complexity_score = 0
        
        # 基于用户输入的复杂度
        if context.user_input:
            input_length = len(context.user_input)
            complexity_score += min(input_length // 100, 20)  # 最多20分
            
            # 检查复杂度指标
            for rule_config in self.analysis_rules.values():
                complexity_indicators = rule_config.get("complexity_indicators", [])
                for indicator in complexity_indicators:
                    if indicator.lower() in context.user_input.lower():
                        complexity_score += 5
        
        # 基于系统状态的复杂度
        if context.system_state:
            state_count = len(context.system_state)
            complexity_score += min(state_count * 2, 30)  # 最多30分
        
        # 基于错误数量的复杂度
        error_count = len(context.recent_errors)
        complexity_score += min(error_count * 5, 25)  # 最多25分
        
        return min(complexity_score, 100)  # 总分不超过100
    
    async def get_analysis_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取分析历史"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        filtered_history = []
        for analysis in self.context_history:
            analysis_time = datetime.fromisoformat(analysis["timestamp"]).timestamp()
            if analysis_time >= cutoff_time:
                filtered_history.append(analysis)
        
        return filtered_history
    
    async def get_pattern_statistics(self) -> Dict[str, Any]:
        """获取模式统计"""
        pattern_stats = {}
        
        for analysis in self.context_history:
            detected_patterns = analysis.get("detected_patterns", {})
            for pattern_type, patterns in detected_patterns.items():
                if pattern_type not in pattern_stats:
                    pattern_stats[pattern_type] = {"count": 0, "patterns": set()}
                
                pattern_stats[pattern_type]["count"] += len(patterns)
                pattern_stats[pattern_type]["patterns"].update(patterns)
        
        # 转换set为list以便JSON序列化
        for pattern_type in pattern_stats:
            pattern_stats[pattern_type]["patterns"] = list(pattern_stats[pattern_type]["patterns"])
        
        return pattern_stats
