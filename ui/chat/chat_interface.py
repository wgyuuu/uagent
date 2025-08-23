"""
Chat Interface

聊天界面 - 处理用户与系统的对话交互
"""

from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
import structlog
import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import uuid4
import json

logger = structlog.get_logger(__name__)


class MessageType(Enum):
    """消息类型"""
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    ERROR = "error"
    INFO = "info"
    WORKFLOW_STATUS = "workflow_status"


class MessageStatus(Enum):
    """消息状态"""
    SENT = "sent"
    DELIVERED = "delivered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChatMessage:
    """聊天消息"""
    message_id: str
    session_id: str
    message_type: MessageType
    content: str
    sender: str
    timestamp: datetime
    status: MessageStatus = MessageStatus.SENT
    metadata: Dict[str, Any] = None
    attachments: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.attachments is None:
            self.attachments = []


@dataclass
class ChatSession:
    """聊天会话"""
    session_id: str
    user_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    is_active: bool = True
    messages: List[ChatMessage] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.context is None:
            self.context = {}


class ChatInterface:
    """
    聊天界面
    
    管理用户与AI系统的对话交互
    """
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.status_callbacks: List[Callable] = []
        self.websocket_connections: Dict[str, Any] = {}
        
        # 注册默认消息处理器
        self._register_default_handlers()
        
        logger.info("聊天界面初始化完成")
    
    def _register_default_handlers(self):
        """注册默认消息处理器"""
        self.message_handlers[MessageType.USER] = self._handle_user_message
        self.message_handlers[MessageType.SYSTEM] = self._handle_system_message
        self.message_handlers[MessageType.AGENT] = self._handle_agent_message
        self.message_handlers[MessageType.ERROR] = self._handle_error_message
        self.message_handlers[MessageType.INFO] = self._handle_info_message
        self.message_handlers[MessageType.WORKFLOW_STATUS] = self._handle_workflow_status
    
    async def create_session(
        self,
        user_id: str,
        title: str = "新对话"
    ) -> ChatSession:
        """创建聊天会话"""
        try:
            session_id = str(uuid4())
            
            session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title=title,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            self.sessions[session_id] = session
            
            # 发送欢迎消息
            welcome_message = await self._create_system_message(
                session_id,
                "欢迎使用UAgent智能助手！我可以帮助您完成各种任务。请告诉我您需要什么帮助？"
            )
            
            session.messages.append(welcome_message)
            
            logger.info(f"聊天会话已创建: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"创建聊天会话失败: {e}")
            raise
    
    async def send_message(
        self,
        session_id: str,
        content: str,
        message_type: MessageType = MessageType.USER,
        sender: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessage:
        """发送消息"""
        try:
            if session_id not in self.sessions:
                raise ValueError(f"会话不存在: {session_id}")
            
            session = self.sessions[session_id]
            
            message = ChatMessage(
                message_id=str(uuid4()),
                session_id=session_id,
                message_type=message_type,
                content=content,
                sender=sender,
                timestamp=datetime.now(),
                metadata=metadata or {},
                attachments=attachments or []
            )
            
            session.messages.append(message)
            session.last_activity = datetime.now()
            
            # 处理消息
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message, session)
            
            # 通知WebSocket连接
            await self._notify_websocket_connections(session_id, message)
            
            logger.info(f"消息已发送: {message.message_id}")
            return message
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise
    
    async def _create_system_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """创建系统消息"""
        return ChatMessage(
            message_id=str(uuid4()),
            session_id=session_id,
            message_type=MessageType.SYSTEM,
            content=content,
            sender="system",
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
    
    async def _handle_user_message(self, message: ChatMessage, session: ChatSession):
        """处理用户消息"""
        try:
            # 更新消息状态
            message.status = MessageStatus.PROCESSING
            
            # 这里应该调用主Agent来处理用户请求
            # 暂时返回一个模拟响应
            response_content = f"我收到了您的消息：{message.content}。正在为您处理..."
            
            response = await self._create_system_message(
                session.session_id,
                response_content,
                {"response_to": message.message_id}
            )
            
            session.messages.append(response)
            message.status = MessageStatus.COMPLETED
            
            logger.info(f"用户消息已处理: {message.message_id}")
            
        except Exception as e:
            message.status = MessageStatus.FAILED
            logger.error(f"处理用户消息失败: {e}")
    
    async def _handle_system_message(self, message: ChatMessage, session: ChatSession):
        """处理系统消息"""
        logger.info(f"系统消息: {message.content}")
    
    async def _handle_agent_message(self, message: ChatMessage, session: ChatSession):
        """处理Agent消息"""
        logger.info(f"Agent消息: {message.content}")
    
    async def _handle_error_message(self, message: ChatMessage, session: ChatSession):
        """处理错误消息"""
        logger.error(f"错误消息: {message.content}")
    
    async def _handle_info_message(self, message: ChatMessage, session: ChatSession):
        """处理信息消息"""
        logger.info(f"信息消息: {message.content}")
    
    async def _handle_workflow_status(self, message: ChatMessage, session: ChatSession):
        """处理工作流状态消息"""
        logger.info(f"工作流状态: {message.content}")
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """获取用户的所有会话"""
        return [
            session for session in self.sessions.values()
            if session.user_id == user_id
        ]
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """获取会话消息"""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        messages = session.messages[offset:offset + limit]
        return messages
    
    async def update_message_status(
        self,
        message_id: str,
        status: MessageStatus
    ) -> bool:
        """更新消息状态"""
        try:
            for session in self.sessions.values():
                for message in session.messages:
                    if message.message_id == message_id:
                        message.status = status
                        await self._notify_websocket_connections(
                            session.session_id,
                            message
                        )
                        return True
            return False
            
        except Exception as e:
            logger.error(f"更新消息状态失败: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"会话已删除: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False
    
    async def clear_session_messages(self, session_id: str) -> bool:
        """清空会话消息"""
        try:
            if session_id in self.sessions:
                self.sessions[session_id].messages.clear()
                logger.info(f"会话消息已清空: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"清空会话消息失败: {e}")
            return False
    
    async def search_messages(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[ChatMessage]:
        """搜索消息"""
        try:
            results = []
            
            sessions_to_search = []
            if session_id:
                if session_id in self.sessions:
                    sessions_to_search = [self.sessions[session_id]]
            elif user_id:
                sessions_to_search = await self.get_user_sessions(user_id)
            else:
                sessions_to_search = list(self.sessions.values())
            
            for session in sessions_to_search:
                for message in session.messages:
                    if query.lower() in message.content.lower():
                        results.append(message)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            return []
    
    def register_message_handler(
        self,
        message_type: MessageType,
        handler: Callable
    ):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"消息处理器已注册: {message_type}")
    
    def register_status_callback(self, callback: Callable):
        """注册状态回调"""
        self.status_callbacks.append(callback)
        logger.info("状态回调已注册")
    
    async def register_websocket_connection(
        self,
        session_id: str,
        websocket: Any
    ):
        """注册WebSocket连接"""
        self.websocket_connections[session_id] = websocket
        logger.info(f"WebSocket连接已注册: {session_id}")
    
    async def unregister_websocket_connection(self, session_id: str):
        """注销WebSocket连接"""
        if session_id in self.websocket_connections:
            del self.websocket_connections[session_id]
            logger.info(f"WebSocket连接已注销: {session_id}")
    
    async def _notify_websocket_connections(
        self,
        session_id: str,
        message: ChatMessage
    ):
        """通知WebSocket连接"""
        try:
            if session_id in self.websocket_connections:
                websocket = self.websocket_connections[session_id]
                message_data = {
                    "type": "message",
                    "data": asdict(message)
                }
                # 这里应该发送WebSocket消息
                # await websocket.send_text(json.dumps(message_data))
                logger.debug(f"WebSocket通知已发送: {session_id}")
                
        except Exception as e:
            logger.error(f"WebSocket通知失败: {e}")
    
    async def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """导出会话数据"""
        try:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            return {
                "session": asdict(session),
                "export_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"导出会话失败: {e}")
            return None
    
    async def import_session(self, session_data: Dict[str, Any]) -> bool:
        """导入会话数据"""
        try:
            session_dict = session_data["session"]
            
            # 重新创建ChatMessage对象
            messages = []
            for msg_dict in session_dict.get("messages", []):
                message = ChatMessage(**msg_dict)
                messages.append(message)
            
            session_dict["messages"] = messages
            session = ChatSession(**session_dict)
            
            self.sessions[session.session_id] = session
            
            logger.info(f"会话已导入: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"导入会话失败: {e}")
            return False
    
    async def get_chat_statistics(self) -> Dict[str, Any]:
        """获取聊天统计信息"""
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() if s.is_active])
        total_messages = sum(len(s.messages) for s in self.sessions.values())
        
        # 按消息类型统计
        message_type_stats = {}
        for session in self.sessions.values():
            for message in session.messages:
                msg_type = message.message_type.value
                message_type_stats[msg_type] = message_type_stats.get(msg_type, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "websocket_connections": len(self.websocket_connections),
            "message_type_distribution": message_type_stats
        }
