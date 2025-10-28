"""
配置管理完整示例

演示 Uplifted 配置管理系统的所有功能：
- 多源配置加载（文件、环境变量、SQLite）
- 配置优先级和合并
- 配置验证
- 热重载
- 配置加密
- 配置模板生成

作者: Uplifted Team
日期: 2025-10-28
"""

import asyncio
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_1_basic_usage():
    """
    示例 1: 基础使用 - 单文件配置
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Usage - Single File Configuration")
    print("=" * 60)

    from uplifted.extensions import (
        ConfigManager,
        ConfigSource,
        ConfigFormat,
        generate_config_template
    )

    # 1. 生成配置模板
    print("\n[Step 1] Generating config template...")
    config_path = "config/example1.yaml"
    template = generate_config_template("default", config_path, format="yaml")
    print(f"✓ Template generated: {config_path}")

    # 2. 创建配置管理器
    print("\n[Step 2] Creating ConfigManager...")
    manager = ConfigManager(logger=logger)

    # 3. 添加配置源
    print("\n[Step 3] Adding config source...")
    manager.add_source(ConfigSource(
        name="main",
        path=config_path,
        format=ConfigFormat.YAML,
        priority=100,
        watch=True,
        required=True
    ))

    # 4. 加载配置
    print("\n[Step 4] Loading configuration...")
    success = await manager.load_all()
    if success:
        print("✓ Configuration loaded successfully")
    else:
        print("✗ Failed to load configuration")
        return

    # 5. 读取配置值
    print("\n[Step 5] Reading configuration values:")
    server_port = manager.get("server.port", 8080)
    log_level = manager.get("logging.level", "INFO")
    plugins_enabled = manager.get("plugins.enabled", True)

    print(f"  • Server port: {server_port}")
    print(f"  • Log level: {log_level}")
    print(f"  • Plugins enabled: {plugins_enabled}")

    # 6. 修改配置
    print("\n[Step 6] Modifying configuration:")
    manager.set("server.port", 9000)
    print(f"  • New server port: {manager.get('server.port')}")

    # 7. 保存配置
    print("\n[Step 7] Saving configuration...")
    if await manager.save_to_source("main"):
        print("✓ Configuration saved")
    else:
        print("✗ Failed to save configuration")

    # 清理
    await manager.shutdown()


async def example_2_multi_source():
    """
    示例 2: 多源配置 - 文件 + 环境变量 + SQLite
    """
    print("\n" + "=" * 60)
    print("Example 2: Multi-Source Configuration")
    print("=" * 60)

    from uplifted.extensions import (
        ConfigManager,
        ConfigSource,
        ConfigFormat,
        EnvConfigLoader,
        SQLiteConfigLoader,
        generate_config_template
    )

    # 1. 生成基础配置
    print("\n[Step 1] Generating base configuration...")
    base_config_path = "config/base.yaml"
    generate_config_template("minimal", base_config_path)

    # 2. 设置环境变量
    print("\n[Step 2] Setting environment variables...")
    os.environ["UPLIFTED__SERVER__PORT"] = "8090"
    os.environ["UPLIFTED__LOGGING__LEVEL"] = "DEBUG"
    os.environ["UPLIFTED__CUSTOM__VALUE"] = "from_env"
    print("  • UPLIFTED__SERVER__PORT = 8090")
    print("  • UPLIFTED__LOGGING__LEVEL = DEBUG")

    # 3. 创建配置管理器
    manager = ConfigManager(logger=logger)

    # 4. 注册自定义加载器
    print("\n[Step 3] Registering custom loaders...")
    manager._loaders[ConfigFormat.JSON] = SQLiteConfigLoader()

    # 5. 添加多个配置源（按优先级）
    print("\n[Step 4] Adding multiple config sources...")

    # 优先级 100: 基础配置文件
    manager.add_source(ConfigSource(
        name="base",
        path=base_config_path,
        format=ConfigFormat.YAML,
        priority=100,
        required=True
    ))

    # 优先级 50: 环境变量（更高优先级）
    # 注意：环境变量加载器需要特殊处理
    env_loader = EnvConfigLoader(prefix="UPLIFTED__", separator="__")
    env_config = env_loader.load("")

    # 优先级 10: SQLite 数据库（最高优先级）
    db_path = "config/override.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # 预先写入一些数据库配置
    db_loader = SQLiteConfigLoader()
    db_loader.save({"server": {"workers": 8}}, db_path)

    manager.add_source(ConfigSource(
        name="database",
        path=db_path,
        format=ConfigFormat.JSON,  # SQLite 使用 JSON 格式键
        priority=10,  # 最高优先级
        required=False
    ))

    # 6. 加载所有配置
    print("\n[Step 5] Loading all configurations...")
    success = await manager.load_all()

    if success:
        print("✓ All configurations loaded")

        # 手动合并环境变量配置
        current_config = manager.get_all()
        from uplifted.extensions import merge_configs
        merged = merge_configs(current_config, env_config)
        manager._config = merged

        # 7. 查看最终配置
        print("\n[Step 6] Final configuration (merged from all sources):")
        server_port = manager.get("server.port")
        server_workers = manager.get("server.workers")
        log_level = manager.get("logging.level")
        custom_value = manager.get("custom.value")

        print(f"  • Server port: {server_port} (from env)")
        print(f"  • Server workers: {server_workers} (from database)")
        print(f"  • Log level: {log_level} (from env)")
        print(f"  • Custom value: {custom_value} (from env)")

        print("\n[Note] Configuration priority order:")
        print("  1. Database (priority 10) - highest")
        print("  2. Environment Variables (merged)")
        print("  3. Base Config File (priority 100) - lowest")

    await manager.shutdown()


async def example_3_validation():
    """
    示例 3: 配置验证
    """
    print("\n" + "=" * 60)
    print("Example 3: Configuration Validation")
    print("=" * 60)

    from uplifted.extensions import (
        ConfigManager,
        ConfigSource,
        ConfigFormat,
        ConfigValidationRule,
        generate_config_template
    )

    # 1. 生成配置
    config_path = "config/validated.yaml"
    generate_config_template("default", config_path)

    # 2. 创建配置管理器
    manager = ConfigManager(logger=logger)

    # 3. 添加验证规则
    print("\n[Step 1] Adding validation rules...")

    # 服务器端口必须是整数，范围 1024-65535
    manager.add_validation_rule(ConfigValidationRule(
        path="server.port",
        required=True,
        type_check=int,
        validator=lambda v: 1024 <= v <= 65535,
        description="Server port must be between 1024 and 65535"
    ))

    # 日志级别必须是有效值
    manager.add_validation_rule(ConfigValidationRule(
        path="logging.level",
        required=True,
        type_check=str,
        validator=lambda v: v in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Log level must be valid"
    ))

    # 数据库路径必须存在父目录
    manager.add_validation_rule(ConfigValidationRule(
        path="database.path",
        required=True,
        type_check=str,
        validator=lambda v: os.path.exists(os.path.dirname(v)) or v.startswith('./'),
        default_value="./data/uplifted.db",
        description="Database path parent directory must exist"
    ))

    print("✓ Validation rules added")

    # 4. 添加配置源并加载
    manager.add_source(ConfigSource(
        name="validated",
        path=config_path,
        format=ConfigFormat.YAML,
        priority=100,
        required=True
    ))

    print("\n[Step 2] Loading and validating configuration...")
    success = await manager.load_all()

    if success:
        print("✓ Configuration validated successfully")
    else:
        print("✗ Validation failed")

    await manager.shutdown()


async def example_4_hot_reload():
    """
    示例 4: 配置热重载
    """
    print("\n" + "=" * 60)
    print("Example 4: Hot Reload")
    print("=" * 60)

    from uplifted.extensions import (
        ConfigManager,
        ConfigSource,
        ConfigFormat,
        generate_config_template
    )

    # 1. 生成配置
    config_path = "config/hot_reload.yaml"
    generate_config_template("minimal", config_path)

    # 2. 创建配置管理器
    manager = ConfigManager(logger=logger)

    # 3. 注册配置变更回调
    print("\n[Step 1] Registering change callback...")

    def on_config_change(event):
        print(f"\n📢 Configuration changed!")
        print(f"   Source: {event.source}")
        print(f"   Path: {event.path}")
        print(f"   Old value: {event.old_value}")
        print(f"   New value: {event.new_value}")

    manager.register_change_callback(on_config_change)
    print("✓ Callback registered")

    # 4. 添加配置源（启用监视）
    manager.add_source(ConfigSource(
        name="hot",
        path=config_path,
        format=ConfigFormat.YAML,
        priority=100,
        watch=True,  # 启用文件监视
        required=True
    ))

    # 5. 加载配置
    print("\n[Step 2] Loading configuration with hot reload enabled...")
    await manager.load_all()
    print("✓ Configuration loaded, file watching started")

    print("\n[Step 3] Current server port:", manager.get("server.port"))

    print("\n[Note] Hot reload is active. File changes will be detected automatically.")
    print("       In production, the config manager watches for file changes")
    print("       and triggers callbacks when modifications occur.")

    # 模拟配置修改（通过代码）
    print("\n[Step 4] Simulating configuration change...")
    manager.set("server.port", 9999)
    print("✓ Configuration modified")

    # 等待一小段时间
    await asyncio.sleep(0.5)

    await manager.shutdown()


async def example_5_encrypted_config():
    """
    示例 5: 加密配置
    """
    print("\n" + "=" * 60)
    print("Example 5: Encrypted Configuration")
    print("=" * 60)

    from uplifted.extensions import (
        EncryptedConfigLoader,
        JSONConfigLoader,
        generate_encryption_key,
        CRYPTO_AVAILABLE
    )

    if not CRYPTO_AVAILABLE:
        print("✗ cryptography package not installed")
        print("  Install with: pip install cryptography")
        return

    # 1. 生成加密密钥
    print("\n[Step 1] Generating encryption key...")
    key_path = "config/encryption.key"
    key = generate_encryption_key(key_path)
    print(f"✓ Encryption key generated: {key_path}")
    print(f"  Key (first 16 bytes): {key[:16]}...")

    # 2. 创建敏感配置
    print("\n[Step 2] Creating sensitive configuration...")
    sensitive_config = {
        "api_keys": {
            "openai": "sk-xxxxxxxxxxxxxxxx",
            "anthropic": "sk-ant-xxxxxxxxxxxxxxxx"
        },
        "database": {
            "password": "super_secret_password"
        }
    }
    print("✓ Sensitive config created")

    # 3. 使用加密加载器保存
    print("\n[Step 3] Encrypting and saving configuration...")
    base_loader = JSONConfigLoader()
    encrypted_loader = EncryptedConfigLoader(base_loader, key)

    encrypted_path = "config/secrets.json.enc"
    success = encrypted_loader.save(sensitive_config, encrypted_path)

    if success:
        print(f"✓ Encrypted config saved: {encrypted_path}")

        # 验证文件确实被加密
        with open(encrypted_path, 'rb') as f:
            encrypted_content = f.read()
        print(f"  Encrypted content (first 50 bytes): {encrypted_content[:50]}...")

    # 4. 加载解密配置
    print("\n[Step 4] Loading and decrypting configuration...")
    loaded_config = encrypted_loader.load(encrypted_path)

    print("✓ Configuration decrypted successfully:")
    print(f"  • OpenAI API Key: {loaded_config['api_keys']['openai']}")
    print(f"  • Database Password: {loaded_config['database']['password']}")

    print("\n[Security Note]")
    print("  • Never commit encryption.key to version control")
    print("  • Store keys securely (environment variables, key vault, etc.)")
    print("  • Use different keys for different environments")


async def example_6_config_templates():
    """
    示例 6: 配置模板
    """
    print("\n" + "=" * 60)
    print("Example 6: Configuration Templates")
    print("=" * 60)

    from uplifted.extensions import (
        generate_config_template,
        export_config,
        import_config,
        compare_configs,
        merge_configs
    )

    # 1. 生成不同环境的模板
    print("\n[Step 1] Generating environment templates...")

    templates = {
        "development": "config/dev.yaml",
        "production": "config/prod.yaml",
        "minimal": "config/minimal.yaml"
    }

    for env, path in templates.items():
        config = generate_config_template(env, path)
        print(f"✓ Generated {env} template: {path}")

    # 2. 比较配置
    print("\n[Step 2] Comparing development vs production:")
    dev_config = import_config(templates["development"])
    prod_config = import_config(templates["production"])

    diff = compare_configs(dev_config, prod_config)

    print(f"  • Added in prod: {len(diff['added'])} keys")
    print(f"  • Removed in prod: {len(diff['removed'])} keys")
    print(f"  • Changed in prod: {len(diff['changed'])} keys")

    if diff['changed']:
        print("\n  Changed values:")
        for key, values in list(diff['changed'].items())[:3]:  # 显示前 3 个
            print(f"    - {key}:")
            print(f"      Dev: {values['old']}")
            print(f"      Prod: {values['new']}")

    # 3. 合并配置
    print("\n[Step 3] Merging configurations...")
    minimal_config = import_config(templates["minimal"])
    custom_overrides = {
        "server": {"port": 8888},
        "custom": {"feature": "enabled"}
    }

    merged = merge_configs(minimal_config, custom_overrides)
    print("✓ Configurations merged")
    print(f"  • Final server port: {merged['server']['port']}")

    # 4. 导出合并后的配置
    print("\n[Step 4] Exporting merged configuration...")
    export_path = "config/custom.yaml"
    if export_config(merged, export_path):
        print(f"✓ Merged config exported: {export_path}")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("  Uplifted Configuration Management Examples")
    print("=" * 80)

    # 创建配置目录
    os.makedirs("config", exist_ok=True)

    try:
        # 示例 1: 基础使用
        await example_1_basic_usage()

        # 示例 2: 多源配置
        await example_2_multi_source()

        # 示例 3: 配置验证
        await example_3_validation()

        # 示例 4: 热重载
        await example_4_hot_reload()

        # 示例 5: 加密配置
        await example_5_encrypted_config()

        # 示例 6: 配置模板
        await example_6_config_templates()

        print("\n" + "=" * 80)
        print("  All examples completed successfully! ✓")
        print("=" * 80)
        print("\nGenerated files:")
        print("  • config/example1.yaml - Basic config")
        print("  • config/base.yaml - Multi-source base")
        print("  • config/override.db - SQLite overrides")
        print("  • config/validated.yaml - Validated config")
        print("  • config/hot_reload.yaml - Hot reload config")
        print("  • config/encryption.key - Encryption key (DO NOT COMMIT)")
        print("  • config/secrets.json.enc - Encrypted secrets")
        print("  • config/dev.yaml, prod.yaml, minimal.yaml - Templates")
        print("  • config/custom.yaml - Merged config")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
