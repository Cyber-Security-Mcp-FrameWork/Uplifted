"""
指标收集模块
提供系统指标、应用指标和自定义指标的收集和管理功能
"""

import asyncio
import psutil
import time
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor

from .logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"          # 计数器（只增不减）
    GAUGE = "gauge"             # 仪表盘（可增可减）
    HISTOGRAM = "histogram"      # 直方图
    SUMMARY = "summary"         # 摘要
    TIMER = "timer"             # 计时器


@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class HistogramBucket:
    """直方图桶"""
    upper_bound: float
    count: int


@dataclass
class HistogramData:
    """直方图数据"""
    buckets: List[HistogramBucket]
    count: int
    sum: float


@dataclass
class SummaryData:
    """摘要数据"""
    count: int
    sum: float
    quantiles: Dict[float, float]  # 分位数


class MetricsCollector(ABC):
    """指标收集器抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._lock = threading.Lock()
    
    @abstractmethod
    async def collect(self) -> List[MetricValue]:
        """收集指标"""
        pass
    
    def add_metric(self, metric: MetricValue) -> None:
        """添加指标"""
        with self._lock:
            self._metrics[metric.name].append(metric)
            
            # 保留最近1000个数据点
            if len(self._metrics[metric.name]) > 1000:
                self._metrics[metric.name] = self._metrics[metric.name][-1000:]
    
    def get_metrics(self, name: Optional[str] = None) -> List[MetricValue]:
        """获取指标"""
        with self._lock:
            if name:
                return self._metrics.get(name, []).copy()
            else:
                all_metrics = []
                for metrics_list in self._metrics.values():
                    all_metrics.extend(metrics_list)
                return all_metrics
    
    def clear_metrics(self, name: Optional[str] = None) -> None:
        """清除指标"""
        with self._lock:
            if name:
                self._metrics.pop(name, None)
            else:
                self._metrics.clear()


class SystemMetricsCollector(MetricsCollector):
    """系统指标收集器"""
    
    def __init__(self):
        super().__init__("system")
        self._last_cpu_times = None
        self._last_network_io = None
        self._last_disk_io = None
    
    async def collect(self) -> List[MetricValue]:
        """收集系统指标"""
        if not self.enabled:
            return []
        
        metrics = []
        timestamp = datetime.now()
        
        try:
            # CPU指标
            cpu_metrics = await self._collect_cpu_metrics(timestamp)
            metrics.extend(cpu_metrics)
            
            # 内存指标
            memory_metrics = await self._collect_memory_metrics(timestamp)
            metrics.extend(memory_metrics)
            
            # 磁盘指标
            disk_metrics = await self._collect_disk_metrics(timestamp)
            metrics.extend(disk_metrics)
            
            # 网络指标
            network_metrics = await self._collect_network_metrics(timestamp)
            metrics.extend(network_metrics)
            
            # 进程指标
            process_metrics = await self._collect_process_metrics(timestamp)
            metrics.extend(process_metrics)
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}", exception=e)
        
        # 添加到内部存储
        for metric in metrics:
            self.add_metric(metric)
        
        return metrics
    
    async def _collect_cpu_metrics(self, timestamp: datetime) -> List[MetricValue]:
        """收集CPU指标"""
        metrics = []
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=None)
        metrics.append(MetricValue(
            name="system.cpu.usage_percent",
            value=cpu_percent,
            metric_type=MetricType.GAUGE,
            timestamp=timestamp,
            unit="percent",
            description="CPU使用率"
        ))
        
        # 每个CPU核心的使用率
        cpu_percents = psutil.cpu_percent(interval=None, percpu=True)
        for i, percent in enumerate(cpu_percents):
            metrics.append(MetricValue(
                name="system.cpu.core_usage_percent",
                value=percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                tags={"core": str(i)},
                unit="percent",
                description=f"CPU核心{i}使用率"
            ))
        
        # CPU时间
        cpu_times = psutil.cpu_times()
        if self._last_cpu_times:
            user_time = cpu_times.user - self._last_cpu_times.user
            system_time = cpu_times.system - self._last_cpu_times.system
            idle_time = cpu_times.idle - self._last_cpu_times.idle
            
            metrics.extend([
                MetricValue(
                    name="system.cpu.user_time",
                    value=user_time,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="seconds",
                    description="用户态CPU时间"
                ),
                MetricValue(
                    name="system.cpu.system_time",
                    value=system_time,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="seconds",
                    description="内核态CPU时间"
                ),
                MetricValue(
                    name="system.cpu.idle_time",
                    value=idle_time,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="seconds",
                    description="空闲CPU时间"
                )
            ])
        
        self._last_cpu_times = cpu_times
        
        # 负载平均值（仅Linux/Unix）
        try:
            load_avg = psutil.getloadavg()
            for i, period in enumerate(['1min', '5min', '15min']):
                metrics.append(MetricValue(
                    name="system.load_average",
                    value=load_avg[i],
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    tags={"period": period},
                    description=f"{period}负载平均值"
                ))
        except AttributeError:
            # Windows不支持getloadavg
            pass
        
        return metrics
    
    async def _collect_memory_metrics(self, timestamp: datetime) -> List[MetricValue]:
        """收集内存指标"""
        metrics = []
        
        # 虚拟内存
        virtual_memory = psutil.virtual_memory()
        metrics.extend([
            MetricValue(
                name="system.memory.total",
                value=virtual_memory.total,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="bytes",
                description="总内存"
            ),
            MetricValue(
                name="system.memory.available",
                value=virtual_memory.available,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="bytes",
                description="可用内存"
            ),
            MetricValue(
                name="system.memory.used",
                value=virtual_memory.used,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="bytes",
                description="已用内存"
            ),
            MetricValue(
                name="system.memory.usage_percent",
                value=virtual_memory.percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="percent",
                description="内存使用率"
            )
        ])
        
        # 交换内存
        swap_memory = psutil.swap_memory()
        metrics.extend([
            MetricValue(
                name="system.swap.total",
                value=swap_memory.total,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="bytes",
                description="总交换内存"
            ),
            MetricValue(
                name="system.swap.used",
                value=swap_memory.used,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="bytes",
                description="已用交换内存"
            ),
            MetricValue(
                name="system.swap.usage_percent",
                value=swap_memory.percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="percent",
                description="交换内存使用率"
            )
        ])
        
        return metrics
    
    async def _collect_disk_metrics(self, timestamp: datetime) -> List[MetricValue]:
        """收集磁盘指标"""
        metrics = []
        
        # 磁盘使用情况
        disk_partitions = psutil.disk_partitions()
        for partition in disk_partitions:
            try:
                disk_usage = psutil.disk_usage(partition.mountpoint)
                device = partition.device.replace('\\', '_').replace(':', '')
                
                metrics.extend([
                    MetricValue(
                        name="system.disk.total",
                        value=disk_usage.total,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        tags={"device": device, "mountpoint": partition.mountpoint},
                        unit="bytes",
                        description="磁盘总容量"
                    ),
                    MetricValue(
                        name="system.disk.used",
                        value=disk_usage.used,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        tags={"device": device, "mountpoint": partition.mountpoint},
                        unit="bytes",
                        description="磁盘已用容量"
                    ),
                    MetricValue(
                        name="system.disk.usage_percent",
                        value=disk_usage.percent,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        tags={"device": device, "mountpoint": partition.mountpoint},
                        unit="percent",
                        description="磁盘使用率"
                    )
                ])
            except (PermissionError, OSError):
                continue
        
        # 磁盘I/O
        disk_io = psutil.disk_io_counters()
        if disk_io and self._last_disk_io:
            read_bytes = disk_io.read_bytes - self._last_disk_io.read_bytes
            write_bytes = disk_io.write_bytes - self._last_disk_io.write_bytes
            read_count = disk_io.read_count - self._last_disk_io.read_count
            write_count = disk_io.write_count - self._last_disk_io.write_count
            
            metrics.extend([
                MetricValue(
                    name="system.disk.read_bytes",
                    value=read_bytes,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="bytes",
                    description="磁盘读取字节数"
                ),
                MetricValue(
                    name="system.disk.write_bytes",
                    value=write_bytes,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="bytes",
                    description="磁盘写入字节数"
                ),
                MetricValue(
                    name="system.disk.read_count",
                    value=read_count,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    description="磁盘读取次数"
                ),
                MetricValue(
                    name="system.disk.write_count",
                    value=write_count,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    description="磁盘写入次数"
                )
            ])
        
        if disk_io:
            self._last_disk_io = disk_io
        
        return metrics
    
    async def _collect_network_metrics(self, timestamp: datetime) -> List[MetricValue]:
        """收集网络指标"""
        metrics = []
        
        # 网络I/O
        network_io = psutil.net_io_counters()
        if network_io and self._last_network_io:
            bytes_sent = network_io.bytes_sent - self._last_network_io.bytes_sent
            bytes_recv = network_io.bytes_recv - self._last_network_io.bytes_recv
            packets_sent = network_io.packets_sent - self._last_network_io.packets_sent
            packets_recv = network_io.packets_recv - self._last_network_io.packets_recv
            
            metrics.extend([
                MetricValue(
                    name="system.network.bytes_sent",
                    value=bytes_sent,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="bytes",
                    description="网络发送字节数"
                ),
                MetricValue(
                    name="system.network.bytes_recv",
                    value=bytes_recv,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    unit="bytes",
                    description="网络接收字节数"
                ),
                MetricValue(
                    name="system.network.packets_sent",
                    value=packets_sent,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    description="网络发送包数"
                ),
                MetricValue(
                    name="system.network.packets_recv",
                    value=packets_recv,
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                    description="网络接收包数"
                )
            ])
        
        if network_io:
            self._last_network_io = network_io
        
        # 网络连接数
        try:
            connections = psutil.net_connections()
            connection_counts = defaultdict(int)
            for conn in connections:
                connection_counts[conn.status] += 1
            
            for status, count in connection_counts.items():
                metrics.append(MetricValue(
                    name="system.network.connections",
                    value=count,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    tags={"status": status},
                    description=f"{status}状态的网络连接数"
                ))
        except (PermissionError, psutil.AccessDenied):
            pass
        
        return metrics
    
    async def _collect_process_metrics(self, timestamp: datetime) -> List[MetricValue]:
        """收集进程指标"""
        metrics = []
        
        try:
            # 当前进程
            current_process = psutil.Process()
            
            # 进程CPU使用率
            cpu_percent = current_process.cpu_percent()
            metrics.append(MetricValue(
                name="process.cpu.usage_percent",
                value=cpu_percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="percent",
                description="进程CPU使用率"
            ))
            
            # 进程内存使用
            memory_info = current_process.memory_info()
            metrics.extend([
                MetricValue(
                    name="process.memory.rss",
                    value=memory_info.rss,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    unit="bytes",
                    description="进程常驻内存"
                ),
                MetricValue(
                    name="process.memory.vms",
                    value=memory_info.vms,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    unit="bytes",
                    description="进程虚拟内存"
                )
            ])
            
            # 进程内存百分比
            memory_percent = current_process.memory_percent()
            metrics.append(MetricValue(
                name="process.memory.usage_percent",
                value=memory_percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                unit="percent",
                description="进程内存使用率"
            ))
            
            # 进程线程数
            num_threads = current_process.num_threads()
            metrics.append(MetricValue(
                name="process.threads.count",
                value=num_threads,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                description="进程线程数"
            ))
            
            # 进程文件描述符数（仅Unix）
            try:
                num_fds = current_process.num_fds()
                metrics.append(MetricValue(
                    name="process.fds.count",
                    value=num_fds,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                    description="进程文件描述符数"
                ))
            except AttributeError:
                # Windows不支持num_fds
                pass
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"无法获取进程指标: {e}")
        
        return metrics


class ApplicationMetricsCollector(MetricsCollector):
    """应用指标收集器"""
    
    def __init__(self):
        super().__init__("application")
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
    
    async def collect(self) -> List[MetricValue]:
        """收集应用指标"""
        if not self.enabled:
            return []
        
        metrics = []
        timestamp = datetime.now()
        
        # 计数器
        for name, value in self._counters.items():
            metrics.append(MetricValue(
                name=f"app.counter.{name}",
                value=value,
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
                description=f"应用计数器: {name}"
            ))
        
        # 仪表盘
        for name, value in self._gauges.items():
            metrics.append(MetricValue(
                name=f"app.gauge.{name}",
                value=value,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
                description=f"应用仪表盘: {name}"
            ))
        
        # 直方图
        for name, values in self._histograms.items():
            if values:
                metrics.extend([
                    MetricValue(
                        name=f"app.histogram.{name}.count",
                        value=len(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        description=f"直方图{name}计数"
                    ),
                    MetricValue(
                        name=f"app.histogram.{name}.sum",
                        value=sum(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        description=f"直方图{name}总和"
                    ),
                    MetricValue(
                        name=f"app.histogram.{name}.avg",
                        value=sum(values) / len(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        description=f"直方图{name}平均值"
                    )
                ])
        
        # 计时器
        for name, values in self._timers.items():
            if values:
                metrics.extend([
                    MetricValue(
                        name=f"app.timer.{name}.count",
                        value=len(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        description=f"计时器{name}计数"
                    ),
                    MetricValue(
                        name=f"app.timer.{name}.avg",
                        value=sum(values) / len(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="seconds",
                        description=f"计时器{name}平均时间"
                    ),
                    MetricValue(
                        name=f"app.timer.{name}.min",
                        value=min(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="seconds",
                        description=f"计时器{name}最小时间"
                    ),
                    MetricValue(
                        name=f"app.timer.{name}.max",
                        value=max(values),
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                        unit="seconds",
                        description=f"计时器{name}最大时间"
                    )
                ])
        
        # 添加到内部存储
        for metric in metrics:
            self.add_metric(metric)
        
        return metrics
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """增加计数器"""
        key = name
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{name},{tag_str}"
        
        self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """设置仪表盘值"""
        key = name
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{name},{tag_str}"
        
        self._gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """记录直方图值"""
        key = name
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{name},{tag_str}"
        
        self._histograms[key].append(value)
        
        # 保留最近1000个值
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]
    
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """记录计时器值"""
        key = name
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{name},{tag_str}"
        
        self._timers[key].append(duration)
        
        # 保留最近1000个值
        if len(self._timers[key]) > 1000:
            self._timers[key] = self._timers[key][-1000:]


class CustomMetricsCollector(MetricsCollector):
    """自定义指标收集器"""
    
    def __init__(self):
        super().__init__("custom")
        self._custom_collectors: List[Callable[[], List[MetricValue]]] = []
    
    async def collect(self) -> List[MetricValue]:
        """收集自定义指标"""
        if not self.enabled:
            return []
        
        metrics = []
        
        for collector_func in self._custom_collectors:
            try:
                custom_metrics = collector_func()
                metrics.extend(custom_metrics)
            except Exception as e:
                logger.error(f"自定义指标收集器执行失败: {e}", exception=e)
        
        # 添加到内部存储
        for metric in metrics:
            self.add_metric(metric)
        
        return metrics
    
    def register_collector(self, collector_func: Callable[[], List[MetricValue]]) -> None:
        """注册自定义指标收集器"""
        self._custom_collectors.append(collector_func)
    
    def unregister_collector(self, collector_func: Callable[[], List[MetricValue]]) -> None:
        """注销自定义指标收集器"""
        if collector_func in self._custom_collectors:
            self._custom_collectors.remove(collector_func)


class MetricsManager:
    """指标管理器"""
    
    def __init__(self):
        self.collectors: Dict[str, MetricsCollector] = {}
        self._collection_interval = 30  # 30秒
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def register_collector(self, collector: MetricsCollector) -> None:
        """注册指标收集器"""
        self.collectors[collector.name] = collector
        logger.info(f"注册指标收集器: {collector.name}")
    
    def unregister_collector(self, name: str) -> None:
        """注销指标收集器"""
        if name in self.collectors:
            del self.collectors[name]
            logger.info(f"注销指标收集器: {name}")
    
    def get_collector(self, name: str) -> Optional[MetricsCollector]:
        """获取指标收集器"""
        return self.collectors.get(name)
    
    def set_collection_interval(self, interval: int) -> None:
        """设置收集间隔（秒）"""
        self._collection_interval = interval
    
    async def start_collection(self) -> None:
        """开始指标收集"""
        if self._running:
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("开始指标收集")
    
    async def stop_collection(self) -> None:
        """停止指标收集"""
        if not self._running:
            return
        
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        self._executor.shutdown(wait=True)
        logger.info("停止指标收集")
    
    async def _collection_loop(self) -> None:
        """指标收集循环"""
        while self._running:
            try:
                await self.collect_all()
                await asyncio.sleep(self._collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指标收集循环错误: {e}", exception=e)
                await asyncio.sleep(5)  # 错误后短暂等待
    
    async def collect_all(self) -> Dict[str, List[MetricValue]]:
        """收集所有指标"""
        results = {}
        
        # 并发收集所有指标
        tasks = []
        for name, collector in self.collectors.items():
            if collector.enabled:
                task = asyncio.create_task(collector.collect())
                tasks.append((name, task))
        
        # 等待所有收集任务完成
        for name, task in tasks:
            try:
                metrics = await task
                results[name] = metrics
            except Exception as e:
                logger.error(f"收集器 {name} 执行失败: {e}", exception=e)
                results[name] = []
        
        return results
    
    def get_all_metrics(self, since: Optional[datetime] = None) -> Dict[str, List[MetricValue]]:
        """获取所有指标"""
        results = {}
        
        for name, collector in self.collectors.items():
            metrics = collector.get_metrics()
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            results[name] = metrics
        
        return results
    
    def get_metrics_by_name(self, metric_name: str, since: Optional[datetime] = None) -> List[MetricValue]:
        """根据名称获取指标"""
        all_metrics = []
        
        for collector in self.collectors.values():
            metrics = collector.get_metrics(metric_name)
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            all_metrics.extend(metrics)
        
        return sorted(all_metrics, key=lambda x: x.timestamp)
    
    def clear_all_metrics(self) -> None:
        """清除所有指标"""
        for collector in self.collectors.values():
            collector.clear_metrics()
        
        logger.info("清除所有指标数据")


# 全局指标管理器实例
_global_metrics_manager: Optional[MetricsManager] = None


def get_global_metrics_manager() -> MetricsManager:
    """获取全局指标管理器实例"""
    global _global_metrics_manager
    if _global_metrics_manager is None:
        _global_metrics_manager = MetricsManager()
        
        # 注册默认收集器
        _global_metrics_manager.register_collector(SystemMetricsCollector())
        _global_metrics_manager.register_collector(ApplicationMetricsCollector())
        _global_metrics_manager.register_collector(CustomMetricsCollector())
    
    return _global_metrics_manager


def get_system_collector() -> SystemMetricsCollector:
    """获取系统指标收集器"""
    manager = get_global_metrics_manager()
    return manager.get_collector("system")


def get_application_collector() -> ApplicationMetricsCollector:
    """获取应用指标收集器"""
    manager = get_global_metrics_manager()
    return manager.get_collector("application")


def get_custom_collector() -> CustomMetricsCollector:
    """获取自定义指标收集器"""
    manager = get_global_metrics_manager()
    return manager.get_collector("custom")


# 便捷函数
def increment_counter(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
    """增加计数器"""
    collector = get_application_collector()
    if collector:
        collector.increment_counter(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """设置仪表盘值"""
    collector = get_application_collector()
    if collector:
        collector.set_gauge(name, value, tags)


def record_histogram(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """记录直方图值"""
    collector = get_application_collector()
    if collector:
        collector.record_histogram(name, value, tags)


def record_timer(name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
    """记录计时器值"""
    collector = get_application_collector()
    if collector:
        collector.record_timer(name, duration, tags)