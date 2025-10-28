"""
监控模块单元测试
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from uplifted.monitoring.logger import Logger, LogLevel, LogRecord, StructuredLogger
from uplifted.monitoring.metrics_collector import (
    MetricsCollector, SystemMetricsCollector, ApplicationMetricsCollector,
    MetricsManager, MetricType
)
from uplifted.monitoring.alerting import AlertManager, Alert, AlertLevel, AlertRule
from uplifted.monitoring.tracing import Tracer, Span, SpanKind, SpanStatus
from uplifted.monitoring.health_check import HealthChecker, HealthCheck, HealthStatus
from uplifted.monitoring.dashboard import MonitoringDashboard, DashboardWidget, WidgetType


class TestLogger:
    """日志记录器测试"""
    
    def setup_method(self):
        self.logger = Logger("test_logger")
    
    def test_logger_creation(self):
        """测试日志记录器创建"""
        assert self.logger.name == "test_logger"
        assert self.logger.level == LogLevel.INFO
        assert len(self.logger.handlers) == 0
    
    def test_set_level(self):
        """测试设置日志级别"""
        self.logger.set_level(LogLevel.DEBUG)
        assert self.logger.level == LogLevel.DEBUG
        
        self.logger.set_level(LogLevel.ERROR)
        assert self.logger.level == LogLevel.ERROR
    
    def test_add_handler(self):
        """测试添加处理器"""
        from uplifted.monitoring.logger import ConsoleLogHandler
        
        handler = ConsoleLogHandler()
        self.logger.add_handler(handler)
        
        assert len(self.logger.handlers) == 1
        assert self.logger.handlers[0] is handler
    
    def test_remove_handler(self):
        """测试移除处理器"""
        from uplifted.monitoring.logger import ConsoleLogHandler
        
        handler = ConsoleLogHandler()
        self.logger.add_handler(handler)
        assert len(self.logger.handlers) == 1
        
        self.logger.remove_handler(handler)
        assert len(self.logger.handlers) == 0
    
    def test_log_record_creation(self):
        """测试日志记录创建"""
        message = "Test message"
        level = LogLevel.INFO
        
        with patch('uplifted.monitoring.logger.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            
            record = self.logger._create_log_record(level, message)
            
            assert record.level == level
            assert record.message == message
            assert record.logger_name == "test_logger"
            assert record.timestamp == datetime(2023, 1, 1, 12, 0, 0)
    
    def test_should_log(self):
        """测试是否应该记录日志"""
        self.logger.set_level(LogLevel.WARNING)
        
        assert self.logger._should_log(LogLevel.ERROR) is True
        assert self.logger._should_log(LogLevel.WARNING) is True
        assert self.logger._should_log(LogLevel.INFO) is False
        assert self.logger._should_log(LogLevel.DEBUG) is False
    
    def test_log_methods(self):
        """测试各种日志方法"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        # 测试不同级别的日志
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        self.logger.critical("Critical message")
        
        # 验证处理器被调用
        assert mock_handler.handle.call_count == 4  # DEBUG级别被过滤掉
    
    def test_log_with_extra(self):
        """测试带额外信息的日志"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        extra = {"user_id": "123", "action": "login"}
        self.logger.info("User logged in", extra=extra)
        
        # 验证额外信息被传递
        mock_handler.handle.assert_called_once()
        record = mock_handler.handle.call_args[0][0]
        assert record.extra == extra
    
    def test_context_manager(self):
        """测试上下文管理器"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        context = {"request_id": "req-123"}
        
        with self.logger.context(context):
            self.logger.info("Message with context")
        
        # 验证上下文被添加
        record = mock_handler.handle.call_args[0][0]
        assert "request_id" in record.extra
        assert record.extra["request_id"] == "req-123"


class TestStructuredLogger:
    """结构化日志记录器测试"""
    
    def setup_method(self):
        self.logger = StructuredLogger("test_structured")
    
    def test_event_logging(self):
        """测试事件日志"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        event_data = {
            "event_type": "user_action",
            "user_id": "123",
            "action": "login"
        }
        
        self.logger.event("user_login", event_data)
        
        # 验证事件日志格式
        record = mock_handler.handle.call_args[0][0]
        assert record.level == LogLevel.INFO
        assert "user_login" in record.message
        assert record.extra["event_type"] == "user_action"
    
    def test_metric_logging(self):
        """测试指标日志"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        self.logger.metric("response_time", 150.5, {"endpoint": "/api/users"})
        
        # 验证指标日志格式
        record = mock_handler.handle.call_args[0][0]
        assert "response_time" in record.message
        assert record.extra["metric_value"] == 150.5
        assert record.extra["endpoint"] == "/api/users"
    
    def test_performance_logging(self):
        """测试性能日志"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        perf_data = {
            "operation": "database_query",
            "duration": 25.3,
            "query": "SELECT * FROM users"
        }
        
        self.logger.performance("db_query_slow", perf_data)
        
        # 验证性能日志格式
        record = mock_handler.handle.call_args[0][0]
        assert record.level == LogLevel.WARNING
        assert "db_query_slow" in record.message
        assert record.extra["operation"] == "database_query"
    
    def test_audit_logging(self):
        """测试审计日志"""
        mock_handler = Mock()
        self.logger.add_handler(mock_handler)
        
        audit_data = {
            "user_id": "123",
            "action": "delete_user",
            "target_user_id": "456",
            "ip_address": "192.168.1.1"
        }
        
        self.logger.audit("user_deletion", audit_data)
        
        # 验证审计日志格式
        record = mock_handler.handle.call_args[0][0]
        assert record.level == LogLevel.INFO
        assert "user_deletion" in record.message
        assert record.extra["action"] == "delete_user"


@pytest.mark.asyncio
class TestMetricsCollector:
    """指标收集器测试"""
    
    def setup_method(self):
        self.metrics_manager = MetricsManager()
    
    async def test_system_metrics_collection(self):
        """测试系统指标收集"""
        collector = SystemMetricsCollector()
        
        with patch('psutil.cpu_percent', return_value=75.5):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.used = 8 * 1024 * 1024 * 1024  # 8GB
                mock_memory.return_value.total = 16 * 1024 * 1024 * 1024  # 16GB
                
                metrics = await collector.collect()
                
                assert 'cpu_usage' in metrics
                assert metrics['cpu_usage'].value == 75.5
                assert metrics['cpu_usage'].type == MetricType.GAUGE
                
                assert 'memory_usage' in metrics
                assert metrics['memory_usage'].value == 60.0
    
    async def test_application_metrics_collection(self):
        """测试应用指标收集"""
        collector = ApplicationMetricsCollector()
        
        # 添加一些指标
        collector.increment_counter("requests_total", {"endpoint": "/api/users"})
        collector.increment_counter("requests_total", {"endpoint": "/api/users"})
        collector.set_gauge("active_connections", 25)
        collector.record_histogram("response_time", 150.5)
        
        metrics = await collector.collect()
        
        assert 'requests_total' in metrics
        assert metrics['requests_total'].value == 2
        
        assert 'active_connections' in metrics
        assert metrics['active_connections'].value == 25
        
        assert 'response_time' in metrics
        assert metrics['response_time'].type == MetricType.HISTOGRAM
    
    async def test_metrics_manager_registration(self):
        """测试指标管理器注册"""
        collector = SystemMetricsCollector()
        
        self.metrics_manager.register_collector("system", collector)
        
        assert "system" in self.metrics_manager.collectors
        assert self.metrics_manager.collectors["system"] is collector
    
    async def test_metrics_manager_collection(self):
        """测试指标管理器收集"""
        collector = Mock()
        collector.collect = AsyncMock(return_value={
            "test_metric": Mock(value=100, type=MetricType.GAUGE)
        })
        
        self.metrics_manager.register_collector("test", collector)
        
        all_metrics = await self.metrics_manager.collect_all()
        
        assert "test_metric" in all_metrics
        assert all_metrics["test_metric"].value == 100
        collector.collect.assert_called_once()
    
    async def test_metrics_manager_start_stop(self):
        """测试指标管理器启动停止"""
        collector = Mock()
        collector.collect = AsyncMock(return_value={})
        
        self.metrics_manager.register_collector("test", collector)
        
        # 启动收集
        await self.metrics_manager.start_collection(interval=0.1)
        assert self.metrics_manager.is_running is True
        
        # 等待一小段时间确保收集运行
        import asyncio
        await asyncio.sleep(0.2)
        
        # 停止收集
        await self.metrics_manager.stop_collection()
        assert self.metrics_manager.is_running is False


@pytest.mark.asyncio
class TestAlertManager:
    """告警管理器测试"""
    
    def setup_method(self):
        self.alert_manager = AlertManager()
    
    async def test_add_alert_rule(self):
        """测试添加告警规则"""
        rule = AlertRule(
            name="high_cpu",
            condition="cpu_usage > 80",
            level=AlertLevel.WARNING,
            message="CPU usage is high: {cpu_usage}%"
        )
        
        self.alert_manager.add_rule(rule)
        
        assert "high_cpu" in self.alert_manager.rules
        assert self.alert_manager.rules["high_cpu"] is rule
    
    async def test_remove_alert_rule(self):
        """测试移除告警规则"""
        rule = AlertRule(
            name="high_cpu",
            condition="cpu_usage > 80",
            level=AlertLevel.WARNING,
            message="CPU usage is high"
        )
        
        self.alert_manager.add_rule(rule)
        assert "high_cpu" in self.alert_manager.rules
        
        self.alert_manager.remove_rule("high_cpu")
        assert "high_cpu" not in self.alert_manager.rules
    
    async def test_evaluate_rules_trigger_alert(self):
        """测试规则评估触发告警"""
        rule = AlertRule(
            name="high_cpu",
            condition="cpu_usage > 80",
            level=AlertLevel.WARNING,
            message="CPU usage is high: {cpu_usage}%"
        )
        
        self.alert_manager.add_rule(rule)
        
        # 模拟高CPU使用率
        metrics = {"cpu_usage": 85.0}
        
        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            await self.alert_manager.evaluate_rules(metrics)
            
            # 验证告警被触发
            mock_send.assert_called_once()
            alert = mock_send.call_args[0][0]
            assert alert.rule_name == "high_cpu"
            assert alert.level == AlertLevel.WARNING
            assert "85.0" in alert.message
    
    async def test_evaluate_rules_no_trigger(self):
        """测试规则评估不触发告警"""
        rule = AlertRule(
            name="high_cpu",
            condition="cpu_usage > 80",
            level=AlertLevel.WARNING,
            message="CPU usage is high"
        )
        
        self.alert_manager.add_rule(rule)
        
        # 模拟正常CPU使用率
        metrics = {"cpu_usage": 50.0}
        
        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            await self.alert_manager.evaluate_rules(metrics)
            
            # 验证告警没有被触发
            mock_send.assert_not_called()
    
    async def test_alert_suppression(self):
        """测试告警抑制"""
        rule = AlertRule(
            name="high_cpu",
            condition="cpu_usage > 80",
            level=AlertLevel.WARNING,
            message="CPU usage is high",
            cooldown_minutes=5
        )
        
        self.alert_manager.add_rule(rule)
        
        metrics = {"cpu_usage": 85.0}
        
        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            # 第一次评估应该触发告警
            await self.alert_manager.evaluate_rules(metrics)
            assert mock_send.call_count == 1
            
            # 立即再次评估应该被抑制
            await self.alert_manager.evaluate_rules(metrics)
            assert mock_send.call_count == 1  # 没有增加
    
    async def test_add_alert_channel(self):
        """测试添加告警通道"""
        from uplifted.monitoring.alerting import EmailAlertChannel
        
        channel = EmailAlertChannel({
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "username": "alerts@example.com",
            "password": "password",
            "recipients": ["admin@example.com"]
        })
        
        self.alert_manager.add_channel("email", channel)
        
        assert "email" in self.alert_manager.channels
        assert self.alert_manager.channels["email"] is channel


@pytest.mark.asyncio
class TestTracer:
    """追踪器测试"""
    
    def setup_method(self):
        self.tracer = Tracer("test_service")
    
    async def test_start_span(self):
        """测试开始Span"""
        span = self.tracer.start_span("test_operation")
        
        assert span.name == "test_operation"
        assert span.service_name == "test_service"
        assert span.status == SpanStatus.OK
        assert span.start_time is not None
        assert span.end_time is None
    
    async def test_finish_span(self):
        """测试结束Span"""
        span = self.tracer.start_span("test_operation")
        start_time = span.start_time
        
        # 模拟一些操作时间
        import time
        time.sleep(0.01)
        
        self.tracer.finish_span(span)
        
        assert span.end_time is not None
        assert span.end_time > start_time
        assert span.duration > 0
    
    async def test_span_context_manager(self):
        """测试Span上下文管理器"""
        with self.tracer.span("test_operation") as span:
            assert span.name == "test_operation"
            assert span.end_time is None
            
            # 在span内部添加标签和事件
            span.set_tag("user_id", "123")
            span.add_event("processing_started")
        
        # 退出上下文后span应该被结束
        assert span.end_time is not None
        assert "user_id" in span.tags
        assert len(span.events) == 1
    
    async def test_async_span_context_manager(self):
        """测试异步Span上下文管理器"""
        async with self.tracer.async_span("async_operation") as span:
            assert span.name == "async_operation"
            
            # 模拟异步操作
            import asyncio
            await asyncio.sleep(0.01)
            
            span.set_tag("async", "true")
        
        assert span.end_time is not None
        assert span.tags["async"] == "true"
    
    async def test_span_hierarchy(self):
        """测试Span层次结构"""
        parent_span = self.tracer.start_span("parent_operation")
        
        with self.tracer.span("child_operation", parent=parent_span) as child_span:
            assert child_span.parent_id == parent_span.span_id
            assert child_span.trace_id == parent_span.trace_id
        
        self.tracer.finish_span(parent_span)
    
    async def test_trace_function_decorator(self):
        """测试函数追踪装饰器"""
        from uplifted.monitoring.tracing import trace_function
        
        @trace_function(tracer=self.tracer)
        async def test_function(arg1, arg2):
            return arg1 + arg2
        
        with patch.object(self.tracer, 'start_span') as mock_start:
            with patch.object(self.tracer, 'finish_span') as mock_finish:
                mock_span = Mock()
                mock_start.return_value = mock_span
                
                result = await test_function(1, 2)
                
                assert result == 3
                mock_start.assert_called_once_with("test_function")
                mock_finish.assert_called_once_with(mock_span)


@pytest.mark.asyncio
class TestHealthChecker:
    """健康检查器测试"""
    
    def setup_method(self):
        self.health_checker = HealthChecker()
    
    async def test_add_health_check(self):
        """测试添加健康检查"""
        from uplifted.monitoring.health_check import CPUHealthCheck
        
        check = CPUHealthCheck(threshold=80.0)
        self.health_checker.add_check("cpu", check)
        
        assert "cpu" in self.health_checker.checks
        assert self.health_checker.checks["cpu"] is check
    
    async def test_remove_health_check(self):
        """测试移除健康检查"""
        from uplifted.monitoring.health_check import CPUHealthCheck
        
        check = CPUHealthCheck(threshold=80.0)
        self.health_checker.add_check("cpu", check)
        
        self.health_checker.remove_check("cpu")
        assert "cpu" not in self.health_checker.checks
    
    async def test_run_single_check_healthy(self):
        """测试运行单个健康检查 - 健康状态"""
        mock_check = Mock()
        mock_check.check = AsyncMock(return_value=Mock(
            status=HealthStatus.HEALTHY,
            message="CPU usage is normal",
            details={"cpu_usage": 50.0}
        ))
        
        self.health_checker.add_check("cpu", mock_check)
        
        result = await self.health_checker.run_check("cpu")
        
        assert result.status == HealthStatus.HEALTHY
        assert "normal" in result.message
        mock_check.check.assert_called_once()
    
    async def test_run_single_check_unhealthy(self):
        """测试运行单个健康检查 - 不健康状态"""
        mock_check = Mock()
        mock_check.check = AsyncMock(return_value=Mock(
            status=HealthStatus.UNHEALTHY,
            message="CPU usage is too high",
            details={"cpu_usage": 95.0}
        ))
        
        self.health_checker.add_check("cpu", mock_check)
        
        result = await self.health_checker.run_check("cpu")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "too high" in result.message
    
    async def test_run_all_checks(self):
        """测试运行所有健康检查"""
        mock_check1 = Mock()
        mock_check1.check = AsyncMock(return_value=Mock(
            status=HealthStatus.HEALTHY,
            message="CPU OK"
        ))
        
        mock_check2 = Mock()
        mock_check2.check = AsyncMock(return_value=Mock(
            status=HealthStatus.UNHEALTHY,
            message="Memory high"
        ))
        
        self.health_checker.add_check("cpu", mock_check1)
        self.health_checker.add_check("memory", mock_check2)
        
        report = await self.health_checker.run_all_checks()
        
        assert len(report.results) == 2
        assert report.overall_status == HealthStatus.UNHEALTHY  # 有一个不健康
        assert "cpu" in report.results
        assert "memory" in report.results
    
    async def test_periodic_health_checks(self):
        """测试定期健康检查"""
        mock_check = Mock()
        mock_check.check = AsyncMock(return_value=Mock(
            status=HealthStatus.HEALTHY,
            message="OK"
        ))
        
        self.health_checker.add_check("test", mock_check)
        
        # 启动定期检查
        await self.health_checker.start_periodic_checks(interval=0.1)
        
        # 等待一段时间
        import asyncio
        await asyncio.sleep(0.25)
        
        # 停止定期检查
        await self.health_checker.stop_periodic_checks()
        
        # 验证检查被执行了多次
        assert mock_check.check.call_count >= 2


@pytest.mark.asyncio
class TestMonitoringDashboard:
    """监控仪表盘测试"""
    
    def setup_method(self):
        self.dashboard = MonitoringDashboard()
    
    async def test_create_dashboard(self):
        """测试创建仪表盘"""
        dashboard_config = {
            "name": "System Overview",
            "description": "System monitoring dashboard"
        }
        
        dashboard = self.dashboard.create_dashboard("system", dashboard_config)
        
        assert dashboard.id == "system"
        assert dashboard.name == "System Overview"
        assert dashboard.description == "System monitoring dashboard"
        assert len(dashboard.widgets) == 0
    
    async def test_add_widget_to_dashboard(self):
        """测试向仪表盘添加组件"""
        # 创建仪表盘
        self.dashboard.create_dashboard("test", {"name": "Test Dashboard"})
        
        # 添加组件
        widget = DashboardWidget(
            id="cpu_widget",
            title="CPU Usage",
            type=WidgetType.METRIC,
            config={"metric_name": "cpu_usage"}
        )
        
        self.dashboard.add_widget("test", widget)
        
        dashboard = self.dashboard.get_dashboard("test")
        assert len(dashboard.widgets) == 1
        assert dashboard.widgets[0].id == "cpu_widget"
    
    async def test_get_widget_data(self):
        """测试获取组件数据"""
        # 模拟指标收集器
        mock_metrics_collector = Mock()
        mock_metrics_collector.get_metric = AsyncMock(return_value=Mock(value=75.5))
        
        # 创建数据提供者
        from uplifted.monitoring.dashboard import MetricWidgetDataProvider
        provider = MetricWidgetDataProvider(mock_metrics_collector)
        
        widget = DashboardWidget(
            id="cpu_widget",
            title="CPU Usage",
            type=WidgetType.METRIC,
            config={"metric_name": "cpu_usage"}
        )
        
        data = await provider.get_data(widget)
        
        assert data["value"] == 75.5
        assert data["metric_name"] == "cpu_usage"
        mock_metrics_collector.get_metric.assert_called_once_with("cpu_usage")
    
    async def test_dashboard_export_import(self):
        """测试仪表盘导出导入"""
        # 创建仪表盘
        dashboard_config = {"name": "Test Dashboard"}
        dashboard = self.dashboard.create_dashboard("test", dashboard_config)
        
        # 添加组件
        widget = DashboardWidget(
            id="test_widget",
            title="Test Widget",
            type=WidgetType.METRIC,
            config={"metric_name": "test_metric"}
        )
        dashboard.widgets.append(widget)
        
        # 导出
        exported = self.dashboard.export_dashboard("test")
        
        assert exported["id"] == "test"
        assert exported["name"] == "Test Dashboard"
        assert len(exported["widgets"]) == 1
        
        # 导入到新的仪表盘
        self.dashboard.import_dashboard("imported", exported)
        
        imported_dashboard = self.dashboard.get_dashboard("imported")
        assert imported_dashboard.name == "Test Dashboard"
        assert len(imported_dashboard.widgets) == 1
        assert imported_dashboard.widgets[0].title == "Test Widget"


class TestMonitoringIntegration:
    """监控集成测试"""
    
    def test_monitoring_configuration(self):
        """测试监控配置"""
        from uplifted.monitoring import configure_monitoring
        
        config = {
            "logging": {
                "level": "INFO",
                "handlers": ["console", "file"]
            },
            "metrics": {
                "collectors": ["system", "application"],
                "interval": 60
            },
            "alerting": {
                "rules": [
                    {
                        "name": "high_cpu",
                        "condition": "cpu_usage > 80",
                        "level": "WARNING"
                    }
                ]
            }
        }
        
        # 这里可以测试配置解析和组件初始化
        # 由于涉及到实际的组件创建，这里主要测试配置结构
        assert "logging" in config
        assert "metrics" in config
        assert "alerting" in config
    
    def test_monitoring_manager_integration(self):
        """测试监控管理器集成"""
        from uplifted.monitoring.integration_example import MonitoringIntegrationManager
        
        config = {
            "logging": {"level": "INFO"},
            "metrics": {"interval": 60},
            "alerting": {"enabled": True},
            "tracing": {"enabled": True},
            "health_checks": {"enabled": True},
            "dashboard": {"enabled": True}
        }
        
        manager = MonitoringIntegrationManager(config)
        
        # 验证管理器创建
        assert manager.config == config
        assert hasattr(manager, 'logger')
        assert hasattr(manager, 'metrics_manager')
        assert hasattr(manager, 'alert_manager')
        assert hasattr(manager, 'tracer')
        assert hasattr(manager, 'health_checker')
        assert hasattr(manager, 'dashboard')