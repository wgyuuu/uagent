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
from .metrics_collector import MetricsCollector, SystemMetricsCollector, Metric
from .alert_manager import AlertManager

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
