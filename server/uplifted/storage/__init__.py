"""
存储和配置模块
提供缓存管理、配置存储等功能
"""

from .caching import CacheManager, save_to_cache_with_expiry, get_from_cache_with_expiry
from .secure_caching import (
    SecureCacheManager,
    SecureSerializer,
    SignatureValidator,
    SerializationError,
    SignatureError,
    create_secure_cache_manager,
    get_global_secure_cache_manager
)
from .configuration import ClientConfiguration

__all__ = [
    # Legacy Caching (不安全，已弃用)
    'CacheManager',
    'save_to_cache_with_expiry',
    'get_from_cache_with_expiry',

    # Secure Caching (推荐)
    'SecureCacheManager',
    'SecureSerializer',
    'SignatureValidator',
    'SerializationError',
    'SignatureError',
    'create_secure_cache_manager',
    'get_global_secure_cache_manager',

    # Configuration
    'ClientConfiguration'
]
