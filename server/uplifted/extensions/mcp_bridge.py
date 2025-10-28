"""
MCP 插件桥接模块

连接插件系统和 MCP 工具服务器，实现插件工具的自动注册和管理。

核心功能：
1. 插件激活时自动注册为 MCP 工具
2. 插件卸载时自动移除工具
3. 维护工具-插件映射关系
4. 支持工具查询和管理

设计原则：
1. 自动化 - 插件工具注册完全自动
2. 一致性 - 工具名称格式统一
3. 可追溯 - 可以查询工具来源插件
4. 容错性 - 注册失败不影响其他工具

使用示例：
    # 创建桥接器
    bridge = MCPPluginBridge(plugin_manager)

    # 注册插件的工具
    await bridge.register_plugin_tools(plugin)

    # 查询工具来源
    plugin_id = bridge.get_tool_source("nmap.port_scan")

    # 同步所有活跃插件
    await bridge.sync_all_plugins()

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from .plugin_manager import Plugin, PluginManager, PluginStatus
from .plugin_manifest import PluginManifest, ToolDefinition
from ..core.interfaces import ILogger


@dataclass
class RegisteredTool:
    """
    已注册工具信息

    记录工具的注册状态和元数据。
    """
    tool_name: str              # 工具全名（如 "com.uplifted.nmap.port_scan"）
    plugin_id: str              # 所属插件 ID
    tool_def: ToolDefinition    # 工具定义
    registered_at: datetime     # 注册时间
    active: bool = True         # 是否激活


class MCPPluginBridge:
    """
    MCP 插件桥接器

    负责在插件系统和 MCP 工具服务器之间建立桥接，
    自动管理工具的注册、卸载和查询。

    属性:
        plugin_manager: 插件管理器实例
        logger: 日志记录器
        _registered_tools: 已注册工具字典 {tool_name: RegisteredTool}
        _plugin_tools: 插件-工具映射 {plugin_id: Set[tool_name]}

    使用示例:
        plugin_manager = PluginManager()
        bridge = MCPPluginBridge(plugin_manager, logger)

        # 注册单个插件的工具
        plugin = plugin_manager.registry.get_plugin("com.uplifted.nmap")
        await bridge.register_plugin_tools(plugin)

        # 批量同步所有插件
        results = await bridge.sync_all_plugins()
        print(f"Synced {len(results)} plugins")
    """

    def __init__(self,
                 plugin_manager: PluginManager,
                 logger: Optional[ILogger] = None):
        """
        初始化 MCP 桥接器

        参数:
            plugin_manager: 插件管理器实例
            logger: 日志记录器（可选）
        """
        self.plugin_manager = plugin_manager
        self.logger = logger or logging.getLogger(__name__)

        # 已注册工具映射：tool_name -> RegisteredTool
        self._registered_tools: Dict[str, RegisteredTool] = {}

        # 插件工具映射：plugin_id -> Set[tool_name]
        self._plugin_tools: Dict[str, Set[str]] = {}

        # 同步锁
        self._lock = asyncio.Lock()

    async def register_plugin_tools(self, plugin: Plugin) -> bool:
        """
        注册插件的所有工具到 MCP 服务器

        自动将插件清单中定义的工具注册为 MCP 工具。
        工具名称格式：{plugin_id}.{tool_name}

        参数:
            plugin: 插件实例

        返回:
            True 表示至少有一个工具注册成功，False 表示全部失败

        异常:
            不会抛出异常，所有错误都会被捕获和记录

        示例:
            plugin = plugin_manager.registry.get_plugin("com.uplifted.nmap")
            success = await bridge.register_plugin_tools(plugin)
            if success:
                print("Tools registered successfully")
        """
        async with self._lock:
            # 检查插件是否有 manifest
            if not hasattr(plugin, 'manifest') or not isinstance(plugin.manifest, PluginManifest):
                if self.logger:
                    self.logger.warning(
                        f"Plugin {plugin.info.name if hasattr(plugin, 'info') else 'unknown'} "
                        "does not have a valid PluginManifest"
                    )
                return False

            manifest = plugin.manifest

            # 检查是否有工具定义
            if not manifest.tools:
                if self.logger:
                    self.logger.info(
                        f"Plugin {manifest.id} does not provide any tools"
                    )
                return True  # 没有工具不是错误

            # 注册每个工具
            success_count = 0
            plugin_tool_names = set()

            for tool_def in manifest.tools:
                try:
                    # 构建工具全名
                    tool_full_name = f"{manifest.id}.{tool_def.name}"

                    # 检查是否已注册
                    if tool_full_name in self._registered_tools:
                        if self.logger:
                            self.logger.warning(
                                f"Tool {tool_full_name} already registered, skipping"
                            )
                        continue

                    # 注册到 MCP 服务器
                    registered = await self._register_mcp_tool(tool_full_name, tool_def, manifest)

                    if registered:
                        # 记录注册信息
                        reg_tool = RegisteredTool(
                            tool_name=tool_full_name,
                            plugin_id=manifest.id,
                            tool_def=tool_def,
                            registered_at=datetime.now(),
                            active=True
                        )

                        self._registered_tools[tool_full_name] = reg_tool
                        plugin_tool_names.add(tool_full_name)
                        success_count += 1

                        if self.logger:
                            self.logger.info(
                                f"✓ Registered tool: {tool_full_name}"
                            )

                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Failed to register tool {tool_def.name} from plugin {manifest.id}: {e}",
                            exc_info=True
                        )

            # 更新插件工具映射
            if plugin_tool_names:
                if manifest.id not in self._plugin_tools:
                    self._plugin_tools[manifest.id] = set()
                self._plugin_tools[manifest.id].update(plugin_tool_names)

            if self.logger:
                self.logger.info(
                    f"Plugin {manifest.id}: registered {success_count}/{len(manifest.tools)} tools"
                )

            return success_count > 0

    async def _register_mcp_tool(self,
                                  tool_name: str,
                                  tool_def: ToolDefinition,
                                  manifest: PluginManifest) -> bool:
        """
        注册单个工具到 MCP 服务器

        内部方法，负责实际的 MCP 工具注册。

        参数:
            tool_name: 工具全名
            tool_def: 工具定义
            manifest: 插件清单

        返回:
            是否注册成功
        """
        try:
            # 导入 MCP 工具注册函数
            from ..tools_server.server.tools import add_mcp_tool_

            # 确定 MCP 命令和参数
            mcp_command = tool_def.mcp_command or "python"
            mcp_args = tool_def.mcp_args or ["-m", tool_def.entry_point]
            mcp_env = tool_def.mcp_env or {}

            # 调用 MCP 注册函数
            await add_mcp_tool_(
                name=tool_name,
                command=mcp_command,
                args=mcp_args,
                env=mcp_env
            )

            return True

        except ImportError as e:
            if self.logger:
                self.logger.error(
                    f"Cannot import MCP tools server: {e}. "
                    "Make sure tools_server is properly installed."
                )
            return False

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"Failed to register MCP tool {tool_name}: {e}",
                    exc_info=True
                )
            return False

    async def unregister_plugin_tools(self, plugin_id: str) -> bool:
        """
        卸载插件的所有工具

        从 MCP 服务器移除插件的所有工具，并清理映射关系。

        参数:
            plugin_id: 插件 ID

        返回:
            是否成功卸载

        示例:
            await bridge.unregister_plugin_tools("com.uplifted.nmap")
        """
        async with self._lock:
            # 查找插件的所有工具
            if plugin_id not in self._plugin_tools:
                if self.logger:
                    self.logger.warning(
                        f"Plugin {plugin_id} has no registered tools"
                    )
                return True

            tool_names = self._plugin_tools[plugin_id].copy()

            # 卸载每个工具
            for tool_name in tool_names:
                try:
                    # 标记为非激活
                    if tool_name in self._registered_tools:
                        self._registered_tools[tool_name].active = False

                    # 从 MCP 服务器移除
                    # TODO: 实现 MCP 工具卸载函数
                    # await remove_mcp_tool_(tool_name)

                    # 从映射中移除
                    del self._registered_tools[tool_name]

                    if self.logger:
                        self.logger.info(
                            f"✓ Unregistered tool: {tool_name}"
                        )

                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Failed to unregister tool {tool_name}: {e}",
                            exc_info=True
                        )

            # 清理插件工具映射
            del self._plugin_tools[plugin_id]

            if self.logger:
                self.logger.info(
                    f"Plugin {plugin_id}: unregistered {len(tool_names)} tools"
                )

            return True

    async def sync_all_plugins(self) -> Dict[str, bool]:
        """
        同步所有活跃插件到 MCP 服务器

        扫描所有状态为 ACTIVE 的插件，注册它们的工具。
        常用于系统启动时的初始化。

        返回:
            插件 ID -> 注册结果的字典

        示例:
            results = await bridge.sync_all_plugins()
            for plugin_id, success in results.items():
                status = "✓" if success else "✗"
                print(f"{status} {plugin_id}")
        """
        async with self._lock:
            results = {}

            # 获取所有活跃插件
            active_plugins = self.plugin_manager.registry.get_plugins_by_status(
                PluginStatus.ACTIVE
            )

            if self.logger:
                self.logger.info(
                    f"Syncing {len(active_plugins)} active plugins to MCP server..."
                )

            # 逐个注册
            for plugin in active_plugins:
                try:
                    if hasattr(plugin, 'manifest'):
                        plugin_id = plugin.manifest.id
                        success = await self.register_plugin_tools(plugin)
                        results[plugin_id] = success
                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Failed to sync plugin: {e}",
                            exc_info=True
                        )

            if self.logger:
                success_count = sum(1 for v in results.values() if v)
                self.logger.info(
                    f"Sync completed: {success_count}/{len(results)} plugins successful"
                )

            return results

    def get_tool_source(self, tool_name: str) -> Optional[str]:
        """
        查询工具来源插件

        根据工具名称查找提供该工具的插件 ID。

        参数:
            tool_name: 工具名称（可以是全名或短名）

        返回:
            插件 ID，如果未找到则返回 None

        示例:
            plugin_id = bridge.get_tool_source("com.uplifted.nmap.port_scan")
            # 返回: "com.uplifted.nmap"

            plugin_id = bridge.get_tool_source("port_scan")
            # 如果唯一，返回插件 ID；否则返回 None
        """
        # 精确匹配
        if tool_name in self._registered_tools:
            return self._registered_tools[tool_name].plugin_id

        # 短名匹配（如果唯一）
        matches = [
            reg_tool.plugin_id
            for name, reg_tool in self._registered_tools.items()
            if name.endswith('.' + tool_name)
        ]

        if len(matches) == 1:
            return matches[0]

        return None

    def get_plugin_tools(self, plugin_id: str) -> List[str]:
        """
        获取插件的所有工具

        参数:
            plugin_id: 插件 ID

        返回:
            工具名称列表

        示例:
            tools = bridge.get_plugin_tools("com.uplifted.nmap")
            # 返回: ["com.uplifted.nmap.port_scan", "com.uplifted.nmap.service_detect"]
        """
        return list(self._plugin_tools.get(plugin_id, set()))

    def get_all_registered_tools(self) -> List[RegisteredTool]:
        """
        获取所有已注册工具

        返回:
            已注册工具列表

        示例:
            tools = bridge.get_all_registered_tools()
            for tool in tools:
                print(f"{tool.tool_name} from {tool.plugin_id}")
        """
        return [
            reg_tool for reg_tool in self._registered_tools.values()
            if reg_tool.active
        ]

    def get_tool_info(self, tool_name: str) -> Optional[RegisteredTool]:
        """
        获取工具详细信息

        参数:
            tool_name: 工具名称

        返回:
            工具信息，如果不存在则返回 None

        示例:
            info = bridge.get_tool_info("com.uplifted.nmap.port_scan")
            if info:
                print(f"Tool: {info.tool_name}")
                print(f"Plugin: {info.plugin_id}")
                print(f"Description: {info.tool_def.description}")
        """
        return self._registered_tools.get(tool_name)

    def get_statistics(self) -> Dict[str, any]:
        """
        获取桥接器统计信息

        返回:
            统计信息字典

        示例:
            stats = bridge.get_statistics()
            print(f"Total tools: {stats['total_tools']}")
            print(f"Total plugins: {stats['total_plugins']}")
        """
        return {
            'total_tools': len(self._registered_tools),
            'active_tools': sum(1 for t in self._registered_tools.values() if t.active),
            'total_plugins': len(self._plugin_tools),
            'tools_by_plugin': {
                plugin_id: len(tools)
                for plugin_id, tools in self._plugin_tools.items()
            }
        }


# 全局桥接器实例
_global_mcp_bridge: Optional[MCPPluginBridge] = None


def get_global_mcp_bridge() -> Optional[MCPPluginBridge]:
    """
    获取全局 MCP 桥接器实例

    返回:
        全局桥接器实例，如果未初始化则返回 None

    使用:
        bridge = get_global_mcp_bridge()
        if bridge:
            tools = bridge.get_all_registered_tools()
    """
    return _global_mcp_bridge


def initialize_mcp_bridge(plugin_manager: PluginManager,
                          logger: Optional[ILogger] = None) -> MCPPluginBridge:
    """
    初始化全局 MCP 桥接器

    应在系统启动时调用一次。

    参数:
        plugin_manager: 插件管理器实例
        logger: 日志记录器（可选）

    返回:
        创建的桥接器实例

    示例:
        # 在系统启动时
        plugin_manager = get_global_plugin_manager()
        bridge = initialize_mcp_bridge(plugin_manager)

        # 同步现有插件
        await bridge.sync_all_plugins()
    """
    global _global_mcp_bridge

    _global_mcp_bridge = MCPPluginBridge(plugin_manager, logger)

    if logger:
        logger.info("MCP Plugin Bridge initialized")

    return _global_mcp_bridge
