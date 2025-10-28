"""
请求限流模块
提供基于令牌桶算法的请求限流功能
"""

import time
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from ..storage.configuration import ClientConfiguration


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10  # 突发请求数量


@dataclass
class TokenBucket:
    """令牌桶"""
    capacity: int
    tokens: float
    last_refill: float
    refill_rate: float  # 每秒补充的令牌数
    
    def consume(self, tokens: int = 1) -> bool:
        """消费令牌"""
        now = time.time()
        
        # 补充令牌
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = now
        
        # 检查是否有足够的令牌
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """请求限流器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, Dict[str, TokenBucket]] = defaultdict(dict)
        self._lock = threading.RLock()
        self._cleanup_interval = 3600  # 1小时清理一次
        self._last_cleanup = time.time()
    
    def is_allowed(self, identifier: str, endpoint: Optional[str] = None) -> Tuple[bool, Dict[str, int]]:
        """
        检查请求是否被允许
        
        Args:
            identifier: 用户标识符（IP地址、用户ID等）
            endpoint: 端点标识符（可选，用于不同端点的独立限流）
            
        Returns:
            (是否允许, 剩余配额信息)
        """
        with self._lock:
            self._cleanup_if_needed()
            
            key = f"{identifier}:{endpoint}" if endpoint else identifier
            
            # 获取或创建令牌桶
            buckets = self._get_or_create_buckets(key)
            
            # 检查各个时间窗口的限制
            minute_allowed = buckets['minute'].consume()
            hour_allowed = buckets['hour'].consume()
            day_allowed = buckets['day'].consume()
            
            # 所有限制都通过才允许请求
            allowed = minute_allowed and hour_allowed and day_allowed
            
            # 计算剩余配额
            remaining = {
                'minute': int(buckets['minute'].tokens),
                'hour': int(buckets['hour'].tokens),
                'day': int(buckets['day'].tokens)
            }
            
            return allowed, remaining
    
    def _get_or_create_buckets(self, key: str) -> Dict[str, TokenBucket]:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            now = time.time()
            self._buckets[key] = {
                'minute': TokenBucket(
                    capacity=self.config.requests_per_minute,
                    tokens=self.config.requests_per_minute,
                    last_refill=now,
                    refill_rate=self.config.requests_per_minute / 60.0
                ),
                'hour': TokenBucket(
                    capacity=self.config.requests_per_hour,
                    tokens=self.config.requests_per_hour,
                    last_refill=now,
                    refill_rate=self.config.requests_per_hour / 3600.0
                ),
                'day': TokenBucket(
                    capacity=self.config.requests_per_day,
                    tokens=self.config.requests_per_day,
                    last_refill=now,
                    refill_rate=self.config.requests_per_day / 86400.0
                )
            }
        
        return self._buckets[key]
    
    def _cleanup_if_needed(self) -> None:
        """清理过期的令牌桶"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired_buckets()
            self._last_cleanup = now
    
    def _cleanup_expired_buckets(self) -> None:
        """清理过期的令牌桶"""
        now = time.time()
        expired_keys = []
        
        for key, buckets in self._buckets.items():
            # 如果所有桶都很久没有使用，则清理
            all_expired = all(
                now - bucket.last_refill > 86400  # 24小时未使用
                for bucket in buckets.values()
            )
            
            if all_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._buckets[key]
    
    def get_status(self, identifier: str, endpoint: Optional[str] = None) -> Dict[str, int]:
        """获取当前限流状态"""
        with self._lock:
            key = f"{identifier}:{endpoint}" if endpoint else identifier
            
            if key not in self._buckets:
                return {
                    'minute': self.config.requests_per_minute,
                    'hour': self.config.requests_per_hour,
                    'day': self.config.requests_per_day
                }
            
            buckets = self._buckets[key]
            
            # 更新令牌数量（不消费）
            now = time.time()
            for bucket in buckets.values():
                time_passed = now - bucket.last_refill
                bucket.tokens = min(bucket.capacity, bucket.tokens + time_passed * bucket.refill_rate)
                bucket.last_refill = now
            
            return {
                'minute': int(buckets['minute'].tokens),
                'hour': int(buckets['hour'].tokens),
                'day': int(buckets['day'].tokens)
            }
    
    def reset_limits(self, identifier: str, endpoint: Optional[str] = None) -> None:
        """重置限流计数"""
        with self._lock:
            key = f"{identifier}:{endpoint}" if endpoint else identifier
            if key in self._buckets:
                del self._buckets[key]
    
    def update_config(self, config: RateLimitConfig) -> None:
        """更新限流配置"""
        with self._lock:
            self.config = config
            # 清空现有桶，使用新配置
            self._buckets.clear()


class GlobalRateLimiter:
    """全局限流器单例"""
    
    _instance: Optional[RateLimiter] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, config: Optional[RateLimitConfig] = None) -> RateLimiter:
        """获取全局限流器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RateLimiter(config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None


class IPRateLimiter:
    """基于IP的限流器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.limiter = RateLimiter(config)
    
    def is_allowed(self, ip_address: str, endpoint: Optional[str] = None) -> Tuple[bool, Dict[str, int]]:
        """检查IP是否被限流"""
        return self.limiter.is_allowed(ip_address, endpoint)
    
    def get_status(self, ip_address: str, endpoint: Optional[str] = None) -> Dict[str, int]:
        """获取IP限流状态"""
        return self.limiter.get_status(ip_address, endpoint)


class UserRateLimiter:
    """基于用户的限流器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.limiter = RateLimiter(config)
    
    def is_allowed(self, user_id: str, endpoint: Optional[str] = None) -> Tuple[bool, Dict[str, int]]:
        """检查用户是否被限流"""
        return self.limiter.is_allowed(user_id, endpoint)
    
    def get_status(self, user_id: str, endpoint: Optional[str] = None) -> Dict[str, int]:
        """获取用户限流状态"""
        return self.limiter.get_status(user_id, endpoint)