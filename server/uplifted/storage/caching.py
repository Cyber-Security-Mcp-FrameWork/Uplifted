"""
用于使用 SQLite 处理数据缓存的模块。
"""

import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import dill
import base64
import time
import threading
from typing import Optional, Any, Dict
from .configuration import ClientConfiguration
from ..core.interfaces import ICache


def save_to_cache_with_expiry(data: Any, cache_key: str, expiry_seconds: int) -> None:
    """
    将数据保存到缓存中，并设置过期时间。
    
    参数：
        data: 要存入缓存的任意数据
        cache_key: 缓存数据的唯一标识符
        expiry_seconds: 缓存失效前的秒数
    """
    the_module = dill.detect.getmodule(data)
    if the_module is not None:
        cloudpickle.register_pickle_by_value(the_module)
        
    current_time = int(time.time())
    expiry_time = current_time + expiry_seconds
    cache_key_full = f"cache_{cache_key}"
    
    cache_data = {
        'data': data,
        'expiry_time': expiry_time,
        'created_at': current_time
    }
    
    try:
        ClientConfiguration.delete(cache_key_full)
        serialized_data = base64.b64encode(cloudpickle.dumps(cache_data)).decode('utf-8')
        ClientConfiguration.set(cache_key_full, serialized_data)
    except Exception:
        ClientConfiguration.delete(cache_key_full)
        raise


def get_from_cache_with_expiry(cache_key: str) -> Optional[Any]:
    """
    如果缓存未过期，则从缓存中获取数据。
    
    参数：
        cache_key: 缓存数据的唯一标识符
        
    返回：
        如果找到且未过期则返回缓存数据，否则返回 None
    """
    cache_key_full = f"cache_{cache_key}"
    serialized_data = ClientConfiguration.get(cache_key_full)

    if serialized_data is None:
        return None
    
    try:
        cache_data = cloudpickle.loads(base64.b64decode(serialized_data))
        current_time = int(time.time())
        
        if current_time > cache_data['expiry_time']:
            ClientConfiguration.delete(cache_key_full)
            return None

        return cache_data['data']
    except Exception:
        ClientConfiguration.delete(cache_key_full)
        return None


class CacheManager(ICache):
    """
    改进的缓存管理器
    提供线程安全的缓存操作和统计信息
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            result = get_from_cache_with_expiry(key)
            if result is not None:
                self._stats['hits'] += 1
            else:
                self._stats['misses'] += 1
            return result
    
    def set(self, key: str, value: Any, expiry_hours: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            expiry_seconds = (expiry_hours * 3600) if expiry_hours else 3600  # 默认1小时
            save_to_cache_with_expiry(value, key, expiry_seconds)
            self._stats['sets'] += 1
    
    def delete(self, key: str) -> None:
        """删除缓存项"""
        with self._lock:
            cache_key_full = f"cache_{key}"
            ClientConfiguration.delete(cache_key_full)
            self._stats['deletes'] += 1
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            # 获取所有缓存键并删除
            all_config = ClientConfiguration.export_all()
            cache_keys = [k for k in all_config.keys() if k.startswith('cache_')]
            for key in cache_keys:
                ClientConfiguration.delete(key)
            self._stats['deletes'] += len(cache_keys)
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **self._stats,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2)
            }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0
            }
    
    def cleanup_expired(self) -> int:
        """清理过期缓存项"""
        with self._lock:
            all_config = ClientConfiguration.export_all()
            cache_keys = [k for k in all_config.keys() if k.startswith('cache_')]
            cleaned_count = 0
            
            for key in cache_keys:
                try:
                    serialized_data = ClientConfiguration.get(key)
                    if serialized_data:
                        cache_data = cloudpickle.loads(base64.b64decode(serialized_data))
                        current_time = int(time.time())
                        
                        if current_time > cache_data['expiry_time']:
                            ClientConfiguration.delete(key)
                            cleaned_count += 1
                except Exception:
                    # 如果数据损坏，也删除
                    ClientConfiguration.delete(key)
                    cleaned_count += 1
            
            return cleaned_count