"""
UAgent Workflow State Manager

工作流状态管理器 - 管理工作流的状态转换和持久化
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from models.base import WorkflowExecution, WorkflowStatus
from models.workflow import WorkflowState, WorkflowEvent, WorkflowEventHandler

logger = structlog.get_logger(__name__)


class WorkflowStateManager:
    """
    工作流状态管理器
    
    管理工作流的状态转换、事件处理和状态持久化
    """
    
    def __init__(self):
        """初始化工作流状态管理器"""
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.event_handlers: List[WorkflowEventHandler] = []
        self.event_history: List[WorkflowEvent] = []
        
        # 状态转换规则
        self.state_transitions = {
            WorkflowStatus.CREATED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
            WorkflowStatus.RUNNING: [WorkflowStatus.PAUSED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED],
            WorkflowStatus.PAUSED: [WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED],
            WorkflowStatus.COMPLETED: [],
            WorkflowStatus.FAILED: [WorkflowStatus.RUNNING],  # 可以重试
            WorkflowStatus.CANCELLED: []
        }
        
        logger.info("工作流状态管理器初始化完成")
    
    async def create_workflow_state(self, workflow_id: str, initial_status: WorkflowStatus = WorkflowStatus.CREATED) -> WorkflowState:
        """创建工作流状态"""
        state = WorkflowState(
            workflow_id=workflow_id,
            current_status=initial_status
        )
        
        self.workflow_states[workflow_id] = state
        
        # 记录状态创建事件
        await self._record_event(workflow_id, "state_created", f"工作流状态已创建: {initial_status.value}")
        
        logger.info(f"工作流状态已创建: {workflow_id}, 状态: {initial_status.value}")
        return state
    
    async def transition_workflow_state(self, workflow_id: str, new_status: WorkflowStatus, reason: str = "") -> bool:
        """转换工作流状态"""
        if workflow_id not in self.workflow_states:
            logger.warning(f"工作流状态不存在: {workflow_id}")
            return False
        
        state = self.workflow_states[workflow_id]
        current_status = state.current_status
        
        # 检查状态转换是否有效
        if new_status not in self.state_transitions.get(current_status, []):
            logger.warning(f"无效的状态转换: {current_status.value} -> {new_status.value}")
            return False
        
        # 执行状态转换
        state.transition_to(new_status, reason)
        
        # 记录状态转换事件
        await self._record_event(workflow_id, "state_transition", 
                               f"状态转换: {current_status.value} -> {new_status.value}, 原因: {reason}")
        
        # 触发事件处理器
        await self._trigger_event_handlers(workflow_id, "state_transition", {
            "from_status": current_status.value,
            "to_status": new_status.value,
            "reason": reason
        })
        
        logger.info(f"工作流状态已转换: {workflow_id}, {current_status.value} -> {new_status.value}")
        return True
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态"""
        return self.workflow_states.get(workflow_id)
    
    async def get_all_workflow_states(self) -> List[WorkflowState]:
        """获取所有工作流状态"""
        return list(self.workflow_states.values())
    
    async def pause_workflow(self, workflow_id: str, reason: str = "") -> bool:
        """暂停工作流"""
        return await self.transition_workflow_state(workflow_id, WorkflowStatus.PAUSED, reason)
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """恢复工作流"""
        return await self.transition_workflow_state(workflow_id, WorkflowStatus.RUNNING, "resumed")
    
    async def cancel_workflow(self, workflow_id: str, reason: str = "") -> bool:
        """取消工作流"""
        return await self.transition_workflow_state(workflow_id, WorkflowStatus.CANCELLED, reason)
    
    async def complete_workflow(self, workflow_id: str, reason: str = "") -> bool:
        """完成工作流"""
        return await self.transition_workflow_state(workflow_id, WorkflowStatus.COMPLETED, reason)
    
    async def fail_workflow(self, workflow_id: str, reason: str = "") -> bool:
        """标记工作流失败"""
        return await self.transition_workflow_state(workflow_id, WorkflowStatus.FAILED, reason)
    
    async def create_checkpoint(self, workflow_id: str, data: Dict[str, Any]) -> bool:
        """创建工作流检查点"""
        if workflow_id not in self.workflow_states:
            return False
        
        state = self.workflow_states[workflow_id]
        state.create_checkpoint(data)
        
        # 记录检查点事件
        await self._record_event(workflow_id, "checkpoint_created", "工作流检查点已创建")
        
        return True
    
    async def get_workflow_events(self, workflow_id: str, limit: int = 100) -> List[WorkflowEvent]:
        """获取工作流事件历史"""
        events = [event for event in self.event_history if event.workflow_id == workflow_id]
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
    
    async def register_event_handler(self, handler: WorkflowEventHandler):
        """注册事件处理器"""
        self.event_handlers.append(handler)
        logger.info(f"事件处理器已注册: {handler.name}")
    
    async def unregister_event_handler(self, handler_name: str):
        """注销事件处理器"""
        self.event_handlers = [h for h in self.event_handlers if h.name != handler_name]
        logger.info(f"事件处理器已注销: {handler_name}")
    
    def get_state_manager_stats(self) -> Dict[str, Any]:
        """获取状态管理器统计信息"""
        status_counts = {}
        for state in self.workflow_states.values():
            status = state.current_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_workflows": len(self.workflow_states),
            "status_distribution": status_counts,
            "total_events": len(self.event_history),
            "event_handlers": len(self.event_handlers)
        }
    
    # ===== 私有方法 =====
    
    async def _record_event(self, workflow_id: str, event_type: str, description: str, data: Dict[str, Any] = None):
        """记录事件"""
        event = WorkflowEvent(
            event_id=f"event_{generate_id()}",
            workflow_id=workflow_id,
            event_type=event_type,
            event_name=event_type,
            description=description,
            data=data or {},
            timestamp=datetime.now()
        )
        
        self.event_history.append(event)
        
        # 保持事件历史在合理范围内
        if len(self.event_history) > 10000:
            self.event_history = self.event_history[-5000:]
    
    async def _trigger_event_handlers(self, workflow_id: str, event_type: str, event_data: Dict[str, Any]):
        """触发事件处理器"""
        for handler in self.event_handlers:
            if event_type in handler.event_types and handler.is_active:
                try:
                    # 这里应该调用具体的处理函数
                    # 暂时只是记录日志
                    logger.info(f"事件处理器 {handler.name} 处理事件: {event_type}")
                except Exception as e:
                    logger.error(f"事件处理器 {handler.name} 处理失败: {e}")


# ===== 工具函数 =====

def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    import uuid
    if prefix:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    return uuid.uuid4().hex[:8]
