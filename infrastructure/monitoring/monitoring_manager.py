"""
Monitoring Manager

监控管理器 - 管理系统监控、指标收集和告警
"""

from typing import Dict, List, Any, Optional, Callable, Union
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import time
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    metrics_interval: int = 30  # 秒
    alert_check_interval: int = 60  # 秒
    retention_days: int = 30
    alert_channels: List[str] = None  # ["email", "webhook", "slack"]
    thresholds: Dict[str, Any] = None


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


@dataclass
class Alert:
    """告警数据"""
    alert_id: str
    name: str
    severity: str  # "info", "warning", "error", "critical"
    message: str
    metric_name: str
    threshold: Union[int, float]
    current_value: Union[int, float]
    timestamp: datetime
    status: str  # "active", "resolved", "acknowledged"
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


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.thresholds = config.thresholds or {}
        self.alert_handlers: Dict[str, Callable] = {}
        
        # 注册默认告警处理器
        self._register_default_handlers()
        
        logger.info("告警管理器初始化完成")
    
    def _register_default_handlers(self):
        """注册默认告警处理器"""
        # 日志告警处理器
        self.register_alert_handler(
            "log",
            self._log_alert
        )
        
        # 控制台告警处理器
        self.register_alert_handler(
            "console",
            self._console_alert
        )
    
    def register_alert_handler(
        self,
        handler_name: str,
        handler_func: Callable
    ):
        """注册告警处理器"""
        try:
            if not callable(handler_func):
                raise ValueError("handler_func必须是可调用对象")
            
            self.alert_handlers[handler_name] = handler_func
            logger.info(f"告警处理器已注册: {handler_name}")
            
        except Exception as e:
            logger.error(f"注册告警处理器失败: {e}")
            raise
    
    def unregister_alert_handler(self, handler_name: str):
        """注销告警处理器"""
        try:
            if handler_name in self.alert_handlers:
                del self.alert_handlers[handler_name]
                logger.info(f"告警处理器已注销: {handler_name}")
            
        except Exception as e:
            logger.error(f"注销告警处理器失败: {e}")
            raise
    
    async def check_alerts(self, metrics: List[Metric]):
        """检查告警"""
        try:
            for metric in metrics:
                await self._check_metric_alerts(metric)
                
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
    
    async def _check_metric_alerts(self, metric: Metric):
        """检查单个指标的告警"""
        try:
            metric_name = metric.name
            
            # 检查是否有对应的阈值配置
            if metric_name not in self.thresholds:
                return
            
            threshold_config = self.thresholds[metric_name]
            threshold_value = threshold_config.get("value")
            severity = threshold_config.get("severity", "warning")
            
            if threshold_value is None:
                return
            
            # 检查是否超过阈值
            should_alert = False
            if isinstance(metric.value, (int, float)) and isinstance(threshold_value, (int, float)):
                if metric.value > threshold_value:
                    should_alert = True
            
            if should_alert:
                await self._create_alert(metric, threshold_value, severity)
                
        except Exception as e:
            logger.error(f"检查指标告警失败: {e}")
    
    async def _create_alert(
        self,
        metric: Metric,
        threshold: Union[int, float],
        severity: str
    ):
        """创建告警"""
        try:
            # 检查是否已存在相同告警
            alert_key = f"{metric.name}_{metric.tags.get('device', 'default')}"
            
            if alert_key in self.active_alerts:
                # 更新现有告警
                alert = self.active_alerts[alert_key]
                alert.current_value = metric.value
                alert.timestamp = datetime.now()
                return
            
            # 创建新告警
            alert_id = f"alert_{int(time.time())}"
            
            alert = Alert(
                alert_id=alert_id,
                name=f"{metric.name} 告警",
                severity=severity,
                message=f"{metric.name} 超过阈值: {metric.value} {metric.unit} > {threshold} {metric.unit}",
                metric_name=metric.name,
                threshold=threshold,
                current_value=metric.value,
                timestamp=datetime.now(),
                status="active",
                metadata={
                    "metric_tags": metric.tags,
                    "metric_unit": metric.unit
                }
            )
            
            # 存储告警
            self.active_alerts[alert_key] = alert
            
            # 记录到历史
            self.alert_history.append({
                "alert_id": alert_id,
                "name": alert.name,
                "severity": severity,
                "timestamp": alert.timestamp.isoformat(),
                "status": "created"
            })
            
            # 触发告警处理器
            await self._trigger_alert_handlers(alert)
            
            logger.warning(f"告警已创建: {alert.name} ({severity})")
            
        except Exception as e:
            logger.error(f"创建告警失败: {e}")
    
    async def _trigger_alert_handlers(self, alert: Alert):
        """触发告警处理器"""
        try:
            for handler_name, handler_func in self.alert_handlers.items():
                try:
                    if asyncio.iscoroutinefunction(handler_func):
                        await handler_func(alert)
                    else:
                        handler_func(alert)
                        
                except Exception as e:
                    logger.error(f"告警处理器 {handler_name} 执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"触发告警处理器失败: {e}")
    
    def _log_alert(self, alert: Alert):
        """日志告警处理器"""
        logger.warning(f"告警: {alert.name} - {alert.message} (严重性: {alert.severity})")
    
    def _console_alert(self, alert: Alert):
        """控制台告警处理器"""
        print(f"\n🚨 告警: {alert.name}")
        print(f"   消息: {alert.message}")
        print(f"   严重性: {alert.severity}")
        print(f"   时间: {alert.timestamp}")
        print()
    
    async def resolve_alert(self, alert_key: str, resolution_message: str = ""):
        """解决告警"""
        try:
            if alert_key not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_key]
            alert.status = "resolved"
            
            # 更新历史记录
            for record in self.alert_history:
                if record["alert_id"] == alert.alert_id:
                    record["status"] = "resolved"
                    record["resolved_at"] = datetime.now().isoformat()
                    record["resolution_message"] = resolution_message
                    break
            
            # 从活跃告警中移除
            del self.active_alerts[alert_key]
            
            logger.info(f"告警已解决: {alert.name}")
            return True
            
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False
    
    async def acknowledge_alert(self, alert_key: str, ack_message: str = ""):
        """确认告警"""
        try:
            if alert_key not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_key]
            alert.status = "acknowledged"
            
            # 更新历史记录
            for record in self.alert_history:
                if record["alert_id"] == alert.alert_id:
                    record["status"] = "acknowledged"
                    record["acknowledged_at"] = datetime.now().isoformat()
                    record["ack_message"] = ack_message
                    break
            
            logger.info(f"告警已确认: {alert.name}")
            return True
            
        except Exception as e:
            logger.error(f"确认告警失败: {e}")
            return False
    
    async def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    async def get_alert_history(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取告警历史"""
        filtered_history = self.alert_history
        
        if severity:
            filtered_history = [h for h in filtered_history if h["severity"] == severity]
        
        if status:
            filtered_history = [h for h in filtered_history if h["status"] == status]
        
        # 按时间排序
        filtered_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return filtered_history[:limit]
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        resolved_alerts = len([h for h in self.alert_history if h["status"] == "resolved"])
        
        # 按严重性统计
        severity_stats = {}
        for alert in self.active_alerts.values():
            severity = alert.severity
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
        
        # 按状态统计
        status_stats = {}
        for record in self.alert_history:
            status = record["status"]
            status_stats[status] = status_stats.get(status, 0) + 1
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "resolved_alerts": resolved_alerts,
            "severity_distribution": severity_stats,
            "status_distribution": status_stats
        }


class MonitoringManager:
    """
    监控管理器
    
    管理系统监控、指标收集和告警
    """
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.metrics_collectors: List[MetricsCollector] = []
        self.alert_manager: Optional[AlertManager] = None
        self.metrics_history: List[Metric] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # 初始化组件
        self._initialize_components()
        
        # 启动监控任务
        if config.enabled:
            self._start_monitoring()
        
        logger.info("监控管理器初始化完成")
    
    def _initialize_components(self):
        """初始化监控组件"""
        try:
            # 添加系统指标收集器
            self.metrics_collectors.append(SystemMetricsCollector())
            
            # 初始化告警管理器
            self.alert_manager = AlertManager(self.config)
            
            logger.info("监控组件初始化完成")
            
        except Exception as e:
            logger.error(f"初始化监控组件失败: {e}")
            raise
    
    def add_metrics_collector(self, collector: MetricsCollector):
        """添加指标收集器"""
        try:
            if not isinstance(collector, MetricsCollector):
                raise ValueError("collector必须是MetricsCollector的实例")
            
            self.metrics_collectors.append(collector)
            logger.info("指标收集器已添加")
            
        except Exception as e:
            logger.error(f"添加指标收集器失败: {e}")
            raise
    
    def remove_metrics_collector(self, collector: MetricsCollector):
        """移除指标收集器"""
        try:
            if collector in self.metrics_collectors:
                self.metrics_collectors.remove(collector)
                logger.info("指标收集器已移除")
            
        except Exception as e:
            logger.error(f"移除指标收集器失败: {e}")
            raise
    
    def _start_monitoring(self):
        """启动监控任务"""
        async def monitoring_loop():
            while True:
                try:
                    await self._collect_and_check_metrics()
                    await asyncio.sleep(self.config.metrics_interval)
                except Exception as e:
                    logger.error(f"监控任务出错: {e}")
                    await asyncio.sleep(self.config.metrics_interval)
        
        self.monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info("监控任务已启动")
    
    async def _collect_and_check_metrics(self):
        """收集和检查指标"""
        try:
            # 收集指标
            all_metrics = []
            for collector in self.metrics_collectors:
                try:
                    metrics = await collector.collect_metrics()
                    all_metrics.extend(metrics)
                except Exception as e:
                    logger.error(f"收集器 {collector.__class__.__name__} 失败: {e}")
            
            # 存储指标
            self.metrics_history.extend(all_metrics)
            
            # 清理过期指标
            await self._cleanup_old_metrics()
            
            # 检查告警
            if self.alert_manager:
                await self.alert_manager.check_alerts(all_metrics)
            
            logger.info(f"收集了 {len(all_metrics)} 个指标")
            
        except Exception as e:
            logger.error(f"收集和检查指标失败: {e}")
    
    async def _cleanup_old_metrics(self):
        """清理过期指标"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.config.retention_days)
            
            # 过滤掉过期指标
            self.metrics_history = [
                metric for metric in self.metrics_history
                if metric.timestamp > cutoff_time
            ]
            
            logger.info(f"清理过期指标完成，当前保留 {len(self.metrics_history)} 个指标")
            
        except Exception as e:
            logger.error(f"清理过期指标失败: {e}")
    
    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        time_range: Optional[timedelta] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """获取指标"""
        try:
            filtered_metrics = self.metrics_history
            
            # 按名称过滤
            if metric_name:
                filtered_metrics = [m for m in filtered_metrics if m.name == metric_name]
            
            # 按标签过滤
            if tags:
                for key, value in tags.items():
                    filtered_metrics = [m for m in filtered_metrics if m.tags.get(key) == value]
            
            # 按时间范围过滤
            if time_range:
                cutoff_time = datetime.now() - time_range
                filtered_metrics = [m for m in filtered_metrics if m.timestamp > cutoff_time]
            
            # 按时间排序并限制数量
            filtered_metrics.sort(key=lambda x: x.timestamp, reverse=True)
            
            return filtered_metrics[:limit]
            
        except Exception as e:
            logger.error(f"获取指标失败: {e}")
            return []
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            if not self.metrics_history:
                return {"message": "暂无指标数据"}
            
            # 按名称分组
            metrics_by_name = {}
            for metric in self.metrics_history:
                if metric.name not in metrics_by_name:
                    metrics_by_name[metric.name] = []
                metrics_by_name[metric.name].append(metric)
            
            # 计算统计信息
            summary = {}
            for name, metrics in metrics_by_name.items():
                if not metrics:
                    continue
                
                values = [m.value for m in metrics if isinstance(m.value, (int, float))]
                if values:
                    summary[name] = {
                        "count": len(metrics),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "latest": metrics[-1].value,
                        "latest_timestamp": metrics[-1].timestamp.isoformat()
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取指标摘要失败: {e}")
            return {}
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        try:
            status = {
                "enabled": self.config.enabled,
                "metrics_interval": self.config.metrics_interval,
                "alert_check_interval": self.config.alert_check_interval,
                "collectors_count": len(self.metrics_collectors),
                "metrics_history_count": len(self.metrics_history),
                "retention_days": self.config.retention_days
            }
            
            # 添加告警状态
            if self.alert_manager:
                alert_stats = await self.alert_manager.get_alert_statistics()
                status["alerts"] = alert_stats
            
            return status
            
        except Exception as e:
            logger.error(f"获取监控状态失败: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """关闭监控管理器"""
        try:
            # 停止监控任务
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("监控管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭监控管理器失败: {e}")
            raise
