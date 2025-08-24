import asyncio
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Dict, Any, List, Optional, Union, Callable
from .monitoring_manager import Metric, MonitoringConfig
import structlog


logger = structlog.get_logger(__name__)


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
