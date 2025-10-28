"""
Uplifted 核心模块
提供依赖注入、服务注册和配置管理等核心功能
"""

from .container import Container
from .registry import ServiceRegistry
from .interfaces import IConfiguration, ICache, ILogger

__all__ = [
    'Container',
    'ServiceRegistry', 
    'IConfiguration',
    'ICache',
    'ILogger'
]