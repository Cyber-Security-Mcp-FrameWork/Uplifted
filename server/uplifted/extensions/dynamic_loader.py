"""
动态加载模块
提供运行时动态加载和卸载模块、类和函数的功能
"""

import asyncio
import threading
import importlib
import importlib.util
import inspect
import sys
import os
import types
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Type, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref
import gc

from ..core.interfaces import ILogger


class LoaderType(Enum):
    """加载器类型"""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    PACKAGE = "package"


class LoadStatus(Enum):
    """加载状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    UNLOADING = "unloading"


@dataclass
class LoadedItem:
    """已加载项目"""
    name: str
    type: LoaderType
    path: str
    module: Optional[types.ModuleType] = None
    obj: Any = None
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    status: LoadStatus = LoadStatus.UNLOADED
    load_time: float = 0.0
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModuleWatcher:
    """模块监视器"""
    
    def __init__(self, loader: 'DynamicLoader'):
        self.loader = weakref.ref(loader)
        self._watched_paths: Set[str] = set()
        self._file_timestamps: Dict[str, float] = {}
    
    def watch_path(self, path: str) -> None:
        """监视路径"""
        self._watched_paths.add(path)
        if os.path.exists(path):
            self._file_timestamps[path] = os.path.getmtime(path)
    
    def unwatch_path(self, path: str) -> None:
        """取消监视路径"""
        self._watched_paths.discard(path)
        self._file_timestamps.pop(path, None)
    
    def check_changes(self) -> List[str]:
        """检查文件变更"""
        changed_files = []
        
        for path in self._watched_paths:
            if not os.path.exists(path):
                continue
            
            current_mtime = os.path.getmtime(path)
            last_mtime = self._file_timestamps.get(path, 0)
            
            if current_mtime > last_mtime:
                changed_files.append(path)
                self._file_timestamps[path] = current_mtime
        
        return changed_files


class DependencyResolver:
    """依赖解析器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}
    
    def add_dependency(self, item: str, dependency: str) -> None:
        """添加依赖关系"""
        if item not in self._dependency_graph:
            self._dependency_graph[item] = set()
        
        if dependency not in self._reverse_graph:
            self._reverse_graph[dependency] = set()
        
        self._dependency_graph[item].add(dependency)
        self._reverse_graph[dependency].add(item)
    
    def remove_dependency(self, item: str, dependency: str) -> None:
        """移除依赖关系"""
        if item in self._dependency_graph:
            self._dependency_graph[item].discard(dependency)
        
        if dependency in self._reverse_graph:
            self._reverse_graph[dependency].discard(item)
    
    def remove_item(self, item: str) -> None:
        """移除项目及其所有依赖关系"""
        # 移除作为依赖者的关系
        if item in self._dependency_graph:
            for dependency in self._dependency_graph[item]:
                if dependency in self._reverse_graph:
                    self._reverse_graph[dependency].discard(item)
            del self._dependency_graph[item]
        
        # 移除作为被依赖者的关系
        if item in self._reverse_graph:
            for dependent in self._reverse_graph[item]:
                if dependent in self._dependency_graph:
                    self._dependency_graph[dependent].discard(item)
            del self._reverse_graph[item]
    
    def get_dependencies(self, item: str) -> Set[str]:
        """获取项目的依赖"""
        return self._dependency_graph.get(item, set()).copy()
    
    def get_dependents(self, item: str) -> Set[str]:
        """获取依赖项目的其他项目"""
        return self._reverse_graph.get(item, set()).copy()
    
    def get_load_order(self, items: Set[str]) -> List[str]:
        """获取加载顺序（拓扑排序）"""
        # 只考虑指定的项目
        filtered_graph = {
            item: deps & items
            for item, deps in self._dependency_graph.items()
            if item in items
        }
        
        # Kahn算法
        in_degree = {item: 0 for item in items}
        
        for item, deps in filtered_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        queue = [item for item, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for item, deps in filtered_graph.items():
                if current in deps:
                    in_degree[item] -= 1
                    if in_degree[item] == 0:
                        queue.append(item)
        
        # 检查循环依赖
        if len(result) != len(items):
            remaining = items - set(result)
            if self.logger:
                self.logger.warning(f"Circular dependency detected: {remaining}")
            # 将剩余项目添加到结果中
            result.extend(remaining)
        
        return result
    
    def get_unload_order(self, items: Set[str]) -> List[str]:
        """获取卸载顺序（加载顺序的逆序）"""
        load_order = self.get_load_order(items)
        return list(reversed(load_order))


class DynamicLoader:
    """动态加载器"""
    
    def __init__(self, 
                 search_paths: Optional[List[str]] = None,
                 logger: Optional[ILogger] = None):
        self.search_paths = search_paths or []
        self.logger = logger
        self._loaded_items: Dict[str, LoadedItem] = {}
        self._dependency_resolver = DependencyResolver(logger)
        self._watcher = ModuleWatcher(self)
        self._lock = asyncio.Lock()
        self._original_modules: Dict[str, types.ModuleType] = {}
        
        # 添加默认搜索路径
        if not self.search_paths:
            self.search_paths = [
                os.getcwd(),
                os.path.join(os.getcwd(), "modules"),
                os.path.join(os.path.dirname(__file__), "modules")
            ]
    
    def add_search_path(self, path: str) -> None:
        """添加搜索路径"""
        if path not in self.search_paths:
            self.search_paths.append(path)
            
            if self.logger:
                self.logger.debug(f"Added search path: {path}")
    
    def remove_search_path(self, path: str) -> None:
        """移除搜索路径"""
        try:
            self.search_paths.remove(path)
            
            if self.logger:
                self.logger.debug(f"Removed search path: {path}")
        except ValueError:
            pass
    
    async def load_module(self, 
                          module_name: str, 
                          file_path: Optional[str] = None,
                          reload: bool = False) -> Optional[types.ModuleType]:
        """加载模块"""
        async with self._lock:
            # 检查是否已加载
            if module_name in self._loaded_items and not reload:
                item = self._loaded_items[module_name]
                if item.status == LoadStatus.LOADED:
                    return item.module
            
            try:
                # 查找模块文件
                if not file_path:
                    file_path = await self._find_module_file(module_name)
                    if not file_path:
                        raise FileNotFoundError(f"Module {module_name} not found")
                
                # 创建加载项
                item = LoadedItem(
                    name=module_name,
                    type=LoaderType.MODULE,
                    path=file_path,
                    status=LoadStatus.LOADING
                )
                
                self._loaded_items[module_name] = item
                
                # 备份原始模块（如果存在）
                if module_name in sys.modules:
                    self._original_modules[module_name] = sys.modules[module_name]
                
                # 加载模块
                start_time = asyncio.get_event_loop().time()
                
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not spec or not spec.loader:
                    raise ImportError(f"Cannot create spec for module {module_name}")
                
                module = importlib.util.module_from_spec(spec)
                
                # 执行模块
                spec.loader.exec_module(module)
                
                # 添加到sys.modules
                sys.modules[module_name] = module
                
                # 更新加载项
                item.module = module
                item.status = LoadStatus.LOADED
                item.load_time = asyncio.get_event_loop().time() - start_time
                
                # 分析依赖关系
                await self._analyze_dependencies(item)
                
                # 监视文件变更
                self._watcher.watch_path(file_path)
                
                if self.logger:
                    self.logger.info(f"Loaded module: {module_name} from {file_path}")
                
                return module
            
            except Exception as e:
                # 更新错误状态
                if module_name in self._loaded_items:
                    self._loaded_items[module_name].status = LoadStatus.ERROR
                    self._loaded_items[module_name].error = e
                
                if self.logger:
                    self.logger.error(f"Error loading module {module_name}: {e}")
                
                return None
    
    async def _find_module_file(self, module_name: str) -> Optional[str]:
        """查找模块文件"""
        # 尝试不同的文件扩展名
        extensions = ['.py', '.pyx', '.so', '.pyd']
        
        for search_path in self.search_paths:
            for ext in extensions:
                # 直接文件
                file_path = os.path.join(search_path, f"{module_name}{ext}")
                if os.path.exists(file_path):
                    return file_path
                
                # 包目录
                package_path = os.path.join(search_path, module_name)
                if os.path.isdir(package_path):
                    init_file = os.path.join(package_path, f"__init__{ext}")
                    if os.path.exists(init_file):
                        return init_file
        
        return None
    
    async def _analyze_dependencies(self, item: LoadedItem) -> None:
        """分析模块依赖关系"""
        if not item.module:
            return
        
        try:
            # 分析import语句
            source_file = item.path
            if os.path.exists(source_file):
                with open(source_file, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # 简单的import分析（可以使用AST进行更精确的分析）
                import ast
                
                tree = ast.parse(source_code)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dep_name = alias.name.split('.')[0]
                            if dep_name in self._loaded_items:
                                self._dependency_resolver.add_dependency(item.name, dep_name)
                                item.dependencies.add(dep_name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dep_name = node.module.split('.')[0]
                            if dep_name in self._loaded_items:
                                self._dependency_resolver.add_dependency(item.name, dep_name)
                                item.dependencies.add(dep_name)
        
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error analyzing dependencies for {item.name}: {e}")
    
    async def unload_module(self, module_name: str, force: bool = False) -> bool:
        """卸载模块"""
        async with self._lock:
            if module_name not in self._loaded_items:
                return False
            
            item = self._loaded_items[module_name]
            
            # 检查依赖关系
            dependents = self._dependency_resolver.get_dependents(module_name)
            if dependents and not force:
                if self.logger:
                    self.logger.error(
                        f"Cannot unload module {module_name}, "
                        f"it has dependents: {dependents}"
                    )
                return False
            
            try:
                item.status = LoadStatus.UNLOADING
                
                # 卸载依赖此模块的其他模块
                if force:
                    for dependent in dependents:
                        await self.unload_module(dependent, force=True)
                
                # 从sys.modules移除
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                # 恢复原始模块（如果存在）
                if module_name in self._original_modules:
                    sys.modules[module_name] = self._original_modules[module_name]
                    del self._original_modules[module_name]
                
                # 停止监视文件
                self._watcher.unwatch_path(item.path)
                
                # 清理依赖关系
                self._dependency_resolver.remove_item(module_name)
                
                # 移除加载项
                del self._loaded_items[module_name]
                
                # 强制垃圾回收
                gc.collect()
                
                if self.logger:
                    self.logger.info(f"Unloaded module: {module_name}")
                
                return True
            
            except Exception as e:
                item.status = LoadStatus.ERROR
                item.error = e
                
                if self.logger:
                    self.logger.error(f"Error unloading module {module_name}: {e}")
                
                return False
    
    async def reload_module(self, module_name: str) -> Optional[types.ModuleType]:
        """重新加载模块"""
        item = self._loaded_items.get(module_name)
        if not item:
            return None
        
        file_path = item.path
        
        # 卸载模块
        if not await self.unload_module(module_name, force=True):
            return None
        
        # 重新加载模块
        return await self.load_module(module_name, file_path)
    
    async def load_class(self, 
                         class_path: str, 
                         module_name: Optional[str] = None) -> Optional[Type]:
        """加载类"""
        try:
            if '.' in class_path:
                module_path, class_name = class_path.rsplit('.', 1)
            else:
                if not module_name:
                    raise ValueError("Module name required for class loading")
                module_path = module_name
                class_name = class_path
            
            # 确保模块已加载
            module = await self.load_module(module_path)
            if not module:
                return None
            
            # 获取类
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                
                if inspect.isclass(cls):
                    # 创建类加载项
                    item = LoadedItem(
                        name=class_path,
                        type=LoaderType.CLASS,
                        path=f"{module_path}.{class_name}",
                        obj=cls,
                        status=LoadStatus.LOADED
                    )
                    
                    self._loaded_items[class_path] = item
                    
                    if self.logger:
                        self.logger.info(f"Loaded class: {class_path}")
                    
                    return cls
                else:
                    raise TypeError(f"{class_name} is not a class")
            else:
                raise AttributeError(f"Class {class_name} not found in module {module_path}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading class {class_path}: {e}")
            return None
    
    async def load_function(self, 
                            function_path: str, 
                            module_name: Optional[str] = None) -> Optional[Callable]:
        """加载函数"""
        try:
            if '.' in function_path:
                module_path, function_name = function_path.rsplit('.', 1)
            else:
                if not module_name:
                    raise ValueError("Module name required for function loading")
                module_path = module_name
                function_name = function_path
            
            # 确保模块已加载
            module = await self.load_module(module_path)
            if not module:
                return None
            
            # 获取函数
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                
                if callable(func):
                    # 创建函数加载项
                    item = LoadedItem(
                        name=function_path,
                        type=LoaderType.FUNCTION,
                        path=f"{module_path}.{function_name}",
                        obj=func,
                        status=LoadStatus.LOADED
                    )
                    
                    self._loaded_items[function_path] = item
                    
                    if self.logger:
                        self.logger.info(f"Loaded function: {function_path}")
                    
                    return func
                else:
                    raise TypeError(f"{function_name} is not callable")
            else:
                raise AttributeError(f"Function {function_name} not found in module {module_path}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading function {function_path}: {e}")
            return None
    
    async def check_file_changes(self) -> List[str]:
        """检查文件变更"""
        changed_files = self._watcher.check_changes()
        
        if changed_files and self.logger:
            self.logger.info(f"Detected file changes: {changed_files}")
        
        return changed_files
    
    async def auto_reload_changed_modules(self) -> List[str]:
        """自动重新加载变更的模块"""
        changed_files = await self.check_file_changes()
        reloaded_modules = []
        
        for file_path in changed_files:
            # 查找对应的模块
            for name, item in self._loaded_items.items():
                if item.type == LoaderType.MODULE and item.path == file_path:
                    if await self.reload_module(name):
                        reloaded_modules.append(name)
                    break
        
        return reloaded_modules
    
    def get_loaded_items(self, 
                         item_type: Optional[LoaderType] = None) -> Dict[str, LoadedItem]:
        """获取已加载的项目"""
        if item_type:
            return {
                name: item for name, item in self._loaded_items.items()
                if item.type == item_type
            }
        
        return self._loaded_items.copy()
    
    def get_item_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取项目信息"""
        item = self._loaded_items.get(name)
        if not item:
            return None
        
        return {
            'name': item.name,
            'type': item.type.value,
            'path': item.path,
            'status': item.status.value,
            'load_time': item.load_time,
            'dependencies': list(item.dependencies),
            'dependents': list(self._dependency_resolver.get_dependents(name)),
            'error': str(item.error) if item.error else None,
            'metadata': item.metadata
        }
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖关系图"""
        return {
            name: list(self._dependency_resolver.get_dependencies(name))
            for name in self._loaded_items.keys()
        }
    
    async def unload_all(self) -> bool:
        """卸载所有项目"""
        # 按卸载顺序卸载
        all_items = set(self._loaded_items.keys())
        unload_order = self._dependency_resolver.get_unload_order(all_items)
        
        success = True
        
        for item_name in unload_order:
            if item_name in self._loaded_items:
                item = self._loaded_items[item_name]
                
                if item.type == LoaderType.MODULE:
                    if not await self.unload_module(item_name, force=True):
                        success = False
                else:
                    # 移除非模块项目
                    del self._loaded_items[item_name]
        
        return success


# 全局动态加载器实例
_global_dynamic_loader: Optional[DynamicLoader] = None
_loader_lock = threading.Lock()


def get_global_dynamic_loader() -> DynamicLoader:
    """获取全局动态加载器"""
    global _global_dynamic_loader
    
    if _global_dynamic_loader is None:
        with _loader_lock:
            if _global_dynamic_loader is None:
                _global_dynamic_loader = DynamicLoader()
    
    return _global_dynamic_loader


# 便捷函数
async def load_module(module_name: str, 
                      file_path: Optional[str] = None,
                      reload: bool = False) -> Optional[types.ModuleType]:
    """加载模块"""
    return await get_global_dynamic_loader().load_module(module_name, file_path, reload)


async def load_class(class_path: str, 
                     module_name: Optional[str] = None) -> Optional[Type]:
    """加载类"""
    return await get_global_dynamic_loader().load_class(class_path, module_name)


async def load_function(function_path: str, 
                        module_name: Optional[str] = None) -> Optional[Callable]:
    """加载函数"""
    return await get_global_dynamic_loader().load_function(function_path, module_name)


async def unload_module(module_name: str, force: bool = False) -> bool:
    """卸载模块"""
    return await get_global_dynamic_loader().unload_module(module_name, force)


async def reload_module(module_name: str) -> Optional[types.ModuleType]:
    """重新加载模块"""
    return await get_global_dynamic_loader().reload_module(module_name)