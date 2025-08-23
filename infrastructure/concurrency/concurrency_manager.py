"""
Concurrency Manager

并发管理器 - 管理系统的并发执行和资源分配
"""

from typing import Dict, List, Any, Optional, Callable, Union
import structlog
import asyncio
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil

logger = structlog.get_logger(__name__)


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_concurrent_tasks: int = 100
    max_threads: int = 20
    max_processes: int = 4
    task_timeout: int = 300  # 秒
    enable_monitoring: bool = True
    resource_limits: Dict[str, Any] = None


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    type: str  # "async", "thread", "process"
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resource_usage: Dict[str, Any]
    metadata: Dict[str, Any]


class ConcurrencyManager:
    """
    并发管理器
    
    管理系统并发执行、资源分配和性能监控
    """
    
    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.resource_monitors: Dict[str, Callable] = {}
        
        # 执行器
        self.thread_executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        
        # 任务队列
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_concurrent_tasks)
        
        # 监控任务
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 初始化
        self._initialize_executors()
        self._register_default_monitors()
        
        if self.config.enable_monitoring:
            self._start_monitoring()
        
        logger.info("并发管理器初始化完成")
    
    def _initialize_executors(self):
        """初始化执行器"""
        try:
            # 线程池执行器
            self.thread_executor = ThreadPoolExecutor(
                max_workers=self.config.max_threads,
                thread_name_prefix="uagent_thread"
            )
            
            # 进程池执行器（仅在需要时创建）
            if self.config.max_processes > 0:
                self.process_executor = ProcessPoolExecutor(
                    max_workers=self.config.max_processes
                )
            
            logger.info(f"执行器初始化完成: 线程池({self.config.max_threads}), 进程池({self.config.max_processes})")
            
        except Exception as e:
            logger.error(f"执行器初始化失败: {e}")
            raise
    
    def _register_default_monitors(self):
        """注册默认资源监控器"""
        # CPU使用率监控
        self.register_resource_monitor(
            "cpu_usage",
            self._monitor_cpu_usage
        )
        
        # 内存使用率监控
        self.register_resource_monitor(
            "memory_usage",
            self._monitor_memory_usage
        )
        
        # 任务数量监控
        self.register_resource_monitor(
            "task_count",
            self._monitor_task_count
        )
    
    def register_resource_monitor(
        self,
        monitor_name: str,
        monitor_func: Callable
    ):
        """注册资源监控器"""
        try:
            if not callable(monitor_func):
                raise ValueError("monitor_func必须是可调用对象")
            
            self.resource_monitors[monitor_name] = monitor_func
            logger.info(f"资源监控器已注册: {monitor_name}")
            
        except Exception as e:
            logger.error(f"注册资源监控器失败: {e}")
            raise
    
    def unregister_resource_monitor(self, monitor_name: str):
        """注销资源监控器"""
        try:
            if monitor_name in self.resource_monitors:
                del self.resource_monitors[monitor_name]
                logger.info(f"资源监控器已注销: {monitor_name}")
            
        except Exception as e:
            logger.error(f"注销资源监控器失败: {e}")
            raise
    
    async def submit_task(
        self,
        name: str,
        task_func: Callable,
        task_type: str = "async",
        priority: int = 0,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交任务
        
        Args:
            name: 任务名称
            task_func: 任务函数
            task_type: 任务类型 ("async", "thread", "process")
            priority: 优先级 (数字越小优先级越高)
            timeout: 超时时间
            metadata: 元数据
            
        Returns:
            任务ID
        """
        try:
            # 检查资源限制
            if not await self._check_resource_limits():
                raise RuntimeError("系统资源不足，无法提交新任务")
            
            # 创建任务信息
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task_info = TaskInfo(
                task_id=task_id,
                name=name,
                type=task_type,
                status="pending",
                priority=priority,
                created_at=datetime.now(),
                resource_usage={},
                metadata=metadata or {}
            )
            
            # 存储任务信息
            self.active_tasks[task_id] = task_info
            
            # 记录到历史
            self.task_history.append({
                "task_id": task_id,
                "name": name,
                "type": task_type,
                "priority": priority,
                "created_at": task_info.created_at.isoformat(),
                "status": "submitted"
            })
            
            logger.info(f"任务已提交: {name} ({task_id})")
            
            # 根据任务类型执行
            if task_type == "async":
                asyncio.create_task(self._execute_async_task(task_id, task_func, timeout))
            elif task_type == "thread":
                asyncio.create_task(self._execute_thread_task(task_id, task_func, timeout))
            elif task_type == "process":
                asyncio.create_task(self._execute_process_task(task_id, task_func, timeout))
            else:
                raise ValueError(f"不支持的任务类型: {task_type}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            raise
    
    async def _execute_async_task(
        self,
        task_id: str,
        task_func: Callable,
        timeout: Optional[int]
    ):
        """执行异步任务"""
        try:
            if task_id not in self.active_tasks:
                return
            
            task_info = self.active_tasks[task_id]
            task_info.status = "running"
            task_info.started_at = datetime.now()
            
            logger.info(f"开始执行异步任务: {task_id}")
            
            # 执行任务
            if asyncio.iscoroutinefunction(task_func):
                if timeout:
                    result = await asyncio.wait_for(task_func(), timeout=timeout)
                else:
                    result = await task_func()
            else:
                # 如果是同步函数，在线程池中执行
                loop = asyncio.get_event_loop()
                if timeout:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(self.thread_executor, task_func),
                        timeout=timeout
                    )
                else:
                    result = await loop.run_in_executor(self.thread_executor, task_func)
            
            # 更新任务状态
            task_info.status = "completed"
            task_info.completed_at = datetime.now()
            
            # 更新历史记录
            for record in self.task_history:
                if record["task_id"] == task_id:
                    record["status"] = "completed"
                    record["completed_at"] = task_info.completed_at.isoformat()
                    break
            
            logger.info(f"异步任务执行完成: {task_id}")
            
        except asyncio.TimeoutError:
            logger.warning(f"异步任务超时: {task_id}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
        except Exception as e:
            logger.error(f"异步任务执行失败: {task_id}, 错误: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
    
    async def _execute_thread_task(
        self,
        task_id: str,
        task_func: Callable,
        timeout: Optional[int]
    ):
        """执行线程任务"""
        try:
            if task_id not in self.active_tasks:
                return
            
            task_info = self.active_tasks[task_id]
            task_info.status = "running"
            task_info.started_at = datetime.now()
            
            logger.info(f"开始执行线程任务: {task_id}")
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            if timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(self.thread_executor, task_func),
                    timeout=timeout
                )
            else:
                result = await loop.run_in_executor(self.thread_executor, task_func)
            
            # 更新任务状态
            task_info.status = "completed"
            task_info.completed_at = datetime.now()
            
            # 更新历史记录
            for record in self.task_history:
                if record["task_id"] == task_id:
                    record["status"] = "completed"
                    record["completed_at"] = task_info.completed_at.isoformat()
                    break
            
            logger.info(f"线程任务执行完成: {task_id}")
            
        except asyncio.TimeoutError:
            logger.warning(f"线程任务超时: {task_id}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
        except Exception as e:
            logger.error(f"线程任务执行失败: {task_id}, 错误: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
    
    async def _execute_process_task(
        self,
        task_id: str,
        task_func: Callable,
        timeout: Optional[int]
    ):
        """执行进程任务"""
        try:
            if task_id not in self.active_tasks:
                return
            
            if not self.process_executor:
                raise RuntimeError("进程执行器未初始化")
            
            task_info = self.active_tasks[task_id]
            task_info.status = "running"
            task_info.started_at = datetime.now()
            
            logger.info(f"开始执行进程任务: {task_id}")
            
            # 在进程池中执行
            loop = asyncio.get_event_loop()
            if timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(self.process_executor, task_func),
                    timeout=timeout
                )
            else:
                result = await loop.run_in_executor(self.process_executor, task_func)
            
            # 更新任务状态
            task_info.status = "completed"
            task_info.completed_at = datetime.now()
            
            # 更新历史记录
            for record in self.task_history:
                if record["task_id"] == task_id:
                    record["status"] = "completed"
                    record["completed_at"] = task_info.completed_at.isoformat()
                    break
            
            logger.info(f"进程任务执行完成: {task_id}")
            
        except asyncio.TimeoutError:
            logger.warning(f"进程任务超时: {task_id}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
        except Exception as e:
            logger.error(f"进程任务执行失败: {task_id}, 错误: {e}")
            if task_id in self.active_tasks:
                self.active_tasks[task_id].status = "failed"
    
    async def _check_resource_limits(self) -> bool:
        """检查资源限制"""
        try:
            # 检查任务数量限制
            if len(self.active_tasks) >= self.config.max_concurrent_tasks:
                logger.warning("达到最大并发任务数限制")
                return False
            
            # 检查系统资源
            if self.config.resource_limits:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                if cpu_percent > self.config.resource_limits.get("max_cpu_percent", 90):
                    logger.warning(f"CPU使用率过高: {cpu_percent}%")
                    return False
                
                if memory.percent > self.config.resource_limits.get("max_memory_percent", 90):
                    logger.warning(f"内存使用率过高: {memory.percent}%")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查资源限制失败: {e}")
            return False
    
    def _start_monitoring(self):
        """启动监控任务"""
        async def monitoring_loop():
            while True:
                try:
                    await self._collect_resource_metrics()
                    await asyncio.sleep(30)  # 每30秒收集一次
                except Exception as e:
                    logger.error(f"监控任务出错: {e}")
                    await asyncio.sleep(30)
        
        self.monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info("资源监控任务已启动")
    
    async def _collect_resource_metrics(self):
        """收集资源指标"""
        try:
            for monitor_name, monitor_func in self.resource_monitors.items():
                try:
                    if asyncio.iscoroutinefunction(monitor_func):
                        metric_value = await monitor_func()
                    else:
                        metric_value = monitor_func()
                    
                    # 更新任务资源使用情况
                    for task_info in self.active_tasks.values():
                        if task_info.status == "running":
                            task_info.resource_usage[monitor_name] = metric_value
                    
                except Exception as e:
                    logger.error(f"收集指标失败 {monitor_name}: {e}")
                    
        except Exception as e:
            logger.error(f"收集资源指标失败: {e}")
    
    def _monitor_cpu_usage(self) -> float:
        """监控CPU使用率"""
        return psutil.cpu_percent(interval=1)
    
    def _monitor_memory_usage(self) -> Dict[str, Any]:
        """监控内存使用率"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        }
    
    def _monitor_task_count(self) -> Dict[str, int]:
        """监控任务数量"""
        status_counts = {}
        for task_info in self.active_tasks.values():
            status = task_info.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return status_counts
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            if task_id not in self.active_tasks:
                return False
            
            task_info = self.active_tasks[task_id]
            if task_info.status in ["completed", "failed", "cancelled"]:
                return False
            
            task_info.status = "cancelled"
            task_info.completed_at = datetime.now()
            
            # 更新历史记录
            for record in self.task_history:
                if record["task_id"] == task_id:
                    record["status"] = "cancelled"
                    record["cancelled_at"] = task_info.completed_at.isoformat()
                    break
            
            logger.info(f"任务已取消: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    async def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.active_tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[TaskInfo]:
        """获取所有任务"""
        return list(self.active_tasks.values())
    
    async def get_tasks_by_status(self, status: str) -> List[TaskInfo]:
        """获取指定状态的任务"""
        return [
            task for task in self.active_tasks.values()
            if task.status == status
        ]
    
    async def get_tasks_by_type(self, task_type: str) -> List[TaskInfo]:
        """获取指定类型的任务"""
        return [
            task for task in self.active_tasks.values()
            if task.type == task_type
        ]
    
    async def get_resource_metrics(self) -> Dict[str, Any]:
        """获取资源指标"""
        try:
            metrics = {}
            
            for monitor_name, monitor_func in self.resource_monitors.items():
                try:
                    if asyncio.iscoroutinefunction(monitor_func):
                        metrics[monitor_name] = await monitor_func()
                    else:
                        metrics[monitor_name] = monitor_func()
                except Exception as e:
                    logger.error(f"获取指标失败 {monitor_name}: {e}")
                    metrics[monitor_name] = None
            
            return metrics
            
        except Exception as e:
            logger.error(f"获取资源指标失败: {e}")
            return {}
    
    async def get_concurrency_statistics(self) -> Dict[str, Any]:
        """获取并发统计信息"""
        total_tasks = len(self.active_tasks)
        total_history = len(self.task_history)
        
        # 按状态统计
        status_stats = {}
        for task in self.active_tasks.values():
            status = task.status
            status_stats[status] = status_stats.get(status, 0) + 1
        
        # 按类型统计
        type_stats = {}
        for task in self.active_tasks.values():
            task_type = task.type
            type_stats[task_type] = type_stats.get(task_type, 0) + 1
        
        # 按优先级统计
        priority_stats = {}
        for task in self.active_tasks.values():
            priority = task.priority
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
        
        return {
            "active_tasks": total_tasks,
            "total_history": total_history,
            "status_distribution": status_stats,
            "type_distribution": type_stats,
            "priority_distribution": priority_stats,
            "resource_monitors": len(self.resource_monitors),
            "max_concurrent_tasks": self.config.max_concurrent_tasks,
            "max_threads": self.config.max_threads,
            "max_processes": self.config.max_processes
        }
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            completed_tasks = []
            
            for task_id, task_info in self.active_tasks.items():
                if (task_info.status in ["completed", "failed", "cancelled"] and
                    task_info.completed_at and
                    task_info.completed_at < cutoff_time):
                    completed_tasks.append(task_id)
            
            for task_id in completed_tasks:
                del self.active_tasks[task_id]
            
            if completed_tasks:
                logger.info(f"清理了 {len(completed_tasks)} 个已完成的任务")
                
        except Exception as e:
            logger.error(f"清理已完成任务失败: {e}")
    
    async def shutdown(self):
        """关闭并发管理器"""
        try:
            # 停止监控任务
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭执行器
            if self.thread_executor:
                self.thread_executor.shutdown(wait=True)
            
            if self.process_executor:
                self.process_executor.shutdown(wait=True)
            
            # 取消所有活跃任务
            for task_id in list(self.active_tasks.keys()):
                await self.cancel_task(task_id)
            
            logger.info("并发管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭并发管理器失败: {e}")
            raise
