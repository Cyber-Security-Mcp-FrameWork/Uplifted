"""
服务注册表
统一管理所有服务的注册和配置
"""

from typing import Dict, Any, Type
from .container import Container, get_container
from .interfaces import (
    IConfiguration, ICache, ILogger, 
    IModelRegistry, IToolManager, IAgentFactory
)


class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self, container: Container = None):
        self.container = container or get_container()
        self._registered_services: Dict[str, Type] = {}
    
    def register_core_services(self) -> None:
        """注册核心服务"""
        from ..storage.configuration import Configuration
        from ..storage.caching import CacheManager
        from ..core.logger import StructuredLogger
        from ..model_registry import ModelRegistryService
        from ..tools_server.tools_client import ToolManager
        from ..server.level_utilized.utility import AgentFactory
        
        # 注册配置服务
        self.container.register_singleton(IConfiguration, Configuration)
        
        # 注册缓存服务
        self.container.register_singleton(ICache, CacheManager)
        
        # 注册日志服务
        self.container.register_singleton(ILogger, StructuredLogger)
        
        # 注册模型注册表服务
        self.container.register_singleton(IModelRegistry, ModelRegistryService)
        
        # 注册工具管理服务
        self.container.register_singleton(IToolManager, ToolManager)
        
        # 注册代理工厂服务
        self.container.register_singleton(IAgentFactory, AgentFactory)
        
        self._registered_services.update({
            'IConfiguration': Configuration,
            'ICache': CacheManager,
            'ILogger': StructuredLogger,
            'IModelRegistry': ModelRegistryService,
            'IToolManager': ToolManager,
            'IAgentFactory': AgentFactory
        })
    
    def register_custom_service(self, interface: Type, implementation: Type, singleton: bool = True) -> None:
        """注册自定义服务"""
        if singleton:
            self.container.register_singleton(interface, implementation)
        else:
            self.container.register_transient(interface, implementation)
        
        self._registered_services[interface.__name__] = implementation
    
    def get_registered_services(self) -> Dict[str, Type]:
        """获取已注册的服务列表"""
        return self._registered_services.copy()
    
    def is_service_registered(self, interface: Type) -> bool:
        """检查服务是否已注册"""
        return interface.__name__ in self._registered_services
    
    def unregister_service(self, interface: Type) -> None:
        """注销服务"""
        service_name = interface.__name__
        if service_name in self._registered_services:
            del self._registered_services[service_name]
            # 注意：这里不能直接从容器中移除，因为可能有其他依赖
    
    def initialize_all_services(self) -> None:
        """初始化所有服务"""
        for interface_name, implementation in self._registered_services.items():
            try:
                # 通过容器解析服务，触发初始化
                interface_type = globals().get(interface_name)
                if interface_type:
                    self.container.resolve(interface_type)
            except Exception as e:
                print(f"Failed to initialize service {interface_name}: {e}")


# 全局服务注册表实例
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """获取全局服务注册表实例"""
    return _registry


def setup_services() -> None:
    """设置所有服务"""
    registry = get_registry()
    registry.register_core_services()
    registry.initialize_all_services()