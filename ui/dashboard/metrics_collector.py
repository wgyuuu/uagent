"""
Metrics Collector

指标收集器 - 收集系统和应用性能指标
"""

from typing import Dict, List, Any, Optional
import structlog
import asyncio
import psutil
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    指标收集器
    
    收集系统性能指标、应用指标和业务指标
    """
    
    def __init__(self):
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {}
        self.collection_interval = 30  # 秒
        self.max_history_size = 1000
        self.running = False
        
        logger.info("指标收集器初始化完成")
    
    async def start_collection(self):
        """开始收集指标"""
        self.running = True
        asyncio.create_task(self._collection_loop())
        logger.info("指标收集已启动")
    
    async def stop_collection(self):
        """停止收集指标"""
        self.running = False
        logger.info("指标收集已停止")
    
    async def _collection_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"收集指标失败: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": disk.percent,
                "disk_total": disk.total,
                "disk_free": disk.free
            }
            
            self._store_metrics("system", metrics)
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    async def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 这里可以收集应用特定的指标
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "active_workflows": 0,  # 从工作流监控器获取
                "active_sessions": 0,   # 从会话管理器获取
                "api_requests": 0,      # 从API统计获取
                "errors_count": 0       # 从错误统计获取
            }
            
            self._store_metrics("application", metrics)
            
        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")
    
    def _store_metrics(self, metric_type: str, metrics: Dict[str, Any]):
        """存储指标"""
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []
        
        self.metrics_history[metric_type].append(metrics)
        
        # 限制历史记录大小
        if len(self.metrics_history[metric_type]) > self.max_history_size:
            self.metrics_history[metric_type] = self.metrics_history[metric_type][-self.max_history_size:]
    
    async def get_latest_metrics(self, metric_type: str) -> Optional[Dict[str, Any]]:
        """获取最新指标"""
        if metric_type in self.metrics_history and self.metrics_history[metric_type]:
            return self.metrics_history[metric_type][-1]
        return None
    
    async def get_metrics_history(
        self,
        metric_type: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if metric_type not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_metrics = []
        for metric in self.metrics_history[metric_type]:
            metric_time = datetime.fromisoformat(metric["timestamp"])
            if metric_time >= cutoff_time:
                filtered_metrics.append(metric)
        
        return filtered_metrics
    
    async def get_aggregated_metrics(
        self,
        metric_type: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """获取聚合指标"""
        history = await self.get_metrics_history(metric_type, hours)
        
        if not history:
            return {}
        
        # 计算平均值、最大值、最小值
        numeric_fields = []
        for metric in history:
            for key, value in metric.items():
                if isinstance(value, (int, float)) and key != "timestamp":
                    numeric_fields.append(key)
        
        numeric_fields = list(set(numeric_fields))
        
        aggregated = {}
        for field in numeric_fields:
            values = [metric[field] for metric in history if field in metric]
            if values:
                aggregated[f"{field}_avg"] = sum(values) / len(values)
                aggregated[f"{field}_max"] = max(values)
                aggregated[f"{field}_min"] = min(values)
        
        return aggregated
