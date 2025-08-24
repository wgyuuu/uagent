from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import time
from typing import List, Dict, Any, Union


import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Metric:
    """指标数据"""
    metric_id: str
    name: str
    value: Union[int, float, str]
    unit: str
    timestamp: datetime
    tags: Dict[str, str]
    metadata: Dict[str, Any]

class MetricsCollector(ABC):
    """指标收集器抽象类"""
    
    @abstractmethod
    async def collect_metrics(self) -> List[Metric]:
        """收集指标"""
        pass


class SystemMetricsCollector(MetricsCollector):
    """系统指标收集器"""
    
    def __init__(self):
        self.collectors = {
            "cpu": self._collect_cpu_metrics,
            "memory": self._collect_memory_metrics,
            "disk": self._collect_disk_metrics,
            "network": self._collect_network_metrics
        }
    
    async def collect_metrics(self) -> List[Metric]:
        """收集系统指标"""
        try:
            metrics = []
            
            for collector_name, collector_func in self.collectors.items():
                try:
                    collector_metrics = await collector_func()
                    metrics.extend(collector_metrics)
                except Exception as e:
                    logger.error(f"收集 {collector_name} 指标失败: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return []
    
    async def _collect_cpu_metrics(self) -> List[Metric]:
        """收集CPU指标"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            metrics = [
                Metric(
                    metric_id=f"cpu_usage_{int(time.time())}",
                    name="cpu_usage",
                    value=cpu_percent,
                    unit="percent",
                    timestamp=datetime.now(),
                    tags={"type": "cpu", "metric": "usage"},
                    metadata={"cpu_count": cpu_count}
                )
            ]
            
            if cpu_freq:
                metrics.append(Metric(
                    metric_id=f"cpu_freq_{int(time.time())}",
                    name="cpu_frequency",
                    value=cpu_freq.current,
                    unit="MHz",
                    timestamp=datetime.now(),
                    tags={"type": "cpu", "metric": "frequency"},
                    metadata={"cpu_count": cpu_count}
                ))
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集CPU指标失败: {e}")
            return []
    
    async def _collect_memory_metrics(self) -> List[Metric]:
        """收集内存指标"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics = [
                Metric(
                    metric_id=f"memory_usage_{int(time.time())}",
                    name="memory_usage",
                    value=memory.percent,
                    unit="percent",
                    timestamp=datetime.now(),
                    tags={"type": "memory", "metric": "usage"},
                    metadata={"total": memory.total, "available": memory.available}
                ),
                Metric(
                    metric_id=f"swap_usage_{int(time.time())}",
                    name="swap_usage",
                    value=swap.percent,
                    unit="percent",
                    timestamp=datetime.now(),
                    tags={"type": "memory", "metric": "swap"},
                    metadata={"total": swap.total, "used": swap.used}
                )
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集内存指标失败: {e}")
            return []
    
    async def _collect_disk_metrics(self) -> List[Metric]:
        """收集磁盘指标"""
        try:
            import psutil
            
            metrics = []
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    metrics.append(Metric(
                        metric_id=f"disk_usage_{partition.device}_{int(time.time())}",
                        name="disk_usage",
                        value=usage.percent,
                        unit="percent",
                        timestamp=datetime.now(),
                        tags={"type": "disk", "device": partition.device, "mountpoint": partition.mountpoint},
                        metadata={"total": usage.total, "free": usage.free}
                    ))
                    
                except Exception as e:
                    logger.warning(f"收集分区 {partition.device} 指标失败: {e}")
                    continue
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集磁盘指标失败: {e}")
            return []
    
    async def _collect_network_metrics(self) -> List[Metric]:
        """收集网络指标"""
        try:
            import psutil
            
            network_io = psutil.net_io_counters()
            
            metrics = [
                Metric(
                    metric_id=f"network_bytes_sent_{int(time.time())}",
                    name="network_bytes_sent",
                    value=network_io.bytes_sent,
                    unit="bytes",
                    timestamp=datetime.now(),
                    tags={"type": "network", "metric": "bytes_sent"},
                    metadata={}
                ),
                Metric(
                    metric_id=f"network_bytes_recv_{int(time.time())}",
                    name="network_bytes_recv",
                    value=network_io.bytes_recv,
                    unit="bytes",
                    timestamp=datetime.now(),
                    tags={"type": "network", "metric": "bytes_recv"},
                    metadata={}
                )
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集网络指标失败: {e}")
            return []
