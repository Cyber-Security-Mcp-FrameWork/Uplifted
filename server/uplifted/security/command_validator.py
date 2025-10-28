"""
命令验证和安全执行模块

提供命令注入防护、白名单验证和审计日志功能。
"""

import re
import shlex
import logging
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass
from enum import Enum


class CommandRiskLevel(Enum):
    """命令风险等级"""
    SAFE = "safe"
    RESTRICTED = "restricted"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


@dataclass
class CommandValidationResult:
    """命令验证结果"""
    is_valid: bool
    risk_level: CommandRiskLevel
    reason: str
    sanitized_command: Optional[str] = None


class CommandValidator:
    """
    命令验证器

    提供多层安全验证：
    1. 命令白名单/黑名单
    2. 参数验证
    3. 危险模式检测
    4. 路径遍历检测
    """

    # 安全命令白名单（只读操作）
    SAFE_COMMANDS: Set[str] = {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'echo',
        'pwd', 'whoami', 'date', 'which', 'wc', 'sort', 'uniq',
        'diff', 'file', 'stat', 'du', 'df'
    }

    # 受限命令（需要额外验证）
    RESTRICTED_COMMANDS: Set[str] = {
        'sed', 'awk', 'cut', 'tr', 'xargs', 'tee'
    }

    # 危险命令（可能修改系统）
    DANGEROUS_COMMANDS: Set[str] = {
        'mkdir', 'touch', 'cp', 'mv', 'ln'
    }

    # 禁止命令（高危操作）
    FORBIDDEN_COMMANDS: Set[str] = {
        'rm', 'dd', 'mkfs', 'fdisk', 'parted',
        'kill', 'killall', 'shutdown', 'reboot', 'halt',
        'useradd', 'userdel', 'usermod', 'passwd',
        'chmod', 'chown', 'chgrp',
        'iptables', 'ufw', 'firewall-cmd',
        'systemctl', 'service',
        'apt', 'yum', 'dnf', 'pip', 'npm',
        'sudo', 'su',
        'curl', 'wget', 'nc', 'netcat', 'telnet', 'ssh', 'scp', 'rsync',
        'python', 'python3', 'perl', 'ruby', 'node', 'bash', 'sh',
        'eval', 'exec', 'source'
    }

    # 危险模式（正则表达式）
    DANGEROUS_PATTERNS: List[str] = [
        r'[;&|]',  # 命令链接
        r'\$\(',  # 命令替换
        r'`',  # 反引号命令替换
        r'>\s*/dev/',  # 设备文件写入
        r'/etc/',  # 系统配置目录
        r'/root/',  # root目录
        r'/proc/',  # proc文件系统
        r'/sys/',  # sys文件系统
        r'\.\.',  # 路径遍历
        r'~',  # home目录
    ]

    def __init__(self,
                 allow_dangerous: bool = False,
                 custom_whitelist: Optional[Set[str]] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化命令验证器

        Args:
            allow_dangerous: 是否允许危险命令（默认禁止）
            custom_whitelist: 自定义白名单（会添加到默认白名单）
            logger: 日志记录器
        """
        self.allow_dangerous = allow_dangerous
        self.logger = logger or logging.getLogger(__name__)

        # 合并白名单
        self.whitelist = self.SAFE_COMMANDS.copy()
        if custom_whitelist:
            self.whitelist.update(custom_whitelist)

        if allow_dangerous:
            self.whitelist.update(self.RESTRICTED_COMMANDS)
            self.whitelist.update(self.DANGEROUS_COMMANDS)
        else:
            self.whitelist.update(self.RESTRICTED_COMMANDS)

    def validate(self, command: str) -> CommandValidationResult:
        """
        验证命令是否安全

        Args:
            command: 要验证的命令字符串

        Returns:
            CommandValidationResult: 验证结果
        """
        if not command or not command.strip():
            return CommandValidationResult(
                is_valid=False,
                risk_level=CommandRiskLevel.FORBIDDEN,
                reason="空命令"
            )

        # 1. 检查危险模式
        pattern_check = self._check_dangerous_patterns(command)
        if not pattern_check.is_valid:
            return pattern_check

        # 2. 解析命令
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            return CommandValidationResult(
                is_valid=False,
                risk_level=CommandRiskLevel.FORBIDDEN,
                reason=f"命令解析失败: {e}"
            )

        if not tokens:
            return CommandValidationResult(
                is_valid=False,
                risk_level=CommandRiskLevel.FORBIDDEN,
                reason="无效命令"
            )

        # 3. 检查命令名称
        base_command = tokens[0].split('/')[-1]  # 处理绝对路径

        if base_command in self.FORBIDDEN_COMMANDS:
            self.logger.warning(f"禁止命令被拒绝: {base_command}")
            return CommandValidationResult(
                is_valid=False,
                risk_level=CommandRiskLevel.FORBIDDEN,
                reason=f"命令 '{base_command}' 被禁止"
            )

        if base_command in self.DANGEROUS_COMMANDS:
            if not self.allow_dangerous:
                return CommandValidationResult(
                    is_valid=False,
                    risk_level=CommandRiskLevel.DANGEROUS,
                    reason=f"命令 '{base_command}' 是危险命令，需要明确授权"
                )
            risk_level = CommandRiskLevel.DANGEROUS
        elif base_command in self.RESTRICTED_COMMANDS:
            risk_level = CommandRiskLevel.RESTRICTED
        elif base_command in self.whitelist:
            risk_level = CommandRiskLevel.SAFE
        else:
            return CommandValidationResult(
                is_valid=False,
                risk_level=CommandRiskLevel.FORBIDDEN,
                reason=f"命令 '{base_command}' 不在白名单中"
            )

        # 4. 验证参数
        arg_check = self._validate_arguments(tokens[1:])
        if not arg_check.is_valid:
            return arg_check

        # 5. 记录审计日志
        self.logger.info(
            f"命令已验证: {base_command}, 风险等级: {risk_level.value}",
            extra={
                'command': command,
                'risk_level': risk_level.value,
                'tokens': tokens
            }
        )

        return CommandValidationResult(
            is_valid=True,
            risk_level=risk_level,
            reason="验证通过",
            sanitized_command=command  # 已经通过shlex验证
        )

    def _check_dangerous_patterns(self, command: str) -> CommandValidationResult:
        """检查危险模式"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return CommandValidationResult(
                    is_valid=False,
                    risk_level=CommandRiskLevel.FORBIDDEN,
                    reason=f"检测到危险模式: {pattern}"
                )

        return CommandValidationResult(
            is_valid=True,
            risk_level=CommandRiskLevel.SAFE,
            reason="未检测到危险模式"
        )

    def _validate_arguments(self, args: List[str]) -> CommandValidationResult:
        """验证命令参数"""
        for arg in args:
            # 检查路径遍历
            if '..' in arg:
                return CommandValidationResult(
                    is_valid=False,
                    risk_level=CommandRiskLevel.FORBIDDEN,
                    reason=f"参数包含路径遍历: {arg}"
                )

            # 检查敏感路径
            sensitive_paths = ['/etc/', '/root/', '/proc/', '/sys/', '/dev/']
            for path in sensitive_paths:
                if path in arg:
                    return CommandValidationResult(
                        is_valid=False,
                        risk_level=CommandRiskLevel.FORBIDDEN,
                        reason=f"参数访问敏感路径: {arg}"
                    )

        return CommandValidationResult(
            is_valid=True,
            risk_level=CommandRiskLevel.SAFE,
            reason="参数验证通过"
        )


class SecureBashExecutor:
    """
    安全的Bash命令执行器

    在现有BashTool基础上添加安全层
    """

    def __init__(self,
                 bash_tool: Any,
                 validator: Optional[CommandValidator] = None,
                 enable_audit_log: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全执行器

        Args:
            bash_tool: 底层BashTool实例
            validator: 命令验证器
            enable_audit_log: 是否启用审计日志
            logger: 日志记录器
        """
        self.bash_tool = bash_tool
        self.validator = validator or CommandValidator()
        self.enable_audit_log = enable_audit_log
        self.logger = logger or logging.getLogger(__name__)

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

    async def execute(self, command: str, **kwargs) -> Any:
        """
        安全执行命令

        Args:
            command: 要执行的命令
            **kwargs: 传递给底层工具的其他参数

        Returns:
            命令执行结果

        Raises:
            SecurityError: 命令未通过安全验证
        """
        # 1. 验证命令
        validation = self.validator.validate(command)

        if not validation.is_valid:
            error_msg = f"命令被拒绝: {validation.reason}"
            self.logger.error(error_msg, extra={'command': command})

            # 记录审计日志
            if self.enable_audit_log:
                self._log_audit(command, validation, success=False)

            raise SecurityError(error_msg)

        # 2. 记录审计日志（执行前）
        if self.enable_audit_log:
            self.logger.info(
                f"执行命令: {command} (风险等级: {validation.risk_level.value})"
            )

        # 3. 执行命令
        try:
            result = await self.bash_tool(command=command, **kwargs)

            # 4. 记录审计日志（执行后）
            if self.enable_audit_log:
                self._log_audit(command, validation, success=True, result=result)

            return result

        except Exception as e:
            # 记录执行失败
            if self.enable_audit_log:
                self._log_audit(command, validation, success=False, error=str(e))
            raise

    def _log_audit(self,
                   command: str,
                   validation: CommandValidationResult,
                   success: bool,
                   result: Any = None,
                   error: Optional[str] = None):
        """记录审计日志"""
        import datetime

        audit_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'command': command,
            'risk_level': validation.risk_level.value,
            'success': success,
            'validation_reason': validation.reason
        }

        if result:
            audit_entry['result'] = str(result)[:500]  # 限制长度

        if error:
            audit_entry['error'] = error

        self.audit_log.append(audit_entry)

        # 限制审计日志大小
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self.audit_log[-limit:]


class SecurityError(Exception):
    """安全相关的异常"""
    pass
