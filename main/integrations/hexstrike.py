# -*- coding: utf-8 -*-
"""
HexStrike AI 整合实现

将 HexStrike AI（150+ 安全工具 + 12+ AI Agents）整合到 Uplifted。
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# 添加框架路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from integration import BaseIntegration

logger = logging.getLogger(__name__)


class HexStrikeIntegration(BaseIntegration):
    """HexStrike AI 整合实现"""

    def __init__(
        self,
        uplifted_url: str = "http://localhost:7541",
        hexstrike_server_url: str = "http://localhost:8888",
        hexstrike_dir: Optional[str] = None
    ):
        """初始化 HexStrike 整合

        Args:
            uplifted_url: Uplifted 服务地址
            hexstrike_server_url: HexStrike Server 地址
            hexstrike_dir: HexStrike AI 目录路径
        """
        super().__init__(uplifted_url)

        self.hexstrike_server_url = hexstrike_server_url

        # 确定 HexStrike 目录
        if hexstrike_dir is None:
            self.hexstrike_dir = Path(__file__).parent.parent / "hexstrike-ai"
        else:
            self.hexstrike_dir = Path(hexstrike_dir)

    # ================================================================
    # 必须实现的方法
    # ================================================================

    def get_integration_name(self) -> str:
        """获取整合名称"""
        return "HexStrike AI"

    def get_service_status(self) -> Dict[str, bool]:
        """检查服务状态"""
        status = {}

        # 检查 Uplifted
        status['Uplifted'] = self.check_uplifted_status()

        # 检查 HexStrike Server
        try:
            response = requests.get(f"{self.hexstrike_server_url}/health", timeout=2)
            status['HexStrike Server'] = response.status_code == 200
        except Exception:
            status['HexStrike Server'] = False

        return status

    def register_to_uplifted(self) -> Dict[str, Any]:
        """将 HexStrike MCP 注册到 Uplifted"""
        mcp_script = self.hexstrike_dir / "hexstrike_mcp.py"
        if not mcp_script.exists():
            raise FileNotFoundError(f"找不到 hexstrike_mcp.py: {mcp_script}")

        mcp_name = "hexstrike-ai"
        mcp_command = sys.executable
        mcp_args = [
            str(mcp_script),
            "--server",
            self.hexstrike_server_url
        ]
        mcp_env = {
            "PYTHONPATH": str(self.hexstrike_dir),
            "HEXSTRIKE_SERVER": self.hexstrike_server_url
        }

        result = self.uplifted_client.add_mcp_tool(
            name=mcp_name,
            command=mcp_command,
            args=mcp_args,
            env=mcp_env
        )
        return result

    def get_available_tools(self) -> List[str]:
        """获取 HexStrike 提供的工具列表"""
        try:
            response = requests.get(f"{self.hexstrike_server_url}/api/tools/list", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('tools', [])
            return []
        except Exception as e:
            logger.error(f"获取 HexStrike 工具列表失败: {e}")
            return []

    # ================================================================
    # 可选实现的方法
    # ================================================================

    def get_service_urls(self) -> Dict[str, str]:
        """获取服务地址"""
        return {
            "Uplifted": self.uplifted_url,
            "HexStrike Server": self.hexstrike_server_url
        }

    def get_startup_commands(self) -> Dict[str, str]:
        """获取服务启动命令"""
        return {
            "Uplifted": "cd server && python -m uplifted.server",
            "HexStrike Server": "cd main/hexstrike-ai && python hexstrike_server.py"
        }

    def get_tool_categories(self) -> Dict[str, List[str]]:
        """获取工具分类"""
        return {
            "🔍 网络扫描": ["nmap", "rustscan", "masscan", "amass", "subfinder"],
            "🌐 Web 测试": ["gobuster", "nuclei", "sqlmap", "ffuf", "nikto"],
            "🔐 密码破解": ["hydra", "john", "hashcat", "medusa"],
            "🔬 二进制分析": ["ghidra", "radare2", "gdb", "binwalk"],
            "☁️ 云安全": ["prowler", "trivy", "kube"],
            "🏆 CTF 工具": ["volatility", "steghide", "foremost", "exiftool"]
        }

    def get_example_prompts(self) -> List[str]:
        """获取示例提示词"""
        return [
            "列出所有网络扫描工具",
            "如何进行 Web 应用安全测试",
            "扫描 example.com（已授权）",
            "使用 nmap 扫描端口",
            "CTF 二进制分析指南"
        ]
