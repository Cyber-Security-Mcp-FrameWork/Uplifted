import base64
import httpx
from typing import Dict, List, Any, Callable, Optional


class ToolManager:
    """Uplifted 函数 API 的客户端，用于管理和调用远程工具。"""

    def __init__(self):
        """初始化 Uplifted 函数客户端，设置基础 URL。"""
        self.base_url = "http://localhost:8086"
    
    def __enter__(self):
        """进入上下文管理，返回自身实例。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理，无需额外清理操作。"""
        pass

    def close(self):
        """关闭客户端会话（占位方法）。"""
        pass

    def list_tools(self) -> Any:
        """获取所有已注册工具的列表。

        返回:
            包含工具信息的 JSON 对象。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/functions/tools",
            )
            response.raise_for_status()
            return response.json()

    def install_library(self, library: str) -> Dict[str, Any]:
        """
        安装指定的第三方库。

        参数:
            library: 要安装的库名称。

        返回:
            工具执行结果的字典。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/tools/install_library",
                json={"library": library},
            )
            response.raise_for_status()
            return response.json()

    def uninstall_library(self, library: str) -> Dict[str, Any]:
        """
        卸载指定的第三方库。

        参数:
            library: 要卸载的库名称。

        返回:
            工具执行结果的字典。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/tools/uninstall_library",
                json={"library": library},
            )
            response.raise_for_status()
            return response.json()

    def add_tool(self, function) -> Dict[str, Any]:
        """
        向 Uplifted API 添加新的函数式工具。

        参数:
            function: 工具函数的定义或标识。

        返回:
            添加操作的结果。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/tools/add_tool",
                json={"function": function},
            )
            response.raise_for_status()
            return response.json()

    def add_mcp_tool(self, name: str, command: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
        """
        添加基于 MCP（多进程客户端）的工具。

        参数:
            name: 工具名称。
            command: 执行命令。
            args: 命令行参数列表。
            env: 环境变量字典。

        返回:
            工具添加结果。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/tools/add_mcp_tool",
                json={"name": name, "command": command, "args": args, "env": env},
            )
            response.raise_for_status()
            return response.json()

    def add_sse_mcp(self, name: str, url: str) -> Dict[str, Any]:
        """
        添加基于 SSE（服务器发送事件）的 MCP 工具。

        参数:
            name: 工具名称。
            url: SSE 事件源 URL。

        返回:
            工具添加结果。"""
        with httpx.Client(timeout=600.0) as session:
            response = session.post(
                f"{self.base_url}/tools/add_sse_mcp",
                json={"name": name, "url": url},
            )
            response.raise_for_status()
            return response.json