"""
Workflow Monitor

工作流监控器 - 监控工作流执行状态和性能
"""

from typing import Dict, List, Any, Optional
import structlog
import asyncio
from datetime import datetime
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class WorkflowStatus:
    """工作流状态"""
    workflow_id: str
    status: str
    progress: float
    start_time: datetime
    current_step: str
    total_steps: int
    completed_steps: int


class WorkflowMonitor:
    """
    工作流监控器
    
    实时监控工作流的执行状态和性能指标
    """
    
    def __init__(self):
        self.workflow_statuses: Dict[str, WorkflowStatus] = {}
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info("工作流监控器初始化完成")
    
    async def start_monitoring(self, workflow_id: str):
        """开始监控工作流"""
        status = WorkflowStatus(
            workflow_id=workflow_id,
            status="running",
            progress=0.0,
            start_time=datetime.now(),
            current_step="initialization",
            total_steps=0,
            completed_steps=0
        )
        
        self.workflow_statuses[workflow_id] = status
        logger.info(f"开始监控工作流: {workflow_id}")
    
    async def update_workflow_status(
        self,
        workflow_id: str,
        status: str,
        progress: float,
        current_step: str
    ):
        """更新工作流状态"""
        if workflow_id in self.workflow_statuses:
            workflow_status = self.workflow_statuses[workflow_id]
            workflow_status.status = status
            workflow_status.progress = progress
            workflow_status.current_step = current_step
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """获取工作流状态"""
        return self.workflow_statuses.get(workflow_id)
    
    async def get_all_active_workflows(self) -> List[WorkflowStatus]:
        """获取所有活跃的工作流"""
        return [
            status for status in self.workflow_statuses.values()
            if status.status in ["running", "paused"]
        ]
    
    async def stop_monitoring(self, workflow_id: str):
        """停止监控工作流"""
        if workflow_id in self.workflow_statuses:
            del self.workflow_statuses[workflow_id]
        if workflow_id in self.performance_metrics:
            del self.performance_metrics[workflow_id]
        
        logger.info(f"停止监控工作流: {workflow_id}")
