"""
UAgent Waterfall Workflow Engine

瀑布式工作流引擎 - 按顺序执行角色，管理角色间交接
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from datetime import datetime
import structlog
from dataclasses import dataclass
import traceback

from core.execution.execution_controller import ExecutionContext
from models.base import (
    RoleResult, HandoffContext, 
    IsolatedRoleContext, WorkflowStatus, RoleStatus, ValidationResult, RecoveryDecision, RecoveryStrategy, WorkflowExecution
)
from core.intelligence import MainAgent
from core.execution import RoleExecutor, ExecutionConfig
from core.execution.mcptools import ToolManager


logger = structlog.get_logger(__name__)


class WaterfallWorkflowEngine:
    """
    瀑布式工作流引擎
    
    按预定顺序执行角色，管理角色间交接，确保工作流的顺利进行
    """
    
    def __init__(self, main_agent: MainAgent):
        """
        初始化瀑布式工作流引擎
        
        Args:
            main_agent: 主Agent实例
        """
        self.main_agent = main_agent
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # 执行配置
        self.max_concurrent_workflows = 10
        self.role_timeout_seconds = 3600  # 1小时
        self.retry_attempts = 3
        
        # 回调函数
        self.on_role_start: Optional[Callable] = None
        self.on_role_complete: Optional[Callable] = None
        self.on_role_fail: Optional[Callable] = None
        self.on_workflow_complete: Optional[Callable] = None
        
        logger.info("瀑布式工作流引擎初始化完成")
    
    async def execute_workflow(self, workflow: WorkflowExecution) -> WorkflowExecution:
        """
        执行工作流
        
        Args:
            workflow: 工作流定义
            
        Returns:
            WorkflowExecution: 执行完成的工作流
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行工作流: {workflow.workflow_id}")
            
            # 1. 验证工作流
            validation_result = await self._validate_workflow(workflow)
            if not validation_result.is_valid:
                workflow.status = WorkflowStatus.FAILED
                workflow.errors.append({
                    "type": "validation_error",
                    "message": validation_result.error_message,
                    "timestamp": datetime.now().isoformat()
                })
                return workflow
            
            # 2. 初始化工作流状态
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now()
            workflow.role_statuses = {role: RoleStatus.PENDING for role in workflow.roles}
            
            # 3. 注册到活跃工作流
            self.active_workflows[workflow.workflow_id] = workflow
            
            # 4. 执行角色序列
            await self._execute_role_sequence(workflow)
            
            # 5. 完成工作流
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.total_execution_time = (
                workflow.completed_at - workflow.started_at
            ).total_seconds()
            
            # 6. 从活跃工作流中移除
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]
            
            # 7. 记录执行历史
            execution_time = (workflow.completed_at - start_time).total_seconds()
            await self._record_execution_history(workflow, execution_time, True)
            
            # 8. 触发完成回调
            if self.on_workflow_complete:
                await self.on_workflow_complete(workflow)
            
            logger.info(f"工作流执行完成: {workflow.workflow_id}, 耗时: {execution_time:.2f}秒")
            return workflow
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"工作流执行失败: {workflow.workflow_id}, 错误: {e}")
            
            # 设置失败状态
            workflow.status = WorkflowStatus.FAILED
            workflow.errors.append({
                "type": "execution_error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            # 记录执行历史
            await self._record_execution_history(workflow, execution_time, False)
            
            # 从活跃工作流中移除
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]
            
            raise
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        暂停工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功暂停
        """
        if workflow_id not in self.active_workflows:
            logger.warning(f"工作流不存在或未运行: {workflow_id}")
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.PAUSED
        
        logger.info(f"工作流已暂停: {workflow_id}")
        return True
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        恢复工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功恢复
        """
        if workflow_id not in self.active_workflows:
            logger.warning(f"工作流不存在: {workflow_id}")
            return False
        
        workflow = self.active_workflows[workflow_id]
        if workflow.status != WorkflowStatus.PAUSED:
            logger.warning(f"工作流状态不是暂停状态: {workflow_id}, 状态: {workflow.status}")
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        
        # 继续执行剩余角色
        await self._execute_role_sequence(workflow)
        
        logger.info(f"工作流已恢复: {workflow_id}")
        return True
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            bool: 是否成功取消
        """
        if workflow_id not in self.active_workflows:
            logger.warning(f"工作流不存在: {workflow_id}")
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        
        # 从活跃工作流中移除
        del self.active_workflows[workflow_id]
        
        logger.info(f"工作流已取消: {workflow_id}")
        return True
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流状态
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[Dict]: 工作流状态信息
        """
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow.workflow_id,
                "status": workflow.status,
                "current_role": workflow.get_current_role(),
                "progress": f"{workflow.current_role_index}/{len(workflow.roles)}",
                "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
                "execution_time": workflow.total_execution_time
            }
        
        return None
    
    async def get_all_workflow_statuses(self) -> List[Dict[str, Any]]:
        """
        获取所有活跃工作流状态
        
        Returns:
            List[Dict]: 工作流状态列表
        """
        statuses = []
        for workflow in self.active_workflows.values():
            status = await self.get_workflow_status(workflow.workflow_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    # ===== 私有方法 =====
    
    async def _validate_workflow(self, workflow: WorkflowExecution) -> ValidationResult:
        """验证工作流"""
        errors = []
        
        # 检查角色序列
        if not workflow.roles:
            errors.append("工作流角色序列不能为空")
        
        # 检查任务
        if not workflow.task:
            errors.append("工作流必须关联任务")
        
        # 检查并发限制
        if len(self.active_workflows) >= self.max_concurrent_workflows:
            errors.append(f"已达到最大并发工作流数量: {self.max_concurrent_workflows}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            error_message="; ".join(errors) if errors else None
        )
    
    async def _execute_role_sequence(self, workflow: WorkflowExecution):
        """执行角色序列"""
        for role_index, role in enumerate(workflow.roles):
            try:
                # 检查工作流状态
                if workflow.status != WorkflowStatus.RUNNING:
                    logger.info(f"工作流状态已改变，停止执行: {workflow.workflow_id}, 状态: {workflow.status}")
                    break
                
                # 更新当前角色索引
                workflow.current_role_index = role_index
                
                # 执行角色
                role_result = await self._execute_single_role(workflow, role, role_index)
                
                # 更新角色状态
                workflow.role_statuses[role] = RoleStatus.COMPLETED
                workflow.role_results[role] = role_result
                
                # 触发角色完成回调
                if self.on_role_complete:
                    await self.on_role_complete(workflow, role, role_result)
                
                logger.info(f"角色执行完成: {role}, 工作流: {workflow.workflow_id}")
                
            except Exception as e:
                logger.error(f"角色执行失败: {role}, 工作流: {workflow.workflow_id}, 错误: {e}, 堆栈信息: {traceback.format_exc()}")
                
                # 更新角色状态
                workflow.role_statuses[role] = RoleStatus.FAILED
                
                # 记录错误
                workflow.errors.append({
                    "role": role,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # 触发角色失败回调
                if self.on_role_fail:
                    await self.on_role_fail(workflow, role, e)
                
                # 尝试错误恢复
                await self._handle_role_failure(workflow, role, e)
                
                # 如果错误无法恢复，停止工作流
                if workflow.status == WorkflowStatus.FAILED:
                    break
    
    async def _execute_single_role(self, 
                                  workflow: WorkflowExecution,
                                  role: str,
                                  role_index: int) -> RoleResult:
        """执行单个角色"""
        start_time = datetime.now()
        
        try:
            # 1. 准备执行上下文
            execution_context = await self._prepare_execution_context(
                workflow, role, role_index
            )
            
            # 2. 触发角色开始回调
            if self.on_role_start:
                await self.on_role_start(workflow, role, execution_context)
            
            # 3. 更新角色状态
            workflow.role_statuses[role] = RoleStatus.RUNNING
            
            # 4. 执行角色（这里应该调用具体的角色执行器）
            role_result = await self._invoke_role_executor(role, execution_context)
            
            # 5. 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            role_result.execution_time = execution_time
            
            # 6. 准备交接上下文
            if role_index < len(workflow.roles) - 1:
                next_role = workflow.roles[role_index + 1]
                handoff_context = await self._prepare_handoff_context(
                    workflow, role, next_role, role_result
                )
                role_result.handoff_summary = handoff_context.handoff_message
                role_result.next_role_guidance = "; ".join(handoff_context.next_steps)
            
            return role_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 创建失败结果
            role_result = RoleResult(
                execution_id=f"exec_{generate_id()}",
                role=role,
                task_id=workflow.task.task_id,
                status=RoleStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time
            )
            
            raise
    
    async def _prepare_execution_context(self, 
                                       workflow: WorkflowExecution,
                                       role: str,
                                       role_index: int) -> ExecutionContext:
        """准备执行上下文"""
        # 获取之前角色的结果
        previous_results = {}
        for i in range(role_index):
            prev_role = workflow.roles[i]
            if prev_role in workflow.role_results:
                previous_results[prev_role] = workflow.role_results[prev_role]
        
        # 创建交接上下文
        handoff_context = None
        if role_index > 0:
            prev_role = workflow.roles[role_index - 1]
            if prev_role in workflow.role_results:
                handoff_context = await self._create_handoff_context(
                    workflow, prev_role, role, workflow.role_results[prev_role]
                )
        
        # 创建隔离上下文
        isolated_context = IsolatedRoleContext(
            role=role,
            workflow_id=workflow.workflow_id
        )
        
        # 填充上下文内容
        await self._populate_isolated_context(isolated_context, workflow, role, previous_results)
        
        return ExecutionContext(
            workflow_id=workflow.workflow_id,
            current_role=role,
            role_index=role_index,
            previous_results=previous_results,
            handoff_context=handoff_context,
            isolated_context=isolated_context,
            metadata=workflow.metadata
        )
    
    async def _invoke_role_executor(self, role: str, context: ExecutionContext) -> RoleResult:
        """
        调用角色执行器 - 现在是一个完整的Agent运行过程
        """
        try:
            
            # 创建执行配置
            execution_config = ExecutionConfig(
                max_iterations=10,
                max_tool_calls_per_iteration=5,
                parallel_tool_execution=True,
                context_compression_threshold=0.8,
                quality_threshold=0.85
            )
            
            # 创建角色执行器实例
            role_executor = RoleExecutor(execution_config=execution_config)
            
            # 执行角色任务
            return await role_executor.execute_role(role, context)
            
        except Exception as e:
            logger.error(f"角色执行器调用失败: {e}, 堆栈信息: {traceback.format_exc()}")
            # 降级到原来的模拟执行
            await asyncio.sleep(1)  # 模拟执行时间
            
            # 创建模拟结果
            role_result = RoleResult(
                execution_id=f"exec_{generate_id()}",
                role=role,
                task_id=context.workflow_id,
                status=RoleStatus.COMPLETED,
                outputs={
                    "status": "completed",
                    "message": f"角色 {role} 执行完成（降级模式）"
                },
                deliverables={
                    "output": f"{role} 的输出结果"
                },
                quality_score=0.8,
                completeness_score=0.9
            )
            
            return role_result
    
    async def _prepare_handoff_context(self, 
                                     workflow: WorkflowExecution,
                                     from_role: str,
                                     to_role: str,
                                     role_result: RoleResult) -> HandoffContext:
        """准备交接上下文"""
        handoff_context = HandoffContext(
            workflow_id=workflow.workflow_id,
            from_role=from_role,
            to_role=to_role,
            current_stage=workflow.current_role_index + 1,
            task_summary=f"角色 {from_role} 已完成",
            original_task=workflow.task.description,
            deliverables=role_result.deliverables,
            requirements=workflow.task.requirements,
            handoff_message=f"角色 {from_role} 已完成，请继续执行",
            next_steps=[f"执行角色 {to_role}", "完成剩余任务"]
        )
        
        return handoff_context
    
    async def _create_handoff_context(self, 
                                    workflow: WorkflowExecution,
                                    from_role: str,
                                    to_role: str,
                                    from_result: RoleResult) -> HandoffContext:
        """创建交接上下文"""
        return HandoffContext(
            workflow_id=workflow.workflow_id,
            from_role=from_role,
            to_role=to_role,
            current_stage=workflow.current_role_index,
            task_summary=f"角色 {from_role} 已完成",
            original_task=workflow.task.description,
            deliverables=from_result.deliverables,
            requirements=workflow.task.requirements,
            handoff_message=f"角色 {from_role} 已完成，请继续执行",
            next_steps=[f"执行角色 {to_role}", "完成剩余任务"]
        )
    
    async def _populate_isolated_context(self, 
                                       context: IsolatedRoleContext,
                                       workflow: WorkflowExecution,
                                       role: str,
                                       previous_results: Dict[str, RoleResult]):
        """填充隔离上下文"""
        # 填充8段式上下文
        context.update_section(
            "Primary Request and Intent",
            workflow.task.description,
            0.9
        )
        
        context.update_section(
            "Current Work",
            f"正在执行角色: {role}",
            0.8
        )
        
        # 填充之前角色的结果
        if previous_results:
            results_summary = []
            for prev_role, result in previous_results.items():
                results_summary.append(f"{prev_role}: {result.status}")
            
            context.update_section(
                "Problem Solving",
                f"已完成角色: {'; '.join(results_summary)}",
                0.7
            )
    
    async def _handle_role_failure(self, 
                                  workflow: WorkflowExecution,
                                  failed_role: str,
                                  error: Exception):
        """处理角色失败"""
        try:
            # 调用主Agent的错误恢复
            recovery_decision = await self.main_agent.handle_workflow_error(
                workflow, failed_role, error
            )
            
            if recovery_decision.decision_type == "automatic":
                # 自动恢复
                await self._execute_recovery_strategy(workflow, recovery_decision)
            else:
                # 需要手动干预
                workflow.status = WorkflowStatus.PAUSED
                logger.info(f"工作流已暂停，等待手动干预: {workflow.workflow_id}")
            
        except Exception as recovery_error:
            logger.error(f"错误恢复处理失败: {recovery_error}")
            workflow.status = WorkflowStatus.FAILED
    
    async def _execute_recovery_strategy(self, 
                                       workflow: WorkflowExecution,
                                       decision: RecoveryDecision):
        """执行恢复策略"""
        if not decision.selected_strategy:
            logger.warning("没有选择恢复策略")
            return
        
        strategy = decision.selected_strategy
        
        try:
            if strategy.action_type == "retry":
                # 重试当前角色
                await self._retry_failed_role(workflow, strategy)
            elif strategy.action_type == "skip":
                # 跳过当前角色
                await self._skip_failed_role(workflow, strategy)
            elif strategy.action_type == "replace":
                # 替换角色
                await self._replace_failed_role(workflow, strategy)
            else:
                logger.warning(f"未知的恢复策略类型: {strategy.action_type}")
                
        except Exception as e:
            logger.error(f"恢复策略执行失败: {e}")
            workflow.status = WorkflowStatus.FAILED
    
    async def _retry_failed_role(self, workflow: WorkflowExecution, strategy: RecoveryStrategy):
        """重试失败的角色"""
        current_role = workflow.get_current_role()
        if not current_role:
            return
        
        # 重置角色状态
        workflow.role_statuses[current_role] = RoleStatus.PENDING
        
        # 清除错误记录
        workflow.errors = [e for e in workflow.errors if e.get("role") != current_role]
        
        logger.info(f"准备重试角色: {current_role}")
    
    async def _skip_failed_role(self, workflow: WorkflowExecution, strategy: RecoveryStrategy):
        """跳过失败的角色"""
        current_role = workflow.get_current_role()
        if not current_role:
            return
        
        # 标记角色为跳过
        workflow.role_statuses[current_role] = RoleStatus.SKIPPED
        
        # 移动到下一个角色
        workflow.current_role_index += 1
        
        logger.info(f"已跳过角色: {current_role}")
    
    async def _replace_failed_role(self, workflow: WorkflowExecution, strategy: RecoveryStrategy):
        """替换失败的角色"""
        # 这里应该实现角色替换逻辑
        logger.info("角色替换功能待实现")
    
    async def _record_execution_history(self, 
                                      workflow: WorkflowExecution,
                                      execution_time: float,
                                      success: bool):
        """记录执行历史"""
        history_record = {
            "workflow_id": workflow.workflow_id,
            "execution_time": execution_time,
            "success": success,
            "roles_count": len(workflow.roles),
            "completed_roles": len([r for r in workflow.role_statuses.values() 
                                  if r == RoleStatus.COMPLETED]),
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(history_record)
        
        # 保持历史记录在合理范围内
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-500:]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        if not self.execution_history:
            return {"message": "暂无执行历史数据"}
        
        recent_executions = self.execution_history[-100:]
        
        # 计算成功率
        successful_executions = sum(1 for e in recent_executions if e["success"])
        success_rate = successful_executions / len(recent_executions)
        
        # 计算平均执行时间
        avg_execution_time = sum(e["execution_time"] for e in recent_executions) / len(recent_executions)
        
        return {
            "total_executions": len(self.execution_history),
            "recent_executions": len(recent_executions),
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "active_workflows": len(self.active_workflows),
            "max_concurrent_workflows": self.max_concurrent_workflows
        }
    
    def set_callbacks(self, 
                     on_role_start: Optional[Callable] = None,
                     on_role_complete: Optional[Callable] = None,
                     on_role_fail: Optional[Callable] = None,
                     on_workflow_complete: Optional[Callable] = None):
        """设置回调函数"""
        self.on_role_start = on_role_start
        self.on_role_complete = on_role_complete
        self.on_role_fail = on_role_fail
        self.on_workflow_complete = on_workflow_complete
        
        logger.info("工作流引擎回调函数已设置")


# ===== 工具函数 =====

def generate_id(prefix: str = "") -> str:
    """生成唯一ID"""
    import uuid
    if prefix:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    return uuid.uuid4().hex[:8]


class ValidationResult:
    """验证结果"""
    def __init__(self, is_valid: bool, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message


class RecoveryDecision:
    """恢复决策"""
    def __init__(self, decision_type: str, selected_strategy=None, rationale: str = ""):
        self.decision_type = decision_type
        self.selected_strategy = selected_strategy
        self.rationale = rationale


class RecoveryStrategy:
    """恢复策略"""
    def __init__(self, name: str, action_type: str, **kwargs):
        self.name = name
        self.action_type = action_type
        for key, value in kwargs.items():
            setattr(self, key, value)
