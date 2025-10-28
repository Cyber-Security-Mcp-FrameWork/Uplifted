"""
扩展性模块集成示例
展示如何使用插件管理、配置管理、钩子系统和动态加载等功能
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .plugin_manager import Plugin, PluginInfo, get_global_plugin_manager
from .config_manager import get_global_config_manager, ConfigSource, ConfigFormat
from .hook_system import get_global_hook_manager, HookPriority
from .dynamic_loader import get_global_dynamic_loader

logger = logging.getLogger(__name__)


class ExamplePlugin(Plugin):
    """示例插件实现"""
    
    def __init__(self):
        super().__init__()
        self.config: Optional[Dict[str, Any]] = None
    
    async def initialize(self) -> None:
        """初始化插件"""
        logger.info(f"初始化插件: {self.info.name}")
        
        # 注册钩子
        hook_manager = get_global_hook_manager()
        await hook_manager.register_hook(
            "user_login",
            self._on_user_login,
            priority=HookPriority.NORMAL
        )
        
        # 加载配置
        config_manager = get_global_config_manager()
        self.config = await config_manager.get("plugins.example", {})
        
        logger.info(f"插件 {self.info.name} 初始化完成")
    
    async def activate(self) -> None:
        """激活插件"""
        logger.info(f"激活插件: {self.info.name}")
    
    async def deactivate(self) -> None:
        """停用插件"""
        logger.info(f"停用插件: {self.info.name}")
        
        # 注销钩子
        hook_manager = get_global_hook_manager()
        await hook_manager.unregister_hook("user_login", self._on_user_login)
    
    async def cleanup(self) -> None:
        """清理插件"""
        logger.info(f"清理插件: {self.info.name}")
        self.config = None
    
    async def _on_user_login(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """用户登录钩子处理"""
        user_id = event_data.get("user_id")
        logger.info(f"插件 {self.info.name} 处理用户登录事件: {user_id}")
        
        # 可以在这里添加自定义逻辑
        return {"processed_by": self.info.name, "timestamp": event_data.get("timestamp")}


class ExtensionIntegrationManager:
    """扩展性集成管理器"""
    
    def __init__(self):
        self.plugin_manager = get_global_plugin_manager()
        self.config_manager = get_global_config_manager()
        self.hook_manager = get_global_hook_manager()
        self.dynamic_loader = get_global_dynamic_loader()
        self._initialized = False
    
    async def initialize(self, config_dir: Path, plugins_dir: Path) -> None:
        """初始化扩展性系统"""
        if self._initialized:
            return
        
        try:
            # 1. 初始化配置管理
            await self._setup_config_management(config_dir)
            
            # 2. 初始化插件管理
            await self._setup_plugin_management(plugins_dir)
            
            # 3. 初始化钩子系统
            await self._setup_hook_system()
            
            # 4. 初始化动态加载
            await self._setup_dynamic_loading()
            
            self._initialized = True
            logger.info("扩展性系统初始化完成")
            
        except Exception as e:
            logger.error(f"扩展性系统初始化失败: {e}")
            raise
    
    async def _setup_config_management(self, config_dir: Path) -> None:
        """设置配置管理"""
        # 添加配置源
        main_config = config_dir / "main.json"
        if main_config.exists():
            await self.config_manager.add_source(
                ConfigSource(
                    name="main",
                    path=str(main_config),
                    format=ConfigFormat.JSON,
                    watch=True
                )
            )
        
        # 添加插件配置
        plugins_config = config_dir / "plugins.yaml"
        if plugins_config.exists():
            await self.config_manager.add_source(
                ConfigSource(
                    name="plugins",
                    path=str(plugins_config),
                    format=ConfigFormat.YAML,
                    watch=True
                )
            )
        
        # 启动配置监视
        await self.config_manager.start_watching()
        
        logger.info("配置管理系统设置完成")
    
    async def _setup_plugin_management(self, plugins_dir: Path) -> None:
        """设置插件管理"""
        # 注册示例插件
        example_plugin = ExamplePlugin()
        example_plugin.info = PluginInfo(
            name="example_plugin",
            version="1.0.0",
            description="示例插件",
            author="Uplifted Team",
            dependencies=[]
        )
        
        await self.plugin_manager.register_plugin(example_plugin)
        
        # 从目录加载插件
        if plugins_dir.exists():
            await self.plugin_manager.load_plugins_from_directory(str(plugins_dir))
        
        logger.info("插件管理系统设置完成")
    
    async def _setup_hook_system(self) -> None:
        """设置钩子系统"""
        # 注册系统级钩子
        await self.hook_manager.register_hook(
            "system_startup",
            self._on_system_startup,
            priority=HookPriority.HIGH
        )
        
        await self.hook_manager.register_hook(
            "system_shutdown",
            self._on_system_shutdown,
            priority=HookPriority.HIGH
        )
        
        logger.info("钩子系统设置完成")
    
    async def _setup_dynamic_loading(self) -> None:
        """设置动态加载"""
        # 添加搜索路径
        await self.dynamic_loader.add_search_path("./plugins")
        await self.dynamic_loader.add_search_path("./extensions")
        
        # 启用自动重载
        await self.dynamic_loader.enable_auto_reload()
        
        logger.info("动态加载系统设置完成")
    
    async def _on_system_startup(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """系统启动钩子"""
        logger.info("系统启动事件触发")
        return {"status": "startup_processed"}
    
    async def _on_system_shutdown(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """系统关闭钩子"""
        logger.info("系统关闭事件触发")
        
        # 清理资源
        await self.cleanup()
        
        return {"status": "shutdown_processed"}
    
    async def load_plugin_dynamically(self, plugin_path: str) -> bool:
        """动态加载插件"""
        try:
            # 动态加载模块
            module = await self.dynamic_loader.load_module(plugin_path)
            if not module:
                return False
            
            # 查找插件类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr != Plugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.error(f"在模块 {plugin_path} 中未找到插件类")
                return False
            
            # 创建并注册插件实例
            plugin_instance = plugin_class()
            await self.plugin_manager.register_plugin(plugin_instance)
            
            logger.info(f"动态加载插件成功: {plugin_path}")
            return True
            
        except Exception as e:
            logger.error(f"动态加载插件失败 {plugin_path}: {e}")
            return False
    
    async def trigger_user_login_event(self, user_id: str) -> Dict[str, Any]:
        """触发用户登录事件"""
        event_data = {
            "user_id": user_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # 触发钩子
        results = await self.hook_manager.emit_hook("user_login", event_data)
        
        logger.info(f"用户登录事件处理完成: {user_id}, 结果数量: {len(results)}")
        return {"event": "user_login", "results": results}
    
    async def reload_configuration(self) -> bool:
        """重新加载配置"""
        try:
            await self.config_manager.reload_all()
            logger.info("配置重新加载完成")
            return True
        except Exception as e:
            logger.error(f"配置重新加载失败: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "plugins": {
                "total": len(self.plugin_manager.get_all_plugins()),
                "active": len([p for p in self.plugin_manager.get_all_plugins() 
                             if p.status.name == "ACTIVE"]),
                "plugins": [
                    {
                        "name": plugin.info.name,
                        "version": plugin.info.version,
                        "status": plugin.status.name
                    }
                    for plugin in self.plugin_manager.get_all_plugins()
                ]
            },
            "hooks": {
                "total": len(self.hook_manager.get_all_hooks()),
                "hooks": list(self.hook_manager.get_all_hooks().keys())
            },
            "config_sources": [
                {
                    "name": source.name,
                    "path": source.path,
                    "format": source.format.name,
                    "watching": source.watch
                }
                for source in self.config_manager.get_sources()
            ],
            "loaded_modules": list(self.dynamic_loader.get_loaded_modules().keys())
        }
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停用所有插件
            for plugin in self.plugin_manager.get_all_plugins():
                if plugin.status.name == "ACTIVE":
                    await self.plugin_manager.deactivate_plugin(plugin.info.name)
            
            # 停止配置监视
            await self.config_manager.stop_watching()
            
            # 禁用动态加载自动重载
            await self.dynamic_loader.disable_auto_reload()
            
            logger.info("扩展性系统清理完成")
            
        except Exception as e:
            logger.error(f"扩展性系统清理失败: {e}")


# 全局集成管理器实例
_global_integration_manager: Optional[ExtensionIntegrationManager] = None


def get_global_integration_manager() -> ExtensionIntegrationManager:
    """获取全局集成管理器实例"""
    global _global_integration_manager
    if _global_integration_manager is None:
        _global_integration_manager = ExtensionIntegrationManager()
    return _global_integration_manager


async def initialize_extensions(config_dir: Path, plugins_dir: Path) -> None:
    """初始化扩展性系统的便捷函数"""
    manager = get_global_integration_manager()
    await manager.initialize(config_dir, plugins_dir)


async def cleanup_extensions() -> None:
    """清理扩展性系统的便捷函数"""
    manager = get_global_integration_manager()
    await manager.cleanup()


# 使用示例
async def main():
    """使用示例"""
    # 初始化扩展性系统
    config_dir = Path("./config")
    plugins_dir = Path("./plugins")
    
    await initialize_extensions(config_dir, plugins_dir)
    
    manager = get_global_integration_manager()
    
    # 触发用户登录事件
    await manager.trigger_user_login_event("user123")
    
    # 获取系统状态
    status = await manager.get_system_status()
    print(f"系统状态: {status}")
    
    # 重新加载配置
    await manager.reload_configuration()
    
    # 清理
    await cleanup_extensions()


if __name__ == "__main__":
    asyncio.run(main())