"""
System Reminder

系统提醒 - 智能上下文感知提醒系统
"""

from typing import Dict, List, Any, Optional, Callable, Set
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import re
import json

logger = structlog.get_logger(__name__)


class ReminderType(Enum):
    """提醒类型"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    ERROR_PREVENTION = "error_prevention"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    WORKFLOW_GUIDANCE = "workflow_guidance"
    QUALITY_ASSURANCE = "quality_assurance"


class ReminderPriority(Enum):
    """提醒优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TriggerCondition(Enum):
    """触发条件"""
    ALWAYS = "always"
    CONTEXT_MATCH = "context_match"
    PATTERN_MATCH = "pattern_match"
    TIME_BASED = "time_based"
    FREQUENCY_BASED = "frequency_based"
    ERROR_PRONE = "error_prone"


@dataclass
class ReminderRule:
    """提醒规则"""
    rule_id: str
    name: str
    description: str
    reminder_type: ReminderType
    priority: ReminderPriority
    trigger_condition: TriggerCondition
    pattern: Optional[str] = None  # 匹配模式（正则表达式）
    context_keywords: List[str] = None  # 上下文关键词
    frequency_limit: Optional[int] = None  # 频率限制（秒）
    max_daily_triggers: Optional[int] = None  # 每日最大触发次数
    conditions: Dict[str, Any] = None  # 其他条件
    message_template: str = ""
    action_suggestions: List[str] = None
    is_active: bool = True
    created_at: datetime = datetime.now()
    
    def __post_init__(self):
        if self.context_keywords is None:
            self.context_keywords = []
        if self.conditions is None:
            self.conditions = {}
        if self.action_suggestions is None:
            self.action_suggestions = []


@dataclass
class ReminderEvent:
    """提醒事件"""
    event_id: str
    rule_id: str
    message: str
    priority: ReminderPriority
    reminder_type: ReminderType
    context: Dict[str, Any]
    suggestions: List[str]
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


@dataclass
class ContextInfo:
    """上下文信息"""
    current_role: Optional[str] = None
    current_task: Optional[str] = None
    workflow_stage: Optional[str] = None
    recent_errors: List[str] = None
    performance_metrics: Dict[str, Any] = None
    user_input: Optional[str] = None
    system_state: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.recent_errors is None:
            self.recent_errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.system_state is None:
            self.system_state = {}


class SystemReminder:
    """
    系统提醒
    
    基于上下文和预定义规则的智能提醒系统
    """
    
    def __init__(self):
        self.reminder_rules: Dict[str, ReminderRule] = {}
        self.event_history: List[ReminderEvent] = []
        self.trigger_frequency: Dict[str, List[datetime]] = {}
        self.context_analyzers: List[Callable] = []
        self.reminder_handlers: Dict[ReminderType, Callable] = {}
        
        # 初始化默认规则
        self._initialize_default_rules()
        
        logger.info("系统提醒初始化完成")
    
    def _initialize_default_rules(self):
        """初始化默认提醒规则"""
        default_rules = [
            # 安全提醒
            ReminderRule(
                rule_id="security_password_hardcode",
                name="硬编码密码检查",
                description="检测代码中的硬编码密码",
                reminder_type=ReminderType.SECURITY,
                priority=ReminderPriority.CRITICAL,
                trigger_condition=TriggerCondition.PATTERN_MATCH,
                pattern=r'password\s*=\s*["\'][^"\']+["\']',
                message_template="⚠️ 检测到可能的硬编码密码，建议使用环境变量或配置文件",
                action_suggestions=[
                    "使用环境变量存储密码",
                    "使用加密配置文件",
                    "考虑使用密钥管理服务"
                ]
            ),
            
            ReminderRule(
                rule_id="security_sql_injection",
                name="SQL注入风险",
                description="检测可能的SQL注入风险",
                reminder_type=ReminderType.SECURITY,
                priority=ReminderPriority.HIGH,
                trigger_condition=TriggerCondition.PATTERN_MATCH,
                pattern=r'SELECT.*\+.*FROM|INSERT.*\+.*INTO',
                message_template="🛡️ 检测到可能的SQL注入风险，建议使用参数化查询",
                action_suggestions=[
                    "使用参数化查询/预编译语句",
                    "验证和清理用户输入",
                    "使用ORM框架"
                ]
            ),
            
            # 性能提醒
            ReminderRule(
                rule_id="performance_large_data",
                name="大数据处理优化",
                description="处理大量数据时的性能提醒",
                reminder_type=ReminderType.PERFORMANCE,
                priority=ReminderPriority.HIGH,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["大数据", "批量处理", "数据量大", "性能"],
                message_template="📊 处理大量数据时建议考虑分批处理和内存优化",
                action_suggestions=[
                    "分批处理数据",
                    "使用流式处理",
                    "优化内存使用",
                    "考虑并行处理"
                ]
            ),
            
            ReminderRule(
                rule_id="performance_nested_loop",
                name="嵌套循环优化",
                description="检测嵌套循环的性能问题",
                reminder_type=ReminderType.PERFORMANCE,
                priority=ReminderPriority.MEDIUM,
                trigger_condition=TriggerCondition.PATTERN_MATCH,
                pattern=r'for.*for.*for',
                message_template="🔄 检测到深层嵌套循环，建议优化算法复杂度",
                action_suggestions=[
                    "考虑使用更高效的算法",
                    "减少循环嵌套层次",
                    "使用数据结构优化查找",
                    "考虑并行处理"
                ]
            ),
            
            # 最佳实践提醒
            ReminderRule(
                rule_id="best_practice_error_handling",
                name="错误处理最佳实践",
                description="提醒添加适当的错误处理",
                reminder_type=ReminderType.BEST_PRACTICE,
                priority=ReminderPriority.MEDIUM,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["异常", "错误", "失败", "处理"],
                message_template="🛠️ 建议添加适当的错误处理和日志记录",
                action_suggestions=[
                    "使用try-catch处理异常",
                    "记录详细的错误日志",
                    "提供用户友好的错误信息",
                    "实现错误恢复机制"
                ]
            ),
            
            ReminderRule(
                rule_id="best_practice_logging",
                name="日志记录最佳实践",
                description="提醒添加合适的日志记录",
                reminder_type=ReminderType.BEST_PRACTICE,
                priority=ReminderPriority.LOW,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["功能", "方法", "函数", "实现"],
                message_template="📝 建议添加适当的日志记录以便调试和监控",
                action_suggestions=[
                    "记录方法入口和出口",
                    "记录关键业务操作",
                    "使用结构化日志",
                    "设置合适的日志级别"
                ],
                frequency_limit=3600  # 1小时内只提醒一次
            ),
            
            # 工作流指导
            ReminderRule(
                rule_id="workflow_testing",
                name="测试提醒",
                description="提醒编写测试用例",
                reminder_type=ReminderType.WORKFLOW_GUIDANCE,
                priority=ReminderPriority.MEDIUM,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["完成", "实现", "功能"],
                message_template="🧪 功能实现完成后，建议编写相应的测试用例",
                action_suggestions=[
                    "编写单元测试",
                    "添加集成测试",
                    "考虑边界条件测试",
                    "验证错误处理逻辑"
                ],
                max_daily_triggers=3
            ),
            
            ReminderRule(
                rule_id="workflow_documentation",
                name="文档提醒",
                description="提醒编写文档",
                reminder_type=ReminderType.WORKFLOW_GUIDANCE,
                priority=ReminderPriority.LOW,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["完成", "新功能", "API"],
                message_template="📚 建议为新功能或API编写相应的文档",
                action_suggestions=[
                    "编写API文档",
                    "更新用户手册",
                    "添加代码注释",
                    "创建使用示例"
                ],
                frequency_limit=7200  # 2小时内只提醒一次
            ),
            
            # 质量保证
            ReminderRule(
                rule_id="quality_code_review",
                name="代码审查提醒",
                description="提醒进行代码审查",
                reminder_type=ReminderType.QUALITY_ASSURANCE,
                priority=ReminderPriority.MEDIUM,
                trigger_condition=TriggerCondition.CONTEXT_MATCH,
                context_keywords=["提交", "完成", "代码"],
                message_template="👥 建议安排代码审查以确保代码质量",
                action_suggestions=[
                    "请同事进行代码审查",
                    "检查代码规范",
                    "验证逻辑正确性",
                    "评估代码可维护性"
                ],
                max_daily_triggers=2
            )
        ]
        
        for rule in default_rules:
            self.reminder_rules[rule.rule_id] = rule
        
        logger.info(f"已加载 {len(default_rules)} 个默认提醒规则")
    
    async def analyze_context(self, context: ContextInfo) -> List[ReminderEvent]:
        """分析上下文并生成提醒"""
        try:
            triggered_reminders = []
            
            for rule in self.reminder_rules.values():
                if not rule.is_active:
                    continue
                
                # 检查是否应该触发提醒
                should_trigger = await self._should_trigger_reminder(rule, context)
                
                if should_trigger:
                    # 检查频率限制
                    if not self._check_frequency_limit(rule):
                        continue
                    
                    # 生成提醒事件
                    reminder_event = await self._create_reminder_event(rule, context)
                    triggered_reminders.append(reminder_event)
                    
                    # 记录触发历史
                    self._record_trigger(rule.rule_id)
            
            # 记录事件历史
            self.event_history.extend(triggered_reminders)
            
            # 清理旧的历史记录
            await self._cleanup_old_events()
            
            return triggered_reminders
            
        except Exception as e:
            logger.error(f"分析上下文失败: {e}")
            return []
    
    async def _should_trigger_reminder(
        self,
        rule: ReminderRule,
        context: ContextInfo
    ) -> bool:
        """判断是否应该触发提醒"""
        try:
            if rule.trigger_condition == TriggerCondition.ALWAYS:
                return True
            
            elif rule.trigger_condition == TriggerCondition.CONTEXT_MATCH:
                return self._match_context_keywords(rule, context)
            
            elif rule.trigger_condition == TriggerCondition.PATTERN_MATCH:
                return self._match_pattern(rule, context)
            
            elif rule.trigger_condition == TriggerCondition.TIME_BASED:
                return self._check_time_condition(rule, context)
            
            elif rule.trigger_condition == TriggerCondition.FREQUENCY_BASED:
                return self._check_frequency_condition(rule, context)
            
            elif rule.trigger_condition == TriggerCondition.ERROR_PRONE:
                return self._check_error_prone_condition(rule, context)
            
            return False
            
        except Exception as e:
            logger.error(f"检查触发条件失败: {e}")
            return False
    
    def _match_context_keywords(self, rule: ReminderRule, context: ContextInfo) -> bool:
        """匹配上下文关键词"""
        if not rule.context_keywords:
            return False
        
        # 构建搜索文本
        search_text = []
        if context.current_task:
            search_text.append(context.current_task.lower())
        if context.user_input:
            search_text.append(context.user_input.lower())
        if context.workflow_stage:
            search_text.append(context.workflow_stage.lower())
        
        full_text = " ".join(search_text)
        
        # 检查关键词匹配
        for keyword in rule.context_keywords:
            if keyword.lower() in full_text:
                return True
        
        return False
    
    def _match_pattern(self, rule: ReminderRule, context: ContextInfo) -> bool:
        """匹配模式"""
        if not rule.pattern:
            return False
        
        # 在用户输入中搜索模式
        if context.user_input:
            try:
                return bool(re.search(rule.pattern, context.user_input, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"正则表达式错误 {rule.pattern}: {e}")
        
        return False
    
    def _check_time_condition(self, rule: ReminderRule, context: ContextInfo) -> bool:
        """检查时间条件"""
        # 可以根据具体需求实现时间相关的触发条件
        # 例如：工作时间提醒、特定时间段提醒等
        return True
    
    def _check_frequency_condition(self, rule: ReminderRule, context: ContextInfo) -> bool:
        """检查频率条件"""
        # 可以根据具体需求实现频率相关的触发条件
        return True
    
    def _check_error_prone_condition(self, rule: ReminderRule, context: ContextInfo) -> bool:
        """检查易出错条件"""
        # 根据历史错误信息判断是否容易出错
        if context.recent_errors:
            return len(context.recent_errors) > 0
        return False
    
    def _check_frequency_limit(self, rule: ReminderRule) -> bool:
        """检查频率限制"""
        current_time = datetime.now()
        rule_id = rule.rule_id
        
        # 检查频率限制
        if rule.frequency_limit:
            if rule_id in self.trigger_frequency:
                last_trigger_times = self.trigger_frequency[rule_id]
                recent_triggers = [
                    t for t in last_trigger_times
                    if (current_time - t).total_seconds() < rule.frequency_limit
                ]
                if recent_triggers:
                    return False
        
        # 检查每日触发次数限制
        if rule.max_daily_triggers:
            if rule_id in self.trigger_frequency:
                today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                today_triggers = [
                    t for t in self.trigger_frequency[rule_id]
                    if t >= today_start
                ]
                if len(today_triggers) >= rule.max_daily_triggers:
                    return False
        
        return True
    
    def _record_trigger(self, rule_id: str):
        """记录触发时间"""
        if rule_id not in self.trigger_frequency:
            self.trigger_frequency[rule_id] = []
        
        self.trigger_frequency[rule_id].append(datetime.now())
        
        # 清理旧的触发记录（保留最近7天）
        cutoff_time = datetime.now() - timedelta(days=7)
        self.trigger_frequency[rule_id] = [
            t for t in self.trigger_frequency[rule_id]
            if t > cutoff_time
        ]
    
    async def _create_reminder_event(
        self,
        rule: ReminderRule,
        context: ContextInfo
    ) -> ReminderEvent:
        """创建提醒事件"""
        event_id = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 渲染消息模板
        message = self._render_message_template(rule, context)
        
        return ReminderEvent(
            event_id=event_id,
            rule_id=rule.rule_id,
            message=message,
            priority=rule.priority,
            reminder_type=rule.reminder_type,
            context=asdict(context),
            suggestions=rule.action_suggestions.copy(),
            triggered_at=datetime.now()
        )
    
    def _render_message_template(self, rule: ReminderRule, context: ContextInfo) -> str:
        """渲染消息模板"""
        message = rule.message_template
        
        # 简单的模板变量替换
        replacements = {
            "{current_role}": context.current_role or "未知角色",
            "{current_task}": context.current_task or "当前任务",
            "{workflow_stage}": context.workflow_stage or "当前阶段"
        }
        
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        
        return message
    
    async def _cleanup_old_events(self):
        """清理旧的事件记录"""
        # 保留最近1000个事件
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]
        
        # 清理超过30天的事件
        cutoff_time = datetime.now() - timedelta(days=30)
        self.event_history = [
            event for event in self.event_history
            if event.triggered_at > cutoff_time
        ]
    
    async def acknowledge_reminder(self, event_id: str) -> bool:
        """确认提醒"""
        try:
            for event in self.event_history:
                if event.event_id == event_id:
                    event.acknowledged = True
                    event.acknowledged_at = datetime.now()
                    logger.info(f"提醒已确认: {event_id}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"确认提醒失败: {e}")
            return False
    
    async def add_rule(self, rule: ReminderRule) -> bool:
        """添加提醒规则"""
        try:
            self.reminder_rules[rule.rule_id] = rule
            logger.info(f"提醒规则已添加: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加提醒规则失败: {e}")
            return False
    
    async def update_rule(self, rule_id: str, **kwargs) -> bool:
        """更新提醒规则"""
        try:
            if rule_id not in self.reminder_rules:
                return False
            
            rule = self.reminder_rules[rule_id]
            
            # 更新属性
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            logger.info(f"提醒规则已更新: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新提醒规则失败: {e}")
            return False
    
    async def remove_rule(self, rule_id: str) -> bool:
        """移除提醒规则"""
        try:
            if rule_id in self.reminder_rules:
                del self.reminder_rules[rule_id]
                logger.info(f"提醒规则已移除: {rule_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"移除提醒规则失败: {e}")
            return False
    
    async def get_active_reminders(
        self,
        priority: Optional[ReminderPriority] = None,
        reminder_type: Optional[ReminderType] = None
    ) -> List[ReminderEvent]:
        """获取活跃的提醒"""
        reminders = [
            event for event in self.event_history
            if not event.acknowledged
        ]
        
        if priority:
            reminders = [r for r in reminders if r.priority == priority]
        
        if reminder_type:
            reminders = [r for r in reminders if r.reminder_type == reminder_type]
        
        return reminders
    
    async def get_reminder_statistics(self) -> Dict[str, Any]:
        """获取提醒统计信息"""
        total_rules = len(self.reminder_rules)
        active_rules = len([r for r in self.reminder_rules.values() if r.is_active])
        total_events = len(self.event_history)
        acknowledged_events = len([e for e in self.event_history if e.acknowledged])
        
        # 按类型统计
        type_stats = {}
        for event in self.event_history:
            event_type = event.reminder_type.value
            type_stats[event_type] = type_stats.get(event_type, 0) + 1
        
        # 按优先级统计
        priority_stats = {}
        for event in self.event_history:
            priority = event.priority.value
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
        
        # 最近24小时的活动
        recent_time = datetime.now() - timedelta(hours=24)
        recent_events = len([
            e for e in self.event_history
            if e.triggered_at > recent_time
        ])
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "total_events": total_events,
            "acknowledged_events": acknowledged_events,
            "unacknowledged_events": total_events - acknowledged_events,
            "type_distribution": type_stats,
            "priority_distribution": priority_stats,
            "recent_24h_events": recent_events,
            "acknowledgment_rate": (acknowledged_events / total_events * 100) if total_events > 0 else 0
        }
