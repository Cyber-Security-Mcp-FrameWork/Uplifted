"""
告警模块
提供告警规则、告警通道和告警管理功能
"""

import asyncio
import json
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import threading
import time

import aiohttp

from .logger import get_logger
from .metrics_collector import MetricValue, get_global_metrics_manager

logger = get_logger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """告警"""
    id: str
    name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    source: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    suppressed_until: Optional[datetime] = None


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    metric_name: str
    condition: str  # 条件表达式，如 "> 80", "< 10", "== 0"
    threshold: Union[int, float]
    level: AlertLevel
    enabled: bool = True
    evaluation_interval: int = 60  # 评估间隔（秒）
    for_duration: int = 300  # 持续时间（秒）
    tags: Dict[str, str] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    
    # 内部状态
    _last_evaluation: Optional[datetime] = field(default=None, init=False)
    _condition_met_since: Optional[datetime] = field(default=None, init=False)
    _active_alert: Optional[Alert] = field(default=None, init=False)


class AlertChannel(ABC):
    """告警通道抽象基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = True
    
    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """发送告警"""
        pass
    
    @abstractmethod
    async def send_resolution(self, alert: Alert) -> bool:
        """发送告警解除通知"""
        pass


class EmailAlertChannel(AlertChannel):
    """邮件告警通道"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_email = config.get("from_email", "")
        self.to_emails = config.get("to_emails", [])
        self.use_tls = config.get("use_tls", True)
    
    async def send_alert(self, alert: Alert) -> bool:
        """发送告警邮件"""
        try:
            subject = f"[{alert.level.value.upper()}] {alert.name}"
            body = self._format_alert_email(alert)
            
            return await self._send_email(subject, body)
        except Exception as e:
            logger.error(f"发送告警邮件失败: {e}", exception=e)
            return False
    
    async def send_resolution(self, alert: Alert) -> bool:
        """发送告警解除邮件"""
        try:
            subject = f"[RESOLVED] {alert.name}"
            body = self._format_resolution_email(alert)
            
            return await self._send_email(subject, body)
        except Exception as e:
            logger.error(f"发送告警解除邮件失败: {e}", exception=e)
            return False
    
    def _format_alert_email(self, alert: Alert) -> str:
        """格式化告警邮件内容"""
        return f"""
告警详情:
- 告警名称: {alert.name}
- 告警级别: {alert.level.value.upper()}
- 告警时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- 告警消息: {alert.message}
- 来源: {alert.source or 'Unknown'}

标签:
{chr(10).join(f"- {k}: {v}" for k, v in alert.tags.items()) if alert.tags else "无"}

元数据:
{json.dumps(alert.metadata, indent=2, ensure_ascii=False) if alert.metadata else "无"}
"""
    
    def _format_resolution_email(self, alert: Alert) -> str:
        """格式化告警解除邮件内容"""
        return f"""
告警已解除:
- 告警名称: {alert.name}
- 告警级别: {alert.level.value.upper()}
- 告警时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- 解除时间: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else 'Unknown'}
- 持续时间: {str(alert.resolved_at - alert.timestamp) if alert.resolved_at else 'Unknown'}
- 告警消息: {alert.message}
"""
    
    async def _send_email(self, subject: str, body: str) -> bool:
        """发送邮件"""
        try:
            # 在线程池中执行同步邮件发送
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_email_sync, subject, body)
        except Exception as e:
            logger.error(f"邮件发送失败: {e}", exception=e)
            return False
    
    def _send_email_sync(self, subject: str, body: str) -> bool:
        """同步发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            logger.error(f"同步邮件发送失败: {e}", exception=e)
            return False


class SlackAlertChannel(AlertChannel):
    """Slack告警通道"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.webhook_url = config.get("webhook_url", "")
        self.channel = config.get("channel", "#alerts")
        self.username = config.get("username", "AlertBot")
    
    async def send_alert(self, alert: Alert) -> bool:
        """发送Slack告警"""
        try:
            payload = self._format_slack_alert(alert)
            return await self._send_slack_message(payload)
        except Exception as e:
            logger.error(f"发送Slack告警失败: {e}", exception=e)
            return False
    
    async def send_resolution(self, alert: Alert) -> bool:
        """发送Slack告警解除通知"""
        try:
            payload = self._format_slack_resolution(alert)
            return await self._send_slack_message(payload)
        except Exception as e:
            logger.error(f"发送Slack告警解除通知失败: {e}", exception=e)
            return False
    
    def _format_slack_alert(self, alert: Alert) -> Dict[str, Any]:
        """格式化Slack告警消息"""
        color_map = {
            AlertLevel.INFO: "good",
            AlertLevel.WARNING: "warning",
            AlertLevel.ERROR: "danger",
            AlertLevel.CRITICAL: "danger"
        }
        
        fields = [
            {"title": "级别", "value": alert.level.value.upper(), "short": True},
            {"title": "时间", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "short": True},
            {"title": "来源", "value": alert.source or "Unknown", "short": True}
        ]
        
        if alert.tags:
            tag_str = ", ".join(f"{k}={v}" for k, v in alert.tags.items())
            fields.append({"title": "标签", "value": tag_str, "short": False})
        
        return {
            "channel": self.channel,
            "username": self.username,
            "attachments": [
                {
                    "color": color_map.get(alert.level, "warning"),
                    "title": f"🚨 {alert.name}",
                    "text": alert.message,
                    "fields": fields,
                    "footer": "Uplifted Alert System",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
    
    def _format_slack_resolution(self, alert: Alert) -> Dict[str, Any]:
        """格式化Slack告警解除消息"""
        duration = ""
        if alert.resolved_at:
            duration = str(alert.resolved_at - alert.timestamp)
        
        fields = [
            {"title": "级别", "value": alert.level.value.upper(), "short": True},
            {"title": "解除时间", "value": alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if alert.resolved_at else "Unknown", "short": True},
            {"title": "持续时间", "value": duration, "short": True}
        ]
        
        return {
            "channel": self.channel,
            "username": self.username,
            "attachments": [
                {
                    "color": "good",
                    "title": f"✅ {alert.name} - 已解除",
                    "text": alert.message,
                    "fields": fields,
                    "footer": "Uplifted Alert System",
                    "ts": int(alert.resolved_at.timestamp()) if alert.resolved_at else int(time.time())
                }
            ]
        }
    
    async def _send_slack_message(self, payload: Dict[str, Any]) -> bool:
        """发送Slack消息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Slack消息发送失败: {e}", exception=e)
            return False


class WebhookAlertChannel(AlertChannel):
    """Webhook告警通道"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.url = config.get("url", "")
        self.method = config.get("method", "POST").upper()
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
    
    async def send_alert(self, alert: Alert) -> bool:
        """发送Webhook告警"""
        try:
            payload = self._format_webhook_payload(alert, "alert")
            return await self._send_webhook(payload)
        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}", exception=e)
            return False
    
    async def send_resolution(self, alert: Alert) -> bool:
        """发送Webhook告警解除通知"""
        try:
            payload = self._format_webhook_payload(alert, "resolution")
            return await self._send_webhook(payload)
        except Exception as e:
            logger.error(f"发送Webhook告警解除通知失败: {e}", exception=e)
            return False
    
    def _format_webhook_payload(self, alert: Alert, event_type: str) -> Dict[str, Any]:
        """格式化Webhook载荷"""
        return {
            "event_type": event_type,
            "alert": {
                "id": alert.id,
                "name": alert.name,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status.value,
                "source": alert.source,
                "tags": alert.tags,
                "metadata": alert.metadata,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            }
        }
    
    async def _send_webhook(self, payload: Dict[str, Any]) -> bool:
        """发送Webhook请求"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.request(
                    self.method,
                    self.url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    return 200 <= response.status < 300
        except Exception as e:
            logger.error(f"Webhook请求失败: {e}", exception=e)
            return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[str, AlertChannel] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._evaluation_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.Lock()
        self.metrics_manager = get_global_metrics_manager()
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self.rules[rule.id] = rule
            logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> None:
        """移除告警规则"""
        with self._lock:
            if rule_id in self.rules:
                rule = self.rules.pop(rule_id)
                # 如果有活跃告警，解除它
                if rule._active_alert:
                    asyncio.create_task(self.resolve_alert(rule._active_alert.id))
                logger.info(f"移除告警规则: {rule.name}")
    
    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警通道"""
        self.channels[channel.name] = channel
        logger.info(f"添加告警通道: {channel.name}")
    
    def remove_channel(self, channel_name: str) -> None:
        """移除告警通道"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            logger.info(f"移除告警通道: {channel_name}")
    
    async def start_evaluation(self) -> None:
        """开始告警评估"""
        if self._running:
            return
        
        self._running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("开始告警评估")
    
    async def stop_evaluation(self) -> None:
        """停止告警评估"""
        if not self._running:
            return
        
        self._running = False
        
        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("停止告警评估")
    
    async def _evaluation_loop(self) -> None:
        """告警评估循环"""
        while self._running:
            try:
                await self._evaluate_all_rules()
                await asyncio.sleep(10)  # 每10秒评估一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"告警评估循环错误: {e}", exception=e)
                await asyncio.sleep(5)
    
    async def _evaluate_all_rules(self) -> None:
        """评估所有告警规则"""
        current_time = datetime.now()
        
        for rule in list(self.rules.values()):
            if not rule.enabled:
                continue
            
            # 检查是否到了评估时间
            if (rule._last_evaluation and 
                (current_time - rule._last_evaluation).total_seconds() < rule.evaluation_interval):
                continue
            
            try:
                await self._evaluate_rule(rule, current_time)
                rule._last_evaluation = current_time
            except Exception as e:
                logger.error(f"评估告警规则失败 {rule.name}: {e}", exception=e)
    
    async def _evaluate_rule(self, rule: AlertRule, current_time: datetime) -> None:
        """评估单个告警规则"""
        # 获取指标数据
        since = current_time - timedelta(seconds=rule.evaluation_interval * 2)
        metrics = self.metrics_manager.get_metrics_by_name(rule.metric_name, since)
        
        if not metrics:
            return
        
        # 使用最新的指标值
        latest_metric = metrics[-1]
        condition_met = self._evaluate_condition(latest_metric.value, rule.condition, rule.threshold)
        
        if condition_met:
            # 条件满足
            if rule._condition_met_since is None:
                rule._condition_met_since = current_time
            
            # 检查是否达到持续时间
            if ((current_time - rule._condition_met_since).total_seconds() >= rule.for_duration and
                rule._active_alert is None):
                # 触发告警
                alert = Alert(
                    id=f"{rule.id}_{int(current_time.timestamp())}",
                    name=rule.name,
                    level=rule.level,
                    message=f"{rule.description} - 当前值: {latest_metric.value}, 阈值: {rule.threshold}",
                    timestamp=current_time,
                    source=f"rule:{rule.id}",
                    tags=rule.tags.copy(),
                    metadata={
                        "rule_id": rule.id,
                        "metric_name": rule.metric_name,
                        "metric_value": latest_metric.value,
                        "threshold": rule.threshold,
                        "condition": rule.condition
                    }
                )
                
                await self._fire_alert(alert, rule)
        else:
            # 条件不满足
            rule._condition_met_since = None
            
            # 如果有活跃告警，解除它
            if rule._active_alert:
                await self.resolve_alert(rule._active_alert.id)
    
    def _evaluate_condition(self, value: Union[int, float], condition: str, threshold: Union[int, float]) -> bool:
        """评估条件"""
        try:
            if condition == ">":
                return value > threshold
            elif condition == ">=":
                return value >= threshold
            elif condition == "<":
                return value < threshold
            elif condition == "<=":
                return value <= threshold
            elif condition == "==":
                return value == threshold
            elif condition == "!=":
                return value != threshold
            else:
                logger.warning(f"未知的条件操作符: {condition}")
                return False
        except Exception as e:
            logger.error(f"条件评估失败: {e}", exception=e)
            return False
    
    async def _fire_alert(self, alert: Alert, rule: AlertRule) -> None:
        """触发告警"""
        # 添加到活跃告警
        self.active_alerts[alert.id] = alert
        rule._active_alert = alert
        
        # 添加到历史记录
        self.alert_history.append(alert)
        
        # 保留最近1000条历史记录
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        logger.warning(f"触发告警: {alert.name} - {alert.message}")
        
        # 发送通知
        await self._send_notifications(alert, rule.notification_channels)
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """解除告警"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts.pop(alert_id)
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        # 清除规则中的活跃告警引用
        for rule in self.rules.values():
            if rule._active_alert and rule._active_alert.id == alert_id:
                rule._active_alert = None
                break
        
        logger.info(f"解除告警: {alert.name}")
        
        # 发送解除通知
        rule = next((r for r in self.rules.values() if r.id == alert.metadata.get("rule_id")), None)
        if rule:
            await self._send_resolution_notifications(alert, rule.notification_channels)
        
        return True
    
    async def suppress_alert(self, alert_id: str, duration: timedelta) -> bool:
        """抑制告警"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.SUPPRESSED
        alert.suppressed_until = datetime.now() + duration
        
        logger.info(f"抑制告警: {alert.name}, 持续时间: {duration}")
        return True
    
    async def _send_notifications(self, alert: Alert, channel_names: List[str]) -> None:
        """发送告警通知"""
        tasks = []
        
        for channel_name in channel_names:
            channel = self.channels.get(channel_name)
            if channel and channel.enabled:
                task = asyncio.create_task(channel.send_alert(alert))
                tasks.append((channel_name, task))
        
        # 等待所有通知发送完成
        for channel_name, task in tasks:
            try:
                success = await task
                if success:
                    logger.info(f"告警通知发送成功: {channel_name}")
                else:
                    logger.error(f"告警通知发送失败: {channel_name}")
            except Exception as e:
                logger.error(f"告警通知发送异常 {channel_name}: {e}", exception=e)
    
    async def _send_resolution_notifications(self, alert: Alert, channel_names: List[str]) -> None:
        """发送告警解除通知"""
        tasks = []
        
        for channel_name in channel_names:
            channel = self.channels.get(channel_name)
            if channel and channel.enabled:
                task = asyncio.create_task(channel.send_resolution(alert))
                tasks.append((channel_name, task))
        
        # 等待所有通知发送完成
        for channel_name, task in tasks:
            try:
                success = await task
                if success:
                    logger.info(f"告警解除通知发送成功: {channel_name}")
                else:
                    logger.error(f"告警解除通知发送失败: {channel_name}")
            except Exception as e:
                logger.error(f"告警解除通知发送异常 {channel_name}: {e}", exception=e)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Alert]:
        """获取告警历史"""
        if limit:
            return self.alert_history[-limit:]
        return self.alert_history.copy()
    
    def get_rules(self) -> List[AlertRule]:
        """获取所有告警规则"""
        return list(self.rules.values())
    
    def get_channels(self) -> List[AlertChannel]:
        """获取所有告警通道"""
        return list(self.channels.values())


# 全局告警管理器实例
_global_alert_manager: Optional[AlertManager] = None


def get_global_alert_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


# 便捷函数
def create_cpu_usage_rule(threshold: float = 80.0, level: AlertLevel = AlertLevel.WARNING) -> AlertRule:
    """创建CPU使用率告警规则"""
    return AlertRule(
        id="cpu_usage_high",
        name="CPU使用率过高",
        description=f"CPU使用率超过{threshold}%",
        metric_name="system.cpu.usage_percent",
        condition=">",
        threshold=threshold,
        level=level,
        evaluation_interval=60,
        for_duration=300
    )


def create_memory_usage_rule(threshold: float = 85.0, level: AlertLevel = AlertLevel.WARNING) -> AlertRule:
    """创建内存使用率告警规则"""
    return AlertRule(
        id="memory_usage_high",
        name="内存使用率过高",
        description=f"内存使用率超过{threshold}%",
        metric_name="system.memory.usage_percent",
        condition=">",
        threshold=threshold,
        level=level,
        evaluation_interval=60,
        for_duration=300
    )


def create_disk_usage_rule(threshold: float = 90.0, level: AlertLevel = AlertLevel.ERROR) -> AlertRule:
    """创建磁盘使用率告警规则"""
    return AlertRule(
        id="disk_usage_high",
        name="磁盘使用率过高",
        description=f"磁盘使用率超过{threshold}%",
        metric_name="system.disk.usage_percent",
        condition=">",
        threshold=threshold,
        level=level,
        evaluation_interval=300,
        for_duration=600
    )