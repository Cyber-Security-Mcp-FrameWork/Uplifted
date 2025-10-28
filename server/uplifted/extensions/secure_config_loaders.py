"""
安全配置加载器 - SEC-005 修复

提供 SQLiteConfigLoader 的安全包装器，防止 SQL 注入攻击。

核心安全特性：
1. SQL 标识符验证 - 验证表名安全性
2. 防止 SQL 注入 - 拒绝危险字符和 SQL 关键字
3. 审计日志 - 记录所有验证操作
4. 完全 API 兼容 - 可直接替换 SQLiteConfigLoader

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .config_loaders import SQLiteConfigLoader
from ..security.sql_validator import (
    SQLIdentifierValidator,
    SQLValidationResult,
    SQLRiskLevel,
    SQLIdentifierType,
    SQLSecurityError
)


class SecureSQLiteConfigLoader(SQLiteConfigLoader):
    """
    安全的 SQLite 配置加载器

    包装 SQLiteConfigLoader，添加 SQL 注入防护。

    使用示例:
        # 基本使用
        loader = SecureSQLiteConfigLoader(table_name="config_store")
        config = loader.load("config.db")

        # 使用严格模式（拒绝可疑标识符）
        loader = SecureSQLiteConfigLoader(
            table_name="config_store",
            strict_mode=True
        )

        # 禁用验证（不推荐）
        loader = SecureSQLiteConfigLoader(
            table_name="config_store",
            enable_validation=False
        )

    安全特性：
        - 表名验证：检查 SQL 关键字、危险字符、长度限制
        - 字符白名单：只允许字母、数字、下划线
        - 审计日志：记录所有验证操作
        - 风险评估：评估标识符风险等级
    """

    def __init__(self,
                 table_name: str = "config_store",
                 enable_validation: bool = True,
                 strict_mode: bool = False,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全 SQLite 配置加载器

        参数:
            table_name: 配置表名
            enable_validation: 是否启用验证
            strict_mode: 严格模式（拒绝可疑标识符）
            logger: 日志记录器

        异常:
            SQLSecurityError: 表名验证失败
        """
        self.enable_validation = enable_validation
        self.strict_mode = strict_mode
        self.logger = logger or logging.getLogger(__name__)

        # 创建验证器
        if self.enable_validation:
            self._validator = SQLIdentifierValidator(self.logger)

            # 验证表名
            self._validate_table_name(table_name)

        # 调用父类初始化
        super().__init__(table_name=table_name)

        self.logger.info(
            f"安全 SQLite 配置加载器已初始化 "
            f"(表名: {table_name}, 验证: {enable_validation}, 严格: {strict_mode})"
        )

    def _validate_table_name(self, table_name: str) -> None:
        """
        验证表名安全性

        参数:
            table_name: 表名

        异常:
            SQLSecurityError: 验证失败
        """
        result = self._validator.validate_identifier(
            table_name,
            SQLIdentifierType.TABLE
        )

        # 记录审计日志
        self.logger.debug(
            f"表名验证: {table_name} - "
            f"有效={result.is_valid}, 风险等级={result.risk_level.value}"
        )

        # 检查验证结果
        if not result.is_valid:
            error_msg = (
                f"无效的表名 '{table_name}': {result.reason} "
                f"(风险等级: {result.risk_level.value})"
            )
            self.logger.error(error_msg)
            raise SQLSecurityError(error_msg)

        # 严格模式：拒绝可疑标识符
        if self.strict_mode and result.risk_level == SQLRiskLevel.SUSPICIOUS:
            error_msg = (
                f"可疑的表名 '{table_name}' 在严格模式下被拒绝: {result.reason}"
            )
            self.logger.warning(error_msg)
            raise SQLSecurityError(error_msg)

        # 警告可疑标识符
        if result.risk_level == SQLRiskLevel.SUSPICIOUS:
            self.logger.warning(
                f"表名 '{table_name}' 被标记为可疑: {result.reason}"
            )

    def load(self, file_path: str) -> Dict[str, Any]:
        """
        从 SQLite 加载配置（安全包装）

        参数:
            file_path: 数据库文件路径

        返回:
            配置字典

        异常:
            ValueError: 加载失败
        """
        try:
            return super().load(file_path)
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        保存配置到 SQLite（安全包装）

        参数:
            data: 配置字典
            file_path: 数据库文件路径

        返回:
            是否成功
        """
        try:
            return super().save(data, file_path)
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False


class SecureConfigLoaderProfile:
    """安全配置加载器配置档案"""

    STRICT = {
        'enable_validation': True,
        'strict_mode': True,
    }

    MODERATE = {
        'enable_validation': True,
        'strict_mode': False,
    }

    PERMISSIVE = {
        'enable_validation': False,
        'strict_mode': False,
    }


def create_secure_sqlite_config_loader(
    table_name: str = "config_store",
    profile: str = "strict",
    logger: Optional[logging.Logger] = None
) -> SecureSQLiteConfigLoader:
    """
    创建安全 SQLite 配置加载器（便捷函数）

    参数:
        table_name: 配置表名
        profile: 安全配置档案（"strict", "moderate", "permissive"）
        logger: 日志记录器

    返回:
        SecureSQLiteConfigLoader 实例

    异常:
        ValueError: 无效的配置档案
        SQLSecurityError: 表名验证失败

    使用示例:
        # 推荐：使用严格模式（生产环境）
        loader = create_secure_sqlite_config_loader(
            table_name="config_store",
            profile="strict"
        )

        # 中等模式：允许可疑标识符但记录警告
        loader = create_secure_sqlite_config_loader(
            table_name="my_config",
            profile="moderate"
        )

        # 宽松模式：禁用验证（仅用于测试）
        loader = create_secure_sqlite_config_loader(
            table_name="test_config",
            profile="permissive"
        )
    """
    # 获取配置档案
    profile = profile.lower()
    if profile == "strict":
        config = SecureConfigLoaderProfile.STRICT
    elif profile == "moderate":
        config = SecureConfigLoaderProfile.MODERATE
    elif profile == "permissive":
        config = SecureConfigLoaderProfile.PERMISSIVE
    else:
        raise ValueError(
            f"无效的配置档案: {profile}. "
            f"可用选项: strict, moderate, permissive"
        )

    return SecureSQLiteConfigLoader(
        table_name=table_name,
        enable_validation=config['enable_validation'],
        strict_mode=config['strict_mode'],
        logger=logger
    )


# 全局实例（延迟初始化）
_global_secure_loader: Optional[SecureSQLiteConfigLoader] = None


def get_global_secure_sqlite_config_loader(
    table_name: str = "config_store",
    profile: str = "strict"
) -> SecureSQLiteConfigLoader:
    """
    获取全局安全 SQLite 配置加载器（单例模式）

    参数:
        table_name: 配置表名（仅首次调用时使用）
        profile: 安全配置档案（仅首次调用时使用）

    返回:
        全局 SecureSQLiteConfigLoader 实例

    注意:
        - 首次调用后，table_name 和 profile 参数将被忽略
        - 如需更改配置，请直接创建新实例
    """
    global _global_secure_loader

    if _global_secure_loader is None:
        _global_secure_loader = create_secure_sqlite_config_loader(
            table_name=table_name,
            profile=profile
        )

    return _global_secure_loader


# 导出所有组件
__all__ = [
    'SecureSQLiteConfigLoader',
    'SecureConfigLoaderProfile',
    'create_secure_sqlite_config_loader',
    'get_global_secure_sqlite_config_loader',
]
