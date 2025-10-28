"""
高性能缓存管理模块
提供多级缓存、缓存预热、智能失效等功能
"""

import asyncio
import threading
import time
import weakref
import hashlib
import pickle
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import json

from ..core.interfaces import ICache, ILogger


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"      # 内存缓存
    L2_REDIS = "l2_redis"        # Redis缓存
    L3_DISK = "l3_disk"          # 磁盘缓存


class EvictionPolicy(Enum):
    """缓存淘汰策略"""
    LRU = "lru"                  # 最近最少使用
    LFU = "lfu"                  # 最少使用频率
    FIFO = "fifo"                # 先进先出
    TTL = "ttl"                  # 基于过期时间


@dataclass
class CacheConfig:
    """缓存配置"""
    max_size: int = 1000
    default_ttl: float = 3600.0  # 1小时
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    enable_compression: bool = False
    compression_threshold: int = 1024  # 超过1KB启用压缩
    enable_serialization: bool = True
    max_memory_usage: int = 100 * 1024 * 1024  # 100MB
    cleanup_interval: float = 300.0  # 5分钟清理一次


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size: int = 0
    
    def __post_init__(self):
        if self.expires_at is None and hasattr(self, 'ttl'):
            self.expires_at = self.created_at + self.ttl
        
        # 估算大小
        if self.size == 0:
            try:
                self.size = len(pickle.dumps(self.value))
            except Exception:
                self.size = 1024  # 默认大小
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    @property
    def age(self) -> float:
        """获取年龄"""
        return time.time() - self.created_at
    
    @property
    def idle_time(self) -> float:
        """获取空闲时间"""
        return time.time() - self.last_accessed
    
    def access(self) -> None:
        """标记访问"""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def hit_rate_percent(self) -> float:
        """命中率百分比"""
        return self.hit_rate * 100


class CacheBackend(ABC):
    """缓存后端接口"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存值"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """获取统计信息"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self, config: CacheConfig, logger: Optional[ILogger] = None):
        self.config = config
        self.logger = logger
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # 启动清理任务
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """启动清理任务"""
        async def cleanup():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Cache cleanup error: {e}")
        
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup())
        except RuntimeError:
            pass
    
    async def _cleanup_expired(self) -> None:
        """清理过期条目"""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats.evictions += 1
            
            # 检查内存使用量
            await self._enforce_memory_limit()
    
    async def _enforce_memory_limit(self) -> None:
        """强制执行内存限制"""
        current_memory = sum(entry.size for entry in self._cache.values())
        
        if current_memory <= self.config.max_memory_usage:
            return
        
        # 根据淘汰策略移除条目
        entries_to_remove = []
        
        if self.config.eviction_policy == EvictionPolicy.LRU:
            # 按最后访问时间排序
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed
            )
        elif self.config.eviction_policy == EvictionPolicy.LFU:
            # 按访问次数排序
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count
            )
        elif self.config.eviction_policy == EvictionPolicy.FIFO:
            # 按创建时间排序
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].created_at
            )
        else:  # TTL
            # 按过期时间排序
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].expires_at or float('inf')
            )
        
        # 移除条目直到内存使用量降到限制以下
        for key, entry in sorted_entries:
            entries_to_remove.append(key)
            current_memory -= entry.size
            
            if current_memory <= self.config.max_memory_usage * 0.8:  # 留20%缓冲
                break
        
        for key in entries_to_remove:
            if key in self._cache:
                del self._cache[key]
                self._stats.evictions += 1
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            entry.access()
            self._stats.hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存值"""
        try:
            async with self._lock:
                ttl = ttl or self.config.default_ttl
                expires_at = time.time() + ttl if ttl > 0 else None
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    expires_at=expires_at
                )
                
                # 检查是否需要压缩
                if (self.config.enable_compression and 
                    entry.size > self.config.compression_threshold):
                    try:
                        import gzip
                        compressed_value = gzip.compress(pickle.dumps(value))
                        if len(compressed_value) < entry.size:
                            entry.value = compressed_value
                            entry.size = len(compressed_value)
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(f"Compression failed: {e}")
                
                self._cache[key] = entry
                self._stats.sets += 1
                
                # 检查大小限制
                if len(self._cache) > self.config.max_size:
                    await self._enforce_memory_limit()
                
                return True
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                return True
            return False
    
    async def clear(self) -> bool:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            return True
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired:
                del self._cache[key]
                self._stats.evictions += 1
                return False
            
            return True
    
    async def get_stats(self) -> CacheStats:
        """获取统计信息"""
        async with self._lock:
            memory_usage = sum(entry.size for entry in self._cache.values())
            
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                sets=self._stats.sets,
                deletes=self._stats.deletes,
                evictions=self._stats.evictions,
                memory_usage=memory_usage,
                entry_count=len(self._cache)
            )
    
    def shutdown(self) -> None:
        """关闭缓存"""
        if self._cleanup_task:
            self._cleanup_task.cancel()


class MultiLevelCache(ICache):
    """多级缓存管理器"""
    
    def __init__(self, 
                 backends: Dict[CacheLevel, CacheBackend],
                 logger: Optional[ILogger] = None):
        self.backends = backends
        self.logger = logger
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """从多级缓存获取值"""
        # 按级别顺序查找
        for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
            backend = self.backends.get(level)
            if backend is None:
                continue
            
            try:
                value = await backend.get(key)
                if value is not None:
                    # 将值回填到更高级别的缓存
                    await self._backfill_cache(key, value, level)
                    
                    async with self._lock:
                        self._stats.hits += 1
                    
                    return value
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache get error in {level}: {e}")
        
        async with self._lock:
            self._stats.misses += 1
        
        return None
    
    async def _backfill_cache(self, key: str, value: Any, found_level: CacheLevel) -> None:
        """回填缓存到更高级别"""
        levels_to_backfill = []
        
        if found_level == CacheLevel.L3_DISK:
            levels_to_backfill = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]
        elif found_level == CacheLevel.L2_REDIS:
            levels_to_backfill = [CacheLevel.L1_MEMORY]
        
        for level in levels_to_backfill:
            backend = self.backends.get(level)
            if backend:
                try:
                    await backend.set(key, value)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Cache backfill error in {level}: {e}")
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存值到所有级别"""
        success = True
        
        for backend in self.backends.values():
            try:
                result = await backend.set(key, value, ttl)
                success = success and result
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache set error: {e}")
                success = False
        
        if success:
            async with self._lock:
                self._stats.sets += 1
        
        return success
    
    async def delete(self, key: str) -> bool:
        """从所有级别删除缓存值"""
        success = True
        
        for backend in self.backends.values():
            try:
                result = await backend.delete(key)
                success = success and result
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache delete error: {e}")
                success = False
        
        if success:
            async with self._lock:
                self._stats.deletes += 1
        
        return success
    
    async def clear(self) -> bool:
        """清空所有级别的缓存"""
        success = True
        
        for backend in self.backends.values():
            try:
                result = await backend.clear()
                success = success and result
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache clear error: {e}")
                success = False
        
        return success
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在于任何级别"""
        for backend in self.backends.values():
            try:
                if await backend.exists(key):
                    return True
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache exists error: {e}")
        
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取所有级别的统计信息"""
        stats = {}
        
        for level, backend in self.backends.items():
            try:
                backend_stats = await backend.get_stats()
                stats[level.value] = {
                    'hits': backend_stats.hits,
                    'misses': backend_stats.misses,
                    'sets': backend_stats.sets,
                    'deletes': backend_stats.deletes,
                    'evictions': backend_stats.evictions,
                    'memory_usage': backend_stats.memory_usage,
                    'entry_count': backend_stats.entry_count,
                    'hit_rate_percent': backend_stats.hit_rate_percent
                }
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Cache stats error for {level}: {e}")
                stats[level.value] = {'error': str(e)}
        
        # 添加总体统计
        stats['total'] = {
            'hits': self._stats.hits,
            'misses': self._stats.misses,
            'sets': self._stats.sets,
            'deletes': self._stats.deletes,
            'hit_rate_percent': self._stats.hit_rate_percent
        }
        
        return stats


class CacheWarmer:
    """缓存预热器"""
    
    def __init__(self, cache: ICache, logger: Optional[ILogger] = None):
        self.cache = cache
        self.logger = logger
        self._warming_tasks: Set[asyncio.Task] = set()
    
    async def warm_cache(self, 
                        data_loader: Callable[[], Dict[str, Any]],
                        batch_size: int = 100,
                        ttl: Optional[float] = None) -> None:
        """预热缓存"""
        try:
            data = data_loader()
            
            # 分批处理
            items = list(data.items())
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # 并发设置缓存
                tasks = [
                    self.cache.set(key, value, ttl)
                    for key, value in batch
                ]
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                if self.logger:
                    self.logger.info(f"Warmed {len(batch)} cache entries")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Cache warming error: {e}")
    
    async def warm_cache_async(self,
                              data_loader: Callable[[], Dict[str, Any]],
                              batch_size: int = 100,
                              ttl: Optional[float] = None) -> asyncio.Task:
        """异步预热缓存"""
        task = asyncio.create_task(
            self.warm_cache(data_loader, batch_size, ttl)
        )
        self._warming_tasks.add(task)
        
        # 清理完成的任务
        task.add_done_callback(self._warming_tasks.discard)
        
        return task
    
    async def wait_for_warming(self) -> None:
        """等待所有预热任务完成"""
        if self._warming_tasks:
            await asyncio.gather(*self._warming_tasks, return_exceptions=True)


class SmartCacheInvalidator:
    """智能缓存失效器"""
    
    def __init__(self, cache: ICache, logger: Optional[ILogger] = None):
        self.cache = cache
        self.logger = logger
        self._invalidation_patterns: Dict[str, List[str]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
    
    def register_pattern(self, pattern: str, keys: List[str]) -> None:
        """注册失效模式"""
        self._invalidation_patterns[pattern] = keys
    
    def register_dependency(self, key: str, dependencies: List[str]) -> None:
        """注册键依赖关系"""
        self._dependency_graph[key] = set(dependencies)
    
    async def invalidate_by_pattern(self, pattern: str) -> None:
        """按模式失效缓存"""
        keys = self._invalidation_patterns.get(pattern, [])
        
        for key in keys:
            await self.cache.delete(key)
            
            # 递归失效依赖的键
            await self._invalidate_dependencies(key)
        
        if self.logger:
            self.logger.info(f"Invalidated {len(keys)} cache entries by pattern: {pattern}")
    
    async def _invalidate_dependencies(self, key: str) -> None:
        """递归失效依赖的键"""
        for dependent_key, dependencies in self._dependency_graph.items():
            if key in dependencies:
                await self.cache.delete(dependent_key)
                await self._invalidate_dependencies(dependent_key)


def create_cache_manager(config: Optional[CacheConfig] = None,
                        logger: Optional[ILogger] = None) -> MultiLevelCache:
    """创建缓存管理器"""
    config = config or CacheConfig()
    
    backends = {
        CacheLevel.L1_MEMORY: MemoryCacheBackend(config, logger)
    }
    
    return MultiLevelCache(backends, logger)