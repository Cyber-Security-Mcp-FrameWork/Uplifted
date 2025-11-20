# -*- coding: utf-8 -*-
"""Uplifted SDK - Python Client Library

完整的 Uplifted API 客户端，支持所有 API 端点。

Usage:
    >>> from uplifted.sdk import UpliftedClient
    >>> client = UpliftedClient("http://localhost:7541")
    >>>
    >>> # 检查服务状态
    >>> client.status()
    >>>
    >>> # 使用 Agent
    >>> result = client.run_agent(prompt="Hello!")
    >>>
    >>> # 管理插件
    >>> plugins = client.list_plugins()
    >>>
    >>> # 关闭客户端
    >>> client.close()
"""

from .client import UpliftedClient, UpliftedBaseClient

__version__ = "1.0.0"
__all__ = ["UpliftedClient", "UpliftedBaseClient"]