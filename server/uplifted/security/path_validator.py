"""
路径验证和安全模块

提供路径遍历防护、符号链接解析和路径白名单验证功能。

核心安全特性：
1. 路径遍历检测 - 防止 .. 攻击
2. 符号链接解析 - 检测真实路径
3. 路径白名单 - 限制可访问目录
4. 路径规范化 - 移除 . 和 ..
5. 审计日志 - 完整的路径访问追踪

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import os
import logging
from pathlib import Path
from typing import Optional, Set, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class PathAccessMode(Enum):
    """路径访问模式"""
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"


class PathRiskLevel(Enum):
    """路径风险等级"""
    SAFE = "safe"           # 安全路径
    SUSPICIOUS = "suspicious"  # 可疑路径
    DANGEROUS = "dangerous"    # 危险路径
    FORBIDDEN = "forbidden"    # 禁止访问


@dataclass
class PathValidationResult:
    """路径验证结果"""
    is_valid: bool
    risk_level: PathRiskLevel
    reason: str
    resolved_path: Optional[Path] = None
    allowed_directory: Optional[Path] = None


class PathValidator:
    """
    路径验证器

    提供多层安全验证：
    1. 路径规范化
    2. 路径遍历检测
    3. 符号链接解析
    4. 白名单验证
    5. 黑名单检测
    """

    # 危险路径模式（黑名单）
    DANGEROUS_PATHS = {
        '/etc', '/root', '/proc', '/sys', '/dev',
        '/boot', '/usr/bin', '/usr/sbin', '/sbin', '/bin',
        '/.ssh', '/.aws', '/.kube',
        '/var/log', '/var/run'
    }

    # 危险文件模式
    DANGEROUS_FILES = {
        'passwd', 'shadow', 'sudoers', 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
        'authorized_keys', 'known_hosts', 'config',
        '.env', '.aws/credentials', '.kube/config'
    }

    def __init__(self,
                 allowed_directories: Optional[List[Path]] = None,
                 allow_symlinks: bool = False,
                 strict_mode: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化路径验证器

        Args:
            allowed_directories: 允许的目录列表（白名单）
            allow_symlinks: 是否允许符号链接
            strict_mode: 严格模式（拒绝所有可疑路径）
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.allow_symlinks = allow_symlinks
        self.strict_mode = strict_mode

        # 默认允许的目录
        if allowed_directories is None:
            # 只允许当前工作目录及其子目录
            allowed_directories = [
                Path.cwd(),
                Path.cwd() / "data",
                Path.cwd() / "temp",
                Path.cwd() / "uploads"
            ]

        # 规范化允许的目录
        self.allowed_directories = [
            self._normalize_path(path).resolve()
            for path in allowed_directories
        ]

        self.logger.info(
            f"PathValidator initialized with {len(self.allowed_directories)} allowed directories"
        )

    def _normalize_path(self, path: Path) -> Path:
        """
        规范化路径

        Args:
            path: 输入路径

        Returns:
            规范化后的路径
        """
        # 展开用户目录
        if str(path).startswith('~'):
            path = Path(os.path.expanduser(str(path)))

        # 转换为绝对路径
        if not path.is_absolute():
            path = Path.cwd() / path

        # 规范化路径（移除 . 和 ..）
        try:
            # 注意：resolve() 会解析符号链接
            return path.resolve()
        except Exception as e:
            self.logger.warning(f"路径规范化失败: {path} - {e}")
            return path

    def _check_path_traversal(self, path_str: str) -> PathValidationResult:
        """
        检查路径遍历攻击

        Args:
            path_str: 路径字符串

        Returns:
            PathValidationResult: 验证结果
        """
        # 检查 ..
        if '..' in path_str:
            return PathValidationResult(
                is_valid=False,
                risk_level=PathRiskLevel.DANGEROUS,
                reason="路径包含路径遍历模式: .."
            )

        # 检查多个连续斜杠
        if '//' in path_str or '\\\\' in path_str:
            return PathValidationResult(
                is_valid=False,
                risk_level=PathRiskLevel.SUSPICIOUS,
                reason="路径包含多个连续斜杠"
            )

        return PathValidationResult(
            is_valid=True,
            risk_level=PathRiskLevel.SAFE,
            reason="未检测到路径遍历"
        )

    def _check_symlink(self, path: Path) -> PathValidationResult:
        """
        检查符号链接

        Args:
            path: 路径对象

        Returns:
            PathValidationResult: 验证结果
        """
        if path.is_symlink():
            if not self.allow_symlinks:
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.DANGEROUS,
                    reason="路径是符号链接，不允许访问"
                )

            # 解析符号链接
            try:
                real_path = path.resolve(strict=False)

                # 检查符号链接指向的路径是否在允许的目录内
                if not self._is_path_allowed(real_path):
                    return PathValidationResult(
                        is_valid=False,
                        risk_level=PathRiskLevel.DANGEROUS,
                        reason=f"符号链接指向不允许的路径: {real_path}",
                        resolved_path=real_path
                    )

            except Exception as e:
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.DANGEROUS,
                    reason=f"无法解析符号链接: {e}"
                )

        return PathValidationResult(
            is_valid=True,
            risk_level=PathRiskLevel.SAFE,
            reason="符号链接检查通过"
        )

    def _check_dangerous_path(self, path: Path) -> PathValidationResult:
        """
        检查危险路径（黑名单）

        Args:
            path: 路径对象

        Returns:
            PathValidationResult: 验证结果
        """
        path_str = str(path)

        # 检查危险路径
        for dangerous_path in self.DANGEROUS_PATHS:
            if path_str.startswith(dangerous_path):
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.FORBIDDEN,
                    reason=f"路径位于危险目录: {dangerous_path}"
                )

        # 检查危险文件
        for dangerous_file in self.DANGEROUS_FILES:
            if dangerous_file in path_str:
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.FORBIDDEN,
                    reason=f"路径包含敏感文件名: {dangerous_file}"
                )

        return PathValidationResult(
            is_valid=True,
            risk_level=PathRiskLevel.SAFE,
            reason="未检测到危险路径"
        )

    def _is_path_allowed(self, path: Path) -> bool:
        """
        检查路径是否在允许的目录内

        Args:
            path: 路径对象

        Returns:
            是否允许
        """
        try:
            # 规范化路径
            normalized_path = self._normalize_path(path)

            # 检查是否在任何允许的目录内
            for allowed_dir in self.allowed_directories:
                try:
                    # 使用 is_relative_to 检查（Python 3.9+）
                    if hasattr(normalized_path, 'is_relative_to'):
                        if normalized_path.is_relative_to(allowed_dir):
                            return True
                    else:
                        # 兼容旧版本
                        try:
                            normalized_path.relative_to(allowed_dir)
                            return True
                        except ValueError:
                            continue
                except Exception:
                    continue

            return False

        except Exception as e:
            self.logger.exception(f"路径检查异常: {path}")
            return False

    def validate(self,
                path: Path | str,
                access_mode: PathAccessMode = PathAccessMode.READ) -> PathValidationResult:
        """
        验证路径是否安全

        Args:
            path: 要验证的路径
            access_mode: 访问模式

        Returns:
            PathValidationResult: 验证结果
        """
        # 转换为 Path 对象
        if isinstance(path, str):
            path_obj = Path(path)
            path_str = path
        else:
            path_obj = path
            path_str = str(path)

        # 1. 检查路径遍历
        traversal_check = self._check_path_traversal(path_str)
        if not traversal_check.is_valid:
            self.logger.warning(f"路径遍历检测失败: {path_str}")
            return traversal_check

        # 2. 规范化路径
        try:
            normalized_path = self._normalize_path(path_obj)
        except Exception as e:
            return PathValidationResult(
                is_valid=False,
                risk_level=PathRiskLevel.DANGEROUS,
                reason=f"路径规范化失败: {e}"
            )

        # 3. 检查危险路径（黑名单）
        dangerous_check = self._check_dangerous_path(normalized_path)
        if not dangerous_check.is_valid:
            self.logger.warning(f"危险路径检测失败: {normalized_path}")
            return dangerous_check

        # 4. 检查白名单
        if not self._is_path_allowed(normalized_path):
            # 找到最近的允许目录（用于错误提示）
            allowed_dirs_str = ', '.join(str(d) for d in self.allowed_directories)
            return PathValidationResult(
                is_valid=False,
                risk_level=PathRiskLevel.FORBIDDEN,
                reason=f"路径不在允许的目录内。允许的目录: {allowed_dirs_str}",
                resolved_path=normalized_path
            )

        # 5. 检查符号链接
        if normalized_path.exists():
            symlink_check = self._check_symlink(normalized_path)
            if not symlink_check.is_valid:
                self.logger.warning(f"符号链接检测失败: {normalized_path}")
                return symlink_check

        # 6. 检查写入权限（如果需要）
        if access_mode in [PathAccessMode.WRITE, PathAccessMode.CREATE, PathAccessMode.DELETE]:
            # 检查父目录是否存在且可写
            parent_dir = normalized_path.parent
            if not parent_dir.exists():
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.DANGEROUS,
                    reason=f"父目录不存在: {parent_dir}"
                )

            if not os.access(parent_dir, os.W_OK):
                return PathValidationResult(
                    is_valid=False,
                    risk_level=PathRiskLevel.FORBIDDEN,
                    reason=f"没有写入权限: {parent_dir}"
                )

        # 所有检查通过
        # 确定允许的目录
        allowed_dir = None
        for allowed in self.allowed_directories:
            try:
                if hasattr(normalized_path, 'is_relative_to'):
                    if normalized_path.is_relative_to(allowed):
                        allowed_dir = allowed
                        break
                else:
                    try:
                        normalized_path.relative_to(allowed)
                        allowed_dir = allowed
                        break
                    except ValueError:
                        continue
            except Exception:
                continue

        self.logger.debug(f"路径验证通过: {normalized_path}")

        return PathValidationResult(
            is_valid=True,
            risk_level=PathRiskLevel.SAFE,
            reason="所有安全检查通过",
            resolved_path=normalized_path,
            allowed_directory=allowed_dir
        )

    def add_allowed_directory(self, directory: Path) -> None:
        """
        添加允许的目录

        Args:
            directory: 目录路径
        """
        normalized = self._normalize_path(directory).resolve()
        if normalized not in self.allowed_directories:
            self.allowed_directories.append(normalized)
            self.logger.info(f"添加允许的目录: {normalized}")

    def remove_allowed_directory(self, directory: Path) -> None:
        """
        移除允许的目录

        Args:
            directory: 目录路径
        """
        normalized = self._normalize_path(directory).resolve()
        if normalized in self.allowed_directories:
            self.allowed_directories.remove(normalized)
            self.logger.info(f"移除允许的目录: {normalized}")


class SecurePathManager:
    """
    安全路径管理器

    结合路径验证和审计日志。
    """

    def __init__(self,
                 validator: Optional[PathValidator] = None,
                 enable_audit_log: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全路径管理器

        Args:
            validator: 路径验证器
            enable_audit_log: 是否启用审计日志
            logger: 日志记录器
        """
        self.validator = validator or PathValidator()
        self.enable_audit_log = enable_audit_log
        self.logger = logger or logging.getLogger(__name__)

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

    def validate_path(self,
                     path: Path | str,
                     access_mode: PathAccessMode = PathAccessMode.READ) -> PathValidationResult:
        """
        验证路径并记录审计日志

        Args:
            path: 要验证的路径
            access_mode: 访问模式

        Returns:
            PathValidationResult: 验证结果
        """
        # 验证路径
        result = self.validator.validate(path, access_mode)

        # 记录审计日志
        if self.enable_audit_log:
            self._log_audit(path, access_mode, result)

        # 如果验证失败，记录错误
        if not result.is_valid:
            self.logger.error(
                f"路径验证失败: {path} - {result.reason} "
                f"(风险等级: {result.risk_level.value})"
            )

        return result

    def _log_audit(self,
                   path: Path | str,
                   access_mode: PathAccessMode,
                   result: PathValidationResult):
        """记录审计日志"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'path': str(path),
            'access_mode': access_mode.value,
            'is_valid': result.is_valid,
            'risk_level': result.risk_level.value,
            'reason': result.reason
        }

        if result.resolved_path:
            audit_entry['resolved_path'] = str(result.resolved_path)

        if result.allowed_directory:
            audit_entry['allowed_directory'] = str(result.allowed_directory)

        self.audit_log.append(audit_entry)

        # 限制日志大小
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self.audit_log[-limit:]


class PathSecurityError(Exception):
    """路径安全相关异常"""
    pass


# 便捷函数：创建默认配置的路径验证器
def create_path_validator(
    profile: str = "strict",
    allowed_directories: Optional[List[Path]] = None,
    logger: Optional[logging.Logger] = None
) -> PathValidator:
    """
    创建预配置的路径验证器

    Args:
        profile: 安全配置档案
            - strict: 严格模式（生产环境推荐）
            - moderate: 中等模式
            - permissive: 宽松模式（仅开发环境）
        allowed_directories: 允许的目录列表
        logger: 日志记录器

    Returns:
        PathValidator: 配置好的验证器
    """
    if profile == "strict":
        # 严格模式：不允许符号链接，严格检查
        return PathValidator(
            allowed_directories=allowed_directories,
            allow_symlinks=False,
            strict_mode=True,
            logger=logger
        )

    elif profile == "moderate":
        # 中等模式：允许符号链接，严格检查
        return PathValidator(
            allowed_directories=allowed_directories,
            allow_symlinks=True,
            strict_mode=True,
            logger=logger
        )

    elif profile == "permissive":
        # 宽松模式：允许符号链接，非严格检查
        return PathValidator(
            allowed_directories=allowed_directories,
            allow_symlinks=True,
            strict_mode=False,
            logger=logger
        )

    else:
        raise ValueError(f"Unknown profile: {profile}")
