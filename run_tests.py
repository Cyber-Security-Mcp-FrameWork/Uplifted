#!/usr/bin/env python3
"""
测试运行脚本

提供便捷的测试运行命令，支持：
- 运行所有测试
- 按类型运行测试（单元/集成/性能）
- 生成覆盖率报告
- 生成HTML报告
- 并行测试执行

使用示例:
    # 运行所有测试
    python run_tests.py

    # 只运行单元测试
    python run_tests.py --unit

    # 运行集成测试
    python run_tests.py --integration

    # 运行性能测试
    python run_tests.py --performance

    # 生成覆盖率报告
    python run_tests.py --coverage

    # 详细输出
    python run_tests.py --verbose

    # 并行运行（使用 4 个进程）
    python run_tests.py --parallel 4
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List


def run_command(cmd: List[str], description: str = "") -> int:
    """
    运行命令并返回退出码

    参数:
        cmd: 命令列表
        description: 命令描述

    返回:
        退出码
    """
    if description:
        print(f"\n{'='*80}")
        print(f"{description}")
        print(f"{'='*80}\n")

    print(f"运行命令: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"错误: {e}")
        return 1


def run_all_tests(args) -> int:
    """运行所有测试"""
    cmd = ["pytest", "server/tests/"]

    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    if args.coverage:
        cmd.extend([
            "--cov=server/uplifted",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])

    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    if args.markers:
        cmd.extend(["-m", args.markers])

    if args.maxfail:
        cmd.extend(["--maxfail", str(args.maxfail)])

    return run_command(cmd, "运行所有测试")


def run_unit_tests(args) -> int:
    """运行单元测试"""
    cmd = ["pytest", "server/tests/unit/", "-m", "unit"]

    if args.verbose:
        cmd.append("-vv")

    if args.coverage:
        cmd.extend([
            "--cov=server/uplifted",
            "--cov-report=html",
            "--cov-report=term"
        ])

    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    return run_command(cmd, "运行单元测试")


def run_integration_tests(args) -> int:
    """运行集成测试"""
    cmd = ["pytest", "server/tests/integration/", "-m", "integration"]

    if args.verbose:
        cmd.append("-vv")

    if args.coverage:
        cmd.extend([
            "--cov=server/uplifted",
            "--cov-report=html",
            "--cov-report=term"
        ])

    return run_command(cmd, "运行集成测试")


def run_performance_tests(args) -> int:
    """运行性能测试"""
    cmd = [
        "pytest",
        "server/tests/performance/",
        "-m", "performance",
        "--benchmark-only",
        "--benchmark-autosave"
    ]

    if args.verbose:
        cmd.append("-vv")

    if args.benchmark_compare:
        cmd.extend(["--benchmark-compare", args.benchmark_compare])

    return run_command(cmd, "运行性能测试")


def run_quick_tests(args) -> int:
    """运行快速测试（跳过慢速测试）"""
    cmd = [
        "pytest",
        "server/tests/",
        "-m", "not slow",
        "-x"  # 第一个失败就停止
    ]

    if args.verbose:
        cmd.append("-vv")

    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    return run_command(cmd, "运行快速测试")


def run_specific_module(args) -> int:
    """运行特定模块的测试"""
    if not args.module:
        print("错误: 请使用 --module 指定模块")
        return 1

    cmd = ["pytest", f"server/tests/", "-k", args.module]

    if args.verbose:
        cmd.append("-vv")

    if args.coverage:
        cmd.extend([
            "--cov=server/uplifted",
            "--cov-report=html",
            "--cov-report=term"
        ])

    return run_command(cmd, f"运行 {args.module} 模块测试")


def generate_coverage_report(args) -> int:
    """生成覆盖率报告"""
    cmd = [
        "pytest",
        "server/tests/",
        "--cov=server/uplifted",
        "--cov-report=html:server/tests/coverage_html",
        "--cov-report=term-missing",
        "--cov-report=xml:server/tests/coverage.xml"
    ]

    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    exit_code = run_command(cmd, "生成覆盖率报告")

    if exit_code == 0:
        print("\n" + "="*80)
        print("覆盖率报告已生成:")
        print(f"  HTML: server/tests/coverage_html/index.html")
        print(f"  XML:  server/tests/coverage.xml")
        print("="*80 + "\n")

    return exit_code


def run_test_suite(args) -> int:
    """运行完整测试套件"""
    print("\n" + "="*80)
    print("运行完整测试套件")
    print("="*80 + "\n")

    results = {}

    # 1. 单元测试
    print("\n[1/3] 运行单元测试...")
    results['unit'] = run_unit_tests(args)

    # 2. 集成测试
    print("\n[2/3] 运行集成测试...")
    results['integration'] = run_integration_tests(args)

    # 3. 性能测试（可选）
    if not args.skip_performance:
        print("\n[3/3] 运行性能测试...")
        results['performance'] = run_performance_tests(args)

    # 输出总结
    print("\n" + "="*80)
    print("测试套件结果总结")
    print("="*80)

    for test_type, exit_code in results.items():
        status = "✓ 通过" if exit_code == 0 else "✗ 失败"
        print(f"{test_type:15s}: {status}")

    print("="*80 + "\n")

    # 如果有任何失败，返回非零退出码
    return max(results.values())


def list_tests(args) -> int:
    """列出所有测试"""
    cmd = ["pytest", "server/tests/", "--collect-only", "-q"]

    if args.markers:
        cmd.extend(["-m", args.markers])

    return run_command(cmd, "列出所有测试")


def run_failed_tests(args) -> int:
    """重新运行上次失败的测试"""
    cmd = ["pytest", "--lf", "-v"]  # --lf = last failed

    if args.coverage:
        cmd.extend([
            "--cov=server/uplifted",
            "--cov-report=html",
            "--cov-report=term"
        ])

    return run_command(cmd, "重新运行失败的测试")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Uplifted 测试运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 运行所有测试
  %(prog)s --unit                    # 只运行单元测试
  %(prog)s --integration             # 只运行集成测试
  %(prog)s --performance             # 只运行性能测试
  %(prog)s --quick                   # 快速测试
  %(prog)s --coverage                # 生成覆盖率报告
  %(prog)s --suite                   # 运行完整测试套件
  %(prog)s --module plugin           # 运行 plugin 相关测试
  %(prog)s --markers "unit and plugin"  # 运行特定标记的测试
  %(prog)s --list                    # 列出所有测试
  %(prog)s --failed                  # 重新运行失败的测试
  %(prog)s --parallel 4              # 并行运行（4个进程）
        """
    )

    # 测试类型选项
    test_group = parser.add_argument_group('测试类型')
    test_group.add_argument(
        '--unit', '-u',
        action='store_true',
        help='只运行单元测试'
    )
    test_group.add_argument(
        '--integration', '-i',
        action='store_true',
        help='只运行集成测试'
    )
    test_group.add_argument(
        '--performance', '-p',
        action='store_true',
        help='只运行性能测试'
    )
    test_group.add_argument(
        '--quick', '-q',
        action='store_true',
        help='快速测试（跳过慢速测试）'
    )
    test_group.add_argument(
        '--suite', '-s',
        action='store_true',
        help='运行完整测试套件'
    )

    # 过滤选项
    filter_group = parser.add_argument_group('过滤选项')
    filter_group.add_argument(
        '--module', '-m',
        type=str,
        help='运行特定模块的测试（如: plugin, config）'
    )
    filter_group.add_argument(
        '--markers',
        type=str,
        help='pytest 标记表达式（如: "unit and plugin"）'
    )

    # 输出选项
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    output_group.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='生成覆盖率报告'
    )
    output_group.add_argument(
        '--list', '-l',
        action='store_true',
        help='列出所有测试'
    )

    # 执行选项
    exec_group = parser.add_argument_group('执行选项')
    exec_group.add_argument(
        '--parallel',
        type=int,
        default=0,
        help='并行运行测试的进程数（默认: 0 = 不并行）'
    )
    exec_group.add_argument(
        '--maxfail',
        type=int,
        default=0,
        help='失败N次后停止（默认: 0 = 不限制）'
    )
    exec_group.add_argument(
        '--failed', '-f',
        action='store_true',
        help='重新运行上次失败的测试'
    )

    # 性能测试选项
    perf_group = parser.add_argument_group('性能测试选项')
    perf_group.add_argument(
        '--benchmark-compare',
        type=str,
        help='与之前的基准测试比较'
    )
    perf_group.add_argument(
        '--skip-performance',
        action='store_true',
        help='在测试套件中跳过性能测试'
    )

    args = parser.parse_args()

    # 根据参数执行相应的测试
    if args.list:
        return list_tests(args)
    elif args.failed:
        return run_failed_tests(args)
    elif args.unit:
        return run_unit_tests(args)
    elif args.integration:
        return run_integration_tests(args)
    elif args.performance:
        return run_performance_tests(args)
    elif args.quick:
        return run_quick_tests(args)
    elif args.suite:
        return run_test_suite(args)
    elif args.module:
        return run_specific_module(args)
    elif args.coverage:
        return generate_coverage_report(args)
    else:
        # 默认运行所有测试
        return run_all_tests(args)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
