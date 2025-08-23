"""
User Question Service

用户问题服务 - 处理用户问题和查询
"""

from typing import Dict, List, Any, Optional, Union
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid

from tools.mcp.user_interaction_mcp import UserInteractionMCPService, InteractionRequest, InteractionResponse

logger = structlog.get_logger(__name__)


@dataclass
class QuestionContext:
    """问题上下文"""
    question_id: str
    session_id: str
    user_id: Optional[str]
    question_text: str
    question_type: str  # "general", "technical", "workflow", "system"
    priority: str
    context_data: Dict[str, Any]
    created_at: datetime
    status: str  # "pending", "processing", "answered", "closed"


@dataclass
class Answer:
    """答案"""
    answer_id: str
    question_id: str
    content: str
    answer_type: str  # "direct", "suggestion", "reference", "action"
    confidence: float  # 0.0 - 1.0
    sources: List[str]
    metadata: Dict[str, Any]
    created_at: datetime


class UserQuestionService:
    """
    用户问题服务
    
    处理用户问题和查询，提供智能问答和上下文管理
    """
    
    def __init__(self, interaction_service: UserInteractionMCPService):
        self.interaction_service = interaction_service
        self.questions: Dict[str, QuestionContext] = {}
        self.answers: Dict[str, Answer] = {}
        self.question_history: List[Dict[str, Any]] = []
        self.question_processors: Dict[str, callable] = {}
        
        # 注册默认问题处理器
        self._register_default_processors()
        
        logger.info("用户问题服务初始化完成")
    
    def _register_default_processors(self):
        """注册默认问题处理器"""
        # 一般问题处理器
        self.register_question_processor(
            "general",
            self._process_general_question
        )
        
        # 技术问题处理器
        self.register_question_processor(
            "technical",
            self._process_technical_question
        )
        
        # 工作流问题处理器
        self.register_question_processor(
            "workflow",
            self._process_workflow_question
        )
        
        # 系统问题处理器
        self.register_question_processor(
            "system",
            self._process_system_question
        )
    
    def register_question_processor(
        self,
        question_type: str,
        processor: callable
    ):
        """注册问题处理器"""
        try:
            if not callable(processor):
                raise ValueError("processor必须是可调用对象")
            
            self.question_processors[question_type] = processor
            logger.info(f"问题处理器已注册: {question_type}")
            
        except Exception as e:
            logger.error(f"注册问题处理器失败: {e}")
            raise
    
    def unregister_question_processor(self, question_type: str):
        """注销问题处理器"""
        try:
            if question_type in self.question_processors:
                del self.question_processors[question_type]
                logger.info(f"问题处理器已注销: {question_type}")
            
        except Exception as e:
            logger.error(f"注销问题处理器失败: {e}")
            raise
    
    async def ask_question(
        self,
        session_id: str,
        question_text: str,
        question_type: str = "general",
        priority: str = "normal",
        context_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> QuestionContext:
        """
        提出问题
        
        Args:
            session_id: 会话ID
            question_text: 问题文本
            question_type: 问题类型
            priority: 优先级
            context_data: 上下文数据
            user_id: 用户ID
            
        Returns:
            问题上下文对象
        """
        try:
            # 验证会话
            session_info = await self.interaction_service.get_session_info(session_id)
            if not session_info:
                raise ValueError(f"会话 {session_id} 不存在")
            
            # 创建问题上下文
            question_id = f"q_{uuid.uuid4().hex[:8]}"
            
            question = QuestionContext(
                question_id=question_id,
                session_id=session_id,
                user_id=user_id or session_info.get("user_id"),
                question_text=question_text,
                question_type=question_type,
                priority=priority,
                context_data=context_data or {},
                created_at=datetime.now(),
                status="pending"
            )
            
            # 存储问题
            self.questions[question_id] = question
            
            # 记录到历史
            self.question_history.append({
                "question_id": question_id,
                "session_id": session_id,
                "question_text": question_text,
                "question_type": question_type,
                "priority": priority,
                "created_at": question.created_at.isoformat(),
                "status": "asked"
            })
            
            logger.info(f"用户问题已创建: {question_id}")
            
            # 自动处理问题
            asyncio.create_task(self._process_question(question_id))
            
            return question
            
        except Exception as e:
            logger.error(f"创建用户问题失败: {e}")
            raise
    
    async def _process_question(self, question_id: str):
        """处理问题"""
        try:
            if question_id not in self.questions:
                return
            
            question = self.questions[question_id]
            question.status = "processing"
            
            logger.info(f"开始处理问题: {question_id}")
            
            # 调用相应的处理器
            processor = self.question_processors.get(question.question_type)
            if processor:
                answer = await processor(question)
            else:
                answer = await self._process_general_question(question)
            
            # 存储答案
            self.answers[question_id] = answer
            
            # 更新问题状态
            question.status = "answered"
            
            # 更新历史记录
            for record in self.question_history:
                if record["question_id"] == question_id:
                    record["status"] = "answered"
                    record["answered_at"] = datetime.now().isoformat()
                    break
            
            logger.info(f"问题处理完成: {question_id}")
            
        except Exception as e:
            logger.error(f"处理问题失败: {question_id}, 错误: {e}")
            
            if question_id in self.questions:
                self.questions[question_id].status = "error"
    
    async def _process_general_question(self, question: QuestionContext) -> Answer:
        """处理一般问题"""
        try:
            # 分析问题内容
            question_analysis = self._analyze_question(question.question_text)
            
            # 生成答案
            answer_content = self._generate_general_answer(question.question_text, question_analysis)
            
            answer = Answer(
                answer_id=f"a_{uuid.uuid4().hex[:8]}",
                question_id=question.question_id,
                content=answer_content,
                answer_type="direct",
                confidence=0.8,
                sources=["general_knowledge"],
                metadata={
                    "question_analysis": question_analysis,
                    "processing_time": "immediate"
                },
                created_at=datetime.now()
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"处理一般问题失败: {e}")
            raise
    
    async def _process_technical_question(self, question: QuestionContext) -> Answer:
        """处理技术问题"""
        try:
            # 技术问题需要更深入的分析
            technical_analysis = self._analyze_technical_question(question.question_text)
            
            # 生成技术答案
            answer_content = self._generate_technical_answer(question.question_text, technical_analysis)
            
            answer = Answer(
                answer_id=f"a_{uuid.uuid4().hex[:8]}",
                question_id=question.question_id,
                content=answer_content,
                answer_type="reference",
                confidence=0.7,
                sources=["technical_database", "code_analysis"],
                metadata={
                    "technical_analysis": technical_analysis,
                    "complexity_level": technical_analysis.get("complexity", "medium")
                },
                created_at=datetime.now()
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"处理技术问题失败: {e}")
            raise
    
    async def _process_workflow_question(self, question: QuestionContext) -> Answer:
        """处理工作流问题"""
        try:
            # 分析工作流相关问题
            workflow_analysis = self._analyze_workflow_question(question.question_text)
            
            # 生成工作流答案
            answer_content = self._generate_workflow_answer(question.question_text, workflow_analysis)
            
            answer = Answer(
                answer_id=f"a_{uuid.uuid4().hex[:8]}",
                question_id=question.question_id,
                content=answer_content,
                answer_type="action",
                confidence=0.9,
                sources=["workflow_engine", "execution_history"],
                metadata={
                    "workflow_analysis": workflow_analysis,
                    "action_required": workflow_analysis.get("action_required", False)
                },
                created_at=datetime.now()
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"处理工作流问题失败: {e}")
            raise
    
    async def _process_system_question(self, question: QuestionContext) -> Answer:
        """处理系统问题"""
        try:
            # 分析系统相关问题
            system_analysis = self._analyze_system_question(question.question_text)
            
            # 生成系统答案
            answer_content = self._generate_system_answer(question.question_text, system_analysis)
            
            answer = Answer(
                answer_id=f"a_{uuid.uuid4().hex[:8]}",
                question_id=question.question_id,
                content=answer_content,
                answer_type="direct",
                confidence=0.95,
                sources=["system_monitor", "performance_metrics"],
                metadata={
                    "system_analysis": system_analysis,
                    "system_status": system_analysis.get("status", "unknown")
                },
                created_at=datetime.now()
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"处理系统问题失败: {e}")
            raise
    
    def _analyze_question(self, question_text: str) -> Dict[str, Any]:
        """分析问题内容"""
        question_lower = question_text.lower()
        
        analysis = {
            "length": len(question_text),
            "word_count": len(question_text.split()),
            "has_question_mark": "?" in question_text,
            "keywords": [],
            "complexity": "simple"
        }
        
        # 提取关键词
        common_keywords = ["如何", "怎么", "为什么", "什么", "哪里", "when", "how", "why", "what", "where"]
        for keyword in common_keywords:
            if keyword in question_lower:
                analysis["keywords"].append(keyword)
        
        # 判断复杂度
        if len(question_text) > 100 or len(analysis["keywords"]) > 2:
            analysis["complexity"] = "complex"
        elif len(question_text) > 50:
            analysis["complexity"] = "medium"
        
        return analysis
    
    def _analyze_technical_question(self, question_text: str) -> Dict[str, Any]:
        """分析技术问题"""
        question_lower = question_text.lower()
        
        analysis = {
            "technical_domains": [],
            "complexity": "medium",
            "requires_code": False,
            "requires_diagram": False
        }
        
        # 识别技术领域
        tech_domains = {
            "programming": ["代码", "编程", "算法", "函数", "类", "code", "programming", "algorithm"],
            "database": ["数据库", "表", "查询", "database", "table", "query", "sql"],
            "network": ["网络", "协议", "连接", "network", "protocol", "connection"],
            "system": ["系统", "性能", "优化", "system", "performance", "optimization"]
        }
        
        for domain, keywords in tech_domains.items():
            if any(keyword in question_lower for keyword in keywords):
                analysis["technical_domains"].append(domain)
        
        # 判断是否需要代码
        code_indicators = ["代码", "实现", "示例", "code", "implementation", "example"]
        if any(indicator in question_lower for indicator in code_indicators):
            analysis["requires_code"] = True
        
        # 判断复杂度
        if len(analysis["technical_domains"]) > 2 or analysis["requires_code"]:
            analysis["complexity"] = "high"
        
        return analysis
    
    def _analyze_workflow_question(self, question_text: str) -> Dict[str, Any]:
        """分析工作流问题"""
        question_lower = question_text.lower()
        
        analysis = {
            "workflow_stages": [],
            "action_required": False,
            "status_inquiry": False,
            "optimization_request": False
        }
        
        # 识别工作流阶段
        workflow_stages = {
            "planning": ["规划", "设计", "planning", "design"],
            "execution": ["执行", "运行", "execution", "running"],
            "monitoring": ["监控", "跟踪", "monitoring", "tracking"],
            "optimization": ["优化", "改进", "optimization", "improvement"]
        }
        
        for stage, keywords in workflow_stages.items():
            if any(keyword in question_lower for keyword in keywords):
                analysis["workflow_stages"].append(stage)
        
        # 判断问题类型
        if any(word in question_lower for word in ["如何", "怎么", "how"]):
            analysis["action_required"] = True
        
        if any(word in question_lower for word in ["状态", "进度", "status", "progress"]):
            analysis["status_inquiry"] = True
        
        if any(word in question_lower for word in ["优化", "改进", "optimize", "improve"]):
            analysis["optimization_request"] = True
        
        return analysis
    
    def _analyze_system_question(self, question_text: str) -> Dict[str, Any]:
        """分析系统问题"""
        question_lower = question_text.lower()
        
        analysis = {
            "system_components": [],
            "status": "unknown",
            "performance_related": False,
            "error_related": False
        }
        
        # 识别系统组件
        system_components = {
            "database": ["数据库", "database", "db"],
            "cache": ["缓存", "cache"],
            "api": ["接口", "api", "endpoint"],
            "queue": ["队列", "queue", "message"],
            "storage": ["存储", "storage", "file"]
        }
        
        for component, keywords in system_components.items():
            if any(keyword in question_lower for keyword in keywords):
                analysis["system_components"].append(component)
        
        # 判断问题类型
        if any(word in question_lower for word in ["性能", "速度", "performance", "speed"]):
            analysis["performance_related"] = True
        
        if any(word in question_lower for word in ["错误", "异常", "error", "exception"]):
            analysis["error_related"] = True
        
        # 判断系统状态
        if any(word in question_lower for word in ["正常", "正常", "normal", "healthy"]):
            analysis["status"] = "healthy"
        elif any(word in question_lower for word in ["问题", "故障", "problem", "issue"]):
            analysis["status"] = "problematic"
        
        return analysis
    
    def _generate_general_answer(self, question: str, analysis: Dict[str, Any]) -> str:
        """生成一般问题答案"""
        if analysis["complexity"] == "simple":
            return f"关于您的问题：{question}\n\n这是一个相对简单的问题，我可以为您提供基本的解答。请告诉我您需要了解的具体方面。"
        else:
            return f"关于您的问题：{question}\n\n这是一个比较复杂的问题，涉及多个方面。我建议我们分步骤来分析和解决。您希望从哪个方面开始？"
    
    def _generate_technical_answer(self, question: str, analysis: Dict[str, Any]) -> str:
        """生成技术问题答案"""
        domains = ", ".join(analysis["technical_domains"])
        
        answer = f"技术问题分析：{question}\n\n"
        answer += f"涉及技术领域：{domains}\n"
        answer += f"复杂度：{analysis['complexity']}\n\n"
        
        if analysis["requires_code"]:
            answer += "这个问题需要代码实现。我可以为您提供代码示例和详细说明。\n"
        
        answer += "请告诉我您的具体技术需求和约束条件。"
        
        return answer
    
    def _generate_workflow_answer(self, question: str, analysis: Dict[str, Any]) -> str:
        """生成工作流问题答案"""
        stages = ", ".join(analysis["workflow_stages"])
        
        answer = f"工作流问题分析：{question}\n\n"
        answer += f"涉及工作流阶段：{stages}\n\n"
        
        if analysis["action_required"]:
            answer += "需要执行具体操作。我可以为您提供详细的操作步骤。\n"
        
        if analysis["status_inquiry"]:
            answer += "这是状态查询。我可以为您检查当前工作流状态。\n"
        
        if analysis["optimization_request"]:
            answer += "这是优化请求。我可以分析当前工作流并提供改进建议。\n"
        
        return answer
    
    def _generate_system_answer(self, question: str, analysis: Dict[str, Any]) -> str:
        """生成系统问题答案"""
        components = ", ".join(analysis["system_components"])
        
        answer = f"系统问题分析：{question}\n\n"
        answer += f"涉及系统组件：{components}\n"
        answer += f"系统状态：{analysis['status']}\n\n"
        
        if analysis["performance_related"]:
            answer += "这是性能相关问题。我可以为您检查系统性能指标。\n"
        
        if analysis["error_related"]:
            answer += "这是错误相关问题。我可以为您检查系统日志和错误信息。\n"
        
        return answer
    
    async def get_question(self, question_id: str) -> Optional[QuestionContext]:
        """获取问题"""
        return self.questions.get(question_id)
    
    async def get_answer(self, question_id: str) -> Optional[Answer]:
        """获取答案"""
        return self.answers.get(question_id)
    
    async def get_questions_by_session(self, session_id: str) -> List[QuestionContext]:
        """获取指定会话的问题"""
        return [
            question for question in self.questions.values()
            if question.session_id == session_id
        ]
    
    async def get_questions_by_type(self, question_type: str) -> List[QuestionContext]:
        """获取指定类型的问题"""
        return [
            question for question in self.questions.values()
            if question.question_type == question_type
        ]
    
    async def get_questions_by_status(self, status: str) -> List[QuestionContext]:
        """获取指定状态的问题"""
        return [
            question for question in self.questions.values()
            if question.status == status
        ]
    
    async def search_questions(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[QuestionContext]:
        """搜索问题"""
        results = []
        
        for question in self.questions.values():
            if session_id and question.session_id != session_id:
                continue
            
            if query.lower() in question.question_text.lower():
                results.append(question)
        
        # 按创建时间排序
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]
    
    async def close_question(self, question_id: str) -> bool:
        """关闭问题"""
        try:
            if question_id not in self.questions:
                return False
            
            question = self.questions[question_id]
            question.status = "closed"
            
            # 更新历史记录
            for record in self.question_history:
                if record["question_id"] == question_id:
                    record["status"] = "closed"
                    record["closed_at"] = datetime.now().isoformat()
                    break
            
            logger.info(f"问题已关闭: {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"关闭问题失败: {e}")
            return False
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        total_questions = len(self.questions)
        total_answers = len(self.answers)
        total_history = len(self.question_history)
        
        # 按状态统计问题
        status_stats = {}
        for question in self.questions.values():
            status = question.status
            status_stats[status] = status_stats.get(status, 0) + 1
        
        # 按类型统计问题
        type_stats = {}
        for question in self.questions.values():
            qtype = question.question_type
            type_stats[qtype] = type_stats.get(qtype, 0) + 1
        
        # 按优先级统计问题
        priority_stats = {}
        for question in self.questions.values():
            priority = question.priority
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
        
        return {
            "total_questions": total_questions,
            "total_answers": total_answers,
            "total_history": total_history,
            "status_distribution": status_stats,
            "type_distribution": type_stats,
            "priority_distribution": priority_stats,
            "processors_registered": len(self.question_processors)
        }
