"""
安全的动态加载器包装器

在原有 DynamicLoader 基础上添加安全验证层，防止任意代码执行攻击。

核心安全特性：
1. 代码签名验证
2. 静态代码分析
3. 权限检查
4. 审计日志
5. 沙箱执行（可选）

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import asyncio
import types
import logging
from typing import Optional, List, Type, Callable
from pathlib import Path

from .dynamic_loader import DynamicLoader, LoaderType
from ..security.plugin_validator import (
    SecurePluginLoader,
    PluginValidator,
    PluginSignature,
    SecurityError,
    create_secure_plugin_loader
)
from ..core.interfaces import ILogger


class SecureDynamicLoader:
    """
    安全的动态加载器

    包装原有 DynamicLoader，添加多层安全防护：
    1. 代码签名验证（可选）
    2. 静态代码分析（检测危险模式）
    3. 权限管理（限制插件能力）
    4. 审计日志（记录所有加载操作）

    使用方式:
        secure_loader = SecureDynamicLoader(profile="strict")
        module = await secure_loader.load_module("plugin_name", "/path/to/plugin.py")
    """

    def __init__(self,
                 search_paths: Optional[List[str]] = None,
                 logger: Optional[ILogger] = None,
                 security_profile: str = "moderate",
                 enable_validation: bool = True):
        """
        初始化安全动态加载器

        Args:
            search_paths: 模块搜索路径
            logger: 日志记录器
            security_profile: 安全配置档案（strict/moderate/permissive）
            enable_validation: 是否启用安全验证（默认 True）
        """
        # 创建底层加载器
        self._base_loader = DynamicLoader(search_paths, logger)
        self.logger = logger or logging.getLogger(__name__)

        # 创建安全加载器
        self.enable_validation = enable_validation
        if enable_validation:
            self._secure_loader = create_secure_plugin_loader(
                profile=security_profile,
                logger=self.logger
            )
        else:
            self._secure_loader = None

        self.logger.info(
            f"SecureDynamicLoader initialized "
            f"(validation={'enabled' if enable_validation else 'disabled'}, "
            f"profile={security_profile})"
        )

    async def load_module(self,
                         module_name: str,
                         file_path: Optional[str] = None,
                         reload: bool = False,
                         signature: Optional[PluginSignature] = None) -> Optional[types.ModuleType]:
        """
        安全加载模块

        Args:
            module_name: 模块名称
            file_path: 文件路径（可选）
            reload: 是否重新加载
            signature: 代码签名（可选）

        Returns:
            加载的模块，验证失败返回 None

        Raises:
            SecurityError: 安全验证失败
        """
        # 1. 查找模块文件（如果未提供）
        if not file_path:
            file_path = await self._base_loader._find_module_file(module_name)
            if not file_path:
                if self.logger:
                    self.logger.error(f"Module {module_name} not found")
                return None

        # 2. 安全验证（如果启用）
        if self.enable_validation and self._secure_loader:
            try:
                # 使用安全加载器进行验证和加载
                module = self._secure_loader.load_plugin_module(
                    module_name,
                    file_path,
                    signature
                )

                if not module:
                    return None

                # 加载成功后，使用基础加载器进行追踪和依赖管理
                # 注意：这里模块已经被安全加载器执行过了
                # 我们需要将其注册到基础加载器的跟踪系统中

                # 将已加载的模块注册到基础加载器
                from .dynamic_loader import LoadedItem, LoadStatus
                import sys

                # 添加到 sys.modules（如果还没有）
                if module_name not in sys.modules:
                    sys.modules[module_name] = module

                # 创建加载项
                item = LoadedItem(
                    name=module_name,
                    type=LoaderType.MODULE,
                    path=file_path,
                    module=module,
                    status=LoadStatus.LOADED
                )

                # 注册到基础加载器
                async with self._base_loader._lock:
                    self._base_loader._loaded_items[module_name] = item

                    # 分析依赖关系
                    await self._base_loader._analyze_dependencies(item)

                    # 监视文件变更
                    self._base_loader._watcher.watch_path(file_path)

                if self.logger:
                    self.logger.info(f"安全加载模块成功: {module_name} from {file_path}")

                return module

            except SecurityError as e:
                # 安全验证失败
                if self.logger:
                    self.logger.error(f"安全验证失败: {module_name} - {e}")
                return None

            except Exception as e:
                if self.logger:
                    self.logger.exception(f"加载模块异常: {module_name}")
                return None

        else:
            # 验证被禁用，使用原始加载器
            self.logger.warning(
                f"安全验证已禁用，直接加载模块: {module_name} "
                "（不推荐在生产环境使用）"
            )
            return await self._base_loader.load_module(module_name, file_path, reload)

    async def unload_module(self, module_name: str, force: bool = False) -> bool:
        """
        卸载模块

        Args:
            module_name: 模块名称
            force: 是否强制卸载

        Returns:
            是否成功
        """
        return await self._base_loader.unload_module(module_name, force)

    async def reload_module(self, module_name: str) -> Optional[types.ModuleType]:
        """
        重新加载模块

        Args:
            module_name: 模块名称

        Returns:
            重新加载的模块
        """
        item = self._base_loader._loaded_items.get(module_name)
        if not item:
            return None

        file_path = item.path

        # 卸载模块
        if not await self.unload_module(module_name, force=True):
            return None

        # 重新加载模块
        return await self.load_module(module_name, file_path, reload=True)

    async def load_class(self,
                        class_path: str,
                        module_name: Optional[str] = None) -> Optional[Type]:
        """
        加载类

        Args:
            class_path: 类路径
            module_name: 模块名称

        Returns:
            加载的类
        """
        # 使用基础加载器的类加载功能
        # 注意：模块已经通过 load_module 安全验证过了
        return await self._base_loader.load_class(class_path, module_name)

    async def load_function(self,
                           function_path: str,
                           module_name: Optional[str] = None) -> Optional[Callable]:
        """
        加载函数

        Args:
            function_path: 函数路径
            module_name: 模块名称

        Returns:
            加载的函数
        """
        # 使用基础加载器的函数加载功能
        return await self._base_loader.load_function(function_path, module_name)

    # 代理其他方法到基础加载器
    def add_search_path(self, path: str) -> None:
        """添加搜索路径"""
        self._base_loader.add_search_path(path)

    def remove_search_path(self, path: str) -> None:
        """移除搜索路径"""
        self._base_loader.remove_search_path(path)

    async def check_file_changes(self) -> List[str]:
        """检查文件变更"""
        return await self._base_loader.check_file_changes()

    async def auto_reload_changed_modules(self) -> List[str]:
        """自动重新加载变更的模块"""
        changed_files = await self.check_file_changes()
        reloaded_modules = []

        for file_path in changed_files:
            # 查找对应的模块
            for name, item in self._base_loader._loaded_items.items():
                if item.type == LoaderType.MODULE and item.path == file_path:
                    # 使用安全的重新加载
                    if await self.reload_module(name):
                        reloaded_modules.append(name)
                    break

        return reloaded_modules

    def get_loaded_items(self, item_type: Optional[LoaderType] = None):
        """获取已加载的项目"""
        return self._base_loader.get_loaded_items(item_type)

    def get_item_info(self, name: str):
        """获取项目信息"""
        return self._base_loader.get_item_info(name)

    def get_dependency_graph(self):
        """获取依赖关系图"""
        return self._base_loader.get_dependency_graph()

    async def unload_all(self) -> bool:
        """卸载所有项目"""
        return await self._base_loader.unload_all()

    def get_audit_log(self, limit: int = 100):
        """
        获取审计日志

        Args:
            limit: 返回的日志条数

        Returns:
            审计日志列表
        """
        if self._secure_loader:
            return self._secure_loader.get_audit_log(limit)
        else:
            return []


# 便捷函数：创建默认安全配置的动态加载器
def create_secure_dynamic_loader(
    profile: str = "moderate",
    search_paths: Optional[List[str]] = None,
    logger: Optional[ILogger] = None
) -> SecureDynamicLoader:
    """
    创建预配置的安全动态加载器

    Args:
        profile: 安全配置档案
            - strict: 严格模式（生产环境推荐）
            - moderate: 中等模式
            - permissive: 宽松模式（仅开发环境）
        search_paths: 模块搜索路径
        logger: 日志记录器

    Returns:
        SecureDynamicLoader: 配置好的安全加载器
    """
    return SecureDynamicLoader(
        search_paths=search_paths,
        logger=logger,
        security_profile=profile,
        enable_validation=True
    )


# 全局安全动态加载器实例（替代原有的全局实例）
_global_secure_dynamic_loader: Optional[SecureDynamicLoader] = None
_secure_loader_lock = asyncio.Lock()


async def get_global_secure_dynamic_loader() -> SecureDynamicLoader:
    """获取全局安全动态加载器"""
    global _global_secure_dynamic_loader

    if _global_secure_dynamic_loader is None:
        async with _secure_loader_lock:
            if _global_secure_dynamic_loader is None:
                _global_secure_dynamic_loader = create_secure_dynamic_loader(
                    profile="moderate"
                )

    return _global_secure_dynamic_loader


# 便捷函数（安全版本）
async def load_module_secure(
    module_name: str,
    file_path: Optional[str] = None,
    reload: bool = False
) -> Optional[types.ModuleType]:
    """安全加载模块"""
    loader = await get_global_secure_dynamic_loader()
    return await loader.load_module(module_name, file_path, reload)


async def load_class_secure(
    class_path: str,
    module_name: Optional[str] = None
) -> Optional[Type]:
    """安全加载类"""
    loader = await get_global_secure_dynamic_loader()
    return await loader.load_class(class_path, module_name)


async def load_function_secure(
    function_path: str,
    module_name: Optional[str] = None
) -> Optional[Callable]:
    """安全加载函数"""
    loader = await get_global_secure_dynamic_loader()
    return await loader.load_function(function_path, module_name)
