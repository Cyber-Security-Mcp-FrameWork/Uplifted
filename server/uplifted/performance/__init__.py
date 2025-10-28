"""
性能优化模块
提供连接池管理、缓存优化、异步处理等性能优化功能
"""

from .connection_pool import (
    ConnectionPool,
    HTTPConnectionPool,
    AsyncHTTPConnectionPool,
    DatabaseConnectionPool,
    ConnectionPoolManager,
    ConnectionConfig,
    ConnectionStats,
    get_global_pool_manager
)

from .cache_manager import (
    MultiLevelCache,
    MemoryCacheBackend,
    CacheBackend,
    CacheLevel,
    EvictionPolicy,
    CacheConfig,
    CacheStats,
    CacheEntry,
    CacheWarmer,
    SmartCacheInvalidator,
    create_cache_manager
)

from .async_processor import (
    AsyncTaskProcessor,
    BatchProcessor,
    ConcurrencyLimiter,
    AsyncPipeline,
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    BatchConfig,
    ProcessorStats,
    get_global_processor
)

from .metrics import (
    MetricsManager,
    MetricCollector,
    SystemMetricCollector,
    ApplicationMetricCollector,
    MetricValue,
    MetricType,
    SystemMetrics,
    ApplicationMetrics,
    get_global_metrics_manager,
    increment_counter,
    set_gauge,
    record_histogram,
    record_timer
)

__all__ = [
    'ConnectionPool',
    'HTTPConnectionPool', 
    'DatabaseConnectionPool',
    'PerformanceCacheManager',
    'CacheStrategy',
    'CacheMetrics',
    'AsyncTaskManager',
    'TaskQueue',
    'TaskResult',
    'PerformanceMetrics',
    'MetricsCollector',
    'MetricsReporter'
]