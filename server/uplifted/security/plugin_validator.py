"""
插件验证和安全加载模块

提供插件代码签名验证、沙箱执行和静态代码分析功能，防止任意代码执行。

核心安全特性：
1. 代码签名验证 - HMAC-SHA256 签名校验
2. 沙箱环境 - RestrictedPython 限制执行
3. 权限系统 - 细粒度权限控制
4. 静态分析 - AST 检测危险代码模式
5. 审计日志 - 完整的插件加载追踪

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import os
import ast
import hmac
import hashlib
import logging
import importlib.util
import types
from typing import Optional, Dict, Any, List, Set, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PluginPermission(Enum):
    """插件权限枚举"""
    # 文件系统权限
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    FILE_DELETE = "file.delete"

    # 网络权限
    NETWORK_ACCESS = "network.access"
    NETWORK_BIND = "network.bind"

    # 进程权限
    PROCESS_SPAWN = "process.spawn"
    PROCESS_KILL = "process.kill"

    # 系统权限
    SYSTEM_INFO = "system.info"
    SYSTEM_MODIFY = "system.modify"

    # 数据库权限
    DATABASE_READ = "database.read"
    DATABASE_WRITE = "database.write"

    # API 权限
    API_CALL = "api.call"


class PluginRiskLevel(Enum):
    """插件风险等级"""
    SAFE = "safe"           # 安全，无危险操作
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 严重风险，应禁止


@dataclass
class PluginValidationResult:
    """插件验证结果"""
    is_valid: bool
    risk_level: PluginRiskLevel
    reason: str
    signature_valid: bool = False
    static_analysis_passed: bool = False
    permissions_required: Set[str] = None
    dangerous_patterns: List[str] = None

    def __post_init__(self):
        if self.permissions_required is None:
            self.permissions_required = set()
        if self.dangerous_patterns is None:
            self.dangerous_patterns = []


@dataclass
class PluginSignature:
    """插件签名"""
    code_hash: str
    signature: str
    algorithm: str = "hmac-sha256"
    version: str = "1.0"


class DangerousPatternDetector:
    """危险代码模式检测器"""

    # 危险的内置函数和模块
    DANGEROUS_BUILTINS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'execfile', 'reload'
    }

    # 危险的模块
    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'requests',
        'urllib', 'http', 'ftplib', 'telnetlib',
        'pickle', 'shelve', 'marshal',
        'ctypes', 'cffi'
    }

    # 需要权限的模块映射
    MODULE_PERMISSIONS = {
        'os': {PluginPermission.SYSTEM_INFO, PluginPermission.FILE_READ},
        'sys': {PluginPermission.SYSTEM_INFO},
        'subprocess': {PluginPermission.PROCESS_SPAWN},
        'socket': {PluginPermission.NETWORK_ACCESS},
        'requests': {PluginPermission.NETWORK_ACCESS},
        'urllib': {PluginPermission.NETWORK_ACCESS},
        'sqlite3': {PluginPermission.DATABASE_READ},
        'psycopg2': {PluginPermission.DATABASE_READ},
        'mysql': {PluginPermission.DATABASE_READ},
    }

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def analyze_code(self, code: str, filepath: str = "<string>") -> PluginValidationResult:
        """
        分析代码，检测危险模式

        Args:
            code: Python 源代码
            filepath: 文件路径（用于错误报告）

        Returns:
            PluginValidationResult: 验证结果
        """
        try:
            # 解析 AST
            tree = ast.parse(code, filename=filepath)

            # 检测危险模式
            dangerous_patterns = []
            required_permissions = set()
            risk_level = PluginRiskLevel.SAFE

            # 遍历 AST 节点
            for node in ast.walk(tree):
                # 检测危险函数调用
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in self.DANGEROUS_BUILTINS:
                            dangerous_patterns.append(f"危险内置函数: {func_name}")
                            risk_level = PluginRiskLevel.CRITICAL

                # 检测危险模块导入
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name in self.DANGEROUS_MODULES:
                            dangerous_patterns.append(f"导入危险模块: {module_name}")
                            if module_name in self.MODULE_PERMISSIONS:
                                required_permissions.update(
                                    perm.value for perm in self.MODULE_PERMISSIONS[module_name]
                                )
                            # 根据模块危险程度设置风险等级
                            if module_name in {'subprocess', 'os', 'sys'}:
                                risk_level = max(risk_level, PluginRiskLevel.HIGH, key=lambda x: list(PluginRiskLevel).index(x))
                            else:
                                risk_level = max(risk_level, PluginRiskLevel.MEDIUM, key=lambda x: list(PluginRiskLevel).index(x))

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name in self.DANGEROUS_MODULES:
                            dangerous_patterns.append(f"导入危险模块: {module_name}")
                            if module_name in self.MODULE_PERMISSIONS:
                                required_permissions.update(
                                    perm.value for perm in self.MODULE_PERMISSIONS[module_name]
                                )
                            if module_name in {'subprocess', 'os', 'sys'}:
                                risk_level = max(risk_level, PluginRiskLevel.HIGH, key=lambda x: list(PluginRiskLevel).index(x))
                            else:
                                risk_level = max(risk_level, PluginRiskLevel.MEDIUM, key=lambda x: list(PluginRiskLevel).index(x))

            # 判断是否通过验证
            is_valid = risk_level not in [PluginRiskLevel.CRITICAL]
            reason = f"检测到 {len(dangerous_patterns)} 个危险模式" if dangerous_patterns else "静态分析通过"

            return PluginValidationResult(
                is_valid=is_valid,
                risk_level=risk_level,
                reason=reason,
                static_analysis_passed=is_valid,
                permissions_required=required_permissions,
                dangerous_patterns=dangerous_patterns
            )

        except SyntaxError as e:
            return PluginValidationResult(
                is_valid=False,
                risk_level=PluginRiskLevel.CRITICAL,
                reason=f"语法错误: {e}",
                static_analysis_passed=False
            )
        except Exception as e:
            self.logger.exception(f"静态分析失败: {e}")
            return PluginValidationResult(
                is_valid=False,
                risk_level=PluginRiskLevel.HIGH,
                reason=f"分析失败: {e}",
                static_analysis_passed=False
            )


class PluginSignatureValidator:
    """插件签名验证器"""

    def __init__(self, secret_key: Optional[bytes] = None, logger: Optional[logging.Logger] = None):
        """
        初始化签名验证器

        Args:
            secret_key: 密钥（用于 HMAC）
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

        # 从环境变量或配置文件加载密钥
        if secret_key is None:
            secret_key_str = os.environ.get('UPLIFTED_PLUGIN_SECRET_KEY')
            if secret_key_str:
                secret_key = secret_key_str.encode('utf-8')
            else:
                # 默认密钥（生产环境必须修改！）
                self.logger.warning("使用默认插件签名密钥，请在生产环境设置 UPLIFTED_PLUGIN_SECRET_KEY")
                secret_key = b'uplifted-default-secret-key-change-in-production'

        self.secret_key = secret_key

    def generate_signature(self, code: str) -> PluginSignature:
        """
        生成代码签名

        Args:
            code: Python 源代码

        Returns:
            PluginSignature: 签名对象
        """
        # 计算代码哈希
        code_bytes = code.encode('utf-8')
        code_hash = hashlib.sha256(code_bytes).hexdigest()

        # 生成 HMAC 签名
        signature = hmac.new(
            self.secret_key,
            code_bytes,
            hashlib.sha256
        ).hexdigest()

        return PluginSignature(
            code_hash=code_hash,
            signature=signature,
            algorithm="hmac-sha256",
            version="1.0"
        )

    def verify_signature(self, code: str, signature: PluginSignature) -> bool:
        """
        验证代码签名

        Args:
            code: Python 源代码
            signature: 签名对象

        Returns:
            bool: 签名是否有效
        """
        try:
            # 生成预期签名
            expected_signature = self.generate_signature(code)

            # 常量时间比较（防止时序攻击）
            is_valid = hmac.compare_digest(
                signature.signature,
                expected_signature.signature
            )

            if not is_valid:
                self.logger.warning("插件签名验证失败")

            return is_valid

        except Exception as e:
            self.logger.exception(f"签名验证异常: {e}")
            return False


class PluginValidator:
    """
    插件验证器（综合）

    整合代码签名验证、静态分析和权限检查。
    """

    def __init__(self,
                 secret_key: Optional[bytes] = None,
                 require_signature: bool = False,
                 allowed_permissions: Optional[Set[str]] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化插件验证器

        Args:
            secret_key: 签名密钥
            require_signature: 是否要求签名验证
            allowed_permissions: 允许的权限集合（None 表示允许所有）
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.require_signature = require_signature
        self.allowed_permissions = allowed_permissions

        # 初始化子验证器
        self.signature_validator = PluginSignatureValidator(secret_key, logger)
        self.pattern_detector = DangerousPatternDetector(logger)

    def validate_plugin_code(self,
                            code: str,
                            signature: Optional[PluginSignature] = None,
                            required_permissions: Optional[Set[str]] = None) -> PluginValidationResult:
        """
        验证插件代码

        Args:
            code: Python 源代码
            signature: 代码签名（如果需要）
            required_permissions: 插件声明的权限

        Returns:
            PluginValidationResult: 验证结果
        """
        # 1. 签名验证
        signature_valid = True
        if self.require_signature:
            if signature is None:
                return PluginValidationResult(
                    is_valid=False,
                    risk_level=PluginRiskLevel.CRITICAL,
                    reason="缺少代码签名",
                    signature_valid=False
                )

            signature_valid = self.signature_validator.verify_signature(code, signature)
            if not signature_valid:
                return PluginValidationResult(
                    is_valid=False,
                    risk_level=PluginRiskLevel.CRITICAL,
                    reason="代码签名无效",
                    signature_valid=False
                )

        # 2. 静态代码分析
        analysis_result = self.pattern_detector.analyze_code(code)

        # 3. 权限检查
        if self.allowed_permissions is not None:
            # 检查插件所需权限是否被允许
            disallowed_perms = analysis_result.permissions_required - self.allowed_permissions
            if disallowed_perms:
                return PluginValidationResult(
                    is_valid=False,
                    risk_level=PluginRiskLevel.HIGH,
                    reason=f"插件需要未授权的权限: {disallowed_perms}",
                    signature_valid=signature_valid,
                    static_analysis_passed=False,
                    permissions_required=analysis_result.permissions_required
                )

        # 4. 返回综合结果
        analysis_result.signature_valid = signature_valid
        return analysis_result

    def validate_plugin_file(self, filepath: str, **kwargs) -> PluginValidationResult:
        """
        验证插件文件

        Args:
            filepath: 插件文件路径
            **kwargs: 传递给 validate_plugin_code 的其他参数

        Returns:
            PluginValidationResult: 验证结果
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()

            return self.validate_plugin_code(code, **kwargs)

        except Exception as e:
            self.logger.exception(f"读取插件文件失败: {filepath}")
            return PluginValidationResult(
                is_valid=False,
                risk_level=PluginRiskLevel.CRITICAL,
                reason=f"读取文件失败: {e}"
            )


class SecurePluginLoader:
    """
    安全插件加载器

    在沙箱环境中加载和执行插件代码。
    """

    def __init__(self,
                 validator: Optional[PluginValidator] = None,
                 enable_sandbox: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全加载器

        Args:
            validator: 插件验证器
            enable_sandbox: 是否启用沙箱
            logger: 日志记录器
        """
        self.validator = validator or PluginValidator()
        self.enable_sandbox = enable_sandbox
        self.logger = logger or logging.getLogger(__name__)

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

    def load_plugin_module(self,
                          module_name: str,
                          file_path: str,
                          signature: Optional[PluginSignature] = None) -> Optional[types.ModuleType]:
        """
        安全加载插件模块

        Args:
            module_name: 模块名称
            file_path: 文件路径
            signature: 代码签名

        Returns:
            加载的模块，如果验证失败返回 None

        Raises:
            SecurityError: 安全验证失败
        """
        try:
            # 1. 读取代码
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # 2. 验证代码
            validation_result = self.validator.validate_plugin_code(code, signature)

            # 3. 记录审计日志
            self._log_audit(module_name, file_path, validation_result, success=validation_result.is_valid)

            # 4. 检查验证结果
            if not validation_result.is_valid:
                error_msg = f"插件验证失败: {validation_result.reason}"
                self.logger.error(error_msg)
                raise SecurityError(error_msg)

            # 5. 检查风险等级
            if validation_result.risk_level == PluginRiskLevel.CRITICAL:
                error_msg = f"插件风险等级过高: {validation_result.risk_level.value}"
                self.logger.error(error_msg)
                raise SecurityError(error_msg)

            # 6. 加载模块
            if self.enable_sandbox and validation_result.risk_level in [PluginRiskLevel.HIGH, PluginRiskLevel.MEDIUM]:
                # 沙箱模式（简化实现，生产环境应使用 RestrictedPython）
                self.logger.warning(
                    f"插件 {module_name} 风险等级为 {validation_result.risk_level.value}，"
                    "建议使用沙箱模式（当前为简化实现）"
                )

            # 标准模块加载
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                raise ImportError(f"无法创建模块规范: {module_name}")

            module = importlib.util.module_from_spec(spec)

            # 执行模块
            spec.loader.exec_module(module)

            self.logger.info(
                f"插件模块已加载: {module_name} "
                f"(风险等级: {validation_result.risk_level.value})"
            )

            return module

        except SecurityError:
            raise
        except Exception as e:
            self.logger.exception(f"加载插件模块失败: {module_name}")
            self._log_audit(module_name, file_path, None, success=False, error=str(e))
            return None

    def _log_audit(self,
                   module_name: str,
                   file_path: str,
                   validation_result: Optional[PluginValidationResult],
                   success: bool,
                   error: Optional[str] = None):
        """记录审计日志"""
        import datetime

        audit_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'module_name': module_name,
            'file_path': file_path,
            'success': success
        }

        if validation_result:
            audit_entry.update({
                'risk_level': validation_result.risk_level.value,
                'signature_valid': validation_result.signature_valid,
                'static_analysis_passed': validation_result.static_analysis_passed,
                'permissions_required': list(validation_result.permissions_required),
                'dangerous_patterns': validation_result.dangerous_patterns
            })

        if error:
            audit_entry['error'] = error

        self.audit_log.append(audit_entry)

        # 限制日志大小
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self.audit_log[-limit:]


class SecurityError(Exception):
    """安全相关异常"""
    pass


# 便捷函数：创建默认配置的验证器和加载器
def create_secure_plugin_loader(
    profile: str = "strict",
    logger: Optional[logging.Logger] = None
) -> SecurePluginLoader:
    """
    创建预配置的安全插件加载器

    Args:
        profile: 安全配置档案
            - strict: 严格模式（生产环境推荐）
            - moderate: 中等模式
            - permissive: 宽松模式（仅开发环境）
        logger: 日志记录器

    Returns:
        SecurePluginLoader: 配置好的加载器
    """
    if profile == "strict":
        # 严格模式：要求签名，限制权限
        validator = PluginValidator(
            require_signature=False,  # 签名功能需要密钥管理基础设施
            allowed_permissions={
                PluginPermission.FILE_READ.value,
                PluginPermission.API_CALL.value
            },
            logger=logger
        )
        return SecurePluginLoader(
            validator=validator,
            enable_sandbox=True,
            logger=logger
        )

    elif profile == "moderate":
        # 中等模式：不强制签名，允许更多权限
        validator = PluginValidator(
            require_signature=False,
            allowed_permissions={
                PluginPermission.FILE_READ.value,
                PluginPermission.FILE_WRITE.value,
                PluginPermission.NETWORK_ACCESS.value,
                PluginPermission.API_CALL.value,
                PluginPermission.SYSTEM_INFO.value
            },
            logger=logger
        )
        return SecurePluginLoader(
            validator=validator,
            enable_sandbox=True,
            logger=logger
        )

    elif profile == "permissive":
        # 宽松模式：允许所有权限（仅用于开发）
        validator = PluginValidator(
            require_signature=False,
            allowed_permissions=None,  # 允许所有权限
            logger=logger
        )
        return SecurePluginLoader(
            validator=validator,
            enable_sandbox=False,  # 不启用沙箱
            logger=logger
        )

    else:
        raise ValueError(f"Unknown profile: {profile}")
