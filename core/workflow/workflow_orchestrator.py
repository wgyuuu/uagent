"""
UAgent Workflow Orchestrator

工作流编排器 - 管理工作流的创建、调度和监控
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import structlog
from dataclasses import dataclass

from models.base import Task, WorkflowExecution, WorkflowStatus
from models.workflow import WorkflowDefinition, ExecutionPlan
from core.intelligence import MainAgent
from core.workflow.waterfall_engine import WaterfallWorkflowEngine

logger = structlog.get_logger(__name__)


@dataclass
class WorkflowRequest:
    """工作流请求"""
    task: Task
    preferred_roles: Optional[List[str]] = None
    workflow_template: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None
    priority: int = 5
    timeout_minutes: Optional[int] = None


class WorkflowOrchestrator:
    """
    工作流编排器
    
    负责工作流的创建、调度、监控和生命周期管理
    """
    
    def __init__(self, main_agent: MainAgent, workflow_engine: WaterfallWorkflowEngine):
        """
        初始化工作流编排器
        
        Args:
            main_agent: 主Agent实例
            workflow_engine: 工作流引擎实例
        """
        self.main_agent = main_agent
        self.workflow_engine = workflow_engine
        
        # 工作流管理
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.workflow_executions: Dict[str, WorkflowExecution] = {}
        self.workflow_queue: List[WorkflowRequest] = []
        
        # 调度配置
        self.max_queued_workflows = 100
        self.scheduler_interval = 5  # 调度器运行间隔(秒)
        self.auto_scheduling = True
        
        # 回调函数
        self.on_workflow_created: Optional[Callable] = None
        self.on_workflow_started: Optional[Callable] = None
        self.on_workflow_completed: Optional[Callable] = None
        self.on_workflow_failed: Optional[Callable] = None
        
        # 启动调度器
        self._scheduler_task = None
        self._start_scheduler()
        
        logger.info("工作流编排器初始化完成")
    
    async def create_workflow(self, request: WorkflowRequest) -> WorkflowExecution:
        """
        创建工作流
        
        Args:
            request: 工作流请求
            
        Returns:
            WorkflowExecution: 创建的工作流执行实例
        """
        try:
            logger.info(f"创建工作流: 任务={request.task.task_id}")
            
            # 1. 任务分析和角色推荐
            task_analysis, workflow_definition = await self.main_agent.analyze_and_plan_task(
                request.task
            )
            
            # 2. 应用用户偏好
            if request.preferred_roles:
                workflow_definition.roles = request.preferred_roles
            
            # 3. 应用自定义配置
            if request.custom_config:
                for key, value in request.custom_config.items():
                    if hasattr(workflow_definition, key):
                        setattr(workflow_definition, key, value)
            
            # 4. 创建执行计划
            execution_plan = await self._create_execution_plan(workflow_definition)
            
            # 5. 创建工作流执行实例
            workflow_execution = WorkflowExecution(
                workflow_id=workflow_definition.workflow_id,
                name=workflow_definition.name,
                description=workflow_definition.description,
                task=request.task,
                roles=workflow_definition.roles,
                current_role_index=0,
                status=WorkflowStatus.CREATED,
                created_by=request.task.created_by,
                metadata={
                    "priority": request.priority,
                    "timeout_minutes": request.timeout_minutes,
                    "execution_plan": execution_plan.model_dump() if execution_plan else None
                }
            )
            
            # 6. 存储工作流定义和执行实例
            self.workflow_definitions[workflow_definition.workflow_id] = workflow_definition
            self.workflow_executions[workflow_execution.workflow_id] = workflow_execution
            
            # 7. 添加到队列
            await self._add_to_queue(workflow_execution, request.priority)
            
            # 8. 触发创建回调
            if self.on_workflow_created:
                await self.on_workflow_created(workflow_execution)
            
            logger.info(f"工作流创建完成: {workflow_execution.workflow_id}")
            return workflow_execution
            
        except Exception as e:
            logger.error(f"工作流创建失败: {e}")
            raise
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """
        启动工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功启动
        """
        if workflow_id not in self.workflow_executions:
            logger.warning(f"工作流不存在: {workflow_id}")
            return False
        
        workflow = self.workflow_executions[workflow_id]
        
        if workflow.status != WorkflowStatus.CREATED:
            logger.warning(f"工作流状态不正确: {workflow_id}, 状态: {workflow.status}")
            return False
        
        try:
            # 启动工作流执行
            await self.workflow_engine.execute_workflow(workflow)
            
            # 触发启动回调
            if self.on_workflow_started:
                await self.on_workflow_started(workflow)
            
            logger.info(f"工作流已启动: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"工作流启动失败: {workflow_id}, 错误: {e}")
            workflow.status = WorkflowStatus.FAILED
            return False
    
    async def schedule_workflow(self, workflow_id: str, priority: int = 5) -> bool:
        """
        调度工作流
        
        Args:
            workflow_id: 工作流ID
            priority: 优先级
            
        Returns:
            bool: 是否成功调度
        """
        if workflow_id not in self.workflow_executions:
            logger.warning(f"工作流不存在: {workflow_id}")
            return False
        
        workflow = self.workflow_executions[workflow_id]
        
        # 添加到调度队列
        await self._add_to_queue(workflow, priority)
        
        logger.info(f"工作流已调度: {workflow_id}, 优先级: {priority}")
        return True
    
    async def get_workflow_info(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流信息
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[Dict]: 工作流信息
        """
        if workflow_id not in self.workflow_executions:
            return None
        
        workflow = self.workflow_executions[workflow_id]
        definition = self.workflow_definitions.get(workflow_id)
        
        info = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "current_role": workflow.get_current_role(),
            "progress": f"{workflow.current_role_index}/{len(workflow.roles)}",
            "roles": workflow.roles,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "execution_time": workflow.total_execution_time,
            "priority": workflow.metadata.get("priority", 5),
            "queue_position": await self._get_queue_position(workflow_id)
        }
        
        if definition:
            info["template_id"] = definition.template_id
            info["quality_gates"] = definition.quality_gates
            info["success_criteria"] = definition.success_criteria
        
        return info
    
    async def get_all_workflows(self, 
                               status_filter: Optional[WorkflowStatus] = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取所有工作流信息
        
        Args:
            status_filter: 状态过滤器
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 工作流信息列表
        """
        workflows = []
        
        for workflow in self.workflow_executions.values():
            if status_filter and workflow.status != status_filter:
                continue
            
            info = await self.get_workflow_info(workflow.workflow_id)
            if info:
                workflows.append(info)
            
            if len(workflows) >= limit:
                break
        
        # 按创建时间排序
        workflows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return workflows
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功取消
        """
        # 从队列中移除
        await self._remove_from_queue(workflow_id)
        
        # 如果正在执行，停止执行
        if workflow_id in self.workflow_engine.active_workflows:
            return await self.workflow_engine.cancel_workflow(workflow_id)
        
        # 如果还未开始，标记为取消
        if workflow_id in self.workflow_executions:
            workflow = self.workflow_executions[workflow_id]
            if workflow.status == WorkflowStatus.CREATED:
                workflow.status = WorkflowStatus.CANCELLED
                workflow.completed_at = datetime.now()
                return True
        
        return False
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        暂停工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功暂停
        """
        return await self.workflow_engine.pause_workflow(workflow_id)
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        恢复工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功恢复
        """
        return await self.workflow_engine.resume_workflow(workflow_id)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            Dict: 队列状态信息
        """
        queue_info = []
        for i, (workflow_id, priority) in enumerate(self.workflow_queue):
            workflow = self.workflow_executions.get(workflow_id)
            if workflow:
                queue_info.append({
                    "position": i + 1,
                    "workflow_id": workflow_id,
                    "name": workflow.name,
                    "priority": priority,
                    "created_at": workflow.created_at.isoformat() if workflow.created_at else None
                })
        
        return {
            "queue_length": len(self.workflow_queue),
            "max_queue_size": self.max_queued_workflows,
            "queued_workflows": queue_info,
            "active_workflows": len(self.workflow_engine.active_workflows),
            "max_concurrent_workflows": self.workflow_engine.max_concurrent_workflows
        }
    
    def set_auto_scheduling(self, enabled: bool):
        """
        设置自动调度
        
        Args:
            enabled: 是否启用自动调度
        """
        self.auto_scheduling = enabled
        logger.info(f"自动调度已{'启用' if enabled else '禁用'}")
    
    def set_callbacks(self,
                     on_workflow_created: Optional[Callable] = None,
                     on_workflow_started: Optional[Callable] = None,
                     on_workflow_completed: Optional[Callable] = None,
                     on_workflow_failed: Optional[Callable] = None):
        """
        设置回调函数
        
        Args:
            on_workflow_created: 工作流创建回调
            on_workflow_started: 工作流启动回调
            on_workflow_completed: 工作流完成回调
            on_workflow_failed: 工作流失败回调
        """
        self.on_workflow_created = on_workflow_created
        self.on_workflow_started = on_workflow_started
        self.on_workflow_completed = on_workflow_completed
        self.on_workflow_failed = on_workflow_failed
        
        # 设置工作流引擎回调
        self.workflow_engine.set_callbacks(
            on_workflow_complete=self._on_workflow_complete,
            on_role_fail=self._on_role_fail
        )
        
        logger.info("工作流编排器回调函数已设置")
    
    # ===== 私有方法 =====
    
    def _start_scheduler(self):
        """启动调度器"""
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("工作流调度器已启动")
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        while True:
            try:
                if self.auto_scheduling:
                    await self._process_queue()
                
                await asyncio.sleep(self.scheduler_interval)
                
            except asyncio.CancelledError:
                logger.info("工作流调度器已停止")
                break
            except Exception as e:
                logger.error(f"调度器错误: {e}")
                await asyncio.sleep(self.scheduler_interval)
    
    async def _process_queue(self):
        """处理队列中的工作流"""
        if not self.workflow_queue:
            return
        
        # 检查是否有可用的执行槽
        if len(self.workflow_engine.active_workflows) >= self.workflow_engine.max_concurrent_workflows:
            return
        
        # 按优先级排序队列
        self.workflow_queue.sort(key=lambda x: x[1], reverse=True)
        
        # 启动可执行的工作流
        workflows_to_start = []
        for workflow_id, priority in self.workflow_queue:
            if len(workflows_to_start) >= 2:  # 每次最多启动2个
                break
            
            workflow = self.workflow_executions.get(workflow_id)
            if workflow and workflow.status == WorkflowStatus.CREATED:
                workflows_to_start.append(workflow_id)
        
        # 启动工作流
        for workflow_id in workflows_to_start:
            try:
                await self.start_workflow(workflow_id)
                await self._remove_from_queue(workflow_id)
            except Exception as e:
                logger.error(f"启动工作流失败: {workflow_id}, 错误: {e}")
    
    async def _add_to_queue(self, workflow: WorkflowExecution, priority: int):
        """添加到队列"""
        if len(self.workflow_queue) >= self.max_queued_workflows:
            # 移除优先级最低的工作流
            self.workflow_queue.sort(key=lambda x: x[1])
            removed_workflow_id, _ = self.workflow_queue.pop(0)
            logger.warning(f"队列已满，移除低优先级工作流: {removed_workflow_id}")
        
        self.workflow_queue.append((workflow.workflow_id, priority))
        logger.info(f"工作流已添加到队列: {workflow.workflow_id}, 优先级: {priority}")
    
    async def _remove_from_queue(self, workflow_id: str):
        """从队列中移除"""
        self.workflow_queue = [(wid, priority) for wid, priority in self.workflow_queue if wid != workflow_id]
        logger.info(f"工作流已从队列中移除: {workflow_id}")
    
    async def _get_queue_position(self, workflow_id: str) -> Optional[int]:
        """获取队列位置"""
        for i, (wid, _) in enumerate(self.workflow_queue):
            if wid == workflow_id:
                return i + 1
        return None
    
    async def _create_execution_plan(self, workflow_definition: WorkflowDefinition) -> Optional[ExecutionPlan]:
        """创建执行计划"""
        try:
            # 估算执行时间
            estimated_time = 0
            for role in workflow_definition.roles:
                # 基于角色的简单时间估算
                role_time_map = {
                    "方案规划师": 60,
                    "编码专家": 180,
                    "测试工程师": 90,
                    "代码审查员": 45,
                    "数据分析师": 120,
                    "股票分析师": 90,
                    "技术写作专家": 75,
                    "调研分析师": 105,
                    "文档阅读专家": 45,
                    "知识整理专家": 60
                }
                estimated_time += role_time_map.get(role, 60)
            
            # 创建执行计划
            plan = ExecutionPlan(
                plan_id=f"plan_{generate_id()}",
                workflow_id=workflow_definition.workflow_id,
                planned_steps=[],  # 这里应该创建具体的步骤
                estimated_total_time=estimated_time,
                created_by="orchestrator"
            )
            
            return plan
            
        except Exception as e:
            logger.warning(f"创建执行计划失败: {e}")
            return None
    
    async def _on_workflow_complete(self, workflow: WorkflowExecution):
        """工作流完成回调"""
        try:
            # 触发完成回调
            if self.on_workflow_completed:
                await self.on_workflow_completed(workflow)
            
            # 清理资源
            if workflow.workflow_id in self.workflow_executions:
                del self.workflow_executions[workflow.workflow_id]
            
            if workflow.workflow_id in self.workflow_definitions:
                del self.workflow_definitions[workflow.workflow_id]
            
            logger.info(f"工作流资源已清理: {workflow.workflow_id}")
            
        except Exception as e:
            logger.error(f"工作流完成回调处理失败: {e}")
    
    async def _on_role_fail(self, workflow: WorkflowExecution, role: str, error: Exception):
        """角色失败回调"""
        try:
            # 触发失败回调
            if self.on_workflow_failed:
                await self.on_workflow_failed(workflow, role, error)
            
        except Exception as e:
            logger.error(f"角色失败回调处理失败: {e}")
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """获取编排器统计信息"""
        return {
            "total_workflows_created": len(self.workflow_executions),
            "active_workflows": len(self.workflow_engine.active_workflows),
            "queued_workflows": len(self.workflow_queue),
            "max_queue_size": self.max_queued_workflows,
            "auto_scheduling": self.auto_scheduling,
            "scheduler_interval": self.scheduler_interval
        }


# ===== 工具函数 =====

def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    import uuid
    if prefix:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    return uuid.uuid4().hex[:8]
