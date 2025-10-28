"""
安全模块
提供认证、授权、限流、命令验证、插件验证等安全功能
"""

from .auth import AuthManager, TokenValidator, APIKeyManager
from .rate_limiter import RateLimiter, RateLimitConfig
from .middleware import SecurityMiddleware, AuthMiddleware, RateLimitMiddleware
from .command_validator import (
    CommandValidator,
    SecureBashExecutor,
    SecurityError,
    CommandRiskLevel,
    CommandValidationResult
)
from .plugin_validator import (
    PluginValidator,
    SecurePluginLoader,
    PluginSignatureValidator,
    DangerousPatternDetector,
    PluginPermission,
    PluginRiskLevel,
    PluginValidationResult,
    PluginSignature,
    create_secure_plugin_loader
)
from .path_validator import (
    PathValidator,
    SecurePathManager,
    PathAccessMode,
    PathRiskLevel,
    PathValidationResult,
    PathSecurityError,
    create_path_validator
)
from .sql_validator import (
    SQLIdentifierValidator,
    SQLInjectionDetector,
    SecureSQLManager,
    SQLIdentifierType,
    SQLRiskLevel,
    SQLValidationResult,
    SQLSecurityError,
    validate_table_name,
    validate_column_name
)

__all__ = [
    # Authentication & Authorization
    'AuthManager',
    'TokenValidator',
    'APIKeyManager',

    # Rate Limiting
    'RateLimiter',
    'RateLimitConfig',

    # Middleware
    'SecurityMiddleware',
    'AuthMiddleware',
    'RateLimitMiddleware',

    # Command Validation (SEC-001)
    'CommandValidator',
    'SecureBashExecutor',
    'SecurityError',
    'CommandRiskLevel',
    'CommandValidationResult',

    # Plugin Validation (SEC-002)
    'PluginValidator',
    'SecurePluginLoader',
    'PluginSignatureValidator',
    'DangerousPatternDetector',
    'PluginPermission',
    'PluginRiskLevel',
    'PluginValidationResult',
    'PluginSignature',
    'create_secure_plugin_loader',

    # Path Validation (SEC-004)
    'PathValidator',
    'SecurePathManager',
    'PathAccessMode',
    'PathRiskLevel',
    'PathValidationResult',
    'PathSecurityError',
    'create_path_validator',

    # SQL Validation (SEC-005)
    'SQLIdentifierValidator',
    'SQLInjectionDetector',
    'SecureSQLManager',
    'SQLIdentifierType',
    'SQLRiskLevel',
    'SQLValidationResult',
    'SQLSecurityError',
    'validate_table_name',
    'validate_column_name'
]