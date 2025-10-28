"""
监控仪表盘模块
提供监控数据可视化和仪表盘功能
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import threading

from .logger import get_logger
from .metrics_collector import get_global_metrics_manager, MetricType
from .alerting import get_global_alert_manager
from .health_check import get_global_health_checker, HealthStatus

logger = get_logger(__name__)


class WidgetType(Enum):
    """组件类型"""
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    GAUGE = "gauge"
    COUNTER = "counter"
    ALERT = "alert"
    HEALTH = "health"
    LOG = "log"


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"


@dataclass
class DashboardWidget:
    """仪表盘组件"""
    id: str
    title: str
    type: WidgetType
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=dict)  # x, y, width, height
    refresh_interval: int = 30  # 刷新间隔（秒）
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "config": self.config,
            "position": self.position,
            "refresh_interval": self.refresh_interval,
            "enabled": self.enabled
        }


@dataclass
class Dashboard:
    """仪表盘"""
    id: str
    name: str
    description: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_widget(self, widget: DashboardWidget) -> None:
        """添加组件"""
        self.widgets.append(widget)
        self.updated_at = datetime.now()
    
    def remove_widget(self, widget_id: str) -> bool:
        """移除组件"""
        for i, widget in enumerate(self.widgets):
            if widget.id == widget_id:
                del self.widgets[i]
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_widget(self, widget_id: str) -> Optional[DashboardWidget]:
        """获取组件"""
        for widget in self.widgets:
            if widget.id == widget_id:
                return widget
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "widgets": [widget.to_dict() for widget in self.widgets],
            "layout": self.layout,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class WidgetDataProvider(ABC):
    """组件数据提供者抽象基类"""
    
    @abstractmethod
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取组件数据"""
        pass


class MetricWidgetDataProvider(WidgetDataProvider):
    """指标组件数据提供者"""
    
    def __init__(self):
        self.metrics_manager = get_global_metrics_manager()
    
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取指标数据"""
        config = widget.config
        metric_name = config.get("metric_name")
        
        if not metric_name:
            return {"error": "未指定指标名称"}
        
        # 设置时间范围
        if time_range:
            since = time_range.get("start")
            until = time_range.get("end")
        else:
            since = datetime.now() - timedelta(hours=1)
            until = None
        
        # 获取指标数据
        metrics = self.metrics_manager.get_metrics_by_name(metric_name, since, until)
        
        if not metrics:
            return {"data": [], "latest_value": None}
        
        # 格式化数据
        data_points = []
        for metric in metrics:
            data_points.append({
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.value
            })
        
        latest_value = metrics[-1].value if metrics else None
        
        return {
            "data": data_points,
            "latest_value": latest_value,
            "metric_name": metric_name,
            "count": len(data_points)
        }


class ChartWidgetDataProvider(WidgetDataProvider):
    """图表组件数据提供者"""
    
    def __init__(self):
        self.metrics_manager = get_global_metrics_manager()
    
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取图表数据"""
        config = widget.config
        metric_names = config.get("metric_names", [])
        chart_type = config.get("chart_type", ChartType.LINE.value)
        
        if not metric_names:
            return {"error": "未指定指标名称"}
        
        # 设置时间范围
        if time_range:
            since = time_range.get("start")
            until = time_range.get("end")
        else:
            since = datetime.now() - timedelta(hours=1)
            until = None
        
        # 获取多个指标的数据
        series_data = []
        
        for metric_name in metric_names:
            metrics = self.metrics_manager.get_metrics_by_name(metric_name, since, until)
            
            data_points = []
            for metric in metrics:
                data_points.append({
                    "x": metric.timestamp.isoformat(),
                    "y": metric.value
                })
            
            series_data.append({
                "name": metric_name,
                "data": data_points
            })
        
        return {
            "series": series_data,
            "chart_type": chart_type,
            "metric_names": metric_names
        }


class AlertWidgetDataProvider(WidgetDataProvider):
    """告警组件数据提供者"""
    
    def __init__(self):
        self.alert_manager = get_global_alert_manager()
    
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取告警数据"""
        config = widget.config
        show_active_only = config.get("show_active_only", True)
        max_alerts = config.get("max_alerts", 50)
        
        if show_active_only:
            alerts = self.alert_manager.get_active_alerts()
        else:
            alerts = self.alert_manager.get_alert_history(limit=max_alerts)
        
        # 格式化告警数据
        alert_data = []
        for alert in alerts:
            alert_data.append({
                "id": alert.id,
                "name": alert.name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status.value,
                "source": alert.source,
                "tags": alert.tags
            })
        
        # 统计信息
        level_counts = {}
        for alert in alerts:
            level = alert.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "alerts": alert_data,
            "total_count": len(alerts),
            "level_counts": level_counts,
            "show_active_only": show_active_only
        }


class HealthWidgetDataProvider(WidgetDataProvider):
    """健康检查组件数据提供者"""
    
    def __init__(self):
        self.health_checker = get_global_health_checker()
    
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取健康检查数据"""
        report = self.health_checker.get_last_report()
        
        if not report:
            return {"error": "暂无健康检查报告"}
        
        # 格式化健康检查数据
        check_data = []
        for check in report.checks:
            check_data.append({
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "timestamp": check.timestamp.isoformat(),
                "duration": check.duration,
                "details": check.details
            })
        
        # 统计信息
        status_counts = {}
        for check in report.checks:
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "overall_status": report.overall_status.value,
            "timestamp": report.timestamp.isoformat(),
            "duration": report.duration,
            "checks": check_data,
            "total_count": len(check_data),
            "status_counts": status_counts
        }


class TableWidgetDataProvider(WidgetDataProvider):
    """表格组件数据提供者"""
    
    def __init__(self):
        self.metrics_manager = get_global_metrics_manager()
    
    async def get_data(self, widget: DashboardWidget, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """获取表格数据"""
        config = widget.config
        data_source = config.get("data_source", "metrics")
        
        if data_source == "metrics":
            return await self._get_metrics_table_data(config, time_range)
        else:
            return {"error": f"不支持的数据源: {data_source}"}
    
    async def _get_metrics_table_data(self, config: Dict[str, Any], time_range: Optional[Dict[str, datetime]]) -> Dict[str, Any]:
        """获取指标表格数据"""
        metric_names = config.get("metric_names", [])
        
        if not metric_names:
            return {"error": "未指定指标名称"}
        
        # 设置时间范围
        if time_range:
            since = time_range.get("start")
        else:
            since = datetime.now() - timedelta(minutes=5)
        
        # 获取最新的指标值
        rows = []
        for metric_name in metric_names:
            metrics = self.metrics_manager.get_metrics_by_name(metric_name, since)
            
            if metrics:
                latest_metric = metrics[-1]
                rows.append({
                    "metric_name": metric_name,
                    "value": latest_metric.value,
                    "timestamp": latest_metric.timestamp.isoformat(),
                    "tags": latest_metric.tags
                })
            else:
                rows.append({
                    "metric_name": metric_name,
                    "value": "N/A",
                    "timestamp": "N/A",
                    "tags": {}
                })
        
        columns = [
            {"key": "metric_name", "title": "指标名称"},
            {"key": "value", "title": "当前值"},
            {"key": "timestamp", "title": "更新时间"},
            {"key": "tags", "title": "标签"}
        ]
        
        return {
            "columns": columns,
            "rows": rows,
            "total_count": len(rows)
        }


class MonitoringDashboard:
    """监控仪表盘"""
    
    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        self.data_providers: Dict[WidgetType, WidgetDataProvider] = {
            WidgetType.METRIC: MetricWidgetDataProvider(),
            WidgetType.CHART: ChartWidgetDataProvider(),
            WidgetType.ALERT: AlertWidgetDataProvider(),
            WidgetType.HEALTH: HealthWidgetDataProvider(),
            WidgetType.TABLE: TableWidgetDataProvider()
        }
        self._lock = threading.Lock()
        
        # 创建默认仪表盘
        self._create_default_dashboard()
    
    def _create_default_dashboard(self) -> None:
        """创建默认仪表盘"""
        dashboard = Dashboard(
            id="default",
            name="系统监控",
            description="默认的系统监控仪表盘"
        )
        
        # 添加系统指标组件
        dashboard.add_widget(DashboardWidget(
            id="cpu_usage",
            title="CPU使用率",
            type=WidgetType.CHART,
            config={
                "metric_names": ["system.cpu.usage_percent"],
                "chart_type": ChartType.LINE.value
            },
            position={"x": 0, "y": 0, "width": 6, "height": 4}
        ))
        
        dashboard.add_widget(DashboardWidget(
            id="memory_usage",
            title="内存使用率",
            type=WidgetType.CHART,
            config={
                "metric_names": ["system.memory.usage_percent"],
                "chart_type": ChartType.LINE.value
            },
            position={"x": 6, "y": 0, "width": 6, "height": 4}
        ))
        
        dashboard.add_widget(DashboardWidget(
            id="disk_usage",
            title="磁盘使用率",
            type=WidgetType.GAUGE,
            config={
                "metric_name": "system.disk.usage_percent"
            },
            position={"x": 0, "y": 4, "width": 3, "height": 3}
        ))
        
        dashboard.add_widget(DashboardWidget(
            id="network_io",
            title="网络I/O",
            type=WidgetType.CHART,
            config={
                "metric_names": ["system.network.bytes_sent", "system.network.bytes_recv"],
                "chart_type": ChartType.AREA.value
            },
            position={"x": 3, "y": 4, "width": 6, "height": 3}
        ))
        
        dashboard.add_widget(DashboardWidget(
            id="active_alerts",
            title="活跃告警",
            type=WidgetType.ALERT,
            config={
                "show_active_only": True,
                "max_alerts": 10
            },
            position={"x": 9, "y": 4, "width": 3, "height": 3}
        ))
        
        dashboard.add_widget(DashboardWidget(
            id="health_status",
            title="健康状态",
            type=WidgetType.HEALTH,
            config={},
            position={"x": 0, "y": 7, "width": 12, "height": 3}
        ))
        
        self.dashboards[dashboard.id] = dashboard
    
    def create_dashboard(self, dashboard: Dashboard) -> None:
        """创建仪表盘"""
        with self._lock:
            self.dashboards[dashboard.id] = dashboard
            logger.info(f"创建仪表盘: {dashboard.name}")
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """获取仪表盘"""
        return self.dashboards.get(dashboard_id)
    
    def list_dashboards(self) -> List[Dashboard]:
        """列出所有仪表盘"""
        return list(self.dashboards.values())
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """删除仪表盘"""
        with self._lock:
            if dashboard_id in self.dashboards:
                del self.dashboards[dashboard_id]
                logger.info(f"删除仪表盘: {dashboard_id}")
                return True
            return False
    
    async def get_widget_data(
        self,
        dashboard_id: str,
        widget_id: str,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """获取组件数据"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return {"error": f"仪表盘不存在: {dashboard_id}"}
        
        widget = dashboard.get_widget(widget_id)
        if not widget:
            return {"error": f"组件不存在: {widget_id}"}
        
        if not widget.enabled:
            return {"error": "组件已禁用"}
        
        provider = self.data_providers.get(widget.type)
        if not provider:
            return {"error": f"不支持的组件类型: {widget.type.value}"}
        
        try:
            data = await provider.get_data(widget, time_range)
            return data
        except Exception as e:
            logger.error(f"获取组件数据失败 {widget_id}: {e}", exception=e)
            return {"error": f"获取数据失败: {str(e)}"}
    
    async def get_dashboard_data(
        self,
        dashboard_id: str,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """获取仪表盘所有组件数据"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return {"error": f"仪表盘不存在: {dashboard_id}"}
        
        widget_data = {}
        
        # 并行获取所有组件数据
        tasks = []
        for widget in dashboard.widgets:
            if widget.enabled:
                task = self.get_widget_data(dashboard_id, widget.id, time_range)
                tasks.append((widget.id, task))
        
        if tasks:
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for i, (widget_id, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    widget_data[widget_id] = {"error": str(result)}
                else:
                    widget_data[widget_id] = result
        
        return {
            "dashboard": dashboard.to_dict(),
            "widget_data": widget_data,
            "timestamp": datetime.now().isoformat()
        }
    
    def add_data_provider(self, widget_type: WidgetType, provider: WidgetDataProvider) -> None:
        """添加数据提供者"""
        self.data_providers[widget_type] = provider
        logger.info(f"添加数据提供者: {widget_type.value}")
    
    def export_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """导出仪表盘配置"""
        dashboard = self.get_dashboard(dashboard_id)
        if dashboard:
            return dashboard.to_dict()
        return None
    
    def import_dashboard(self, config: Dict[str, Any]) -> bool:
        """导入仪表盘配置"""
        try:
            dashboard = Dashboard(
                id=config["id"],
                name=config["name"],
                description=config["description"],
                layout=config.get("layout", {})
            )
            
            for widget_config in config.get("widgets", []):
                widget = DashboardWidget(
                    id=widget_config["id"],
                    title=widget_config["title"],
                    type=WidgetType(widget_config["type"]),
                    config=widget_config.get("config", {}),
                    position=widget_config.get("position", {}),
                    refresh_interval=widget_config.get("refresh_interval", 30),
                    enabled=widget_config.get("enabled", True)
                )
                dashboard.add_widget(widget)
            
            self.create_dashboard(dashboard)
            return True
        except Exception as e:
            logger.error(f"导入仪表盘失败: {e}", exception=e)
            return False


# 全局监控仪表盘实例
_global_monitoring_dashboard: Optional[MonitoringDashboard] = None


def get_global_monitoring_dashboard() -> MonitoringDashboard:
    """获取全局监控仪表盘实例"""
    global _global_monitoring_dashboard
    if _global_monitoring_dashboard is None:
        _global_monitoring_dashboard = MonitoringDashboard()
    return _global_monitoring_dashboard


# 便捷函数
def create_metric_widget(
    widget_id: str,
    title: str,
    metric_name: str,
    position: Optional[Dict[str, int]] = None
) -> DashboardWidget:
    """创建指标组件"""
    return DashboardWidget(
        id=widget_id,
        title=title,
        type=WidgetType.METRIC,
        config={"metric_name": metric_name},
        position=position or {"x": 0, "y": 0, "width": 4, "height": 3}
    )


def create_chart_widget(
    widget_id: str,
    title: str,
    metric_names: List[str],
    chart_type: ChartType = ChartType.LINE,
    position: Optional[Dict[str, int]] = None
) -> DashboardWidget:
    """创建图表组件"""
    return DashboardWidget(
        id=widget_id,
        title=title,
        type=WidgetType.CHART,
        config={
            "metric_names": metric_names,
            "chart_type": chart_type.value
        },
        position=position or {"x": 0, "y": 0, "width": 6, "height": 4}
    )


def create_alert_widget(
    widget_id: str,
    title: str = "告警",
    show_active_only: bool = True,
    max_alerts: int = 10,
    position: Optional[Dict[str, int]] = None
) -> DashboardWidget:
    """创建告警组件"""
    return DashboardWidget(
        id=widget_id,
        title=title,
        type=WidgetType.ALERT,
        config={
            "show_active_only": show_active_only,
            "max_alerts": max_alerts
        },
        position=position or {"x": 0, "y": 0, "width": 4, "height": 4}
    )


def create_health_widget(
    widget_id: str,
    title: str = "健康状态",
    position: Optional[Dict[str, int]] = None
) -> DashboardWidget:
    """创建健康检查组件"""
    return DashboardWidget(
        id=widget_id,
        title=title,
        type=WidgetType.HEALTH,
        config={},
        position=position or {"x": 0, "y": 0, "width": 6, "height": 3}
    )