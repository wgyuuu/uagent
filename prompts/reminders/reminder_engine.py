"""
Reminder Engine

提醒引擎 - 智能提醒规则执行引擎
"""

from typing import Dict, List, Any, Optional, Callable
import structlog
import asyncio
from datetime import datetime
from dataclasses import dataclass

from .system_reminder import SystemReminder, ReminderRule, ReminderEvent, ContextInfo

logger = structlog.get_logger(__name__)


class ReminderEngine:
    """
    提醒引擎
    
    智能提醒系统的核心执行引擎
    """
    
    def __init__(self):
        self.system_reminder = SystemReminder()
        self.context_providers: List[Callable] = []
        self.event_handlers: List[Callable] = []
        self.running = False
        
        logger.info("提醒引擎初始化完成")
    
    def register_context_provider(self, provider: Callable):
        """注册上下文提供者"""
        self.context_providers.append(provider)
        logger.info("上下文提供者已注册")
    
    def register_event_handler(self, handler: Callable):
        """注册事件处理器"""
        self.event_handlers.append(handler)
        logger.info("事件处理器已注册")
    
    async def start(self):
        """启动提醒引擎"""
        self.running = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("提醒引擎已启动")
    
    async def stop(self):
        """停止提醒引擎"""
        self.running = False
        logger.info("提醒引擎已停止")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 收集上下文
                context = await self._collect_context()
                
                # 分析并生成提醒
                reminders = await self.system_reminder.analyze_context(context)
                
                # 处理提醒事件
                for reminder in reminders:
                    await self._handle_reminder_event(reminder)
                
                # 等待下次检查
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(30)
    
    async def _collect_context(self) -> ContextInfo:
        """收集上下文信息"""
        context = ContextInfo()
        
        try:
            for provider in self.context_providers:
                provider_context = await provider()
                if isinstance(provider_context, dict):
                    # 合并上下文
                    for key, value in provider_context.items():
                        if hasattr(context, key):
                            setattr(context, key, value)
        
        except Exception as e:
            logger.error(f"收集上下文失败: {e}")
        
        return context
    
    async def _handle_reminder_event(self, event: ReminderEvent):
        """处理提醒事件"""
        try:
            logger.info(f"提醒事件: {event.message}")
            
            for handler in self.event_handlers:
                await handler(event)
                
        except Exception as e:
            logger.error(f"处理提醒事件失败: {e}")
    
    async def add_rule(self, rule: ReminderRule) -> bool:
        """添加提醒规则"""
        return await self.system_reminder.add_rule(rule)
    
    async def remove_rule(self, rule_id: str) -> bool:
        """移除提醒规则"""
        return await self.system_reminder.remove_rule(rule_id)
    
    async def get_active_reminders(self) -> List[ReminderEvent]:
        """获取活跃的提醒"""
        return await self.system_reminder.get_active_reminders()
    
    async def acknowledge_reminder(self, event_id: str) -> bool:
        """确认提醒"""
        return await self.system_reminder.acknowledge_reminder(event_id)
