"""
Tool Execution Coordinator

工具执行协调器 - 负责工具执行的协调和管理
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class ToolExecutionCoordinator:
    """
    工具执行协调器
    
    负责工具执行的协调和管理，包括：
    - 执行队列管理
    - 资源分配
    - 执行状态跟踪
    - 错误处理和恢复
    """
    
    def __init__(self):
        """初始化工具执行协调器"""
        self.execution_queue = asyncio.Queue()
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.execution_results: Dict[str, Any] = {}
        self.resource_usage: Dict[str, float] = {}
        
        # 配置
        self.max_concurrent_executions = 10
        self.max_queue_size = 100
        self.execution_timeout = 300  # 5分钟
        
        # 启动协调器
        self.coordinator_task = None
        self._start_coordinator()
        
        logger.info("工具执行协调器初始化完成")
    
    def _start_coordinator(self):
        """启动协调器"""
        self.coordinator_task = asyncio.create_task(self._coordinator_worker())
    
    async def _coordinator_worker(self):
        """协调器工作循环"""
        while True:
            try:
                # 处理执行队列
                await self._process_execution_queue()
                
                # 清理过期结果
                await self._cleanup_expired_results()
                
                # 监控资源使用
                await self._monitor_resource_usage()
                
                # 短暂休眠
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"协调器工作循环错误: {e}")
                await asyncio.sleep(1)  # 错误后等待
    
    async def _process_execution_queue(self):
        """处理执行队列"""
        try:
            # 检查是否有可用的执行槽
            if len(self.active_executions) >= self.max_concurrent_executions:
                return
            
            # 从队列获取执行请求
            if self.execution_queue.empty():
                return
            
            # 获取执行请求（非阻塞）
            try:
                execution_request = self.execution_queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            
            # 创建执行任务
            task = asyncio.create_task(self._execute_with_coordination(execution_request))
            execution_id = execution_request.get("execution_id", f"exec_{datetime.now().timestamp()}")
            
            self.active_executions[execution_id] = task
            
            # 标记任务完成
            self.execution_queue.task_done()
            
        except Exception as e:
            logger.error(f"处理执行队列失败: {e}")
    
    async def _execute_with_coordination(self, execution_request: Dict[str, Any]):
        """协调执行工具"""
        execution_id = execution_request.get("execution_id")
        start_time = datetime.now()
        
        try:
            # 记录开始执行
            self.execution_results[execution_id] = {
                "status": "running",
                "start_time": start_time.isoformat(),
                "request": execution_request
            }
            
            # 执行工具调用
            tool_manager = execution_request.get("tool_manager")
            tool_calls = execution_request.get("tool_calls", [])
            role = execution_request.get("role", "unknown")
            context = execution_request.get("context", {})
            
            if tool_manager and hasattr(tool_manager, 'execute_tools_batch'):
                results = await tool_manager.execute_tools_batch(tool_calls, role, context)
            else:
                # 降级到单个工具执行
                results = []
                for tool_call in tool_calls:
                    if hasattr(tool_manager, 'execute_tool'):
                        result = await tool_manager.execute_tool(
                            tool_call.get("tool_name"),
                            tool_call.get("parameters", {}),
                            role,
                            context
                        )
                        results.append(result)
                    else:
                        results.append({
                            "success": False,
                            "error": "工具管理器不支持批量执行"
                        })
            
            # 记录执行结果
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.execution_results[execution_id].update({
                "status": "completed",
                "end_time": datetime.now().isoformat(),
                "execution_time": execution_time,
                "results": results,
                "success": all(r.get("success", False) for r in results)
            })
            
            logger.info(f"工具执行完成: {execution_id}, 耗时: {execution_time:.3f}s")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 记录错误
            self.execution_results[execution_id].update({
                "status": "failed",
                "end_time": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "success": False
            })
            
            logger.error(f"工具执行失败: {execution_id}, 错误: {e}")
            
        finally:
            # 清理活动执行记录
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _cleanup_expired_results(self):
        """清理过期的执行结果"""
        try:
            current_time = datetime.now()
            expired_ids = []
            
            for execution_id, result in self.execution_results.items():
                # 检查是否过期
                if "start_time" in result:
                    start_time = datetime.fromisoformat(result["start_time"])
                    elapsed = (current_time - start_time).total_seconds()
                    
                    if elapsed > self.execution_timeout:
                        expired_ids.append(execution_id)
            
            # 清理过期结果
            for execution_id in expired_ids:
                del self.execution_results[execution_id]
            
            if expired_ids:
                logger.debug(f"清理了 {len(expired_ids)} 个过期的执行结果")
                
        except Exception as e:
            logger.error(f"清理过期结果失败: {e}")
    
    async def _monitor_resource_usage(self):
        """监控资源使用"""
        try:
            # 监控队列大小
            queue_size = self.execution_queue.qsize()
            if queue_size > self.max_queue_size * 0.8:
                logger.warning(f"执行队列即将满: {queue_size}/{self.max_queue_size}")
            
            # 监控并发执行数
            active_count = len(self.active_executions)
            if active_count > self.max_concurrent_executions * 0.8:
                logger.warning(f"并发执行数即将达到上限: {active_count}/{self.max_concurrent_executions}")
                
        except Exception as e:
            logger.error(f"监控资源使用失败: {e}")
    
    async def submit_execution(self, 
                             tool_manager: Any,
                             tool_calls: List[Dict[str, Any]],
                             role: str = "unknown",
                             context: Dict[str, Any] = None,
                             priority: int = 1) -> str:
        """提交工具执行请求"""
        try:
            # 检查队列是否已满
            if self.execution_queue.qsize() >= self.max_queue_size:
                raise RuntimeError("执行队列已满")
            
            # 生成执行ID
            execution_id = f"exec_{datetime.now().timestamp()}_{priority}"
            
            # 创建执行请求
            execution_request = {
                "execution_id": execution_id,
                "tool_manager": tool_manager,
                "tool_calls": tool_calls,
                "role": role,
                "context": context,
                "priority": priority,
                "submitted_at": datetime.now().isoformat()
            }
            
            # 添加到执行队列
            await self.execution_queue.put(execution_request)
            
            logger.info(f"工具执行请求已提交: {execution_id}, 队列位置: {self.execution_queue.qsize()}")
            
            return execution_id
            
        except Exception as e:
            logger.error(f"提交工具执行请求失败: {e}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        return self.execution_results.get(execution_id)
    
    async def wait_for_execution(self, execution_id: str, timeout: int = None) -> Optional[Dict[str, Any]]:
        """等待执行完成"""
        try:
            start_time = datetime.now()
            timeout_seconds = timeout or self.execution_timeout
            
            while True:
                # 检查执行结果
                result = self.execution_results.get(execution_id)
                if result and result.get("status") in ["completed", "failed"]:
                    return result
                
                # 检查超时
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.warning(f"等待执行超时: {execution_id}")
                    return None
                
                # 短暂等待
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"等待执行完成失败: {e}")
            return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        try:
            # 检查是否在活动执行中
            if execution_id in self.active_executions:
                task = self.active_executions[execution_id]
                task.cancel()
                del self.active_executions[execution_id]
                
                # 更新状态
                if execution_id in self.execution_results:
                    self.execution_results[execution_id].update({
                        "status": "cancelled",
                        "end_time": datetime.now().isoformat()
                    })
                
                logger.info(f"执行已取消: {execution_id}")
                return True
            
            # 检查是否在队列中（这里需要更复杂的队列管理）
            logger.warning(f"无法取消执行: {execution_id} (可能已完成或不在队列中)")
            return False
            
        except Exception as e:
            logger.error(f"取消执行失败: {e}")
            return False
    
    def get_coordinator_status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        return {
            "queue_size": self.execution_queue.qsize(),
            "active_executions": len(self.active_executions),
            "completed_executions": len([r for r in self.execution_results.values() if r.get("status") in ["completed", "failed"]]),
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_queue_size": self.max_queue_size,
            "execution_timeout": self.execution_timeout,
            "active_tools": list(self.active_executions.keys())
        }
    
    async def shutdown(self):
        """关闭协调器"""
        try:
            # 取消所有活动执行
            for execution_id, task in self.active_executions.items():
                task.cancel()
            
            # 等待所有任务完成
            if self.active_executions:
                await asyncio.gather(*self.active_executions.values(), return_exceptions=True)
            
            # 取消协调器任务
            if self.coordinator_task:
                self.coordinator_task.cancel()
                try:
                    await self.coordinator_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("工具执行协调器已关闭")
            
        except Exception as e:
            logger.error(f"关闭协调器失败: {e}")
