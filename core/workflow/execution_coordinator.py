"""
UAgent Execution Coordinator

执行协调器 - 协调工作流的执行和监控
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from models.base import WorkflowExecution, RoleResult
from models.workflow import ExecutionMetrics, WorkflowStep
from core.workflow.waterfall_engine import WaterfallWorkflowEngine

logger = structlog.get_logger(__name__)


class ExecutionCoordinator:
    """
    执行协调器
    
    负责协调工作流的执行，收集执行指标，监控执行状态
    """
    
    def __init__(self, workflow_engine: WaterfallWorkflowEngine):
        """
        初始化执行协调器
        
        Args:
            workflow_engine: 工作流引擎实例
        """
        self.workflow_engine = workflow_engine
        self.execution_metrics: Dict[str, ExecutionMetrics] = {}
        self.monitoring_active = True
        
        # 启动监控任务
        self._monitor_task = asyncio.create_task(self._monitor_executions())
        
        logger.info("执行协调器初始化完成")
    
    async def start_monitoring(self, workflow_id: str):
        """开始监控工作流执行"""
        if workflow_id not in self.execution_metrics:
            self.execution_metrics[workflow_id] = ExecutionMetrics(workflow_id=workflow_id)
        
        logger.info(f"开始监控工作流: {workflow_id}")
    
    async def stop_monitoring(self, workflow_id: str):
        """停止监控工作流执行"""
        if workflow_id in self.execution_metrics:
            del self.execution_metrics[workflow_id]
            logger.info(f"停止监控工作流: {workflow_id}")
    
    async def get_execution_metrics(self, workflow_id: str) -> Optional[ExecutionMetrics]:
        """获取执行指标"""
        return self.execution_metrics.get(workflow_id)
    
    async def get_all_metrics(self) -> List[ExecutionMetrics]:
        """获取所有执行指标"""
        return list(self.execution_metrics.values())
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        return {
            "monitored_workflows": len(self.execution_metrics),
            "monitoring_active": self.monitoring_active,
            "total_metrics": len(self.execution_metrics)
        }
    
    # ===== 私有方法 =====
    
    async def _monitor_executions(self):
        """监控执行的主循环"""
        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await asyncio.sleep(5)  # 每5秒收集一次指标
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self):
        """收集执行指标"""
        for workflow_id in list(self.execution_metrics.keys()):
            try:
                await self._update_workflow_metrics(workflow_id)
            except Exception as e:
                logger.error(f"更新工作流指标失败: {workflow_id}, 错误: {e}")
    
    async def _update_workflow_metrics(self, workflow_id: str):
        """更新工作流指标"""
        if workflow_id not in self.workflow_engine.active_workflows:
            return
        
        workflow = self.workflow_engine.active_workflows[workflow_id]
        metrics = self.execution_metrics[workflow_id]
        
        # 更新基本指标
        if workflow.started_at:
            elapsed_time = (datetime.now() - workflow.started_at).total_seconds()
            metrics.total_execution_time = elapsed_time
        
        # 更新角色执行指标
        completed_roles = len([r for r in workflow.role_statuses.values() if r == "completed"])
        if completed_roles > 0:
            metrics.average_step_time = metrics.total_execution_time / completed_roles
        
        # 更新错误指标
        metrics.total_errors = len(workflow.errors)
        
        # 更新质量指标
        if workflow.quality_metrics:
            metrics.overall_quality_score = sum(workflow.quality_metrics.values()) / len(workflow.quality_metrics)
        
        # 更新用户交互指标
        metrics.user_interventions = len(workflow.user_interventions)
        
        metrics.last_updated = datetime.now()
    
    async def _cleanup_completed_workflows(self):
        """清理已完成的工作流指标"""
        completed_workflows = []
        
        for workflow_id in self.execution_metrics:
            if workflow_id not in self.workflow_engine.active_workflows:
                completed_workflows.append(workflow_id)
        
        for workflow_id in completed_workflows:
            await self.stop_monitoring(workflow_id)
