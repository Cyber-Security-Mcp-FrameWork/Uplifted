"""
插件管理模块
提供插件的加载、卸载、管理和生命周期控制功能
"""

import asyncio
import threading
import importlib
import importlib.util
import inspect
import sys
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref

from ..core.interfaces import ILogger


class PluginStatus(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADING = "unloading"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    config_schema: Optional[Dict[str, Any]] = None
    min_api_version: str = "1.0.0"
    max_api_version: str = "2.0.0"


@dataclass
class PluginConfig:
    """插件配置"""
    enabled: bool = True
    auto_load: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    load_priority: int = 100  # 数值越小优先级越高


class Plugin(ABC):
    """插件基类"""

    def __init__(self, info: PluginInfo, config: PluginConfig):
        self.info = info
        self.config = config
        self.status = PluginStatus.UNLOADED
        self.logger: Optional[ILogger] = None
        self._hooks: Dict[str, List[Callable]] = {}
        # 可选的 manifest 属性，用于 MCP 工具注册
        self.manifest: Optional[Any] = None  # PluginManifest, 避免循环导入
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def activate(self) -> bool:
        """激活插件"""
        pass
    
    @abstractmethod
    async def deactivate(self) -> bool:
        """停用插件"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """清理插件资源"""
        pass
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """注册钩子回调"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)
    
    def unregister_hook(self, hook_name: str, callback: Callable) -> None:
        """取消注册钩子回调"""
        if hook_name in self._hooks:
            try:
                self._hooks[hook_name].remove(callback)
            except ValueError:
                pass
    
    def get_hooks(self, hook_name: str) -> List[Callable]:
        """获取钩子回调列表"""
        return self._hooks.get(hook_name, [])
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """设置配置值"""
        self.config.config[key] = value


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_configs: Dict[str, PluginConfig] = {}
        self._dependency_graph: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """注册插件"""
        with self._lock:
            if plugin.info.name in self._plugins:
                if self.logger:
                    self.logger.warning(f"Plugin {plugin.info.name} already registered")
                return False
            
            self._plugins[plugin.info.name] = plugin
            self._dependency_graph[plugin.info.name] = plugin.info.dependencies.copy()
            
            if self.logger:
                self.logger.info(f"Plugin {plugin.info.name} registered")
            
            return True
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """取消注册插件"""
        with self._lock:
            if plugin_name not in self._plugins:
                return False
            
            # 检查是否有其他插件依赖此插件
            dependents = self._get_dependents(plugin_name)
            if dependents:
                if self.logger:
                    self.logger.error(
                        f"Cannot unregister plugin {plugin_name}, "
                        f"it has dependents: {dependents}"
                    )
                return False
            
            del self._plugins[plugin_name]
            del self._dependency_graph[plugin_name]
            
            if self.logger:
                self.logger.info(f"Plugin {plugin_name} unregistered")
            
            return True
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """获取插件"""
        with self._lock:
            return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Plugin]:
        """获取所有插件"""
        with self._lock:
            return self._plugins.copy()
    
    def get_plugins_by_status(self, status: PluginStatus) -> List[Plugin]:
        """根据状态获取插件"""
        with self._lock:
            return [
                plugin for plugin in self._plugins.values()
                if plugin.status == status
            ]
    
    def _get_dependents(self, plugin_name: str) -> List[str]:
        """获取依赖指定插件的插件列表"""
        dependents = []
        for name, dependencies in self._dependency_graph.items():
            if plugin_name in dependencies:
                dependents.append(name)
        return dependents
    
    def get_load_order(self) -> List[str]:
        """获取插件加载顺序（拓扑排序）"""
        with self._lock:
            # 使用Kahn算法进行拓扑排序
            in_degree = {name: 0 for name in self._plugins.keys()}
            
            # 计算入度
            for dependencies in self._dependency_graph.values():
                for dep in dependencies:
                    if dep in in_degree:
                        in_degree[dep] += 1
            
            # 按优先级排序
            plugins_by_priority = sorted(
                self._plugins.items(),
                key=lambda x: x[1].config.load_priority
            )
            
            queue = []
            result = []
            
            # 将入度为0的节点加入队列
            for name, plugin in plugins_by_priority:
                if in_degree[name] == 0:
                    queue.append(name)
            
            while queue:
                current = queue.pop(0)
                result.append(current)
                
                # 更新依赖此插件的其他插件的入度
                for name, dependencies in self._dependency_graph.items():
                    if current in dependencies:
                        in_degree[name] -= 1
                        if in_degree[name] == 0:
                            queue.append(name)
            
            # 检查是否有循环依赖
            if len(result) != len(self._plugins):
                remaining = set(self._plugins.keys()) - set(result)
                if self.logger:
                    self.logger.error(f"Circular dependency detected in plugins: {remaining}")
                # 将剩余插件添加到结果中（可能导致运行时错误）
                result.extend(remaining)
            
            return result


class PluginManager:
    """插件管理器"""

    def __init__(self,
                 plugin_dirs: Optional[List[str]] = None,
                 logger: Optional[ILogger] = None):
        self.plugin_dirs = plugin_dirs or []
        self.logger = logger
        self.registry = PluginRegistry(logger)
        self._loader_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._mcp_bridge: Optional[Any] = None  # MCPPluginBridge, 避免循环导入

        # 添加默认插件目录
        if not self.plugin_dirs:
            self.plugin_dirs = [
                os.path.join(os.getcwd(), "plugins"),
                os.path.join(os.path.dirname(__file__), "plugins")
            ]

    def set_mcp_bridge(self, bridge: Any) -> None:
        """
        设置 MCP 桥接器

        参数:
            bridge: MCPPluginBridge 实例
        """
        self._mcp_bridge = bridge
        if self.logger:
            self.logger.info("MCP bridge connected to plugin manager")
    
    async def discover_plugins(self) -> List[str]:
        """发现插件"""
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            try:
                for item in os.listdir(plugin_dir):
                    item_path = os.path.join(plugin_dir, item)
                    
                    # 检查Python文件
                    if item.endswith('.py') and not item.startswith('_'):
                        plugin_name = item[:-3]
                        discovered.append(plugin_name)
                    
                    # 检查包目录
                    elif os.path.isdir(item_path) and not item.startswith('_'):
                        init_file = os.path.join(item_path, '__init__.py')
                        if os.path.exists(init_file):
                            discovered.append(item)
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error discovering plugins in {plugin_dir}: {e}")
        
        return discovered
    
    async def load_plugin(self, plugin_name: str) -> bool:
        """加载插件"""
        async with self._lock:
            # 检查插件是否已加载
            existing_plugin = self.registry.get_plugin(plugin_name)
            if existing_plugin and existing_plugin.status != PluginStatus.UNLOADED:
                if self.logger:
                    self.logger.warning(f"Plugin {plugin_name} already loaded")
                return False
            
            try:
                # 查找插件文件
                plugin_module = await self._load_plugin_module(plugin_name)
                if not plugin_module:
                    return False
                
                # 获取插件信息
                plugin_info = await self._get_plugin_info(plugin_module)
                if not plugin_info:
                    return False
                
                # 检查依赖
                if not await self._check_dependencies(plugin_info.dependencies):
                    return False
                
                # 创建插件实例
                plugin_class = await self._get_plugin_class(plugin_module)
                if not plugin_class:
                    return False
                
                plugin_config = PluginConfig()  # 可以从配置文件加载
                plugin = plugin_class(plugin_info, plugin_config)
                plugin.logger = self.logger

                # 如果有 manifest，附加到插件实例
                if hasattr(plugin_info, '_manifest'):
                    plugin.manifest = plugin_info._manifest

                # 注册插件
                if not self.registry.register_plugin(plugin):
                    return False
                
                # 初始化插件
                plugin.status = PluginStatus.LOADING
                
                try:
                    if await plugin.initialize():
                        plugin.status = PluginStatus.LOADED
                        
                        if self.logger:
                            self.logger.info(f"Plugin {plugin_name} loaded successfully")
                        
                        return True
                    else:
                        plugin.status = PluginStatus.ERROR
                        return False
                
                except Exception as e:
                    plugin.status = PluginStatus.ERROR
                    if self.logger:
                        self.logger.error(f"Error initializing plugin {plugin_name}: {e}")
                    return False
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error loading plugin {plugin_name}: {e}")
                return False
    
    async def _load_plugin_module(self, plugin_name: str) -> Optional[Any]:
        """加载插件模块"""
        for plugin_dir in self.plugin_dirs:
            # 尝试加载Python文件
            plugin_file = os.path.join(plugin_dir, f"{plugin_name}.py")
            if os.path.exists(plugin_file):
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        return module
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error loading plugin file {plugin_file}: {e}")
            
            # 尝试加载包目录
            plugin_package = os.path.join(plugin_dir, plugin_name)
            if os.path.isdir(plugin_package):
                init_file = os.path.join(plugin_package, '__init__.py')
                if os.path.exists(init_file):
                    try:
                        spec = importlib.util.spec_from_file_location(
                            plugin_name, init_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            return module
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error loading plugin package {plugin_package}: {e}")
        
        return None
    
    async def _get_plugin_info(self, module: Any) -> Optional[PluginInfo]:
        """获取插件信息"""
        try:
            # 优先检查 PluginManifest (新格式)
            if hasattr(module, 'PLUGIN_MANIFEST'):
                manifest = module.PLUGIN_MANIFEST
                # 导入 manifest_to_plugin_info 进行转换
                try:
                    from .plugin_manifest import manifest_to_plugin_info
                    plugin_info = manifest_to_plugin_info(manifest)
                    # 存储 manifest 引用供后续使用
                    plugin_info._manifest = manifest
                    return plugin_info
                except ImportError:
                    if self.logger:
                        self.logger.warning("plugin_manifest module not available, falling back to PLUGIN_INFO")

            # 兼容旧格式
            if hasattr(module, 'PLUGIN_INFO'):
                info_dict = module.PLUGIN_INFO
                return PluginInfo(**info_dict)
            elif hasattr(module, 'get_plugin_info'):
                info_dict = module.get_plugin_info()
                return PluginInfo(**info_dict)
            else:
                # 尝试从模块属性构建信息
                name = getattr(module, '__name__', 'unknown')
                version = getattr(module, '__version__', '1.0.0')
                description = getattr(module, '__doc__', '')

                return PluginInfo(
                    name=name,
                    version=version,
                    description=description
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting plugin info: {e}")
            return None
    
    async def _get_plugin_class(self, module: Any) -> Optional[Type[Plugin]]:
        """获取插件类"""
        try:
            # 查找Plugin子类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj != Plugin:
                    return obj
            
            # 查找特定名称的类
            if hasattr(module, 'Plugin'):
                return module.Plugin
            
            if hasattr(module, 'MainPlugin'):
                return module.MainPlugin
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting plugin class: {e}")
        
        return None
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查插件依赖"""
        for dep in dependencies:
            plugin = self.registry.get_plugin(dep)
            if not plugin or plugin.status not in [PluginStatus.LOADED, PluginStatus.ACTIVE]:
                if self.logger:
                    self.logger.error(f"Dependency {dep} not satisfied")
                return False
        
        return True
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        async with self._lock:
            plugin = self.registry.get_plugin(plugin_name)
            if not plugin:
                return False

            if plugin.status == PluginStatus.UNLOADED:
                return True

            try:
                plugin.status = PluginStatus.UNLOADING

                # 如果设置了 MCP 桥接器，先卸载工具
                if self._mcp_bridge is not None and hasattr(plugin, 'manifest'):
                    try:
                        await self._mcp_bridge.unregister_plugin_tools(plugin.manifest.id)
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(
                                f"Failed to unregister MCP tools for {plugin_name}: {e}"
                            )

                # 停用插件
                if plugin.status == PluginStatus.ACTIVE:
                    await plugin.deactivate()

                # 清理插件
                await plugin.cleanup()

                # 取消注册
                self.registry.unregister_plugin(plugin_name)

                if self.logger:
                    self.logger.info(f"Plugin {plugin_name} unloaded successfully")

                return True

            except Exception as e:
                plugin.status = PluginStatus.ERROR
                if self.logger:
                    self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
                return False
    
    async def activate_plugin(self, plugin_name: str) -> bool:
        """激活插件"""
        plugin = self.registry.get_plugin(plugin_name)
        if not plugin:
            return False

        if plugin.status != PluginStatus.LOADED:
            return False

        try:
            if await plugin.activate():
                plugin.status = PluginStatus.ACTIVE

                if self.logger:
                    self.logger.info(f"Plugin {plugin_name} activated")

                # 如果设置了 MCP 桥接器，自动注册工具
                if self._mcp_bridge is not None:
                    try:
                        await self._mcp_bridge.register_plugin_tools(plugin)
                    except Exception as e:
                        if self.logger:
                            self.logger.warning(
                                f"Failed to register MCP tools for {plugin_name}: {e}"
                            )

                return True
            else:
                return False

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            if self.logger:
                self.logger.error(f"Error activating plugin {plugin_name}: {e}")
            return False
    
    async def deactivate_plugin(self, plugin_name: str) -> bool:
        """停用插件"""
        plugin = self.registry.get_plugin(plugin_name)
        if not plugin:
            return False

        if plugin.status != PluginStatus.ACTIVE:
            return False

        try:
            # 如果设置了 MCP 桥接器，先卸载工具
            if self._mcp_bridge is not None and hasattr(plugin, 'manifest'):
                try:
                    await self._mcp_bridge.unregister_plugin_tools(plugin.manifest.id)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Failed to unregister MCP tools for {plugin_name}: {e}"
                        )

            if await plugin.deactivate():
                plugin.status = PluginStatus.INACTIVE

                if self.logger:
                    self.logger.info(f"Plugin {plugin_name} deactivated")

                return True
            else:
                return False

        except Exception as e:
            plugin.status = PluginStatus.ERROR
            if self.logger:
                self.logger.error(f"Error deactivating plugin {plugin_name}: {e}")
            return False
    
    async def load_all_plugins(self) -> Dict[str, bool]:
        """加载所有插件"""
        discovered = await self.discover_plugins()
        results = {}
        
        # 按依赖顺序加载
        for plugin_name in discovered:
            results[plugin_name] = await self.load_plugin(plugin_name)
        
        return results
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        # 先卸载
        await self.unload_plugin(plugin_name)
        
        # 清理模块缓存
        modules_to_remove = []
        for module_name in sys.modules:
            if module_name.startswith(plugin_name):
                modules_to_remove.append(module_name)
        
        for module_name in modules_to_remove:
            del sys.modules[module_name]
        
        # 重新加载
        return await self.load_plugin(plugin_name)
    
    def get_plugin_status(self, plugin_name: str) -> Optional[PluginStatus]:
        """获取插件状态"""
        plugin = self.registry.get_plugin(plugin_name)
        return plugin.status if plugin else None
    
    def get_all_plugin_status(self) -> Dict[str, PluginStatus]:
        """获取所有插件状态"""
        return {
            name: plugin.status
            for name, plugin in self.registry.get_all_plugins().items()
        }


# 全局插件管理器实例
_global_plugin_manager: Optional[PluginManager] = None
_manager_lock = threading.Lock()


def get_global_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _global_plugin_manager
    
    if _global_plugin_manager is None:
        with _manager_lock:
            if _global_plugin_manager is None:
                _global_plugin_manager = PluginManager()
    
    return _global_plugin_manager