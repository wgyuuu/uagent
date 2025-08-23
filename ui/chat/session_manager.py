"""
Chat Session Manager

聊天会话管理器 - 管理用户会话的生命周期
"""

from typing import Dict, List, Any, Optional
import structlog
import asyncio
from datetime import datetime, timedelta

from .chat_interface import ChatSession, ChatMessage

logger = structlog.get_logger(__name__)


class ChatSessionManager:
    """
    聊天会话管理器
    
    管理用户会话的创建、维护和清理
    """
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        
        logger.info("聊天会话管理器初始化完成")
    
    async def create_session(self, user_id: str, title: str = "新对话") -> ChatSession:
        """创建会话"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.sessions[session_id] = session
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)
        
        logger.info(f"会话已创建: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """获取用户会话"""
        session_ids = self.user_sessions.get(user_id, [])
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]
    
    async def update_session_activity(self, session_id: str):
        """更新会话活动时间"""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.now()
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        user_id = session.user_id
        
        # 从用户会话列表中移除
        if user_id in self.user_sessions:
            self.user_sessions[user_id] = [
                sid for sid in self.user_sessions[user_id] 
                if sid != session_id
            ]
        
        # 删除会话
        del self.sessions[session_id]
        
        logger.info(f"会话已删除: {session_id}")
        return True
    
    async def cleanup_inactive_sessions(self, max_inactive_hours: int = 24):
        """清理不活跃的会话"""
        cutoff_time = datetime.now() - timedelta(hours=max_inactive_hours)
        sessions_to_delete = []
        
        for session_id, session in self.sessions.items():
            if session.last_activity < cutoff_time:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            await self.delete_session(session_id)
        
        if sessions_to_delete:
            logger.info(f"清理了 {len(sessions_to_delete)} 个不活跃的会话")
