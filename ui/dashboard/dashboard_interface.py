"""
Dashboard Interface

仪表板界面 - 提供系统监控和管理功能
"""

from typing import Dict, List, Any, Optional, Callable
import structlog
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = structlog.get_logger(__name__)


class WidgetType(Enum):
    """仪表板组件类型"""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    STATUS = "status"
    LOG = "log"
    WORKFLOW = "workflow"


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    GAUGE = "gauge"


@dataclass
class DashboardWidget:
    """仪表板组件"""
    widget_id: str
    title: str
    widget_type: WidgetType
    config: Dict[str, Any]
    data: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: int = 30  # 秒
    last_updated: Optional[datetime] = None
    is_visible: bool = True


@dataclass
class Dashboard:
    """仪表板"""
    dashboard_id: str
    name: str
    description: str
    user_id: str
    widgets: List[DashboardWidget]
    created_at: datetime
    updated_at: datetime
    is_default: bool = False
    layout_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.layout_config is None:
            self.layout_config = {"cols": 12, "rows": 24}


class DashboardInterface:
    """
    仪表板界面
    
    提供系统监控、数据可视化和管理功能
    """
    
    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.widget_data_providers: Dict[str, Callable] = {}
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        
        # 初始化默认仪表板
        self._initialize_default_dashboards()
        
        logger.info("仪表板界面初始化完成")
    
    def _initialize_default_dashboards(self):
        """初始化默认仪表板"""
        try:
            # 系统概览仪表板
            system_dashboard = self._create_system_overview_dashboard()
            self.dashboards[system_dashboard.dashboard_id] = system_dashboard
            
            # 工作流监控仪表板
            workflow_dashboard = self._create_workflow_monitoring_dashboard()
            self.dashboards[workflow_dashboard.dashboard_id] = workflow_dashboard
            
            # 性能监控仪表板
            performance_dashboard = self._create_performance_monitoring_dashboard()
            self.dashboards[performance_dashboard.dashboard_id] = performance_dashboard
            
            logger.info("默认仪表板已创建")
            
        except Exception as e:
            logger.error(f"初始化默认仪表板失败: {e}")
    
    def _create_system_overview_dashboard(self) -> Dashboard:
        """创建系统概览仪表板"""
        widgets = [
            # 系统状态组件
            DashboardWidget(
                widget_id="system_status",
                title="系统状态",
                widget_type=WidgetType.STATUS,
                config={
                    "items": ["cpu", "memory", "disk", "network"]
                },
                data={},
                position={"x": 0, "y": 0, "width": 3, "height": 4}
            ),
            
            # 活跃用户数
            DashboardWidget(
                widget_id="active_users",
                title="活跃用户",
                widget_type=WidgetType.METRIC,
                config={
                    "unit": "人",
                    "format": "number"
                },
                data={"value": 0},
                position={"x": 3, "y": 0, "width": 3, "height": 2}
            ),
            
            # 任务执行统计
            DashboardWidget(
                widget_id="task_statistics",
                title="任务执行统计",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.PIE.value,
                    "categories": ["成功", "失败", "进行中", "等待中"]
                },
                data={},
                position={"x": 6, "y": 0, "width": 6, "height": 4}
            ),
            
            # 工作流执行趋势
            DashboardWidget(
                widget_id="workflow_trend",
                title="工作流执行趋势",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.LINE.value,
                    "time_range": "24h"
                },
                data={},
                position={"x": 0, "y": 4, "width": 12, "height": 4}
            ),
            
            # 最近活动日志
            DashboardWidget(
                widget_id="recent_activities",
                title="最近活动",
                widget_type=WidgetType.LOG,
                config={
                    "max_entries": 10,
                    "auto_refresh": True
                },
                data={"logs": []},
                position={"x": 0, "y": 8, "width": 12, "height": 4}
            )
        ]
        
        return Dashboard(
            dashboard_id="system_overview",
            name="系统概览",
            description="系统整体状态和活动概览",
            user_id="system",
            widgets=widgets,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_default=True
        )
    
    def _create_workflow_monitoring_dashboard(self) -> Dashboard:
        """创建工作流监控仪表板"""
        widgets = [
            # 当前运行的工作流
            DashboardWidget(
                widget_id="running_workflows",
                title="运行中的工作流",
                widget_type=WidgetType.TABLE,
                config={
                    "columns": ["工作流ID", "状态", "进度", "开始时间", "预计完成时间"]
                },
                data={"rows": []},
                position={"x": 0, "y": 0, "width": 12, "height": 6}
            ),
            
            # 工作流成功率
            DashboardWidget(
                widget_id="workflow_success_rate",
                title="工作流成功率",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.GAUGE.value,
                    "max_value": 100,
                    "unit": "%"
                },
                data={"value": 0},
                position={"x": 0, "y": 6, "width": 4, "height": 4}
            ),
            
            # 平均执行时间
            DashboardWidget(
                widget_id="avg_execution_time",
                title="平均执行时间",
                widget_type=WidgetType.METRIC,
                config={
                    "unit": "分钟",
                    "format": "time"
                },
                data={"value": 0},
                position={"x": 4, "y": 6, "width": 4, "height": 2}
            ),
            
            # 今日执行次数
            DashboardWidget(
                widget_id="daily_executions",
                title="今日执行次数",
                widget_type=WidgetType.METRIC,
                config={
                    "unit": "次",
                    "format": "number"
                },
                data={"value": 0},
                position={"x": 8, "y": 6, "width": 4, "height": 2}
            ),
            
            # 错误率趋势
            DashboardWidget(
                widget_id="error_rate_trend",
                title="错误率趋势",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.AREA.value,
                    "time_range": "7d"
                },
                data={},
                position={"x": 4, "y": 8, "width": 8, "height": 4}
            )
        ]
        
        return Dashboard(
            dashboard_id="workflow_monitoring",
            name="工作流监控",
            description="工作流执行状态和性能监控",
            user_id="system",
            widgets=widgets,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_default=True
        )
    
    def _create_performance_monitoring_dashboard(self) -> Dashboard:
        """创建性能监控仪表板"""
        widgets = [
            # CPU使用率
            DashboardWidget(
                widget_id="cpu_usage",
                title="CPU使用率",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.LINE.value,
                    "time_range": "1h",
                    "unit": "%"
                },
                data={},
                position={"x": 0, "y": 0, "width": 6, "height": 4}
            ),
            
            # 内存使用率
            DashboardWidget(
                widget_id="memory_usage",
                title="内存使用率",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.LINE.value,
                    "time_range": "1h",
                    "unit": "%"
                },
                data={},
                position={"x": 6, "y": 0, "width": 6, "height": 4}
            ),
            
            # 磁盘使用情况
            DashboardWidget(
                widget_id="disk_usage",
                title="磁盘使用情况",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.BAR.value
                },
                data={},
                position={"x": 0, "y": 4, "width": 6, "height": 4}
            ),
            
            # 网络流量
            DashboardWidget(
                widget_id="network_traffic",
                title="网络流量",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.AREA.value,
                    "time_range": "1h",
                    "unit": "MB/s"
                },
                data={},
                position={"x": 6, "y": 4, "width": 6, "height": 4}
            ),
            
            # 响应时间分布
            DashboardWidget(
                widget_id="response_time_distribution",
                title="响应时间分布",
                widget_type=WidgetType.CHART,
                config={
                    "chart_type": ChartType.BAR.value,
                    "unit": "ms"
                },
                data={},
                position={"x": 0, "y": 8, "width": 12, "height": 4}
            )
        ]
        
        return Dashboard(
            dashboard_id="performance_monitoring",
            name="性能监控",
            description="系统性能指标监控",
            user_id="system",
            widgets=widgets,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_default=True
        )
    
    async def create_dashboard(
        self,
        name: str,
        description: str,
        user_id: str,
        widgets: Optional[List[DashboardWidget]] = None
    ) -> Dashboard:
        """创建仪表板"""
        try:
            dashboard_id = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            dashboard = Dashboard(
                dashboard_id=dashboard_id,
                name=name,
                description=description,
                user_id=user_id,
                widgets=widgets or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.dashboards[dashboard_id] = dashboard
            
            logger.info(f"仪表板已创建: {dashboard_id}")
            return dashboard
            
        except Exception as e:
            logger.error(f"创建仪表板失败: {e}")
            raise
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """获取仪表板"""
        return self.dashboards.get(dashboard_id)
    
    async def get_user_dashboards(self, user_id: str) -> List[Dashboard]:
        """获取用户的仪表板"""
        return [
            dashboard for dashboard in self.dashboards.values()
            if dashboard.user_id == user_id or dashboard.is_default
        ]
    
    async def update_dashboard(
        self,
        dashboard_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        widgets: Optional[List[DashboardWidget]] = None,
        layout_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新仪表板"""
        try:
            if dashboard_id not in self.dashboards:
                return False
            
            dashboard = self.dashboards[dashboard_id]
            
            if name is not None:
                dashboard.name = name
            if description is not None:
                dashboard.description = description
            if widgets is not None:
                dashboard.widgets = widgets
            if layout_config is not None:
                dashboard.layout_config = layout_config
            
            dashboard.updated_at = datetime.now()
            
            logger.info(f"仪表板已更新: {dashboard_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新仪表板失败: {e}")
            return False
    
    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """删除仪表板"""
        try:
            if dashboard_id in self.dashboards:
                # 停止相关的刷新任务
                await self._stop_dashboard_refresh_tasks(dashboard_id)
                
                del self.dashboards[dashboard_id]
                logger.info(f"仪表板已删除: {dashboard_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除仪表板失败: {e}")
            return False
    
    async def add_widget(
        self,
        dashboard_id: str,
        widget: DashboardWidget
    ) -> bool:
        """添加组件"""
        try:
            if dashboard_id not in self.dashboards:
                return False
            
            dashboard = self.dashboards[dashboard_id]
            dashboard.widgets.append(widget)
            dashboard.updated_at = datetime.now()
            
            # 启动组件数据刷新
            await self._start_widget_refresh(dashboard_id, widget.widget_id)
            
            logger.info(f"组件已添加: {widget.widget_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加组件失败: {e}")
            return False
    
    async def remove_widget(
        self,
        dashboard_id: str,
        widget_id: str
    ) -> bool:
        """移除组件"""
        try:
            if dashboard_id not in self.dashboards:
                return False
            
            dashboard = self.dashboards[dashboard_id]
            dashboard.widgets = [
                w for w in dashboard.widgets 
                if w.widget_id != widget_id
            ]
            dashboard.updated_at = datetime.now()
            
            # 停止组件数据刷新
            await self._stop_widget_refresh(dashboard_id, widget_id)
            
            logger.info(f"组件已移除: {widget_id}")
            return True
            
        except Exception as e:
            logger.error(f"移除组件失败: {e}")
            return False
    
    async def update_widget_data(
        self,
        dashboard_id: str,
        widget_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """更新组件数据"""
        try:
            if dashboard_id not in self.dashboards:
                return False
            
            dashboard = self.dashboards[dashboard_id]
            
            for widget in dashboard.widgets:
                if widget.widget_id == widget_id:
                    widget.data = data
                    widget.last_updated = datetime.now()
                    
                    # 通知订阅者
                    await self._notify_subscribers(dashboard_id, widget_id, data)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"更新组件数据失败: {e}")
            return False
    
    def register_data_provider(
        self,
        widget_type: str,
        provider: Callable
    ):
        """注册数据提供者"""
        self.widget_data_providers[widget_type] = provider
        logger.info(f"数据提供者已注册: {widget_type}")
    
    async def subscribe_to_updates(
        self,
        dashboard_id: str,
        callback: Callable
    ):
        """订阅更新"""
        if dashboard_id not in self.subscribers:
            self.subscribers[dashboard_id] = []
        
        self.subscribers[dashboard_id].append(callback)
        logger.info(f"已订阅仪表板更新: {dashboard_id}")
    
    async def _start_widget_refresh(self, dashboard_id: str, widget_id: str):
        """启动组件数据刷新"""
        try:
            task_key = f"{dashboard_id}:{widget_id}"
            
            if task_key in self.refresh_tasks:
                self.refresh_tasks[task_key].cancel()
            
            async def refresh_loop():
                while True:
                    try:
                        dashboard = self.dashboards.get(dashboard_id)
                        if not dashboard:
                            break
                        
                        widget = None
                        for w in dashboard.widgets:
                            if w.widget_id == widget_id:
                                widget = w
                                break
                        
                        if not widget:
                            break
                        
                        # 获取数据提供者
                        provider_key = widget.widget_type.value
                        if provider_key in self.widget_data_providers:
                            provider = self.widget_data_providers[provider_key]
                            new_data = await provider(widget.config)
                            await self.update_widget_data(dashboard_id, widget_id, new_data)
                        
                        await asyncio.sleep(widget.refresh_interval)
                        
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"组件数据刷新出错: {e}")
                        await asyncio.sleep(30)
            
            task = asyncio.create_task(refresh_loop())
            self.refresh_tasks[task_key] = task
            
        except Exception as e:
            logger.error(f"启动组件刷新失败: {e}")
    
    async def _stop_widget_refresh(self, dashboard_id: str, widget_id: str):
        """停止组件数据刷新"""
        task_key = f"{dashboard_id}:{widget_id}"
        
        if task_key in self.refresh_tasks:
            self.refresh_tasks[task_key].cancel()
            del self.refresh_tasks[task_key]
    
    async def _stop_dashboard_refresh_tasks(self, dashboard_id: str):
        """停止仪表板的所有刷新任务"""
        tasks_to_remove = []
        
        for task_key in self.refresh_tasks:
            if task_key.startswith(f"{dashboard_id}:"):
                self.refresh_tasks[task_key].cancel()
                tasks_to_remove.append(task_key)
        
        for task_key in tasks_to_remove:
            del self.refresh_tasks[task_key]
    
    async def _notify_subscribers(
        self,
        dashboard_id: str,
        widget_id: str,
        data: Dict[str, Any]
    ):
        """通知订阅者"""
        try:
            if dashboard_id in self.subscribers:
                for callback in self.subscribers[dashboard_id]:
                    await callback(widget_id, data)
                    
        except Exception as e:
            logger.error(f"通知订阅者失败: {e}")
    
    async def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """获取仪表板完整数据"""
        try:
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return None
            
            return {
                "dashboard": asdict(dashboard),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取仪表板数据失败: {e}")
            return None
    
    async def export_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """导出仪表板配置"""
        try:
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return None
            
            return {
                "dashboard_config": asdict(dashboard),
                "export_time": datetime.now().isoformat(),
                "version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"导出仪表板失败: {e}")
            return None
    
    async def import_dashboard(
        self,
        config_data: Dict[str, Any],
        user_id: str
    ) -> Optional[str]:
        """导入仪表板配置"""
        try:
            dashboard_config = config_data["dashboard_config"]
            
            # 生成新的ID
            new_dashboard_id = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            dashboard_config["dashboard_id"] = new_dashboard_id
            dashboard_config["user_id"] = user_id
            dashboard_config["created_at"] = datetime.now()
            dashboard_config["updated_at"] = datetime.now()
            
            # 重新创建组件对象
            widgets = []
            for widget_dict in dashboard_config.get("widgets", []):
                widget = DashboardWidget(**widget_dict)
                widgets.append(widget)
            
            dashboard_config["widgets"] = widgets
            dashboard = Dashboard(**dashboard_config)
            
            self.dashboards[new_dashboard_id] = dashboard
            
            logger.info(f"仪表板已导入: {new_dashboard_id}")
            return new_dashboard_id
            
        except Exception as e:
            logger.error(f"导入仪表板失败: {e}")
            return None
    
    async def get_dashboard_statistics(self) -> Dict[str, Any]:
        """获取仪表板统计信息"""
        total_dashboards = len(self.dashboards)
        default_dashboards = len([d for d in self.dashboards.values() if d.is_default])
        custom_dashboards = total_dashboards - default_dashboards
        total_widgets = sum(len(d.widgets) for d in self.dashboards.values())
        active_refresh_tasks = len(self.refresh_tasks)
        
        # 按类型统计组件
        widget_type_stats = {}
        for dashboard in self.dashboards.values():
            for widget in dashboard.widgets:
                widget_type = widget.widget_type.value
                widget_type_stats[widget_type] = widget_type_stats.get(widget_type, 0) + 1
        
        return {
            "total_dashboards": total_dashboards,
            "default_dashboards": default_dashboards,
            "custom_dashboards": custom_dashboards,
            "total_widgets": total_widgets,
            "active_refresh_tasks": active_refresh_tasks,
            "widget_type_distribution": widget_type_stats,
            "total_subscribers": sum(len(subs) for subs in self.subscribers.values())
        }
