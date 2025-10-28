"""
插件系统初始化模块

提供便捷的初始化函数，集成插件管理器和 MCP 桥接器。

使用示例:
    from uplifted.extensions.plugin_system_init import initialize_plugin_system

    # 在服务器启动时
    plugin_manager, mcp_bridge = await initialize_plugin_system(
        plugin_dirs=["plugins"],
        logger=logger
    )

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import asyncio
from typing import Optional, List, Tuple
from pathlib import Path

from .plugin_manager import PluginManager, get_global_plugin_manager
from .mcp_bridge import MCPPluginBridge, initialize_mcp_bridge, get_global_mcp_bridge
from ..core.interfaces import ILogger


async def initialize_plugin_system(
    plugin_dirs: Optional[List[str]] = None,
    logger: Optional[ILogger] = None,
    auto_discover: bool = True,
    auto_load: bool = True,
    auto_activate: bool = True
) -> Tuple[PluginManager, MCPPluginBridge]:
    """
    初始化完整的插件系统

    自动设置插件管理器、MCP 桥接器，并完成插件发现、加载和激活。

    参数:
        plugin_dirs: 插件目录列表，如果为 None 则使用默认目录
        logger: 日志记录器（可选）
        auto_discover: 是否自动发现插件（默认 True）
        auto_load: 是否自动加载插件（默认 True）
        auto_activate: 是否自动激活插件（默认 True）

    返回:
        (plugin_manager, mcp_bridge) 元组

    示例:
        # 完整初始化（自动发现、加载、激活）
        pm, bridge = await initialize_plugin_system()

        # 仅初始化，不自动加载
        pm, bridge = await initialize_plugin_system(auto_load=False)
        # 手动加载特定插件
        await pm.load_plugin("my_plugin")
        await pm.activate_plugin("my_plugin")

    流程:
        1. 创建或获取全局插件管理器
        2. 创建 MCP 桥接器并连接到插件管理器
        3. 如果 auto_discover: 发现所有插件
        4. 如果 auto_load: 加载所有发现的插件
        5. 如果 auto_activate: 激活所有已加载的插件
        6. 同步所有活跃插件的工具到 MCP 服务器

    注意:
        - 此函数应在服务器启动时调用一次
        - 如果已经初始化过，会返回现有实例
    """
    # 获取或创建插件管理器
    if plugin_dirs:
        plugin_manager = PluginManager(plugin_dirs=plugin_dirs, logger=logger)
    else:
        plugin_manager = get_global_plugin_manager()
        if logger and plugin_manager.logger is None:
            plugin_manager.logger = logger

    # 创建 MCP 桥接器
    mcp_bridge = initialize_mcp_bridge(plugin_manager, logger)

    # 将桥接器连接到插件管理器
    plugin_manager.set_mcp_bridge(mcp_bridge)

    if logger:
        logger.info("Plugin system initialized")

    # 自动发现插件
    if auto_discover:
        discovered_plugins = await plugin_manager.discover_plugins()
        if logger:
            logger.info(f"Discovered {len(discovered_plugins)} plugins: {discovered_plugins}")

        # 自动加载插件
        if auto_load:
            load_results = {}
            for plugin_name in discovered_plugins:
                try:
                    success = await plugin_manager.load_plugin(plugin_name)
                    load_results[plugin_name] = success

                    # 自动激活
                    if success and auto_activate:
                        await plugin_manager.activate_plugin(plugin_name)
                except Exception as e:
                    if logger:
                        logger.error(f"Error loading plugin {plugin_name}: {e}", exc_info=True)
                    load_results[plugin_name] = False

            if logger:
                success_count = sum(1 for v in load_results.values() if v)
                logger.info(
                    f"Loaded {success_count}/{len(load_results)} plugins successfully"
                )

    # 同步所有活跃插件到 MCP 服务器
    sync_results = await mcp_bridge.sync_all_plugins()
    if logger:
        logger.info(
            f"Synced {len(sync_results)} plugins to MCP server"
        )

    return plugin_manager, mcp_bridge


async def shutdown_plugin_system(
    plugin_manager: Optional[PluginManager] = None,
    logger: Optional[ILogger] = None
) -> None:
    """
    关闭插件系统

    停用并卸载所有插件，清理资源。

    参数:
        plugin_manager: 插件管理器实例，如果为 None 则使用全局实例
        logger: 日志记录器（可选）

    示例:
        await shutdown_plugin_system()

    注意:
        - 应在服务器关闭时调用
        - 会按依赖关系逆序卸载插件
    """
    if plugin_manager is None:
        plugin_manager = get_global_plugin_manager()

    if logger:
        logger.info("Shutting down plugin system...")

    # 获取所有插件
    all_plugins = plugin_manager.registry.get_all_plugins()

    # 按加载顺序的逆序卸载
    load_order = plugin_manager.registry.get_load_order()
    unload_order = list(reversed(load_order))

    for plugin_name in unload_order:
        try:
            await plugin_manager.unload_plugin(plugin_name)
        except Exception as e:
            if logger:
                logger.error(f"Error unloading plugin {plugin_name}: {e}", exc_info=True)

    if logger:
        logger.info("Plugin system shutdown complete")


def get_plugin_system_status(
    plugin_manager: Optional[PluginManager] = None,
    mcp_bridge: Optional[MCPPluginBridge] = None
) -> dict:
    """
    获取插件系统状态

    返回插件管理器和 MCP 桥接器的详细状态信息。

    参数:
        plugin_manager: 插件管理器实例，如果为 None 则使用全局实例
        mcp_bridge: MCP 桥接器实例，如果为 None 则使用全局实例

    返回:
        包含系统状态的字典

    示例:
        status = get_plugin_system_status()
        print(f"Total plugins: {status['plugin_count']}")
        print(f"Active plugins: {status['active_plugin_count']}")
        print(f"Total tools: {status['mcp_stats']['total_tools']}")
    """
    if plugin_manager is None:
        plugin_manager = get_global_plugin_manager()

    if mcp_bridge is None:
        mcp_bridge = get_global_mcp_bridge()

    # 插件状态
    all_plugins = plugin_manager.registry.get_all_plugins()
    plugin_status = plugin_manager.get_all_plugin_status()

    status = {
        'plugin_count': len(all_plugins),
        'active_plugin_count': sum(
            1 for s in plugin_status.values() if s.value == 'active'
        ),
        'plugins': {
            name: {
                'status': status.value,
                'version': plugin.info.version,
                'description': plugin.info.description
            }
            for name, (status, plugin) in zip(
                plugin_status.keys(),
                [(s, p) for s, p in zip(plugin_status.values(), all_plugins.values())]
            )
        }
    }

    # MCP 桥接器状态
    if mcp_bridge:
        status['mcp_stats'] = mcp_bridge.get_statistics()
        status['mcp_available'] = True
    else:
        status['mcp_stats'] = {}
        status['mcp_available'] = False

    return status


# 便捷的全局初始化函数
async def quick_start(
    plugin_dirs: Optional[List[str]] = None,
    logger: Optional[ILogger] = None
) -> Tuple[PluginManager, MCPPluginBridge]:
    """
    快速启动插件系统

    等同于调用 initialize_plugin_system，所有参数使用默认值。

    参数:
        plugin_dirs: 插件目录列表（可选）
        logger: 日志记录器（可选）

    返回:
        (plugin_manager, mcp_bridge) 元组

    示例:
        from uplifted.extensions.plugin_system_init import quick_start

        # 在 main() 中
        pm, bridge = await quick_start(logger=app_logger)
    """
    return await initialize_plugin_system(
        plugin_dirs=plugin_dirs,
        logger=logger,
        auto_discover=True,
        auto_load=True,
        auto_activate=True
    )


__all__ = [
    'initialize_plugin_system',
    'shutdown_plugin_system',
    'get_plugin_system_status',
    'quick_start'
]
