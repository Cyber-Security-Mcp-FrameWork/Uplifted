"""
钩子系统模块
提供事件驱动的钩子机制，支持插件和模块间的松耦合通信
"""

import asyncio
import threading
import inspect
import weakref
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Union, Type, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque

from ..core.interfaces import ILogger


class HookPriority(Enum):
    """钩子优先级"""
    HIGHEST = 1
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


class HookExecutionMode(Enum):
    """钩子执行模式"""
    SYNC = "sync"          # 同步执行
    ASYNC = "async"        # 异步执行
    PARALLEL = "parallel"  # 并行执行
    SEQUENTIAL = "sequential"  # 顺序执行


@dataclass
class HookResult:
    """钩子执行结果"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    hook_name: str = ""
    callback_name: str = ""


@dataclass
class HookEvent:
    """钩子事件"""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    cancellable: bool = False
    cancelled: bool = False
    
    def cancel(self) -> None:
        """取消事件"""
        if self.cancellable:
            self.cancelled = True


class HookCallback:
    """钩子回调包装器"""
    
    def __init__(self,
                 callback: Callable,
                 priority: HookPriority = HookPriority.NORMAL,
                 once: bool = False,
                 condition: Optional[Callable[[HookEvent], bool]] = None,
                 name: str = ""):
        self.callback = callback
        self.priority = priority
        self.once = once
        self.condition = condition
        self.name = name or self._get_callback_name(callback)
        self.call_count = 0
        self.last_called = 0.0
        self.total_execution_time = 0.0
        self.is_async = asyncio.iscoroutinefunction(callback)
    
    def _get_callback_name(self, callback: Callable) -> str:
        """获取回调函数名称"""
        if hasattr(callback, '__name__'):
            return callback.__name__
        elif hasattr(callback, '__class__'):
            return f"{callback.__class__.__name__}.{getattr(callback, '__func__', 'call')}"
        else:
            return str(callback)
    
    def should_execute(self, event: HookEvent) -> bool:
        """检查是否应该执行回调"""
        if self.condition:
            try:
                return self.condition(event)
            except Exception:
                return False
        return True
    
    async def execute(self, event: HookEvent, *args, **kwargs) -> HookResult:
        """执行回调"""
        start_time = time.time()
        
        try:
            if not self.should_execute(event):
                return HookResult(
                    success=True,
                    result=None,
                    hook_name=event.name,
                    callback_name=self.name
                )
            
            if self.is_async:
                result = await self.callback(event, *args, **kwargs)
            else:
                result = self.callback(event, *args, **kwargs)
            
            execution_time = time.time() - start_time
            self.call_count += 1
            self.last_called = time.time()
            self.total_execution_time += execution_time
            
            return HookResult(
                success=True,
                result=result,
                execution_time=execution_time,
                hook_name=event.name,
                callback_name=self.name
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return HookResult(
                success=False,
                error=e,
                execution_time=execution_time,
                hook_name=event.name,
                callback_name=self.name
            )


class HookFilter:
    """钩子过滤器"""
    
    def __init__(self, name: str, filter_func: Callable[[HookEvent], bool]):
        self.name = name
        self.filter_func = filter_func
    
    def should_process(self, event: HookEvent) -> bool:
        """检查事件是否应该被处理"""
        try:
            return self.filter_func(event)
        except Exception:
            return True


class HookMiddleware(ABC):
    """钩子中间件抽象基类"""
    
    @abstractmethod
    async def before_hook(self, event: HookEvent) -> bool:
        """钩子执行前处理，返回False可阻止执行"""
        pass
    
    @abstractmethod
    async def after_hook(self, event: HookEvent, results: List[HookResult]) -> None:
        """钩子执行后处理"""
        pass


class LoggingMiddleware(HookMiddleware):
    """日志中间件"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
    
    async def before_hook(self, event: HookEvent) -> bool:
        """记录钩子执行前日志"""
        if self.logger:
            self.logger.debug(f"Executing hook: {event.name}")
        return True
    
    async def after_hook(self, event: HookEvent, results: List[HookResult]) -> None:
        """记录钩子执行后日志"""
        if self.logger:
            success_count = sum(1 for r in results if r.success)
            total_time = sum(r.execution_time for r in results)
            
            self.logger.debug(
                f"Hook {event.name} completed: "
                f"{success_count}/{len(results)} successful, "
                f"total time: {total_time:.3f}s"
            )


class PerformanceMiddleware(HookMiddleware):
    """性能监控中间件"""
    
    def __init__(self, slow_threshold: float = 1.0):
        self.slow_threshold = slow_threshold
        self.hook_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'call_count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf')
        })
    
    async def before_hook(self, event: HookEvent) -> bool:
        """记录开始时间"""
        event.data['_perf_start'] = time.time()
        return True
    
    async def after_hook(self, event: HookEvent, results: List[HookResult]) -> None:
        """更新性能统计"""
        start_time = event.data.get('_perf_start', 0)
        total_time = time.time() - start_time
        
        stats = self.hook_stats[event.name]
        stats['call_count'] += 1
        stats['total_time'] += total_time
        stats['avg_time'] = stats['total_time'] / stats['call_count']
        stats['max_time'] = max(stats['max_time'], total_time)
        stats['min_time'] = min(stats['min_time'], total_time)
        
        # 检查慢钩子
        if total_time > self.slow_threshold:
            # 可以在这里记录慢钩子日志或发送警告
            pass
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计"""
        return dict(self.hook_stats)


class HookManager:
    """钩子管理器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._hooks: Dict[str, List[HookCallback]] = defaultdict(list)
        self._filters: Dict[str, List[HookFilter]] = defaultdict(list)
        self._middleware: List[HookMiddleware] = []
        self._event_history: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()
        self._global_enabled = True
        self._hook_enabled: Dict[str, bool] = defaultdict(lambda: True)
        
        # 添加默认中间件
        if logger:
            self.add_middleware(LoggingMiddleware(logger))
        self.add_middleware(PerformanceMiddleware())
    
    def register(self,
                 hook_name: str,
                 callback: Callable,
                 priority: HookPriority = HookPriority.NORMAL,
                 once: bool = False,
                 condition: Optional[Callable[[HookEvent], bool]] = None,
                 name: str = "") -> str:
        """注册钩子回调"""
        hook_callback = HookCallback(
            callback=callback,
            priority=priority,
            once=once,
            condition=condition,
            name=name
        )
        
        self._hooks[hook_name].append(hook_callback)
        
        # 按优先级排序
        self._hooks[hook_name].sort(key=lambda x: x.priority.value)
        
        if self.logger:
            self.logger.debug(f"Registered hook callback: {hook_name}.{hook_callback.name}")
        
        return hook_callback.name
    
    def unregister(self, hook_name: str, callback_name: str = None) -> bool:
        """取消注册钩子回调"""
        if hook_name not in self._hooks:
            return False
        
        if callback_name:
            # 移除特定回调
            original_count = len(self._hooks[hook_name])
            self._hooks[hook_name] = [
                cb for cb in self._hooks[hook_name]
                if cb.name != callback_name
            ]
            removed = original_count - len(self._hooks[hook_name])
            
            if removed > 0 and self.logger:
                self.logger.debug(f"Unregistered hook callback: {hook_name}.{callback_name}")
            
            return removed > 0
        else:
            # 移除所有回调
            count = len(self._hooks[hook_name])
            del self._hooks[hook_name]
            
            if count > 0 and self.logger:
                self.logger.debug(f"Unregistered all callbacks for hook: {hook_name}")
            
            return count > 0
    
    def add_filter(self, hook_name: str, filter_obj: HookFilter) -> None:
        """添加钩子过滤器"""
        self._filters[hook_name].append(filter_obj)
        
        if self.logger:
            self.logger.debug(f"Added filter to hook: {hook_name}.{filter_obj.name}")
    
    def remove_filter(self, hook_name: str, filter_name: str) -> bool:
        """移除钩子过滤器"""
        if hook_name not in self._filters:
            return False
        
        original_count = len(self._filters[hook_name])
        self._filters[hook_name] = [
            f for f in self._filters[hook_name]
            if f.name != filter_name
        ]
        
        removed = original_count - len(self._filters[hook_name])
        
        if removed > 0 and self.logger:
            self.logger.debug(f"Removed filter from hook: {hook_name}.{filter_name}")
        
        return removed > 0
    
    def add_middleware(self, middleware: HookMiddleware) -> None:
        """添加中间件"""
        self._middleware.append(middleware)
        
        if self.logger:
            self.logger.debug(f"Added middleware: {middleware.__class__.__name__}")
    
    def remove_middleware(self, middleware_class: Type[HookMiddleware]) -> bool:
        """移除中间件"""
        original_count = len(self._middleware)
        self._middleware = [
            m for m in self._middleware
            if not isinstance(m, middleware_class)
        ]
        
        removed = original_count - len(self._middleware)
        
        if removed > 0 and self.logger:
            self.logger.debug(f"Removed middleware: {middleware_class.__name__}")
        
        return removed > 0
    
    async def emit(self,
                   hook_name: str,
                   data: Optional[Dict[str, Any]] = None,
                   source: str = "",
                   cancellable: bool = False,
                   mode: HookExecutionMode = HookExecutionMode.SEQUENTIAL,
                   *args, **kwargs) -> List[HookResult]:
        """触发钩子"""
        if not self._global_enabled or not self._hook_enabled[hook_name]:
            return []
        
        # 创建事件
        event = HookEvent(
            name=hook_name,
            data=data or {},
            source=source,
            cancellable=cancellable
        )
        
        # 添加到历史记录
        self._event_history.append(event)
        
        # 应用过滤器
        for filter_obj in self._filters[hook_name]:
            if not filter_obj.should_process(event):
                return []
        
        # 执行中间件前置处理
        for middleware in self._middleware:
            try:
                if not await middleware.before_hook(event):
                    return []
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in middleware before_hook: {e}")
        
        # 获取回调列表
        callbacks = self._hooks.get(hook_name, [])
        if not callbacks:
            return []
        
        # 执行回调
        results = []
        
        try:
            if mode == HookExecutionMode.PARALLEL:
                # 并行执行
                tasks = []
                for callback in callbacks:
                    if event.cancelled and event.cancellable:
                        break
                    task = callback.execute(event, *args, **kwargs)
                    tasks.append(task)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # 处理异常结果
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            results[i] = HookResult(
                                success=False,
                                error=result,
                                hook_name=hook_name,
                                callback_name=callbacks[i].name if i < len(callbacks) else "unknown"
                            )
            
            else:
                # 顺序执行
                for callback in callbacks:
                    if event.cancelled and event.cancellable:
                        break
                    
                    result = await callback.execute(event, *args, **kwargs)
                    results.append(result)
                    
                    # 移除一次性回调
                    if callback.once:
                        self._hooks[hook_name].remove(callback)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error executing hook {hook_name}: {e}")
        
        # 执行中间件后置处理
        for middleware in self._middleware:
            try:
                await middleware.after_hook(event, results)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in middleware after_hook: {e}")
        
        return results
    
    def emit_sync(self,
                  hook_name: str,
                  data: Optional[Dict[str, Any]] = None,
                  source: str = "",
                  *args, **kwargs) -> List[HookResult]:
        """同步触发钩子（仅执行同步回调）"""
        if not self._global_enabled or not self._hook_enabled[hook_name]:
            return []
        
        event = HookEvent(
            name=hook_name,
            data=data or {},
            source=source,
            cancellable=False
        )
        
        # 添加到历史记录
        self._event_history.append(event)
        
        # 应用过滤器
        for filter_obj in self._filters[hook_name]:
            if not filter_obj.should_process(event):
                return []
        
        # 获取同步回调
        callbacks = [
            cb for cb in self._hooks.get(hook_name, [])
            if not cb.is_async
        ]
        
        results = []
        
        for callback in callbacks:
            try:
                start_time = time.time()
                
                if not callback.should_execute(event):
                    continue
                
                result = callback.callback(event, *args, **kwargs)
                execution_time = time.time() - start_time
                
                callback.call_count += 1
                callback.last_called = time.time()
                callback.total_execution_time += execution_time
                
                results.append(HookResult(
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    hook_name=hook_name,
                    callback_name=callback.name
                ))
                
                # 移除一次性回调
                if callback.once:
                    self._hooks[hook_name].remove(callback)
            
            except Exception as e:
                results.append(HookResult(
                    success=False,
                    error=e,
                    hook_name=hook_name,
                    callback_name=callback.name
                ))
        
        return results
    
    def enable_hook(self, hook_name: str) -> None:
        """启用钩子"""
        self._hook_enabled[hook_name] = True
        
        if self.logger:
            self.logger.debug(f"Enabled hook: {hook_name}")
    
    def disable_hook(self, hook_name: str) -> None:
        """禁用钩子"""
        self._hook_enabled[hook_name] = False
        
        if self.logger:
            self.logger.debug(f"Disabled hook: {hook_name}")
    
    def enable_all(self) -> None:
        """启用所有钩子"""
        self._global_enabled = True
        
        if self.logger:
            self.logger.debug("Enabled all hooks")
    
    def disable_all(self) -> None:
        """禁用所有钩子"""
        self._global_enabled = False
        
        if self.logger:
            self.logger.debug("Disabled all hooks")
    
    def get_hook_info(self, hook_name: str) -> Dict[str, Any]:
        """获取钩子信息"""
        callbacks = self._hooks.get(hook_name, [])
        
        return {
            'name': hook_name,
            'enabled': self._hook_enabled[hook_name],
            'callback_count': len(callbacks),
            'callbacks': [
                {
                    'name': cb.name,
                    'priority': cb.priority.name,
                    'call_count': cb.call_count,
                    'total_execution_time': cb.total_execution_time,
                    'avg_execution_time': (
                        cb.total_execution_time / cb.call_count
                        if cb.call_count > 0 else 0
                    ),
                    'is_async': cb.is_async,
                    'once': cb.once
                }
                for cb in callbacks
            ],
            'filter_count': len(self._filters.get(hook_name, []))
        }
    
    def get_all_hooks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有钩子信息"""
        all_hook_names = set(self._hooks.keys()) | set(self._hook_enabled.keys())
        
        return {
            hook_name: self.get_hook_info(hook_name)
            for hook_name in all_hook_names
        }
    
    def get_event_history(self, limit: int = 100) -> List[HookEvent]:
        """获取事件历史"""
        return list(self._event_history)[-limit:]
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        perf_middleware = None
        for middleware in self._middleware:
            if isinstance(middleware, PerformanceMiddleware):
                perf_middleware = middleware
                break
        
        if perf_middleware:
            return perf_middleware.get_stats()
        
        return {}


# 全局钩子管理器实例
_global_hook_manager: Optional[HookManager] = None
_manager_lock = threading.Lock()


def get_global_hook_manager() -> HookManager:
    """获取全局钩子管理器"""
    global _global_hook_manager
    
    if _global_hook_manager is None:
        with _manager_lock:
            if _global_hook_manager is None:
                _global_hook_manager = HookManager()
    
    return _global_hook_manager


# 便捷函数
def register_hook(hook_name: str,
                  callback: Callable,
                  priority: HookPriority = HookPriority.NORMAL,
                  once: bool = False,
                  condition: Optional[Callable[[HookEvent], bool]] = None,
                  name: str = "") -> str:
    """注册钩子回调"""
    return get_global_hook_manager().register(
        hook_name, callback, priority, once, condition, name
    )


def unregister_hook(hook_name: str, callback_name: str = None) -> bool:
    """取消注册钩子回调"""
    return get_global_hook_manager().unregister(hook_name, callback_name)


async def emit_hook(hook_name: str,
                    data: Optional[Dict[str, Any]] = None,
                    source: str = "",
                    cancellable: bool = False,
                    mode: HookExecutionMode = HookExecutionMode.SEQUENTIAL,
                    *args, **kwargs) -> List[HookResult]:
    """触发钩子"""
    return await get_global_hook_manager().emit(
        hook_name, data, source, cancellable, mode, *args, **kwargs
    )


def emit_hook_sync(hook_name: str,
                   data: Optional[Dict[str, Any]] = None,
                   source: str = "",
                   *args, **kwargs) -> List[HookResult]:
    """同步触发钩子"""
    return get_global_hook_manager().emit_sync(hook_name, data, source, *args, **kwargs)