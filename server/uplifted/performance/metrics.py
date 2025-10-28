"""
性能指标监控模块
提供系统性能监控、指标收集和分析功能
"""

import asyncio
import threading
import time
import psutil
import gc
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics

from ..core.interfaces import ILogger


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"              # 仪表盘
    HISTOGRAM = "histogram"      # 直方图
    TIMER = "timer"              # 计时器


@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: Union[int, float]
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage_percent: float
    disk_used: int
    disk_free: int
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    file_descriptors: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class ApplicationMetrics:
    """应用指标"""
    request_count: int = 0
    error_count: int = 0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    queue_size: int = 0
    gc_collections: int = 0
    timestamp: float = field(default_factory=time.time)


class MetricCollector(ABC):
    """指标收集器接口"""
    
    @abstractmethod
    async def collect(self) -> List[MetricValue]:
        """收集指标"""
        pass


class SystemMetricCollector(MetricCollector):
    """系统指标收集器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._process = psutil.Process()
        self._last_network_stats = None
    
    async def collect(self) -> List[MetricValue]:
        """收集系统指标"""
        metrics = []
        timestamp = time.time()
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            metrics.append(MetricValue(
                name="system.cpu.percent",
                value=cpu_percent,
                timestamp=timestamp,
                metric_type=MetricType.GAUGE
            ))
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            metrics.extend([
                MetricValue(
                    name="system.memory.percent",
                    value=memory.percent,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="system.memory.used",
                    value=memory.used,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="system.memory.available",
                    value=memory.available,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                )
            ])
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            metrics.extend([
                MetricValue(
                    name="system.disk.percent",
                    value=(disk.used / disk.total) * 100,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="system.disk.used",
                    value=disk.used,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="system.disk.free",
                    value=disk.free,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                )
            ])
            
            # 网络统计
            network = psutil.net_io_counters()
            if network:
                metrics.extend([
                    MetricValue(
                        name="system.network.bytes_sent",
                        value=network.bytes_sent,
                        timestamp=timestamp,
                        metric_type=MetricType.COUNTER
                    ),
                    MetricValue(
                        name="system.network.bytes_recv",
                        value=network.bytes_recv,
                        timestamp=timestamp,
                        metric_type=MetricType.COUNTER
                    )
                ])
            
            # 进程信息
            process_count = len(psutil.pids())
            metrics.append(MetricValue(
                name="system.process.count",
                value=process_count,
                timestamp=timestamp,
                metric_type=MetricType.GAUGE
            ))
            
            # 当前进程信息
            process_memory = self._process.memory_info()
            metrics.extend([
                MetricValue(
                    name="process.memory.rss",
                    value=process_memory.rss,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="process.memory.vms",
                    value=process_memory.vms,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="process.cpu.percent",
                    value=self._process.cpu_percent(),
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ),
                MetricValue(
                    name="process.threads",
                    value=self._process.num_threads(),
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                )
            ])
            
            # 文件描述符（仅Unix系统）
            try:
                fd_count = self._process.num_fds()
                metrics.append(MetricValue(
                    name="process.file_descriptors",
                    value=fd_count,
                    timestamp=timestamp,
                    metric_type=MetricType.GAUGE
                ))
            except (AttributeError, psutil.AccessDenied):
                pass
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error collecting system metrics: {e}")
        
        return metrics


class ApplicationMetricCollector(MetricCollector):
    """应用指标收集器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.RLock()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """增加计数器"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """设置仪表盘值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录直方图值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录计时器值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._timers[key].append(duration)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        """解析指标键"""
        if '[' not in key:
            return key, {}
        
        name, label_part = key.split('[', 1)
        label_part = label_part.rstrip(']')
        
        labels = {}
        if label_part:
            for pair in label_part.split(','):
                k, v = pair.split('=', 1)
                labels[k] = v
        
        return name, labels
    
    async def collect(self) -> List[MetricValue]:
        """收集应用指标"""
        metrics = []
        timestamp = time.time()
        
        with self._lock:
            # 收集计数器
            for key, value in self._counters.items():
                name, labels = self._parse_key(key)
                metrics.append(MetricValue(
                    name=name,
                    value=value,
                    timestamp=timestamp,
                    labels=labels,
                    metric_type=MetricType.COUNTER
                ))
            
            # 收集仪表盘
            for key, value in self._gauges.items():
                name, labels = self._parse_key(key)
                metrics.append(MetricValue(
                    name=name,
                    value=value,
                    timestamp=timestamp,
                    labels=labels,
                    metric_type=MetricType.GAUGE
                ))
            
            # 收集直方图统计
            for key, values in self._histograms.items():
                if values:
                    name, labels = self._parse_key(key)
                    values_list = list(values)
                    
                    metrics.extend([
                        MetricValue(
                            name=f"{name}.count",
                            value=len(values_list),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.avg",
                            value=statistics.mean(values_list),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.p50",
                            value=statistics.median(values_list),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.p95",
                            value=self._percentile(values_list, 0.95),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.p99",
                            value=self._percentile(values_list, 0.99),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        )
                    ])
            
            # 收集计时器统计
            for key, values in self._timers.items():
                if values:
                    name, labels = self._parse_key(key)
                    values_list = list(values)
                    
                    metrics.extend([
                        MetricValue(
                            name=f"{name}.count",
                            value=len(values_list),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.avg",
                            value=statistics.mean(values_list),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.p95",
                            value=self._percentile(values_list, 0.95),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        ),
                        MetricValue(
                            name=f"{name}.p99",
                            value=self._percentile(values_list, 0.99),
                            timestamp=timestamp,
                            labels=labels,
                            metric_type=MetricType.GAUGE
                        )
                    ])
        
        # 添加GC统计
        gc_stats = gc.get_stats()
        if gc_stats:
            for i, stat in enumerate(gc_stats):
                metrics.extend([
                    MetricValue(
                        name="gc.collections",
                        value=stat.get('collections', 0),
                        timestamp=timestamp,
                        labels={'generation': str(i)},
                        metric_type=MetricType.COUNTER
                    ),
                    MetricValue(
                        name="gc.collected",
                        value=stat.get('collected', 0),
                        timestamp=timestamp,
                        labels={'generation': str(i)},
                        metric_type=MetricType.COUNTER
                    ),
                    MetricValue(
                        name="gc.uncollectable",
                        value=stat.get('uncollectable', 0),
                        timestamp=timestamp,
                        labels={'generation': str(i)},
                        metric_type=MetricType.COUNTER
                    )
                ])
        
        return metrics
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]


class MetricsManager:
    """指标管理器"""
    
    def __init__(self, 
                 collection_interval: float = 60.0,
                 retention_period: float = 3600.0,
                 logger: Optional[ILogger] = None):
        self.collection_interval = collection_interval
        self.retention_period = retention_period
        self.logger = logger
        
        self._collectors: List[MetricCollector] = []
        self._metrics_history: deque = deque()
        self._collection_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._lock = asyncio.Lock()
        
        # 默认收集器
        self.system_collector = SystemMetricCollector(logger)
        self.app_collector = ApplicationMetricCollector(logger)
        
        self.add_collector(self.system_collector)
        self.add_collector(self.app_collector)
        
        # 启动收集任务
        self._start_collection()
    
    def add_collector(self, collector: MetricCollector) -> None:
        """添加指标收集器"""
        self._collectors.append(collector)
    
    def _start_collection(self) -> None:
        """启动指标收集任务"""
        async def collect_metrics():
            while not self._shutdown:
                try:
                    await self._collect_all_metrics()
                    await asyncio.sleep(self.collection_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Metrics collection error: {e}")
                    await asyncio.sleep(self.collection_interval)
        
        try:
            loop = asyncio.get_event_loop()
            self._collection_task = loop.create_task(collect_metrics())
        except RuntimeError:
            pass
    
    async def _collect_all_metrics(self) -> None:
        """收集所有指标"""
        all_metrics = []
        
        for collector in self._collectors:
            try:
                metrics = await collector.collect()
                all_metrics.extend(metrics)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error collecting metrics from {collector}: {e}")
        
        async with self._lock:
            # 添加到历史记录
            self._metrics_history.append({
                'timestamp': time.time(),
                'metrics': all_metrics
            })
            
            # 清理过期数据
            cutoff_time = time.time() - self.retention_period
            while (self._metrics_history and 
                   self._metrics_history[0]['timestamp'] < cutoff_time):
                self._metrics_history.popleft()
    
    async def get_current_metrics(self) -> List[MetricValue]:
        """获取当前指标"""
        all_metrics = []
        
        for collector in self._collectors:
            try:
                metrics = await collector.collect()
                all_metrics.extend(metrics)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error collecting current metrics from {collector}: {e}")
        
        return all_metrics
    
    async def get_metrics_history(self, 
                                 start_time: Optional[float] = None,
                                 end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """获取指标历史"""
        async with self._lock:
            history = list(self._metrics_history)
        
        if start_time or end_time:
            filtered_history = []
            for entry in history:
                timestamp = entry['timestamp']
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                filtered_history.append(entry)
            return filtered_history
        
        return history
    
    async def get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """获取指标摘要"""
        async with self._lock:
            history = list(self._metrics_history)
        
        values = []
        for entry in history:
            for metric in entry['metrics']:
                if metric.name == metric_name:
                    values.append(metric.value)
        
        if not values:
            return {'error': f'No data found for metric {metric_name}'}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99)
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    async def export_metrics(self, format_type: str = 'json') -> str:
        """导出指标"""
        metrics = await self.get_current_metrics()
        
        if format_type == 'json':
            import json
            return json.dumps([
                {
                    'name': m.name,
                    'value': m.value,
                    'timestamp': m.timestamp,
                    'labels': m.labels,
                    'type': m.metric_type.value
                }
                for m in metrics
            ], indent=2)
        
        elif format_type == 'prometheus':
            lines = []
            for metric in metrics:
                labels_str = ''
                if metric.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    labels_str = '{' + ','.join(label_pairs) + '}'
                
                lines.append(f'{metric.name}{labels_str} {metric.value} {int(metric.timestamp * 1000)}')
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def shutdown(self) -> None:
        """关闭指标管理器"""
        self._shutdown = True
        
        if self._collection_task:
            self._collection_task.cancel()


# 全局指标管理器实例
_global_metrics_manager: Optional[MetricsManager] = None
_metrics_lock = threading.Lock()


def get_global_metrics_manager() -> MetricsManager:
    """获取全局指标管理器"""
    global _global_metrics_manager
    
    if _global_metrics_manager is None:
        with _metrics_lock:
            if _global_metrics_manager is None:
                _global_metrics_manager = MetricsManager()
    
    return _global_metrics_manager


# 便捷函数
def increment_counter(name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
    """增加计数器"""
    manager = get_global_metrics_manager()
    manager.app_collector.increment_counter(name, value, labels)


def set_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """设置仪表盘值"""
    manager = get_global_metrics_manager()
    manager.app_collector.set_gauge(name, value, labels)


def record_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """记录直方图值"""
    manager = get_global_metrics_manager()
    manager.app_collector.record_histogram(name, value, labels)


def record_timer(name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
    """记录计时器值"""
    manager = get_global_metrics_manager()
    manager.app_collector.record_timer(name, duration, labels)