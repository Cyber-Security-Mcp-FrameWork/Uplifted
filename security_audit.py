#!/usr/bin/env python3
"""
安全审计脚本

对 Uplifted 项目进行全面的安全审计，包括：
- 依赖漏洞扫描（使用 safety）
- 代码安全扫描（使用 bandit）
- 密码和敏感信息检测
- 权限和配置检查
- 生成安全审计报告

使用示例:
    # 运行完整安全审计
    python security_audit.py

    # 只扫描依赖
    python security_audit.py --dependencies-only

    # 只扫描代码
    python security_audit.py --code-only

    # 生成详细报告
    python security_audit.py --detailed

    # 输出到文件
    python security_audit.py --output security_report.txt
"""

import sys
import argparse
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class SecurityAuditor:
    """安全审计器"""

    def __init__(self, output_file: str = None, detailed: bool = False):
        """
        初始化安全审计器

        参数:
            output_file: 输出文件路径
            detailed: 是否生成详细报告
        """
        self.output_file = output_file
        self.detailed = detailed
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {
                "total_issues": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }

    def print_section(self, title: str):
        """打印章节标题"""
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}\n")

    def run_command(self, cmd: List[str]) -> tuple[int, str]:
        """
        运行命令并返回退出码和输出

        参数:
            cmd: 命令列表

        返回:
            (退出码, 输出)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            return 1, str(e)

    def check_dependencies(self) -> Dict[str, Any]:
        """
        检查依赖漏洞（使用 safety）

        返回:
            检查结果字典
        """
        self.print_section("1. 依赖漏洞扫描 (Safety)")

        result = {
            "name": "dependency_vulnerabilities",
            "status": "unknown",
            "issues": [],
            "output": ""
        }

        # 检查 safety 是否安装
        check_code, _ = self.run_command(["safety", "--version"])
        if check_code != 0:
            print("⚠ Warning: safety 未安装，跳过依赖扫描")
            print("安装: pip install safety")
            result["status"] = "skipped"
            result["output"] = "safety not installed"
            return result

        # 运行 safety 检查
        print("正在扫描依赖漏洞...")
        exit_code, output = self.run_command([
            "safety", "check",
            "--json",
            "--file", "server/requirements-test.txt"
        ])

        result["output"] = output

        try:
            # 解析 JSON 输出
            vulnerabilities = json.loads(output)

            if isinstance(vulnerabilities, list) and len(vulnerabilities) > 0:
                result["status"] = "failed"
                result["issues"] = vulnerabilities

                print(f"✗ 发现 {len(vulnerabilities)} 个漏洞:\n")
                for vuln in vulnerabilities:
                    print(f"  - {vuln.get('package', 'unknown')}")
                    print(f"    版本: {vuln.get('installed_version', 'unknown')}")
                    print(f"    漏洞: {vuln.get('vulnerability', 'unknown')}")
                    print(f"    建议: {vuln.get('recommendation', 'unknown')}\n")

                    # 更新统计
                    severity = vuln.get('severity', 'unknown').lower()
                    if severity in self.results["summary"]:
                        self.results["summary"][severity] += 1
                    self.results["summary"]["total_issues"] += 1
            else:
                result["status"] = "passed"
                print("✓ 未发现依赖漏洞")

        except json.JSONDecodeError:
            # safety 输出可能不是 JSON 格式
            if "No known security vulnerabilities found" in output:
                result["status"] = "passed"
                print("✓ 未发现依赖漏洞")
            else:
                result["status"] = "failed"
                print("✗ Safety 扫描失败")
                print(output)

        return result

    def check_code_security(self) -> Dict[str, Any]:
        """
        检查代码安全问题（使用 bandit）

        返回:
            检查结果字典
        """
        self.print_section("2. 代码安全扫描 (Bandit)")

        result = {
            "name": "code_security",
            "status": "unknown",
            "issues": [],
            "output": ""
        }

        # 检查 bandit 是否安装
        check_code, _ = self.run_command(["bandit", "--version"])
        if check_code != 0:
            print("⚠ Warning: bandit 未安装，跳过代码扫描")
            print("安装: pip install bandit")
            result["status"] = "skipped"
            result["output"] = "bandit not installed"
            return result

        # 运行 bandit 检查
        print("正在扫描代码安全问题...")
        exit_code, output = self.run_command([
            "bandit",
            "-r", "server/uplifted/",
            "-f", "json",
            "-ll"  # 只报告中高严重性问题
        ])

        result["output"] = output

        try:
            # 解析 JSON 输出
            bandit_result = json.loads(output)

            issues = bandit_result.get("results", [])

            if len(issues) > 0:
                result["status"] = "warning"
                result["issues"] = issues

                print(f"⚠ 发现 {len(issues)} 个潜在安全问题:\n")

                for issue in issues:
                    print(f"  - {issue.get('test_id', 'unknown')}: {issue.get('issue_text', 'unknown')}")
                    print(f"    文件: {issue.get('filename', 'unknown')}")
                    print(f"    行号: {issue.get('line_number', 'unknown')}")
                    print(f"    严重性: {issue.get('issue_severity', 'unknown')}")
                    print(f"    置信度: {issue.get('issue_confidence', 'unknown')}\n")

                    # 更新统计
                    severity = issue.get('issue_severity', 'unknown').lower()
                    if severity in self.results["summary"]:
                        self.results["summary"][severity] += 1
                    self.results["summary"]["total_issues"] += 1
            else:
                result["status"] = "passed"
                print("✓ 未发现严重的代码安全问题")

        except json.JSONDecodeError:
            result["status"] = "error"
            print("✗ Bandit 扫描失败")
            print(output)

        return result

    def check_secrets(self) -> Dict[str, Any]:
        """
        检查硬编码的密码和敏感信息

        返回:
            检查结果字典
        """
        self.print_section("3. 密码和敏感信息检测")

        result = {
            "name": "secrets_detection",
            "status": "unknown",
            "issues": [],
            "output": ""
        }

        # 定义敏感关键词模式
        sensitive_patterns = [
            "password",
            "secret",
            "api_key",
            "apikey",
            "token",
            "private_key",
            "aws_access_key",
            "db_password"
        ]

        print("正在扫描硬编码密码和敏感信息...")

        issues = []
        source_dir = Path("server/uplifted")

        for py_file in source_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line_lower = line.lower()

                        # 跳过注释
                        if line.strip().startswith('#'):
                            continue

                        # 检查敏感模式
                        for pattern in sensitive_patterns:
                            if pattern in line_lower and '=' in line:
                                # 可能是赋值语句
                                if not line.strip().startswith('"""') and \
                                   'os.environ' not in line and \
                                   'config' not in line_lower:
                                    issues.append({
                                        "file": str(py_file),
                                        "line": line_num,
                                        "pattern": pattern,
                                        "content": line.strip()[:80]  # 只显示前80字符
                                    })

            except Exception as e:
                print(f"警告: 无法读取文件 {py_file}: {e}")

        if len(issues) > 0:
            result["status"] = "warning"
            result["issues"] = issues

            print(f"⚠ 发现 {len(issues)} 个潜在的硬编码敏感信息:\n")

            for issue in issues:
                print(f"  - 文件: {issue['file']}")
                print(f"    行号: {issue['line']}")
                print(f"    模式: {issue['pattern']}")
                print(f"    内容: {issue['content']}\n")

                self.results["summary"]["medium"] += 1
                self.results["summary"]["total_issues"] += 1
        else:
            result["status"] = "passed"
            print("✓ 未发现硬编码的敏感信息")

        return result

    def check_file_permissions(self) -> Dict[str, Any]:
        """
        检查敏感文件权限

        返回:
            检查结果字典
        """
        self.print_section("4. 文件权限检查")

        result = {
            "name": "file_permissions",
            "status": "unknown",
            "issues": [],
            "output": ""
        }

        print("正在检查敏感文件权限...")

        sensitive_files = [
            ".env",
            ".env.example",
            "config/*.conf",
            "*.key",
            "*.pem"
        ]

        issues = []

        for pattern in sensitive_files:
            for file in Path(".").rglob(pattern):
                if file.is_file():
                    # 检查文件权限（仅限 Unix 系统）
                    if os.name != 'nt':  # 不是 Windows
                        stat_info = file.stat()
                        mode = oct(stat_info.st_mode)[-3:]

                        if mode not in ['600', '400']:
                            issues.append({
                                "file": str(file),
                                "permissions": mode,
                                "recommendation": "应设置为 600 或 400"
                            })

        if len(issues) > 0:
            result["status"] = "warning"
            result["issues"] = issues

            print(f"⚠ 发现 {len(issues)} 个权限问题:\n")

            for issue in issues:
                print(f"  - 文件: {issue['file']}")
                print(f"    权限: {issue['permissions']}")
                print(f"    建议: {issue['recommendation']}\n")

                self.results["summary"]["medium"] += 1
                self.results["summary"]["total_issues"] += 1
        else:
            result["status"] = "passed"
            print("✓ 敏感文件权限正常")

        return result

    def check_configuration_security(self) -> Dict[str, Any]:
        """
        检查配置安全性

        返回:
            检查结果字典
        """
        self.print_section("5. 配置安全检查")

        result = {
            "name": "configuration_security",
            "status": "unknown",
            "issues": [],
            "output": ""
        }

        print("正在检查配置安全...")

        # 检查是否有示例配置文件
        if Path(".env.example").exists() and not Path(".env").exists():
            print("✓ 使用 .env.example 模板，实际 .env 未提交")
        elif Path(".env").exists():
            # 检查 .gitignore 是否包含 .env
            if Path(".gitignore").exists():
                with open(".gitignore", 'r') as f:
                    if ".env" in f.read():
                        print("✓ .env 已在 .gitignore 中")
                    else:
                        result["issues"].append({
                            "issue": ".env 未在 .gitignore 中",
                            "severity": "high"
                        })
                        self.results["summary"]["high"] += 1
                        self.results["summary"]["total_issues"] += 1

        # 检查是否使用了加密配置
        config_files = list(Path("server/uplifted").rglob("*config*.py"))
        uses_encryption = False

        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'EncryptedConfigLoader' in content or 'Fernet' in content:
                        uses_encryption = True
                        break
            except:
                pass

        if uses_encryption:
            print("✓ 使用了加密配置加载器")
        else:
            print("⚠ 未检测到加密配置的使用")

        if len(result["issues"]) == 0:
            result["status"] = "passed"
        else:
            result["status"] = "warning"

        return result

    def generate_report(self):
        """生成安全审计报告"""
        self.print_section("安全审计报告")

        # 输出摘要
        summary = self.results["summary"]

        print("问题统计:")
        print(f"  总问题数: {summary['total_issues']}")
        print(f"  严重 (Critical): {summary['critical']}")
        print(f"  高 (High):      {summary['high']}")
        print(f"  中 (Medium):    {summary['medium']}")
        print(f"  低 (Low):       {summary['low']}\n")

        # 总体评估
        if summary['total_issues'] == 0:
            print("✓ 总体评估: 优秀 - 未发现安全问题")
            overall_status = "优秀"
        elif summary['critical'] > 0 or summary['high'] > 3:
            print("✗ 总体评估: 需要立即修复严重问题")
            overall_status = "需要改进"
        elif summary['medium'] > 5:
            print("⚠ 总体评估: 建议修复中等优先级问题")
            overall_status = "一般"
        else:
            print("✓ 总体评估: 良好 - 仅有少量低优先级问题")
            overall_status = "良好"

        self.results["overall_status"] = overall_status

        # 保存到文件
        if self.output_file:
            try:
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.write("="*80 + "\n")
                    f.write("Uplifted 安全审计报告\n")
                    f.write("="*80 + "\n\n")

                    f.write(f"生成时间: {self.results['timestamp']}\n")
                    f.write(f"总体评估: {overall_status}\n\n")

                    f.write("问题统计:\n")
                    f.write(f"  总问题数: {summary['total_issues']}\n")
                    f.write(f"  严重: {summary['critical']}\n")
                    f.write(f"  高:   {summary['high']}\n")
                    f.write(f"  中:   {summary['medium']}\n")
                    f.write(f"  低:   {summary['low']}\n\n")

                    # 详细检查结果
                    if self.detailed:
                        f.write("\n详细检查结果:\n")
                        f.write("="*80 + "\n\n")

                        for check_name, check_result in self.results["checks"].items():
                            f.write(f"\n{check_name}:\n")
                            f.write(f"  状态: {check_result['status']}\n")

                            if check_result.get('issues'):
                                f.write(f"  问题数: {len(check_result['issues'])}\n")

                                for issue in check_result['issues']:
                                    f.write(f"\n  - {json.dumps(issue, indent=4, ensure_ascii=False)}\n")

                print(f"\n✓ 报告已保存到: {self.output_file}")

            except Exception as e:
                print(f"\n✗ 保存报告失败: {e}")

    def run_audit(self, dependencies_only: bool = False, code_only: bool = False):
        """
        运行完整的安全审计

        参数:
            dependencies_only: 仅扫描依赖
            code_only: 仅扫描代码
        """
        print("\n" + "="*80)
        print("Uplifted 安全审计")
        print("="*80)

        if dependencies_only:
            self.results["checks"]["dependencies"] = self.check_dependencies()
        elif code_only:
            self.results["checks"]["code_security"] = self.check_code_security()
            self.results["checks"]["secrets"] = self.check_secrets()
        else:
            # 运行所有检查
            self.results["checks"]["dependencies"] = self.check_dependencies()
            self.results["checks"]["code_security"] = self.check_code_security()
            self.results["checks"]["secrets"] = self.check_secrets()
            self.results["checks"]["file_permissions"] = self.check_file_permissions()
            self.results["checks"]["configuration"] = self.check_configuration_security()

        # 生成报告
        self.generate_report()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Uplifted 安全审计脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dependencies-only',
        action='store_true',
        help='仅扫描依赖漏洞'
    )
    parser.add_argument(
        '--code-only',
        action='store_true',
        help='仅扫描代码安全'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='生成详细报告'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='输出报告文件路径'
    )

    args = parser.parse_args()

    auditor = SecurityAuditor(
        output_file=args.output,
        detailed=args.detailed
    )

    auditor.run_audit(
        dependencies_only=args.dependencies_only,
        code_only=args.code_only
    )


if __name__ == "__main__":
    main()
