#!/usr/bin/env python3
"""
测试运行脚本

提供便捷的测试运行命令和选项
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """测试运行器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
    
    def run_unit_tests(self, verbose: bool = False, coverage: bool = True) -> int:
        """运行单元测试"""
        cmd = ["python", "-m", "pytest", "tests/unit"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=uplifted",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing"
            ])
        
        cmd.append("--tb=short")
        
        print(f"Running unit tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """运行集成测试"""
        cmd = ["python", "-m", "pytest", "tests/integration"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["--tb=short", "-m", "integration"])
        
        print(f"Running integration tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_performance_tests(self, verbose: bool = False) -> int:
        """运行性能测试"""
        cmd = ["python", "-m", "pytest", "tests/performance"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend([
            "--tb=short",
            "-m", "performance",
            "--benchmark-only",
            "--benchmark-sort=mean"
        ])
        
        print(f"Running performance tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_all_tests(self, verbose: bool = False, coverage: bool = True) -> int:
        """运行所有测试"""
        cmd = ["python", "-m", "pytest"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=uplifted",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=xml"
            ])
        
        cmd.extend([
            "--tb=short",
            "--durations=10"
        ])
        
        print(f"Running all tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> int:
        """运行特定测试"""
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        cmd.append("--tb=short")
        
        print(f"Running specific test: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_tests_by_marker(self, marker: str, verbose: bool = False) -> int:
        """按标记运行测试"""
        cmd = ["python", "-m", "pytest", "-m", marker]
        
        if verbose:
            cmd.append("-v")
        
        cmd.append("--tb=short")
        
        print(f"Running tests with marker '{marker}': {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_failed_tests(self, verbose: bool = False) -> int:
        """重新运行失败的测试"""
        cmd = ["python", "-m", "pytest", "--lf"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.append("--tb=short")
        
        print(f"Running failed tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_parallel_tests(self, workers: int = 4, verbose: bool = False) -> int:
        """并行运行测试"""
        cmd = ["python", "-m", "pytest", "-n", str(workers)]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend(["--tb=short", "--dist=worksteal"])
        
        print(f"Running tests in parallel with {workers} workers: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def generate_coverage_report(self) -> int:
        """生成覆盖率报告"""
        cmd = ["python", "-m", "coverage", "html"]
        
        print(f"Generating coverage report: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.project_root).returncode
        
        if result == 0:
            print("Coverage report generated in htmlcov/index.html")
        
        return result
    
    def check_code_quality(self) -> int:
        """检查代码质量"""
        print("Checking code quality...")
        
        # 运行 black 检查
        print("Running black...")
        black_result = subprocess.run(
            ["python", "-m", "black", "--check", "uplifted", "tests"],
            cwd=self.project_root
        ).returncode
        
        # 运行 isort 检查
        print("Running isort...")
        isort_result = subprocess.run(
            ["python", "-m", "isort", "--check-only", "uplifted", "tests"],
            cwd=self.project_root
        ).returncode
        
        # 运行 flake8 检查
        print("Running flake8...")
        flake8_result = subprocess.run(
            ["python", "-m", "flake8", "uplifted", "tests"],
            cwd=self.project_root
        ).returncode
        
        # 运行 mypy 检查
        print("Running mypy...")
        mypy_result = subprocess.run(
            ["python", "-m", "mypy", "uplifted"],
            cwd=self.project_root
        ).returncode
        
        # 运行 bandit 安全检查
        print("Running bandit...")
        bandit_result = subprocess.run(
            ["python", "-m", "bandit", "-r", "uplifted"],
            cwd=self.project_root
        ).returncode
        
        total_errors = sum([black_result, isort_result, flake8_result, mypy_result, bandit_result])
        
        if total_errors == 0:
            print("All code quality checks passed!")
        else:
            print(f"Code quality checks failed with {total_errors} errors")
        
        return total_errors
    
    def install_test_dependencies(self) -> int:
        """安装测试依赖"""
        cmd = ["python", "-m", "pip", "install", "-r", "requirements-test.txt"]
        
        print(f"Installing test dependencies: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Test runner for Uplifted project")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # 单元测试
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    
    # 集成测试
    integration_parser = subparsers.add_parser("integration", help="Run integration tests")
    
    # 性能测试
    performance_parser = subparsers.add_parser("performance", help="Run performance tests")
    
    # 所有测试
    all_parser = subparsers.add_parser("all", help="Run all tests")
    
    # 特定测试
    specific_parser = subparsers.add_parser("specific", help="Run specific test")
    specific_parser.add_argument("path", help="Test path to run")
    
    # 按标记运行
    marker_parser = subparsers.add_parser("marker", help="Run tests by marker")
    marker_parser.add_argument("marker", help="Test marker to run")
    
    # 失败测试
    failed_parser = subparsers.add_parser("failed", help="Run failed tests")
    
    # 并行测试
    parallel_parser = subparsers.add_parser("parallel", help="Run tests in parallel")
    parallel_parser.add_argument("-w", "--workers", type=int, default=4, help="Number of workers")
    
    # 覆盖率报告
    coverage_parser = subparsers.add_parser("coverage", help="Generate coverage report")
    
    # 代码质量检查
    quality_parser = subparsers.add_parser("quality", help="Check code quality")
    
    # 安装依赖
    install_parser = subparsers.add_parser("install", help="Install test dependencies")
    
    args = parser.parse_args()
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)
    
    # 执行命令
    if args.command == "unit":
        return runner.run_unit_tests(args.verbose, not args.no_coverage)
    elif args.command == "integration":
        return runner.run_integration_tests(args.verbose)
    elif args.command == "performance":
        return runner.run_performance_tests(args.verbose)
    elif args.command == "all":
        return runner.run_all_tests(args.verbose, not args.no_coverage)
    elif args.command == "specific":
        return runner.run_specific_test(args.path, args.verbose)
    elif args.command == "marker":
        return runner.run_tests_by_marker(args.marker, args.verbose)
    elif args.command == "failed":
        return runner.run_failed_tests(args.verbose)
    elif args.command == "parallel":
        return runner.run_parallel_tests(args.workers, args.verbose)
    elif args.command == "coverage":
        return runner.generate_coverage_report()
    elif args.command == "quality":
        return runner.check_code_quality()
    elif args.command == "install":
        return runner.install_test_dependencies()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())