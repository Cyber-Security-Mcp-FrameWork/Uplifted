#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HexStrike AI x Uplifted 整合工具

问答式交互工具，用于将 HexStrike AI 整合到 Uplifted。

使用前提：
1. Uplifted 服务已启动 (http://localhost:7541)
2. HexStrike Server 已启动 (http://localhost:8888)

使用方式：
    python hexstrike_integration.py
"""

import sys
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any
import requests

# 添加 SDK 路径
sdk_path = Path(__file__).parent / "sdk"
sys.path.insert(0, str(sdk_path))

from sdk import UpliftedClient

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


class HexStrikeIntegration:
    """HexStrike AI x Uplifted 整合类"""

    def __init__(
        self,
        uplifted_url: str = "http://localhost:7541",
        hexstrike_server_url: str = "http://localhost:8888",
        hexstrike_dir: Optional[str] = None
    ):
        """初始化整合配置"""
        self.uplifted_url = uplifted_url
        self.hexstrike_server_url = hexstrike_server_url

        # 确定 HexStrike 目录
        if hexstrike_dir is None:
            self.hexstrike_dir = Path(__file__).parent / "hexstrike-ai"
        else:
            self.hexstrike_dir = Path(hexstrike_dir)

        # 初始化 Uplifted 客户端
        self.uplifted_client = UpliftedClient(uplifted_url)

    def check_services(self) -> Dict[str, bool]:
        """检查服务状态"""
        status = {}

        # 检查 Uplifted
        try:
            status['uplifted'] = self.uplifted_client.status()
        except Exception:
            status['uplifted'] = False

        # 检查 HexStrike Server
        try:
            response = requests.get(f"{self.hexstrike_server_url}/health", timeout=2)
            status['hexstrike'] = response.status_code == 200
        except Exception:
            status['hexstrike'] = False

        return status

    def register_hexstrike_mcp(self) -> Dict[str, Any]:
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

    def get_hexstrike_tools(self) -> List[str]:
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

    def run_agent(self, prompt: str, tools: Optional[List[str]] = None, **kwargs) -> Any:
        """通过 Uplifted 运行 Agent"""
        return self.uplifted_client.run_agent(
            prompt=prompt,
            tools=tools or [],
            **kwargs
        )


class ConversationalCLI:
    """问答式交互界面"""

    def __init__(self, integration: HexStrikeIntegration):
        self.integration = integration
        self.mcp_registered = False

    def print_header(self):
        """打印欢迎头"""
        print(f"\n{Colors.HEADER}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}    HexStrike AI x Uplifted 整合助手{Colors.RESET}")
        print(f"{Colors.DIM}    AI-Powered Cybersecurity Automation Platform{Colors.RESET}")
        print(f"{Colors.HEADER}{'='*70}{Colors.RESET}\n")

    def print_status_summary(self, status: Dict[str, bool]):
        """打印状态摘要"""
        if all(status.values()):
            print(f"{Colors.GREEN}✓ 所有服务运行正常{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠ 部分服务未运行：{Colors.RESET}")
            if not status['uplifted']:
                print(f"  {Colors.RED}✗ Uplifted 未运行{Colors.RESET} - 启动: {Colors.DIM}cd server && python -m uplifted.server{Colors.RESET}")
            if not status['hexstrike']:
                print(f"  {Colors.RED}✗ HexStrike 未运行{Colors.RESET} - 启动: {Colors.DIM}cd main/hexstrike-ai && python hexstrike_server.py{Colors.RESET}")

    def print_help(self):
        """打印帮助信息"""
        print(f"\n{Colors.BOLD}我可以帮您：{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 检查服务状态 - 输入: {Colors.DIM}状态 / status{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 注册 HexStrike - 输入: {Colors.DIM}注册 / register{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 测试整合 - 输入: {Colors.DIM}测试 / test{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 列出工具 - 输入: {Colors.DIM}工具 / tools{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 运行任务 - 直接描述您的需求，例如：")
        print(f"    {Colors.DIM}\"扫描 example.com\"")
        print(f"    \"列出所有网络扫描工具\"")
        print(f"    \"如何进行 Web 应用安全测试\"{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 退出 - 输入: {Colors.DIM}退出 / exit / quit{Colors.RESET}")
        print()

    def handle_status(self):
        """处理状态查询"""
        print(f"\n{Colors.BOLD}正在检查服务状态...{Colors.RESET}\n")

        status = self.integration.check_services()

        # Uplifted
        if status['uplifted']:
            print(f"{Colors.GREEN}✓ Uplifted 服务正常{Colors.RESET}")
            print(f"  地址: {self.integration.uplifted_url}")
        else:
            print(f"{Colors.RED}✗ Uplifted 服务未运行{Colors.RESET}")
            print(f"  {Colors.YELLOW}启动命令:{Colors.RESET} cd server && python -m uplifted.server")

        # HexStrike
        if status['hexstrike']:
            print(f"{Colors.GREEN}✓ HexStrike Server 正常{Colors.RESET}")
            print(f"  地址: {self.integration.hexstrike_server_url}")
        else:
            print(f"{Colors.RED}✗ HexStrike Server 未运行{Colors.RESET}")
            print(f"  {Colors.YELLOW}启动命令:{Colors.RESET} cd main/hexstrike-ai && python hexstrike_server.py")

        print()

    def handle_register(self):
        """处理 MCP 注册"""
        print(f"\n{Colors.BOLD}正在注册 HexStrike MCP...{Colors.RESET}\n")

        # 检查服务
        status = self.integration.check_services()
        if not status['uplifted']:
            print(f"{Colors.RED}✗ Uplifted 服务未运行，无法注册{Colors.RESET}")
            print(f"  请先启动 Uplifted 服务\n")
            return
        if not status['hexstrike']:
            print(f"{Colors.RED}✗ HexStrike Server 未运行，无法注册{Colors.RESET}")
            print(f"  请先启动 HexStrike Server\n")
            return

        try:
            result = self.integration.register_hexstrike_mcp()
            self.mcp_registered = True
            print(f"{Colors.GREEN}✓ HexStrike MCP 注册成功！{Colors.RESET}")
            print(f"  现在可以通过 Uplifted Agent 使用 HexStrike 工具了\n")
        except Exception as e:
            print(f"{Colors.RED}✗ 注册失败: {e}{Colors.RESET}\n")

    def handle_test(self):
        """处理整合测试"""
        print(f"\n{Colors.BOLD}正在测试整合...{Colors.RESET}\n")

        # 检查服务
        status = self.integration.check_services()

        if not status['uplifted']:
            print(f"{Colors.RED}✗ Uplifted 服务未运行{Colors.RESET}\n")
            return False
        print(f"{Colors.GREEN}✓ Uplifted 服务正常{Colors.RESET}")

        if not status['hexstrike']:
            print(f"{Colors.RED}✗ HexStrike Server 未运行{Colors.RESET}\n")
            return False
        print(f"{Colors.GREEN}✓ HexStrike Server 正常{Colors.RESET}")

        # 测试工具列表
        try:
            tools_info = self.integration.uplifted_client.call_get_tools()
            tool_count = tools_info.get('count', 0)
            print(f"{Colors.GREEN}✓ 成功获取工具列表（共 {tool_count} 个工具）{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}✗ 获取工具列表失败: {e}{Colors.RESET}\n")
            return False

        print(f"\n{Colors.GREEN}{'='*60}")
        print("整合测试通过！")
        print(f"{'='*60}{Colors.RESET}\n")
        return True

    def handle_list_tools(self):
        """处理工具列表"""
        print(f"\n{Colors.BOLD}HexStrike 工具列表：{Colors.RESET}\n")

        if not self.integration.check_services()['hexstrike']:
            print(f"{Colors.RED}✗ HexStrike Server 未运行{Colors.RESET}\n")
            return

        tools = self.integration.get_hexstrike_tools()

        if not tools:
            print(f"{Colors.YELLOW}未找到工具（HexStrike Server 可能未完全启动）{Colors.RESET}\n")
            return

        print(f"找到 {Colors.GREEN}{len(tools)}{Colors.RESET} 个安全工具\n")

        # 分类显示
        categories = {
            "🔍 网络扫描": ["nmap", "rustscan", "masscan", "amass", "subfinder"],
            "🌐 Web 测试": ["gobuster", "nuclei", "sqlmap", "ffuf", "nikto"],
            "🔐 密码破解": ["hydra", "john", "hashcat", "medusa"],
            "🔬 二进制分析": ["ghidra", "radare2", "gdb", "binwalk"],
            "☁️ 云安全": ["prowler", "trivy", "kube"],
            "🏆 CTF 工具": ["volatility", "steghide", "foremost", "exiftool"]
        }

        for category, keywords in categories.items():
            category_tools = [t for t in tools if any(k in t.lower() for k in keywords)]
            if category_tools:
                print(f"{Colors.CYAN}{category}:{Colors.RESET}")
                for tool in category_tools[:5]:
                    print(f"  • {tool}")
                if len(category_tools) > 5:
                    print(f"  {Colors.DIM}... 还有 {len(category_tools) - 5} 个{Colors.RESET}")
                print()

    def handle_agent_request(self, user_input: str):
        """处理 Agent 请求"""
        print(f"\n{Colors.CYAN}正在处理您的请求...{Colors.RESET}\n")

        status = self.integration.check_services()
        if not all(status.values()):
            print(f"{Colors.RED}✗ 服务未完全启动，无法执行{Colors.RESET}")
            self.print_status_summary(status)
            print()
            return

        if not self.mcp_registered:
            print(f"{Colors.YELLOW}⚠ 提示: HexStrike MCP 尚未注册{Colors.RESET}")
            register = input(f"是否现在注册？(y/n) {Colors.DIM}[y]{Colors.RESET}: ").strip().lower()
            if register in ['', 'y', 'yes']:
                self.handle_register()
            else:
                print(f"{Colors.YELLOW}取消执行{Colors.RESET}\n")
                return

        try:
            result = self.integration.run_agent(prompt=user_input)
            print(f"{Colors.GREEN}{'='*60}")
            print("Agent 响应：")
            print(f"{'='*60}{Colors.RESET}\n")
            print(result)
            print()
        except Exception as e:
            print(f"{Colors.RED}✗ 执行失败: {e}{Colors.RESET}\n")

    def parse_intent(self, user_input: str) -> str:
        """解析用户意图"""
        user_input = user_input.lower().strip()

        # 退出命令
        if user_input in ['exit', 'quit', '退出', 'q', 'bye']:
            return 'exit'

        # 帮助命令
        if user_input in ['help', '帮助', 'h', '?']:
            return 'help'

        # 状态查询
        if any(kw in user_input for kw in ['状态', 'status', 'check', '检查']):
            return 'status'

        # 注册命令
        if any(kw in user_input for kw in ['注册', 'register', 'setup']):
            return 'register'

        # 测试命令
        if any(kw in user_input for kw in ['测试', 'test', '验证']):
            return 'test'

        # 工具列表
        if any(kw in user_input for kw in ['工具', 'tools', 'list', '列出']):
            return 'list_tools'

        # 其他任何输入都视为 Agent 请求
        return 'agent_request'

    def run(self):
        """运行交互式对话"""
        self.print_header()

        # 首次检查服务
        print(f"{Colors.BOLD}欢迎使用 HexStrike AI x Uplifted 整合助手！{Colors.RESET}\n")
        status = self.integration.check_services()
        self.print_status_summary(status)

        print(f"\n{Colors.DIM}输入 'help' 或 '帮助' 查看可用命令{Colors.RESET}")
        print(f"{Colors.DIM}您也可以直接描述您的需求，例如：\"列出所有网络扫描工具\"{Colors.RESET}\n")

        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = input(f"{Colors.BOLD}{Colors.CYAN}您>{Colors.RESET} ").strip()

                if not user_input:
                    continue

                # 解析意图
                intent = self.parse_intent(user_input)

                # 执行对应操作
                if intent == 'exit':
                    print(f"\n{Colors.GREEN}再见！祝您安全测试顺利 🚀{Colors.RESET}\n")
                    break
                elif intent == 'help':
                    self.print_help()
                elif intent == 'status':
                    self.handle_status()
                elif intent == 'register':
                    self.handle_register()
                elif intent == 'test':
                    self.handle_test()
                elif intent == 'list_tools':
                    self.handle_list_tools()
                elif intent == 'agent_request':
                    self.handle_agent_request(user_input)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}操作已取消{Colors.RESET}")
                continue
            except EOFError:
                print(f"\n\n{Colors.GREEN}再见！{Colors.RESET}\n")
                break
            except Exception as e:
                print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}\n")


def main():
    """主函数"""
    try:
        # 创建整合实例
        integration = HexStrikeIntegration(
            uplifted_url="http://localhost:7541",
            hexstrike_server_url="http://localhost:8888"
        )

        # 运行交互式对话
        cli = ConversationalCLI(integration)
        cli.run()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}程序已退出{Colors.RESET}\n")
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
