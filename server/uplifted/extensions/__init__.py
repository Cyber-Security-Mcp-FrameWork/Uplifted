"""
扩展性模块
提供插件管理、配置管理、钩子系统和动态加载等功能
"""

from .plugin_manager import (
    Plugin,
    PluginInfo,
    PluginConfig,
    PluginStatus,
    PluginManager,
    PluginRegistry,
    get_global_plugin_manager
)

from .config_manager import (
    ConfigManager,
    ConfigSource,
    ConfigFormat,
    ConfigValidationRule,
    ConfigChangeEvent,
    ConfigLoader,
    JSONConfigLoader,
    YAMLConfigLoader,
    ConfigValidator,
    get_global_config_manager,
    get_config,
    set_config,
    reload_config
)

from .config_loaders import (
    EnvConfigLoader,
    SQLiteConfigLoader,
    TOMLConfigLoader,
    INIConfigLoader,
    EncryptedConfigLoader,
    TOML_AVAILABLE,
    CRYPTO_AVAILABLE
)

from .secure_config_loaders import (
    SecureSQLiteConfigLoader,
    SecureConfigLoaderProfile,
    create_secure_sqlite_config_loader,
    get_global_secure_sqlite_config_loader
)

from .config_utils import (
    ConfigTemplate,
    ConfigSection,
    ConfigField,
    generate_config_template,
    export_config,
    import_config,
    compare_configs,
    merge_configs,
    validate_config_schema,
    generate_encryption_key,
    load_encryption_key
)

from .hook_system import (
    HookManager,
    HookEvent,
    HookResult,
    HookPriority,
    HookExecutionMode,
    HookCallback,
    HookFilter,
    HookMiddleware,
    LoggingMiddleware,
    PerformanceMiddleware,
    get_global_hook_manager,
    register_hook,
    unregister_hook,
    emit_hook,
    emit_hook_sync
)

from .dynamic_loader import (
    DynamicLoader,
    LoadedItem,
    LoaderType,
    LoadStatus,
    DependencyResolver,
    ModuleWatcher,
    get_global_dynamic_loader,
    load_module,
    load_class,
    load_function,
    unload_module,
    reload_module
)

from .secure_dynamic_loader import (
    SecureDynamicLoader,
    create_secure_dynamic_loader,
    get_global_secure_dynamic_loader,
    load_module_secure,
    load_class_secure,
    load_function_secure
)

from .plugin_manifest import (
    PluginManifest,
    ToolDefinition,
    ResourceRequirements,
    PluginCategory,
    PermissionType,
    generate_manifest_template,
    manifest_to_plugin_info
)

from .mcp_bridge import (
    MCPPluginBridge,
    RegisteredTool,
    get_global_mcp_bridge,
    initialize_mcp_bridge
)

from .plugin_system_init import (
    initialize_plugin_system,
    shutdown_plugin_system,
    get_plugin_system_status,
    quick_start
)

__all__ = [
    # Plugin Management
    'PluginManager',
    'Plugin',
    'PluginInfo',
    'PluginStatus',
    'PluginConfig',
    'PluginRegistry',
    'get_global_plugin_manager',

    # Plugin Manifest
    'PluginManifest',
    'ToolDefinition',
    'ResourceRequirements',
    'PluginCategory',
    'PermissionType',
    'generate_manifest_template',
    'manifest_to_plugin_info',

    # MCP Bridge
    'MCPPluginBridge',
    'RegisteredTool',
    'get_global_mcp_bridge',
    'initialize_mcp_bridge',

    # Plugin System Initialization
    'initialize_plugin_system',
    'shutdown_plugin_system',
    'get_plugin_system_status',
    'quick_start',

    # Configuration Management
    'ConfigManager',
    'ConfigSource',
    'ConfigFormat',
    'ConfigValidationRule',
    'ConfigChangeEvent',
    'ConfigLoader',
    'JSONConfigLoader',
    'YAMLConfigLoader',
    'ConfigValidator',
    'get_global_config_manager',
    'get_config',
    'set_config',
    'reload_config',

    # Advanced Config Loaders
    'EnvConfigLoader',
    'SQLiteConfigLoader',
    'TOMLConfigLoader',
    'INIConfigLoader',
    'EncryptedConfigLoader',
    'TOML_AVAILABLE',
    'CRYPTO_AVAILABLE',

    # Secure Config Loaders (SEC-005)
    'SecureSQLiteConfigLoader',
    'SecureConfigLoaderProfile',
    'create_secure_sqlite_config_loader',
    'get_global_secure_sqlite_config_loader',

    # Config Utils
    'ConfigTemplate',
    'ConfigSection',
    'ConfigField',
    'generate_config_template',
    'export_config',
    'import_config',
    'compare_configs',
    'merge_configs',
    'validate_config_schema',
    'generate_encryption_key',
    'load_encryption_key',

    # Hook System
    'HookManager',
    'HookEvent',
    'HookResult',
    'HookPriority',
    'HookExecutionMode',
    'HookCallback',
    'HookFilter',
    'HookMiddleware',
    'LoggingMiddleware',
    'PerformanceMiddleware',
    'get_global_hook_manager',
    'register_hook',
    'unregister_hook',
    'emit_hook',
    'emit_hook_sync',

    # Dynamic Loading
    'DynamicLoader',
    'LoadedItem',
    'LoaderType',
    'LoadStatus',
    'DependencyResolver',
    'ModuleWatcher',
    'get_global_dynamic_loader',
    'load_module',
    'load_class',
    'load_function',
    'unload_module',
    'reload_module',

    # Secure Dynamic Loading
    'SecureDynamicLoader',
    'create_secure_dynamic_loader',
    'get_global_secure_dynamic_loader',
    'load_module_secure',
    'load_class_secure',
    'load_function_secure'
]