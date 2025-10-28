"""
完整的服务器启动示例（集成插件系统）

演示如何在 Uplifted 服务器启动时初始化插件系统，
包括插件发现、加载、激活和 MCP 工具注册。

使用方法:
    python examples/server_with_plugins.py

作者: Uplifted Team
日期: 2025-10-28
"""

import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    主函数：初始化并启动服务器
    """
    logger.info("=" * 60)
    logger.info("Uplifted Server with Plugin System")
    logger.info("=" * 60)

    # 导入 Uplifted 模块
    from uplifted.extensions import (
        quick_start,
        get_plugin_system_status,
        shutdown_plugin_system
    )

    # 1. 初始化插件系统
    logger.info("\n[Step 1] Initializing plugin system...")
    try:
        # 指定插件目录（可选，默认会搜索 ./plugins 和内置目录）
        plugin_dirs = [
            str(Path(__file__).parent / "plugins"),  # examples/plugins/
        ]

        # 快速启动：自动发现、加载、激活所有插件
        plugin_manager, mcp_bridge = await quick_start(
            plugin_dirs=plugin_dirs,
            logger=logger
        )

        logger.info("✓ Plugin system initialized successfully")

    except Exception as e:
        logger.error(f"✗ Failed to initialize plugin system: {e}", exc_info=True)
        return

    # 2. 显示系统状态
    logger.info("\n[Step 2] Plugin system status:")
    status = get_plugin_system_status(plugin_manager, mcp_bridge)

    logger.info(f"  • Total plugins: {status['plugin_count']}")
    logger.info(f"  • Active plugins: {status['active_plugin_count']}")
    logger.info(f"  • MCP available: {status['mcp_available']}")

    if status['mcp_available']:
        mcp_stats = status['mcp_stats']
        logger.info(f"  • Total tools: {mcp_stats['total_tools']}")
        logger.info(f"  • Active tools: {mcp_stats['active_tools']}")

        # 显示每个插件的工具数量
        logger.info("\n  Tools by plugin:")
        for plugin_id, count in mcp_stats.get('tools_by_plugin', {}).items():
            logger.info(f"    - {plugin_id}: {count} tools")

    # 显示所有插件详情
    logger.info("\n  Loaded plugins:")
    for plugin_name, plugin_info in status.get('plugins', {}).items():
        logger.info(
            f"    - {plugin_name} v{plugin_info['version']} [{plugin_info['status']}]"
        )
        if plugin_info['description']:
            logger.info(f"      {plugin_info['description']}")

    # 3. 启动 FastAPI 服务器
    logger.info("\n[Step 3] Starting FastAPI server...")
    logger.info("  Server will be available at:")
    logger.info("    • Main API: http://localhost:7541")
    logger.info("    • Plugin API: http://localhost:7541/api/v1/plugins")
    logger.info("    • Tools API: http://localhost:7541/api/v1/tools")
    logger.info("    • System Status: http://localhost:7541/api/v1/system/status")
    logger.info("    • API Docs: http://localhost:7541/docs")

    # 导入并运行服务器
    from uplifted.server import run_main_server_internal

    try:
        # 在实际部署中，可以使用 run_main_server() 而不是 run_main_server_internal()
        # run_main_server_internal() 用于开发模式，启用热重载
        run_main_server_internal(reload=False)

    except KeyboardInterrupt:
        logger.info("\n[Shutdown] Received shutdown signal")

    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)

    finally:
        # 4. 清理插件系统
        logger.info("\n[Step 4] Shutting down plugin system...")
        try:
            await shutdown_plugin_system(plugin_manager, logger)
            logger.info("✓ Plugin system shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("Server stopped")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
