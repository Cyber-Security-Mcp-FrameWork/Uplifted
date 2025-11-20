# -*- coding: utf-8 -*-
"""
基础整合类

定义通用的整合接口，所有具体整合都应继承此类。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

# 添加 SDK 路径
sdk_path = Path(__file__).parent.parent / "sdk"
sys.path.insert(0, str(sdk_path))

from sdk import UpliftedClient


class BaseIntegration(ABC):
    """基础整合类，定义通用整合接口"""

    def __init__(self, uplifted_url: str = "http://localhost:7541"):
        """初始化整合

        Args:
            uplifted_url: Uplifted 服务地址
        """
        self.uplifted_url = uplifted_url
        self.uplifted_client = UpliftedClient(uplifted_url)

    # ================================================================
    # 必须实现的方法（子类必须覆盖）
    # ================================================================

    @abstractmethod
    def get_integration_name(self) -> str:
        """获取整合名称

        Returns:
            str: 整合名称，如 "HexStrike AI"
        """
        pass

    @abstractmethod
    def get_service_status(self) -> Dict[str, bool]:
        """检查整合服务状态

        Returns:
            Dict[str, bool]: 各服务的运行状态
            示例: {'uplifted': True, 'external_service': True}
        """
        pass

    @abstractmethod
    def register_to_uplifted(self) -> Dict[str, Any]:
        """将工具注册到 Uplifted

        Returns:
            Dict[str, Any]: 注册结果
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表

        Returns:
            List[str]: 工具名称列表
        """
        pass

    # ================================================================
    # 可选实现的方法（子类可以覆盖以提供更多功能）
    # ================================================================

    def get_service_urls(self) -> Dict[str, str]:
        """获取服务地址信息

        Returns:
            Dict[str, str]: 服务名称到 URL 的映射
        """
        return {
            "uplifted": self.uplifted_url
        }

    def get_startup_commands(self) -> Dict[str, str]:
        """获取服务启动命令

        Returns:
            Dict[str, str]: 服务名称到启动命令的映射
        """
        return {}

    def get_tool_categories(self) -> Dict[str, List[str]]:
        """获取工具分类

        Returns:
            Dict[str, List[str]]: 分类名到关键词列表的映射
            示例: {"网络工具": ["nmap", "scan"], "Web工具": ["gobuster"]}
        """
        return {}

    def get_example_prompts(self) -> List[str]:
        """获取示例提示词

        Returns:
            List[str]: 示例提示词列表
        """
        return []

    # ================================================================
    # 通用方法（所有整合都可使用）
    # ================================================================

    def check_uplifted_status(self) -> bool:
        """检查 Uplifted 服务状态

        Returns:
            bool: True 表示服务正常
        """
        try:
            return self.uplifted_client.status()
        except Exception:
            return False

    def run_agent(self, prompt: str, tools: Optional[List[str]] = None, **kwargs) -> Any:
        """通过 Uplifted 运行 Agent

        Args:
            prompt: 提示词
            tools: 工具列表（可选）
            **kwargs: 其他参数

        Returns:
            Any: Agent 执行结果
        """
        return self.uplifted_client.run_agent(
            prompt=prompt,
            tools=tools or [],
            **kwargs
        )

    def test_integration(self) -> bool:
        """测试整合是否成功

        Returns:
            bool: 测试是否通过
        """
        # 检查所有服务状态
        status = self.get_service_status()
        if not all(status.values()):
            return False

        # 测试工具列表获取
        try:
            tools_info = self.uplifted_client.call_get_tools()
            return tools_info.get('count', 0) > 0
        except Exception:
            return False
