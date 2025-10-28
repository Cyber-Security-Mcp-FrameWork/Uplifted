"""
监控系统集成示例
展示如何使用监控和日志模块的各个组件
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from .logger import get_logger, configure_logging, LogLevel
from .metrics_collector import get_global_metrics_manager, MetricType
from .alerting import get_global_alert_manager, AlertLevel, create_cpu_alert_rule, create_memory_alert_rule
from .tracing import get_global_tracer, trace_function
from .health_check import get_global_health_checker, CPUHealthCheck, MemoryHealthCheck, DiskHealthCheck
from .dashboard import (
    get_global_monitoring_dashboard,
    Dashboard,
    create_metric_widget,
    create_chart_widget,
    create_alert_widget,
    create_health_widget,
    ChartType
)

logger = get_logger(__name__)


class MonitoringIntegrationManager:
    """监控系统集成管理器"""
    
    def __init__(self):
        self.metrics_manager = get_global_metrics_manager()
        self.alert_manager = get_global_alert_manager()
        self.tracer = get_global_tracer()
        self.health_checker = get_global_health_checker()
        self.dashboard = get_global_monitoring_dashboard()
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化监控系统"""
        if self._initialized:
            return
        
        logger.info("初始化监控系统...")
        
        # 配置日志
        configure_logging(
            level=LogLevel.INFO,
            format_type="json",
            log_file="logs/monitoring.log",
            max_file_size=10 * 1024 * 1024,  # 10MB
            backup_count=5
        )
        
        # 启动指标收集
        await self._setup_metrics()
        
        # 设置告警规则
        await self._setup_alerts()
        
        # 配置健康检查
        await self._setup_health_checks()
        
        # 创建自定义仪表盘
        await self._setup_dashboard()
        
        # 启动监控服务
        await self._start_monitoring_services()
        
        self._initialized = True
        logger.info("监控系统初始化完成")
    
    async def _setup_metrics(self) -> None:
        """设置指标收集"""
        logger.info("设置指标收集...")
        
        # 启动系统指标收集
        await self.metrics_manager.start_collection()
        
        # 注册自定义指标
        await self.metrics_manager.register_metric("app.requests.total", MetricType.COUNTER)
        await self.metrics_manager.register_metric("app.requests.duration", MetricType.HISTOGRAM)
        await self.metrics_manager.register_metric("app.active_users", MetricType.GAUGE)
        await self.metrics_manager.register_metric("app.queue.size", MetricType.GAUGE)
        
        logger.info("指标收集设置完成")
    
    async def _setup_alerts(self) -> None:
        """设置告警规则"""
        logger.info("设置告警规则...")
        
        # 创建系统告警规则
        cpu_rule = create_cpu_alert_rule(threshold=80.0)
        memory_rule = create_memory_alert_rule(threshold=85.0)
        
        # 创建自定义告警规则
        from .alerting import AlertRule
        
        # 应用请求错误率告警
        error_rate_rule = AlertRule(
            id="app_error_rate_high",
            name="应用错误率过高",
            description="应用错误率超过5%",
            condition="app.requests.error_rate > 0.05",
            level=AlertLevel.WARNING,
            enabled=True
        )
        
        # 队列积压告警
        queue_size_rule = AlertRule(
            id="queue_size_high",
            name="队列积压过多",
            description="队列大小超过1000",
            condition="app.queue.size > 1000",
            level=AlertLevel.CRITICAL,
            enabled=True
        )
        
        # 添加告警规则
        self.alert_manager.add_rule(cpu_rule)
        self.alert_manager.add_rule(memory_rule)
        self.alert_manager.add_rule(error_rate_rule)
        self.alert_manager.add_rule(queue_size_rule)
        
        # 启动告警管理器
        await self.alert_manager.start()
        
        logger.info("告警规则设置完成")
    
    async def _setup_health_checks(self) -> None:
        """设置健康检查"""
        logger.info("设置健康检查...")
        
        # 添加系统健康检查
        self.health_checker.add_check(CPUHealthCheck("cpu_check", threshold=90.0))
        self.health_checker.add_check(MemoryHealthCheck("memory_check", threshold=90.0))
        self.health_checker.add_check(DiskHealthCheck("disk_check", path="/", threshold=90.0))
        
        # 添加自定义健康检查
        from .health_check import CustomHealthCheck
        
        async def check_database_connection():
            """检查数据库连接"""
            # 模拟数据库连接检查
            await asyncio.sleep(0.1)
            return True, "数据库连接正常"
        
        async def check_redis_connection():
            """检查Redis连接"""
            # 模拟Redis连接检查
            await asyncio.sleep(0.1)
            return True, "Redis连接正常"
        
        db_check = CustomHealthCheck("database_check", check_database_connection)
        redis_check = CustomHealthCheck("redis_check", check_redis_connection)
        
        self.health_checker.add_check(db_check)
        self.health_checker.add_check(redis_check)
        
        # 启动定期健康检查
        await self.health_checker.start_periodic_check(interval=30)
        
        logger.info("健康检查设置完成")
    
    async def _setup_dashboard(self) -> None:
        """设置仪表盘"""
        logger.info("设置仪表盘...")
        
        # 创建应用监控仪表盘
        app_dashboard = Dashboard(
            id="app_monitoring",
            name="应用监控",
            description="应用程序监控仪表盘"
        )
        
        # 添加应用指标组件
        app_dashboard.add_widget(create_metric_widget(
            "app_requests_total",
            "总请求数",
            "app.requests.total",
            {"x": 0, "y": 0, "width": 3, "height": 2}
        ))
        
        app_dashboard.add_widget(create_chart_widget(
            "app_requests_chart",
            "请求趋势",
            ["app.requests.total", "app.requests.error_count"],
            ChartType.LINE,
            {"x": 3, "y": 0, "width": 6, "height": 4}
        ))
        
        app_dashboard.add_widget(create_metric_widget(
            "app_active_users",
            "活跃用户数",
            "app.active_users",
            {"x": 9, "y": 0, "width": 3, "height": 2}
        ))
        
        app_dashboard.add_widget(create_chart_widget(
            "app_response_time",
            "响应时间分布",
            ["app.requests.duration"],
            ChartType.HISTOGRAM,
            {"x": 0, "y": 4, "width": 6, "height": 4}
        ))
        
        app_dashboard.add_widget(create_alert_widget(
            "app_alerts",
            "应用告警",
            True,
            10,
            {"x": 6, "y": 4, "width": 3, "height": 4}
        ))
        
        app_dashboard.add_widget(create_health_widget(
            "app_health",
            "应用健康状态",
            {"x": 9, "y": 4, "width": 3, "height": 4}
        ))
        
        # 创建仪表盘
        self.dashboard.create_dashboard(app_dashboard)
        
        logger.info("仪表盘设置完成")
    
    async def _start_monitoring_services(self) -> None:
        """启动监控服务"""
        logger.info("启动监控服务...")
        
        # 启动追踪器
        await self.tracer.start()
        
        logger.info("监控服务启动完成")
    
    @trace_function
    async def simulate_application_load(self, duration: int = 60) -> None:
        """模拟应用负载"""
        logger.info(f"开始模拟应用负载，持续 {duration} 秒...")
        
        start_time = time.time()
        request_count = 0
        error_count = 0
        
        while time.time() - start_time < duration:
            # 模拟请求处理
            with self.tracer.start_span("process_request") as span:
                # 增加请求计数
                request_count += 1
                await self.metrics_manager.increment("app.requests.total")
                
                # 模拟请求处理时间
                processing_time = 0.1 + (time.time() % 1) * 0.5  # 0.1-0.6秒
                await asyncio.sleep(processing_time)
                
                # 记录响应时间
                await self.metrics_manager.record_histogram("app.requests.duration", processing_time)
                
                # 模拟错误
                if request_count % 20 == 0:  # 5%错误率
                    error_count += 1
                    await self.metrics_manager.increment("app.requests.error_count")
                    span.set_status("ERROR", "模拟错误")
                    logger.warning(f"模拟请求错误: {request_count}")
                
                # 更新活跃用户数
                active_users = 100 + int((time.time() % 60) * 2)  # 100-220之间变化
                await self.metrics_manager.set_gauge("app.active_users", active_users)
                
                # 更新队列大小
                queue_size = max(0, 50 + int((time.time() % 30) * 10) - request_count % 100)
                await self.metrics_manager.set_gauge("app.queue.size", queue_size)
                
                span.set_attribute("request_id", request_count)
                span.set_attribute("processing_time", processing_time)
            
            # 控制请求频率
            await asyncio.sleep(0.5)
        
        logger.info(f"应用负载模拟完成，总请求: {request_count}, 错误: {error_count}")
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        summary = {}
        
        # 获取指标摘要
        metrics_summary = await self.metrics_manager.get_summary()
        summary["metrics"] = metrics_summary
        
        # 获取告警摘要
        active_alerts = self.alert_manager.get_active_alerts()
        summary["alerts"] = {
            "active_count": len(active_alerts),
            "active_alerts": [
                {
                    "name": alert.name,
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in active_alerts[:5]  # 只显示前5个
            ]
        }
        
        # 获取健康检查摘要
        health_report = self.health_checker.get_last_report()
        if health_report:
            summary["health"] = {
                "overall_status": health_report.overall_status.value,
                "timestamp": health_report.timestamp.isoformat(),
                "checks_count": len(health_report.checks),
                "failed_checks": [
                    check.name for check in health_report.checks 
                    if check.status.name != "HEALTHY"
                ]
            }
        
        # 获取追踪摘要
        trace_summary = await self.tracer.get_summary()
        summary["tracing"] = trace_summary
        
        return summary
    
    async def shutdown(self) -> None:
        """关闭监控系统"""
        logger.info("关闭监控系统...")
        
        # 停止各个组件
        await self.metrics_manager.stop_collection()
        await self.alert_manager.stop()
        await self.health_checker.stop_periodic_check()
        await self.tracer.stop()
        
        logger.info("监控系统已关闭")


async def main():
    """主函数 - 监控系统集成示例"""
    manager = MonitoringIntegrationManager()
    
    try:
        # 初始化监控系统
        await manager.initialize()
        
        # 模拟应用负载
        load_task = asyncio.create_task(manager.simulate_application_load(120))
        
        # 定期输出监控摘要
        for i in range(4):  # 每30秒输出一次，共4次
            await asyncio.sleep(30)
            summary = await manager.get_monitoring_summary()
            logger.info(f"监控摘要 #{i+1}: {summary}")
        
        # 等待负载模拟完成
        await load_task
        
        # 最终摘要
        final_summary = await manager.get_monitoring_summary()
        logger.info(f"最终监控摘要: {final_summary}")
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"监控系统运行错误: {e}", exception=e)
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())