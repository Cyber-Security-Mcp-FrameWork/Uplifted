"""
SQL 注入防护模块

提供 SQL 标识符验证、参数化查询辅助和 SQL 注入检测功能。

核心安全特性：
1. SQL 标识符验证 - 验证表名、列名等
2. SQL 关键字检测 - 禁止使用 SQL 关键字
3. 长度限制 - 防止过长标识符
4. 字符白名单 - 只允许安全字符
5. 审计日志 - 记录所有验证操作

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class SQLIdentifierType(Enum):
    """SQL 标识符类型"""
    TABLE = "table"
    COLUMN = "column"
    DATABASE = "database"
    INDEX = "index"
    VIEW = "view"


class SQLRiskLevel(Enum):
    """SQL 风险等级"""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


@dataclass
class SQLValidationResult:
    """SQL 验证结果"""
    is_valid: bool
    risk_level: SQLRiskLevel
    reason: str
    sanitized_identifier: Optional[str] = None


class SQLIdentifierValidator:
    """
    SQL 标识符验证器

    验证 SQL 标识符（表名、列名等）的安全性，防止 SQL 注入。
    """

    # SQL 关键字（不允许作为标识符）
    SQL_KEYWORDS = {
        # DDL
        'CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'RENAME',
        # DML
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE',
        # DCL
        'GRANT', 'REVOKE',
        # TCL
        'COMMIT', 'ROLLBACK', 'SAVEPOINT',
        # 其他
        'TABLE', 'DATABASE', 'INDEX', 'VIEW', 'TRIGGER',
        'PROCEDURE', 'FUNCTION', 'FROM', 'WHERE', 'JOIN',
        'UNION', 'ORDER', 'GROUP', 'HAVING', 'LIMIT',
        'EXEC', 'EXECUTE', 'DECLARE', 'SET',
        # 危险函数
        'LOAD_FILE', 'INTO', 'OUTFILE', 'DUMPFILE',
        'SHELL', 'SYSTEM', 'EXEC'
    }

    # 危险字符和模式
    DANGEROUS_PATTERNS = [
        r'[;\'"`]',        # SQL 分隔符和引号
        r'--',             # SQL 注释
        r'/\*',            # SQL 多行注释开始
        r'\*/',            # SQL 多行注释结束
        r'\\',             # 转义字符
        r'\s+OR\s+',       # OR 注入
        r'\s+AND\s+',      # AND 注入
        r'=',              # 等号（可能用于注入）
        r'<|>',            # 比较符号
        r'\(',             # 括号（可能用于函数调用）
        r'\)',
        r'\+',             # 算术运算符
        r'\-',
        r'\*',
        r'/',
    ]

    # 有效标识符模式（只允许字母、数字、下划线）
    VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    # 最大长度限制
    MAX_IDENTIFIER_LENGTH = 64

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化 SQL 标识符验证器

        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

    def validate_identifier(self,
                           identifier: str,
                           identifier_type: SQLIdentifierType = SQLIdentifierType.TABLE) -> SQLValidationResult:
        """
        验证 SQL 标识符

        Args:
            identifier: 标识符字符串
            identifier_type: 标识符类型

        Returns:
            SQLValidationResult: 验证结果
        """
        # 1. 检查是否为空
        if not identifier or not identifier.strip():
            return SQLValidationResult(
                is_valid=False,
                risk_level=SQLRiskLevel.FORBIDDEN,
                reason="标识符为空"
            )

        identifier = identifier.strip()

        # 2. 检查长度
        if len(identifier) > self.MAX_IDENTIFIER_LENGTH:
            return SQLValidationResult(
                is_valid=False,
                risk_level=SQLRiskLevel.FORBIDDEN,
                reason=f"标识符过长（最大 {self.MAX_IDENTIFIER_LENGTH} 字符）"
            )

        # 3. 检查是否为 SQL 关键字
        if identifier.upper() in self.SQL_KEYWORDS:
            return SQLValidationResult(
                is_valid=False,
                risk_level=SQLRiskLevel.FORBIDDEN,
                reason=f"标识符不能是 SQL 关键字: {identifier}"
            )

        # 4. 检查危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, identifier, re.IGNORECASE):
                return SQLValidationResult(
                    is_valid=False,
                    risk_level=SQLRiskLevel.DANGEROUS,
                    reason=f"标识符包含危险模式: {pattern}"
                )

        # 5. 检查字符白名单
        if not self.VALID_IDENTIFIER_PATTERN.match(identifier):
            return SQLValidationResult(
                is_valid=False,
                risk_level=SQLRiskLevel.DANGEROUS,
                reason="标识符只能包含字母、数字和下划线，且必须以字母或下划线开头"
            )

        # 6. 检查是否包含连续下划线（可疑）
        if '__' in identifier:
            return SQLValidationResult(
                is_valid=True,
                risk_level=SQLRiskLevel.SUSPICIOUS,
                reason="标识符包含连续下划线（可疑但允许）",
                sanitized_identifier=identifier
            )

        # 所有检查通过
        self.logger.debug(f"SQL 标识符验证通过: {identifier}")

        return SQLValidationResult(
            is_valid=True,
            risk_level=SQLRiskLevel.SAFE,
            reason="验证通过",
            sanitized_identifier=identifier
        )

    def validate_table_name(self, table_name: str) -> SQLValidationResult:
        """
        验证表名（便捷方法）

        Args:
            table_name: 表名

        Returns:
            SQLValidationResult: 验证结果
        """
        return self.validate_identifier(table_name, SQLIdentifierType.TABLE)

    def validate_column_name(self, column_name: str) -> SQLValidationResult:
        """
        验证列名（便捷方法）

        Args:
            column_name: 列名

        Returns:
            SQLValidationResult: 验证结果
        """
        return self.validate_identifier(column_name, SQLIdentifierType.COLUMN)

    def sanitize_identifier(self, identifier: str) -> Optional[str]:
        """
        净化标识符（如果可能）

        Args:
            identifier: 原始标识符

        Returns:
            净化后的标识符，如果无法净化返回 None
        """
        # 移除空白字符
        identifier = identifier.strip()

        # 如果验证通过，返回原标识符
        result = self.validate_identifier(identifier)
        if result.is_valid:
            return result.sanitized_identifier

        # 尝试净化
        # 只保留安全字符
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', identifier)

        # 确保以字母或下划线开头
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized

        # 再次验证
        result = self.validate_identifier(sanitized)
        if result.is_valid:
            self.logger.warning(f"标识符已净化: {identifier} -> {sanitized}")
            return sanitized

        return None


class SQLInjectionDetector:
    """
    SQL 注入检测器

    检测 SQL 查询中的注入模式。
    """

    # SQL 注入模式
    INJECTION_PATTERNS = [
        # 经典注入
        r"'\s*OR\s+'.*?'='",
        r"'\s*OR\s+1=1",
        r"'\s*OR\s+'1'='1",
        r"--",
        r";.*?(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER)",

        # 联合查询注入
        r"UNION\s+SELECT",
        r"UNION\s+ALL\s+SELECT",

        # 时间盲注
        r"SLEEP\s*\(",
        r"WAITFOR\s+DELAY",
        r"BENCHMARK\s*\(",

        # 布尔盲注
        r"AND\s+1=1",
        r"AND\s+1=2",

        # 堆叠查询
        r";\s*DROP",
        r";\s*DELETE",
        r";\s*INSERT",

        # 注释注入
        r"/\*.*?\*/",

        # 函数注入
        r"LOAD_FILE\s*\(",
        r"INTO\s+OUTFILE",
        r"INTO\s+DUMPFILE",
    ]

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化 SQL 注入检测器

        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

    def detect_injection(self, query: str) -> SQLValidationResult:
        """
        检测 SQL 注入

        Args:
            query: SQL 查询字符串

        Returns:
            SQLValidationResult: 检测结果
        """
        # 检查每个注入模式
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE | re.DOTALL):
                self.logger.warning(f"检测到 SQL 注入模式: {pattern}")
                return SQLValidationResult(
                    is_valid=False,
                    risk_level=SQLRiskLevel.DANGEROUS,
                    reason=f"检测到 SQL 注入模式: {pattern}"
                )

        return SQLValidationResult(
            is_valid=True,
            risk_level=SQLRiskLevel.SAFE,
            reason="未检测到 SQL 注入"
        )


class SecureSQLManager:
    """
    安全 SQL 管理器

    结合标识符验证和注入检测。
    """

    def __init__(self,
                 enable_audit_log: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全 SQL 管理器

        Args:
            enable_audit_log: 是否启用审计日志
            logger: 日志记录器
        """
        self.identifier_validator = SQLIdentifierValidator(logger)
        self.injection_detector = SQLInjectionDetector(logger)
        self.enable_audit_log = enable_audit_log
        self.logger = logger or logging.getLogger(__name__)

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

    def validate_identifier(self,
                           identifier: str,
                           identifier_type: SQLIdentifierType = SQLIdentifierType.TABLE) -> SQLValidationResult:
        """
        验证标识符并记录审计日志

        Args:
            identifier: 标识符
            identifier_type: 标识符类型

        Returns:
            SQLValidationResult: 验证结果
        """
        result = self.identifier_validator.validate_identifier(identifier, identifier_type)

        # 记录审计日志
        if self.enable_audit_log:
            self._log_audit('validate_identifier', identifier, result, identifier_type=identifier_type.value)

        # 如果验证失败，记录错误
        if not result.is_valid:
            self.logger.error(
                f"SQL 标识符验证失败: {identifier} - {result.reason} "
                f"(风险等级: {result.risk_level.value})"
            )

        return result

    def detect_injection(self, query: str) -> SQLValidationResult:
        """
        检测 SQL 注入并记录审计日志

        Args:
            query: SQL 查询

        Returns:
            SQLValidationResult: 检测结果
        """
        result = self.injection_detector.detect_injection(query)

        # 记录审计日志
        if self.enable_audit_log:
            self._log_audit('detect_injection', query[:100], result)  # 限制查询长度

        # 如果检测到注入，记录错误
        if not result.is_valid:
            self.logger.error(
                f"检测到 SQL 注入: {query[:100]}... - {result.reason}"
            )

        return result

    def _log_audit(self,
                   operation: str,
                   input_value: str,
                   result: SQLValidationResult,
                   **extra):
        """记录审计日志"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'input': input_value,
            'is_valid': result.is_valid,
            'risk_level': result.risk_level.value,
            'reason': result.reason
        }

        if extra:
            audit_entry.update(extra)

        self.audit_log.append(audit_entry)

        # 限制日志大小
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self.audit_log[-limit:]


class SQLSecurityError(Exception):
    """SQL 安全相关异常"""
    pass


# 便捷函数
def validate_table_name(table_name: str) -> SQLValidationResult:
    """
    验证表名（便捷函数）

    Args:
        table_name: 表名

    Returns:
        SQLValidationResult: 验证结果

    Raises:
        SQLSecurityError: 验证失败
    """
    validator = SQLIdentifierValidator()
    result = validator.validate_table_name(table_name)

    if not result.is_valid:
        raise SQLSecurityError(f"无效的表名: {result.reason}")

    return result


def validate_column_name(column_name: str) -> SQLValidationResult:
    """
    验证列名（便捷函数）

    Args:
        column_name: 列名

    Returns:
        SQLValidationResult: 验证结果

    Raises:
        SQLSecurityError: 验证失败
    """
    validator = SQLIdentifierValidator()
    result = validator.validate_column_name(column_name)

    if not result.is_valid:
        raise SQLSecurityError(f"无效的列名: {result.reason}")

    return result
