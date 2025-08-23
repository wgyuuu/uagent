"""
Message Handler

消息处理器 - 处理聊天消息的业务逻辑
"""

from typing import Dict, List, Any, Optional, Callable
import structlog
import asyncio
from datetime import datetime
from dataclasses import dataclass

from .chat_interface import ChatMessage, ChatSession, MessageType, MessageStatus

logger = structlog.get_logger(__name__)


class MessageHandler:
    """
    消息处理器
    
    处理不同类型消息的业务逻辑
    """
    
    def __init__(self):
        self.handlers: Dict[MessageType, Callable] = {}
        self.middleware: List[Callable] = []
        
        logger.info("消息处理器初始化完成")
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        self.handlers[message_type] = handler
        logger.info(f"消息处理器已注册: {message_type}")
    
    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self.middleware.append(middleware)
        logger.info("中间件已添加")
    
    async def process_message(
        self,
        message: ChatMessage,
        session: ChatSession
    ) -> Optional[ChatMessage]:
        """处理消息"""
        try:
            # 执行中间件
            for middleware in self.middleware:
                await middleware(message, session)
            
            # 查找处理器
            handler = self.handlers.get(message.message_type)
            if handler:
                return await handler(message, session)
            
            logger.warning(f"未找到消息处理器: {message.message_type}")
            return None
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return None
