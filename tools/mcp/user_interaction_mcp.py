"""
User Interaction MCP Service

用户交互MCP服务 - 将用户对话作为核心MCP服务
"""

from typing import Dict, List, Any, Optional, Callable, Union
import structlog
import asyncio
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid

from models.base import MCPToolDefinition, ToolExecutionResult, UserSession

logger = structlog.get_logger(__name__)


@dataclass
class InteractionRequest:
    """交互请求"""
    request_id: str
    session_id: str
    user_id: Optional[str]
    message: str
    message_type: str  # "question", "confirmation", "choice", "feedback"
    context: Dict[str, Any]
    timestamp: datetime
    priority: str = "normal"  # "low", "normal", "high", "urgent"


@dataclass
class InteractionResponse:
    """交互响应"""
    response_id: str
    request_id: str
    session_id: str
    content: str
    response_type: str  # "answer", "question", "choice", "action"
    options: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class UserInteractionMCPService:
    """
    用户交互MCP服务
    
    将用户对话作为核心MCP服务，支持实时问题、确认、选择和会话管理
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, UserSession] = {}
        self.session_history: List[Dict[str, Any]] = []
        self.interaction_handlers: Dict[str, Callable] = {}
        self.pending_interactions: Dict[str, InteractionRequest] = {}
        self.interaction_responses: Dict[str, InteractionResponse] = {}
        
        # 注册默认交互处理器
        self._register_default_handlers()
        
        # 启动会话清理任务
        self.cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("用户交互MCP服务初始化完成")
    
    def _register_default_handlers(self):
        """注册默认交互处理器"""
        # 问题处理
        self.register_interaction_handler(
            "question",
            self._handle_question_interaction
        )
        
        # 确认处理
        self.register_interaction_handler(
            "confirmation",
            self._handle_confirmation_interaction
        )
        
        # 选择处理
        self.register_interaction_handler(
            "choice",
            self._handle_choice_interaction
        )
        
        # 反馈处理
        self.register_interaction_handler(
            "feedback",
            self._handle_feedback_interaction
        )
    
    def register_interaction_handler(
        self,
        interaction_type: str,
        handler: Callable
    ):
        """注册交互处理器"""
        try:
            if not callable(handler):
                raise ValueError("handler必须是可调用对象")
            
            self.interaction_handlers[interaction_type] = handler
            logger.info(f"交互处理器已注册: {interaction_type}")
            
        except Exception as e:
            logger.error(f"注册交互处理器失败: {e}")
            raise
    
    def unregister_interaction_handler(self, interaction_type: str):
        """注销交互处理器"""
        try:
            if interaction_type in self.interaction_handlers:
                del self.interaction_handlers[interaction_type]
                logger.info(f"交互处理器已注销: {interaction_type}")
            
        except Exception as e:
            logger.error(f"注销交互处理器失败: {e}")
            raise
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        session_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            session_type: 会话类型
            metadata: 元数据
            
        Returns:
            用户会话对象
        """
        try:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                session_type=session_type,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                status="active",
                metadata=metadata or {}
            )
            
            # 存储会话
            self.active_sessions[session_id] = session
            
            # 记录到历史
            self.session_history.append({
                "session_id": session_id,
                "user_id": user_id,
                "session_type": session_type,
                "created_at": session.created_at.isoformat(),
                "status": "created"
            })
            
            logger.info(f"用户会话已创建: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"创建用户会话失败: {e}")
            raise
    
    async def close_session(self, session_id: str) -> bool:
        """关闭用户会话"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"会话 {session_id} 不存在")
                return False
            
            session = self.active_sessions[session_id]
            session.status = "closed"
            session.last_activity = datetime.now()
            
            # 更新历史记录
            for record in self.session_history:
                if record["session_id"] == session_id:
                    record["status"] = "closed"
                    record["closed_at"] = datetime.now().isoformat()
                    break
            
            # 从活跃会话移除
            del self.active_sessions[session_id]
            
            logger.info(f"用户会话已关闭: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"关闭用户会话失败: {e}")
            raise
    
    async def process_interaction(
        self,
        session_id: str,
        message: str,
        message_type: str = "question",
        context: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        user_id: Optional[str] = None
    ) -> InteractionResponse:
        """
        处理用户交互
        
        Args:
            session_id: 会话ID
            message: 用户消息
            message_type: 消息类型
            context: 上下文信息
            priority: 优先级
            user_id: 用户ID
            
        Returns:
            交互响应
        """
        try:
            # 验证会话
            if session_id not in self.active_sessions:
                raise ValueError(f"会话 {session_id} 不存在或已关闭")
            
            session = self.active_sessions[session_id]
            session.last_activity = datetime.now()
            
            # 创建交互请求
            request = InteractionRequest(
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                user_id=user_id or session.user_id,
                message=message,
                message_type=message_type,
                context=context or {},
                timestamp=datetime.now(),
                priority=priority
            )
            
            # 存储请求
            self.pending_interactions[request.request_id] = request
            
            logger.info(f"处理交互请求: {request.request_id}, 类型: {message_type}")
            
            # 调用相应的处理器
            handler = self.interaction_handlers.get(message_type)
            if handler:
                response = await handler(request, session)
            else:
                response = await self._handle_default_interaction(request, session)
            
            # 存储响应
            self.interaction_responses[response.response_id] = response
            
            # 清理已处理的请求
            if request.request_id in self.pending_interactions:
                del self.pending_interactions[request.request_id]
            
            logger.info(f"交互处理完成: {request.request_id}")
            return response
            
        except Exception as e:
            logger.error(f"处理用户交互失败: {e}")
            
            # 创建错误响应
            error_response = InteractionResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id="error",
                session_id=session_id,
                content=f"处理交互时出错: {str(e)}",
                response_type="error",
                metadata={"error": str(e), "error_type": type(e).__name__},
                timestamp=datetime.now()
            )
            
            return error_response
    
    async def _handle_question_interaction(
        self,
        request: InteractionRequest,
        session: UserSession
    ) -> InteractionResponse:
        """处理问题交互"""
        try:
            # 这里可以实现更智能的问题处理逻辑
            # 目前返回一个基本的响应
            
            response_content = f"收到您的问题: {request.message}\n\n我正在分析您的问题，请稍等..."
            
            response = InteractionResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                session_id=request.session_id,
                content=response_content,
                response_type="answer",
                metadata={
                    "question_type": "general",
                    "processing_status": "analyzing",
                    "estimated_time": "30秒"
                },
                timestamp=datetime.now()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理问题交互失败: {e}")
            raise
    
    async def _handle_confirmation_interaction(
        self,
        request: InteractionRequest,
        session: UserSession
    ) -> InteractionResponse:
        """处理确认交互"""
        try:
            # 解析确认请求
            message_lower = request.message.lower()
            
            if any(word in message_lower for word in ["是", "yes", "确认", "confirm", "同意", "agree"]):
                confirmation_result = "confirmed"
                response_content = "已确认您的请求。"
            elif any(word in message_lower for word in ["否", "no", "取消", "cancel", "拒绝", "reject"]):
                confirmation_result = "rejected"
                response_content = "已取消您的请求。"
            else:
                confirmation_result = "unclear"
                response_content = "您的确认信息不明确，请明确回答是或否。"
            
            response = InteractionResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                session_id=request.session_id,
                content=response_content,
                response_type="confirmation",
                metadata={
                    "confirmation_result": confirmation_result,
                    "original_message": request.message
                },
                timestamp=datetime.now()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理确认交互失败: {e}")
            raise
    
    async def _handle_choice_interaction(
        self,
        request: InteractionRequest,
        session: UserSession
    ) -> InteractionResponse:
        """处理选择交互"""
        try:
            # 从上下文中提取选项
            options = request.context.get("options", [])
            
            if not options:
                response_content = "没有可选择的选项。"
                response_type = "error"
            else:
                # 分析用户选择
                user_choice = self._parse_user_choice(request.message, options)
                
                if user_choice:
                    response_content = f"您选择了: {user_choice['label']}"
                    response_type = "choice"
                else:
                    response_content = "请从以下选项中选择:\n" + "\n".join(
                        f"{i+1}. {opt['label']}" for i, opt in enumerate(options)
                    )
                    response_type = "question"
            
            response = InteractionResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                session_id=request.session_id,
                content=response_content,
                response_type=response_type,
                options=options if response_type == "question" else None,
                metadata={
                    "user_choice": user_choice if 'user_choice' in locals() else None,
                    "available_options": len(options)
                },
                timestamp=datetime.now()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理选择交互失败: {e}")
            raise
    
    async def _handle_feedback_interaction(
        self,
        request: InteractionRequest,
        session: UserSession
    ) -> InteractionResponse:
        """处理反馈交互"""
        try:
            # 分析反馈内容
            feedback_analysis = self._analyze_feedback(request.message)
            
            response_content = f"感谢您的反馈！\n\n反馈类型: {feedback_analysis['type']}\n情感倾向: {feedback_analysis['sentiment']}"
            
            if feedback_analysis['suggestions']:
                response_content += f"\n\n改进建议: {', '.join(feedback_analysis['suggestions'])}"
            
            response = InteractionResponse(
                response_id=f"resp_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                session_id=request.session_id,
                content=response_content,
                response_type="feedback",
                metadata={
                    "feedback_analysis": feedback_analysis,
                    "feedback_length": len(request.message)
                },
                timestamp=datetime.now()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理反馈交互失败: {e}")
            raise
    
    async def _handle_default_interaction(
        self,
        request: InteractionRequest,
        session: UserSession
    ) -> InteractionResponse:
        """处理默认交互"""
        response = InteractionResponse(
            response_id=f"resp_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            session_id=request.session_id,
            content=f"收到您的消息: {request.message}\n\n我正在处理您的请求...",
            response_type="acknowledgment",
            metadata={
                "message_type": request.message_type,
                "priority": request.priority
            },
            timestamp=datetime.now()
        )
        
        return response
    
    def _parse_user_choice(self, message: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """解析用户选择"""
        message_lower = message.lower()
        
        # 尝试数字选择
        for i, option in enumerate(options):
            if str(i + 1) in message or option['label'].lower() in message_lower:
                return option
        
        # 尝试关键词匹配
        for option in options:
            if any(keyword.lower() in message_lower for keyword in option.get('keywords', [])):
                return option
        
        return None
    
    def _analyze_feedback(self, message: str) -> Dict[str, Any]:
        """分析反馈内容"""
        message_lower = message.lower()
        
        # 简单的情感分析
        positive_words = ["好", "棒", "优秀", "满意", "喜欢", "good", "great", "excellent", "satisfied"]
        negative_words = ["差", "糟糕", "不满意", "不喜欢", "bad", "terrible", "unsatisfied", "dislike"]
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # 反馈类型分析
        feedback_types = {
            "bug_report": ["错误", "bug", "问题", "故障", "error", "issue"],
            "feature_request": ["功能", "建议", "需求", "feature", "request", "suggestion"],
            "improvement": ["改进", "优化", "提升", "improvement", "optimization"],
            "general": ["反馈", "意见", "feedback", "comment"]
        }
        
        detected_type = "general"
        for ftype, keywords in feedback_types.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_type = ftype
                break
        
        # 生成改进建议
        suggestions = []
        if sentiment == "negative":
            suggestions.append("我们会认真分析您的问题并尽快改进")
        elif sentiment == "positive":
            suggestions.append("我们会继续保持并进一步提升服务质量")
        
        return {
            "type": detected_type,
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count,
            "suggestions": suggestions
        }
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # 统计交互数量
        interaction_count = len([
            req for req in self.pending_interactions.values()
            if req.session_id == session_id
        ])
        
        response_count = len([
            resp for resp in self.interaction_responses.values()
            if resp.session_id == session_id
        ])
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "status": session.status,
            "interaction_count": interaction_count,
            "response_count": response_count,
            "metadata": session.metadata
        }
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话信息"""
        return [
            await self.get_session_info(session_id)
            for session_id in self.active_sessions.keys()
        ]
    
    async def get_session_interactions(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取会话交互历史"""
        interactions = []
        
        # 获取请求
        for request in self.pending_interactions.values():
            if request.session_id == session_id:
                interactions.append({
                    "type": "request",
                    "timestamp": request.timestamp.isoformat(),
                    "message": request.message,
                    "message_type": request.message_type,
                    "priority": request.priority
                })
        
        # 获取响应
        for response in self.interaction_responses.values():
            if response.session_id == session_id:
                interactions.append({
                    "type": "response",
                    "timestamp": response.timestamp.isoformat() if response.timestamp else None,
                    "content": response.content,
                    "response_type": response.response_type
                })
        
        # 按时间排序
        interactions.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        
        return interactions[:limit]
    
    async def search_interactions(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索交互历史"""
        results = []
        
        # 搜索请求
        for request in self.pending_interactions.values():
            if session_id and request.session_id != session_id:
                continue
            
            if query.lower() in request.message.lower():
                results.append({
                    "type": "request",
                    "session_id": request.session_id,
                    "timestamp": request.timestamp.isoformat(),
                    "message": request.message,
                    "message_type": request.message_type
                })
        
        # 搜索响应
        for response in self.interaction_responses.values():
            if session_id and response.session_id != session_id:
                continue
            
            if query.lower() in response.content.lower():
                results.append({
                    "type": "response",
                    "session_id": response.session_id,
                    "timestamp": response.timestamp.isoformat() if response.timestamp else None,
                    "content": response.content,
                    "response_type": response.response_type
                })
        
        # 按时间排序并限制结果
        results.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return results[:limit]
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await self._cleanup_expired_sessions()
                    await asyncio.sleep(300)  # 每5分钟清理一次
                except Exception as e:
                    logger.error(f"清理任务出错: {e}")
                    await asyncio.sleep(300)
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("会话清理任务已启动")
    
    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                # 检查会话是否超过24小时未活动
                if current_time - session.last_activity > timedelta(hours=24):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                await self.close_session(session_id)
            
            if expired_sessions:
                logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
                
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        total_sessions = len(self.active_sessions)
        total_history = len(self.session_history)
        total_pending = len(self.pending_interactions)
        total_responses = len(self.interaction_responses)
        
        # 按类型统计会话
        session_types = {}
        for session in self.active_sessions.values():
            session_type = session.session_type
            session_types[session_type] = session_types.get(session_type, 0) + 1
        
        # 按类型统计交互
        interaction_types = {}
        for request in self.pending_interactions.values():
            msg_type = request.message_type
            interaction_types[msg_type] = interaction_types.get(msg_type, 0) + 1
        
        return {
            "active_sessions": total_sessions,
            "total_history": total_history,
            "pending_interactions": total_pending,
            "total_responses": total_responses,
            "session_type_distribution": session_types,
            "interaction_type_distribution": interaction_types,
            "handlers_registered": len(self.interaction_handlers)
        }
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 停止清理任务
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭所有会话
            for session_id in list(self.active_sessions.keys()):
                await self.close_session(session_id)
            
            logger.info("用户交互MCP服务已关闭")
            
        except Exception as e:
            logger.error(f"关闭服务失败: {e}")
            raise
