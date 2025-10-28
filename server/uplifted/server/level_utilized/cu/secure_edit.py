"""
安全的文件编辑工具包装器

在原有 EditTool 基础上添加路径安全验证层，防止路径遍历攻击。

核心安全特性：
1. 路径白名单验证
2. 路径遍历检测
3. 符号链接解析
4. 危险路径黑名单
5. 审计日志

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import logging
from pathlib import Path
from typing import Literal, Optional, List

from anthropic.types.beta import BetaToolTextEditor20241022Param

from .base import ToolError, ToolResult
from .edit import EditTool, Command
from .....security.path_validator import (
    PathValidator,
    SecurePathManager,
    PathAccessMode,
    PathSecurityError,
    create_path_validator
)


class SecureEditTool(EditTool):
    """
    安全的文件编辑工具

    在原有 EditTool 基础上添加多层路径安全防护：
    1. 路径白名单验证
    2. 路径遍历检测（.. 等）
    3. 符号链接解析和验证
    4. 危险路径黑名单
    5. 审计日志记录

    使用方式:
        secure_edit = SecureEditTool(
            allowed_directories=[Path("/app/data"), Path("/app/temp")]
        )
        result = await secure_edit(command="view", path="/app/data/file.txt")
    """

    def __init__(self,
                 allowed_directories: Optional[List[Path]] = None,
                 security_profile: str = "moderate",
                 enable_validation: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全文件编辑工具

        Args:
            allowed_directories: 允许访问的目录列表（白名单）
            security_profile: 安全配置档案（strict/moderate/permissive）
            enable_validation: 是否启用安全验证
            logger: 日志记录器
        """
        super().__init__()

        self.logger = logger or logging.getLogger(__name__)
        self.enable_validation = enable_validation

        # 创建路径管理器
        if enable_validation:
            validator = create_path_validator(
                profile=security_profile,
                allowed_directories=allowed_directories,
                logger=logger
            )
            self._path_manager = SecurePathManager(
                validator=validator,
                enable_audit_log=True,
                logger=logger
            )
        else:
            self._path_manager = None

        self.logger.info(
            f"SecureEditTool initialized "
            f"(validation={'enabled' if enable_validation else 'disabled'}, "
            f"profile={security_profile})"
        )

    def validate_path(self, command: str, path: Path):
        """
        检查路径和命令的组合是否有效（覆盖父类方法）

        Args:
            command: 命令名称
            path: 路径对象

        Raises:
            ToolError: 路径验证失败
        """
        # 如果启用了安全验证，使用增强的验证
        if self.enable_validation and self._path_manager:
            # 确定访问模式
            if command == "view":
                access_mode = PathAccessMode.READ
            elif command == "create":
                access_mode = PathAccessMode.CREATE
            elif command in ["str_replace", "insert"]:
                access_mode = PathAccessMode.WRITE
            elif command == "undo_edit":
                access_mode = PathAccessMode.WRITE
            else:
                access_mode = PathAccessMode.READ

            # 验证路径安全性
            validation_result = self._path_manager.validate_path(path, access_mode)

            if not validation_result.is_valid:
                # 路径验证失败
                error_msg = f"路径访问被拒绝: {validation_result.reason}"
                self.logger.error(
                    f"路径验证失败: {path} - {validation_result.reason} "
                    f"(风险等级: {validation_result.risk_level.value})"
                )
                raise ToolError(error_msg)

            # 使用解析后的路径（防止符号链接攻击）
            if validation_result.resolved_path:
                # 注意：这里不修改 path，因为 Path 对象是不可变的
                # 在实际操作中会使用解析后的路径
                pass

        # 调用父类的基础验证
        super().validate_path(command, path)

    async def __call__(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ):
        """
        执行文件编辑命令（带安全验证）

        Args:
            command: 命令类型
            path: 文件路径
            file_text: 文件内容（create 命令）
            view_range: 查看范围（view 命令）
            old_str: 旧字符串（str_replace 命令）
            new_str: 新字符串（str_replace/insert 命令）
            insert_line: 插入行号（insert 命令）
            **kwargs: 其他参数

        Returns:
            ToolResult: 命令执行结果

        Raises:
            ToolError: 命令执行失败或安全验证失败
        """
        # 转换路径
        _path = Path(path)

        # 安全验证
        self.validate_path(command, _path)

        # 如果启用了验证，使用解析后的安全路径
        if self.enable_validation and self._path_manager:
            # 再次验证以获取解析后的路径
            if command == "view":
                access_mode = PathAccessMode.READ
            elif command == "create":
                access_mode = PathAccessMode.CREATE
            else:
                access_mode = PathAccessMode.WRITE

            validation_result = self._path_manager.validate_path(_path, access_mode)
            if validation_result.resolved_path:
                # 使用解析后的安全路径
                _path = validation_result.resolved_path

        # 调用父类方法执行实际操作
        return await super().__call__(
            command=command,
            path=str(_path),  # 使用安全路径
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
            **kwargs
        )

    def add_allowed_directory(self, directory: Path) -> None:
        """
        添加允许的目录

        Args:
            directory: 目录路径
        """
        if self._path_manager and self._path_manager.validator:
            self._path_manager.validator.add_allowed_directory(directory)

    def remove_allowed_directory(self, directory: Path) -> None:
        """
        移除允许的目录

        Args:
            directory: 目录路径
        """
        if self._path_manager and self._path_manager.validator:
            self._path_manager.validator.remove_allowed_directory(directory)

    def get_audit_log(self, limit: int = 100):
        """
        获取审计日志

        Args:
            limit: 返回的日志条数

        Returns:
            审计日志列表
        """
        if self._path_manager:
            return self._path_manager.get_audit_log(limit)
        else:
            return []

    def get_allowed_directories(self) -> List[Path]:
        """
        获取允许的目录列表

        Returns:
            允许的目录列表
        """
        if self._path_manager and self._path_manager.validator:
            return self._path_manager.validator.allowed_directories.copy()
        else:
            return []


# 便捷函数：创建默认安全配置的编辑工具
def create_secure_edit_tool(
    profile: str = "moderate",
    allowed_directories: Optional[List[Path]] = None,
    logger: Optional[logging.Logger] = None
) -> SecureEditTool:
    """
    创建预配置的安全文件编辑工具

    Args:
        profile: 安全配置档案
            - strict: 严格模式（生产环境推荐）
            - moderate: 中等模式
            - permissive: 宽松模式（仅开发环境）
        allowed_directories: 允许的目录列表
        logger: 日志记录器

    Returns:
        SecureEditTool: 配置好的安全编辑工具
    """
    return SecureEditTool(
        allowed_directories=allowed_directories,
        security_profile=profile,
        enable_validation=True,
        logger=logger
    )
