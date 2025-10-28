"""
依赖注入容器
解决模块间循环依赖问题，实现松耦合架构
"""

from typing import Any, Dict, Type, TypeVar, Callable, Optional
import threading
from functools import wraps
import inspect

T = TypeVar('T')


class Container:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """注册单例服务"""
        with self._lock:
            service_name = interface.__name__
            self._factories[service_name] = implementation
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """注册瞬态服务"""
        with self._lock:
            service_name = interface.__name__
            self._services[service_name] = implementation
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """注册实例"""
        with self._lock:
            service_name = interface.__name__
            self._singletons[service_name] = instance
    
    def resolve(self, interface: Type[T]) -> T:
        """解析服务"""
        service_name = interface.__name__
        
        # 检查是否有已注册的实例
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # 检查是否有单例工厂
        if service_name in self._factories:
            with self._lock:
                if service_name not in self._singletons:
                    factory = self._factories[service_name]
                    instance = self._create_instance(factory)
                    self._singletons[service_name] = instance
                return self._singletons[service_name]
        
        # 检查是否有瞬态服务
        if service_name in self._services:
            factory = self._services[service_name]
            return self._create_instance(factory)
        
        raise ValueError(f"Service {service_name} not registered")
    
    def _create_instance(self, factory: Type[T]) -> T:
        """创建实例，自动注入依赖"""
        try:
            # 获取构造函数签名
            sig = inspect.signature(factory.__init__)
            params = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # 尝试解析依赖
                if param.annotation != inspect.Parameter.empty:
                    try:
                        dependency = self.resolve(param.annotation)
                        params[param_name] = dependency
                    except ValueError:
                        # 如果无法解析依赖，使用默认值
                        if param.default != inspect.Parameter.empty:
                            params[param_name] = param.default
                        else:
                            # 如果没有默认值，跳过该参数
                            pass
            
            return factory(**params)
        except Exception as e:
            # 如果自动注入失败，尝试无参构造
            try:
                return factory()
            except Exception:
                raise ValueError(f"Failed to create instance of {factory.__name__}: {e}")
    
    def clear(self) -> None:
        """清空容器"""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# 全局容器实例
_container = Container()


def get_container() -> Container:
    """获取全局容器实例"""
    return _container


def inject(interface: Type[T]) -> T:
    """依赖注入装饰器"""
    return _container.resolve(interface)


def injectable(cls):
    """标记类为可注入的"""
    original_init = cls.__init__
    
    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # 自动注入依赖
        sig = inspect.signature(original_init)
        injected_kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self'] or param_name in kwargs:
                continue
            
            if param.annotation != inspect.Parameter.empty:
                try:
                    dependency = _container.resolve(param.annotation)
                    injected_kwargs[param_name] = dependency
                except ValueError:
                    pass
        
        # 合并注入的依赖和原有参数
        kwargs.update(injected_kwargs)
        original_init(self, *args, **kwargs)
    
    cls.__init__ = new_init
    return cls