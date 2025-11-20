# -*- coding: utf-8 -*-
"""
通用交互式 CLI

提供问答式交互界面，支持任何 BaseIntegration 实现。
"""

from typing import Dict
from .base import BaseIntegration


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


class ConversationalCLI:
    """通用问答式交互界面"""

    def __init__(self, integration: BaseIntegration):
        """初始化 CLI

        Args:
            integration: BaseIntegration 实现
        """
        self.integration = integration
        self.registered = False

    def print_header(self):
        """打印欢迎头"""
        name = self.integration.get_integration_name()
        print(f"\n{Colors.HEADER}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}    {name} x Uplifted 整合助手{Colors.RESET}")
        print(f"{Colors.DIM}    Powered by Uplifted Integration Framework{Colors.RESET}")
        print(f"{Colors.HEADER}{'='*70}{Colors.RESET}\n")

    def print_status_summary(self, status: Dict[str, bool]):
        """打印状态摘要

        Args:
            status: 服务状态字典
        """
        if all(status.values()):
            print(f"{Colors.GREEN}✓ 所有服务运行正常{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠ 部分服务未运行：{Colors.RESET}")
            startup_commands = self.integration.get_startup_commands()
            for service, is_running in status.items():
                if not is_running:
                    cmd = startup_commands.get(service, "未提供启动命令")
                    print(f"  {Colors.RED}✗ {service} 未运行{Colors.RESET}")
                    if cmd != "未提供启动命令":
                        print(f"    启动: {Colors.DIM}{cmd}{Colors.RESET}")

    def print_help(self):
        """打印帮助信息"""
        print(f"\n{Colors.BOLD}我可以帮您：{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 检查服务状态 - 输入: {Colors.DIM}状态 / status{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 注册整合 - 输入: {Colors.DIM}注册 / register{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 测试整合 - 输入: {Colors.DIM}测试 / test{Colors.RESET}")
        print(f"  {Colors.CYAN}•{Colors.RESET} 列出工具 - 输入: {Colors.DIM}工具 / tools{Colors.RESET}")

        # 显示示例提示词
        examples = self.integration.get_example_prompts()
        if examples:
            print(f"  {Colors.CYAN}•{Colors.RESET} 运行任务 - 直接描述您的需求，例如：")
            for example in examples[:3]:  # 只显示前 3 个
                print(f"    {Colors.DIM}\"{example}\"{Colors.RESET}")

        print(f"  {Colors.CYAN}•{Colors.RESET} 退出 - 输入: {Colors.DIM}退出 / exit / quit{Colors.RESET}")
        print()

    def handle_status(self):
        """处理状态查询"""
        print(f"\n{Colors.BOLD}正在检查服务状态...{Colors.RESET}\n")

        status = self.integration.get_service_status()
        urls = self.integration.get_service_urls()

        for service, is_running in status.items():
            url = urls.get(service, "")
            if is_running:
                print(f"{Colors.GREEN}✓ {service} 服务正常{Colors.RESET}")
                if url:
                    print(f"  地址: {url}")
            else:
                print(f"{Colors.RED}✗ {service} 服务未运行{Colors.RESET}")
                startup_cmd = self.integration.get_startup_commands().get(service)
                if startup_cmd:
                    print(f"  {Colors.YELLOW}启动命令:{Colors.RESET} {startup_cmd}")

        print()

    def handle_register(self):
        """处理注册"""
        name = self.integration.get_integration_name()
        print(f"\n{Colors.BOLD}正在注册 {name}...{Colors.RESET}\n")

        # 检查服务
        status = self.integration.get_service_status()
        if not all(status.values()):
            print(f"{Colors.RED}✗ 部分服务未运行，无法注册{Colors.RESET}")
            self.print_status_summary(status)
            print()
            return

        try:
            result = self.integration.register_to_uplifted()
            self.registered = True
            print(f"{Colors.GREEN}✓ {name} 注册成功！{Colors.RESET}")
            print(f"  现在可以通过 Uplifted Agent 使用工具了\n")
        except Exception as e:
            print(f"{Colors.RED}✗ 注册失败: {e}{Colors.RESET}\n")

    def handle_test(self):
        """处理整合测试"""
        print(f"\n{Colors.BOLD}正在测试整合...{Colors.RESET}\n")

        # 检查服务
        status = self.integration.get_service_status()

        for service, is_running in status.items():
            if is_running:
                print(f"{Colors.GREEN}✓ {service} 服务正常{Colors.RESET}")
            else:
                print(f"{Colors.RED}✗ {service} 服务未运行{Colors.RESET}")
                print()
                return False

        # 测试整合
        if self.integration.test_integration():
            print(f"\n{Colors.GREEN}{'='*60}")
            print("整合测试通过！")
            print(f"{'='*60}{Colors.RESET}\n")
            return True
        else:
            print(f"\n{Colors.RED}整合测试失败{Colors.RESET}\n")
            return False

    def handle_list_tools(self):
        """处理工具列表"""
        name = self.integration.get_integration_name()
        print(f"\n{Colors.BOLD}{name} 工具列表：{Colors.RESET}\n")

        tools = self.integration.get_available_tools()

        if not tools:
            print(f"{Colors.YELLOW}未找到工具{Colors.RESET}\n")
            return

        print(f"找到 {Colors.GREEN}{len(tools)}{Colors.RESET} 个工具\n")

        # 按分类显示
        categories = self.integration.get_tool_categories()

        if categories:
            for category, keywords in categories.items():
                category_tools = [t for t in tools if any(k in t.lower() for k in keywords)]
                if category_tools:
                    print(f"{Colors.CYAN}{category}:{Colors.RESET}")
                    for tool in category_tools[:5]:
                        print(f"  • {tool}")
                    if len(category_tools) > 5:
                        print(f"  {Colors.DIM}... 还有 {len(category_tools) - 5} 个{Colors.RESET}")
                    print()
        else:
            # 无分类，直接显示
            for tool in tools[:20]:  # 只显示前 20 个
                print(f"  • {tool}")
            if len(tools) > 20:
                print(f"\n  {Colors.DIM}... 还有 {len(tools) - 20} 个工具{Colors.RESET}")
            print()

    def handle_agent_request(self, user_input: str):
        """处理 Agent 请求

        Args:
            user_input: 用户输入
        """
        print(f"\n{Colors.CYAN}正在处理您的请求...{Colors.RESET}\n")

        status = self.integration.get_service_status()
        if not all(status.values()):
            print(f"{Colors.RED}✗ 服务未完全启动，无法执行{Colors.RESET}")
            self.print_status_summary(status)
            print()
            return

        if not self.registered:
            print(f"{Colors.YELLOW}⚠ 提示: 整合尚未注册{Colors.RESET}")
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
        """解析用户意图

        Args:
            user_input: 用户输入

        Returns:
            str: 意图类型
        """
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
        name = self.integration.get_integration_name()
        print(f"{Colors.BOLD}欢迎使用 {name} x Uplifted 整合助手！{Colors.RESET}\n")
        status = self.integration.get_service_status()
        self.print_status_summary(status)

        print(f"\n{Colors.DIM}输入 'help' 或 '帮助' 查看可用命令{Colors.RESET}")
        print(f"{Colors.DIM}您也可以直接描述您的需求{Colors.RESET}\n")

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
                    print(f"\n{Colors.GREEN}再见！{Colors.RESET}\n")
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
