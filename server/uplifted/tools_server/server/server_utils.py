import logging
from typing import Dict, Any, List, Optional

# 全局字典用于存储服务器实例
# 键: (name, command, tuple(args), frozenset(env.items()))
# 值: 服务器实例
_server_instances = {}

async def cleanup_all_servers():
    """
    清理所有服务器实例。
    应在应用程序关闭时调用此函数。
    """
    if not _server_instances:
        logging.info("没有需要清理的服务器实例")
        return
        
    logging.info(f"正在清理 {_server_instances.__len__()} 个服务器实例")
    # 为避免循环导入，此处需要导入 Server
    # 仅在关闭期间调用 cleanup_all_servers 时才安全
    for server in list(_server_instances.values()):
        try:
            await server.cleanup()
        except Exception as e:
            logging.error(f"清理服务器 {server.name} 时出错: {e}")
    
    # 为确保万无一失，清空字典
    _server_instances.clear()
    logging.info("所有服务器实例已被清理")