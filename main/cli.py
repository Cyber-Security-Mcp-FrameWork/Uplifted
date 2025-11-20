#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uplifted 整合工具 CLI

通用的整合工具入口，支持多种工具整合。

使用方式：
    python cli.py hexstrike       # 使用 HexStrike AI 整合
    python cli.py <integration>   # 使用其他整合
"""

import sys
import argparse
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from integration import ConversationalCLI
from integrations import HexStrikeIntegration


# 可用的整合实现
AVAILABLE_INTEGRATIONS = {
    "hexstrike": {
        "class": HexStrikeIntegration,
        "description": "HexStrike AI - AI 驱动的网络安全自动化平台（150+ 工具 + 12+ AI Agents）"
    },
    # 未来可以添加更多整合
    # "other_tool": {
    #     "class": OtherToolIntegration,
    #     "description": "其他工具的整合"
    # },
}


def list_integrations():
    """列出所有可用的整合"""
    print("\n可用的整合：\n")
    for name, info in AVAILABLE_INTEGRATIONS.items():
        print(f"  • {name}")
        print(f"    {info['description']}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Uplifted 整合工具 CLI - 通用的工具整合界面",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python cli.py hexstrike           # 启动 HexStrike AI 整合
  python cli.py --list              # 列出所有可用的整合
        """
    )

    parser.add_argument(
        "integration",
        nargs="?",
        default="hexstrike",
        help="要使用的整合名称（默认: hexstrike）"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的整合"
    )

    parser.add_argument(
        "--uplifted-url",
        default="http://localhost:7541",
        help="Uplifted 服务地址（默认: http://localhost:7541）"
    )

    args = parser.parse_args()

    # 列出整合
    if args.list:
        list_integrations()
        return

    # 检查整合是否存在
    if args.integration not in AVAILABLE_INTEGRATIONS:
        print(f"错误: 未知的整合 '{args.integration}'")
        print(f"\n可用的整合: {', '.join(AVAILABLE_INTEGRATIONS.keys())}")
        print(f"使用 'python cli.py --list' 查看详细信息")
        sys.exit(1)

    try:
        # 创建整合实例
        integration_info = AVAILABLE_INTEGRATIONS[args.integration]
        integration_class = integration_info["class"]

        # 根据不同整合传入不同参数
        if args.integration == "hexstrike":
            integration = integration_class(uplifted_url=args.uplifted_url)
        else:
            integration = integration_class(uplifted_url=args.uplifted_url)

        # 运行交互式 CLI
        cli = ConversationalCLI(integration)
        cli.run()

    except KeyboardInterrupt:
        print("\n\n程序已退出\n")
    except Exception as e:
        print(f"\n发生错误: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
