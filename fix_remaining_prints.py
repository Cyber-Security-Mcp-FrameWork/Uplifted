#!/usr/bin/env python3
"""
批量替换 print() 调试语句为日志记录

此脚本会：
1. 扫描指定目录下的所有 .py 文件
2. 查找并替换 print() 语句为适当的日志记录
3. 自动添加 logging import 和 logger 配置

作者: Uplifted Team
日期: 2025-10-28
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# 需要处理的文件列表
TARGET_FILES = [
    "server/uplifted/server/__init__.py",
    "server/uplifted/core/registry.py",
    "server/uplifted/tools_server/function_client.py",
    "server/uplifted/tools_server/server/function_tools.py",
    "server/uplifted/server/level_utilized/cu/computer.py",
    "server/uplifted/server/level_utilized/bu/browseruse.py",
    "server/uplifted/server/level_one/call.py",
    "server/uplifted/server/level_one/server/server.py",
    "server/uplifted/monitoring/tracing.py",
    "server/uplifted/monitoring/logger.py",
    "server/uplifted/extensions/config_utils.py",
    "server/uplifted/extensions/mcp_bridge.py",
    "server/uplifted/extensions/plugin_system_init.py",
    "server/uplifted/extensions/plugin_manifest.py",
    "server/uplifted/extensions/integration_example.py",
    "server/uplifted/server/openapi_config.py",
]


def has_logging_import(content: str) -> bool:
    """检查文件是否已导入 logging"""
    return bool(re.search(r'^import logging', content, re.MULTILINE))


def has_logger_definition(content: str) -> bool:
    """检查文件是否已定义 logger"""
    return bool(re.search(r'logger\s*=\s*logging\.getLogger', content))


def add_logging_setup(content: str) -> str:
    """添加 logging 导入和 logger 配置"""
    lines = content.split('\n')

    # 查找最后一个 import 语句的位置
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
            last_import_idx = i

    # 如果没有找到 logging import，则添加
    if not has_logging_import(content):
        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, 'import logging')
            last_import_idx += 1
        else:
            lines.insert(0, 'import logging')
            last_import_idx = 0

    # 如果没有 logger 定义，则添加
    if not has_logger_definition(content):
        # 在 imports 之后添加空行和 logger 定义
        lines.insert(last_import_idx + 2, '')
        lines.insert(last_import_idx + 3, '# 配置日志记录器')
        lines.insert(last_import_idx + 4, 'logger = logging.getLogger(__name__)')
        lines.insert(last_import_idx + 5, '')

    return '\n'.join(lines)


def classify_print_statement(print_content: str, context: str) -> str:
    """根据内容分类 print 语句，返回适当的日志级别"""
    lower_content = print_content.lower()
    lower_context = context.lower()

    # 错误相关
    if any(word in lower_content for word in ['error', 'failed', 'exception', '错误', '失败', '异常', '出错']):
        return 'error'

    # 警告相关
    if any(word in lower_content for word in ['warning', 'warn', 'suspicious', '警告', '可疑']):
        return 'warning'

    # 调试相关
    if any(word in lower_content for word in ['debug', 'processing', 'chunk', 'block', '处理', '调试', '正在']):
        return 'debug'

    # 信息相关
    if any(word in lower_content for word in ['success', 'completed', 'finished', '成功', '完成', '已']):
        return 'info'

    # 默认使用 debug 级别
    return 'debug'


def replace_print_statements(content: str) -> Tuple[str, int]:
    """替换文件中的所有 print 语句"""
    replacements = 0

    # 匹配 print 语句的正则表达式
    # 支持：print(...), print(f"..."), print("..." + ...), etc.
    pattern = r'print\s*\((.*?)\)(?:\s*#.*)?$'

    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines):
        # 获取上下文（前后各3行）
        context_start = max(0, i - 3)
        context_end = min(len(lines), i + 4)
        context = '\n'.join(lines[context_start:context_end])

        # 查找 print 语句
        match = re.search(pattern, line)
        if match and line.strip().startswith('print('):
            print_arg = match.group(1).strip()

            # 跳过空 print
            if not print_arg or print_arg == '""' or print_arg == "''":
                new_lines.append(line)
                continue

            # 分类日志级别
            log_level = classify_print_statement(print_arg, context)

            # 检查是否需要 exc_info
            exc_info = ''
            if log_level == 'error' and 'except' in context.lower():
                exc_info = ', exc_info=True'

            # 获取缩进
            indent = len(line) - len(line.lstrip())

            # 替换为日志记录
            new_line = ' ' * indent + f'logger.{log_level}({print_arg}{exc_info})'
            new_lines.append(new_line)
            replacements += 1
        else:
            new_lines.append(line)

    return '\n'.join(new_lines), replacements


def process_file(file_path: Path) -> Tuple[bool, int]:
    """处理单个文件"""
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有 print 语句
        if 'print(' not in content:
            return False, 0

        # 添加 logging 配置
        content = add_logging_setup(content)

        # 替换 print 语句
        new_content, count = replace_print_statements(content)

        if count > 0:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return True, count

        return False, 0

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return False, 0


def main():
    """主函数"""
    print("=" * 60)
    print("批量修复 print() 调试语句")
    print("=" * 60)
    print()

    base_dir = Path(__file__).parent
    total_files = 0
    total_replacements = 0

    for file_path_str in TARGET_FILES:
        file_path = base_dir / file_path_str

        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            continue

        print(f"处理: {file_path.relative_to(base_dir)}")
        success, count = process_file(file_path)

        if success:
            print(f"  ✅ 替换了 {count} 个 print 语句")
            total_files += 1
            total_replacements += count
        else:
            print(f"  ⏭️  没有需要替换的 print 语句")

    print()
    print("=" * 60)
    print(f"完成! 处理了 {total_files} 个文件，替换了 {total_replacements} 个 print 语句")
    print("=" * 60)


if __name__ == "__main__":
    main()
