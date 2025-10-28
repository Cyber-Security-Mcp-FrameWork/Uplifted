# Uplifted 配置管理指南

完整的配置管理系统使用指南

## 目录

- [概览](#概览)
- [快速开始](#快速开始)
- [配置加载器](#配置加载器)
- [配置源和优先级](#配置源和优先级)
- [配置验证](#配置验证)
- [配置热重载](#配置热重载)
- [配置加密](#配置加密)
- [配置模板](#配置模板)
- [高级用法](#高级用法)
- [最佳实践](#最佳实践)

## 概览

Uplifted 提供了一个强大而灵活的配置管理系统，支持：

✅ **多种配置源**
- 配置文件（YAML、JSON、TOML、INI）
- 环境变量
- SQLite 数据库
- 加密配置文件

✅ **配置优先级和合并**
- 多个配置源按优先级合并
- 深度合并嵌套配置

✅ **配置验证**
- 类型检查
- 自定义验证规则
- 默认值

✅ **热重载**
- 文件变更自动检测
- 配置变更通知
- 防抖处理

✅ **配置工具**
- 模板生成
- 配置导入/导出
- 配置比较和合并
- 加密密钥管理

## 快速开始

### 1. 生成配置模板

```python
from uplifted.extensions import generate_config_template

# 生成默认模板
config = generate_config_template("default", "config.yaml")

# 生成最小模板
config = generate_config_template("minimal", "config.yaml")

# 生成生产环境模板
config = generate_config_template("production", "prod.yaml")
```

### 2. 加载配置

```python
import asyncio
from uplifted.extensions import (
    ConfigManager,
    ConfigSource,
    ConfigFormat
)

async def main():
    # 创建配置管理器
    manager = ConfigManager()

    # 添加配置源
    manager.add_source(ConfigSource(
        name="main",
        path="config.yaml",
        format=ConfigFormat.YAML,
        priority=100,
        watch=True,
        required=True
    ))

    # 加载配置
    await manager.load_all()

    # 读取配置值
    port = manager.get("server.port", 8080)
    log_level = manager.get("logging.level", "INFO")

    print(f"Server port: {port}")
    print(f"Log level: {log_level}")

asyncio.run(main())
```

### 3. 使用便捷函数

```python
from uplifted.extensions import get_config, set_config, reload_config

# 读取配置
port = get_config("server.port", 8080)

# 设置配置（仅内存）
set_config("server.port", 9000)

# 重新加载所有配置
await reload_config()
```

## 配置加载器

### JSONConfigLoader

加载 JSON 格式配置。

```python
from uplifted.extensions import JSONConfigLoader

loader = JSONConfigLoader()
config = loader.load("config.json")
loader.save(config, "output.json")
```

### YAMLConfigLoader

加载 YAML 格式配置。

```python
from uplifted.extensions import YAMLConfigLoader

loader = YAMLConfigLoader()
config = loader.load("config.yaml")
loader.save(config, "output.yaml")
```

### EnvConfigLoader

从环境变量加载配置。

```python
from uplifted.extensions import EnvConfigLoader

# 设置环境变量
# UPLIFTED__SERVER__PORT=8080
# UPLIFTED__SERVER__HOST=localhost
# UPLIFTED__LOGGING__LEVEL=DEBUG

# 创建加载器
loader = EnvConfigLoader(
    prefix="UPLIFTED__",
    separator="__",
    lowercase_keys=True
)

config = loader.load("")
# 结果: {
#   "server": {"port": 8080, "host": "localhost"},
#   "logging": {"level": "DEBUG"}
# }
```

**支持的值类型**:
- 布尔值: `true`, `false`, `yes`, `no`, `1`, `0`
- 整数: `123`
- 浮点数: `123.45`
- JSON: `'["a","b"]'`, `'{"key":"value"}'`
- 字符串: 其他值

### SQLiteConfigLoader

从 SQLite 数据库加载和保存配置。

```python
from uplifted.extensions import SQLiteConfigLoader

loader = SQLiteConfigLoader(table_name="config_store")

# 保存配置
config = {"server": {"port": 8080}, "database": {"host": "localhost"}}
loader.save(config, "config.db")

# 加载配置
loaded = loader.load("config.db")
```

**数据库结构**:
```sql
CREATE TABLE config_store (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**特性**:
- 线程安全
- 支持嵌套键（如 `database.host`）
- JSON 序列化存储

### TOMLConfigLoader

加载 TOML 格式配置（需要 `pip install toml`）。

```python
from uplifted.extensions import TOMLConfigLoader, TOML_AVAILABLE

if TOML_AVAILABLE:
    loader = TOMLConfigLoader()
    config = loader.load("config.toml")
```

### INIConfigLoader

加载 INI 格式配置。

```python
from uplifted.extensions import INIConfigLoader

loader = INIConfigLoader()
config = loader.load("config.ini")
# 结果: {"section1": {"key1": "value1"}, ...}
```

### EncryptedConfigLoader

加密配置加载器（需要 `pip install cryptography`）。

```python
from uplifted.extensions import (
    EncryptedConfigLoader,
    JSONConfigLoader,
    generate_encryption_key,
    CRYPTO_AVAILABLE
)

if CRYPTO_AVAILABLE:
    # 生成密钥
    key = generate_encryption_key("encryption.key")

    # 创建加密加载器
    base_loader = JSONConfigLoader()
    loader = EncryptedConfigLoader(base_loader, key)

    # 保存加密配置
    sensitive = {"api_key": "secret", "password": "12345"}
    loader.save(sensitive, "secrets.json.enc")

    # 加载解密配置
    config = loader.load("secrets.json.enc")
```

## 配置源和优先级

### 添加多个配置源

```python
from uplifted.extensions import ConfigManager, ConfigSource, ConfigFormat

manager = ConfigManager()

# 优先级 100: 默认配置（最低优先级）
manager.add_source(ConfigSource(
    name="defaults",
    path="config/defaults.yaml",
    format=ConfigFormat.YAML,
    priority=100,
    required=True
))

# 优先级 50: 环境特定配置
manager.add_source(ConfigSource(
    name="environment",
    path="config/production.yaml",
    format=ConfigFormat.YAML,
    priority=50,
    required=False
))

# 优先级 10: 本地覆盖（最高优先级）
manager.add_source(ConfigSource(
    name="local",
    path="config/local.yaml",
    format=ConfigFormat.YAML,
    priority=10,
    required=False
))

await manager.load_all()
```

**优先级规则**:
- 数值越小，优先级越高
- 相同键的值会被高优先级配置覆盖
- 嵌套字典会深度合并

**示例**:
```yaml
# defaults.yaml (priority 100)
server:
  host: localhost
  port: 8080
  workers: 4

# production.yaml (priority 50)
server:
  port: 7541
  workers: 8
logging:
  level: WARNING

# 最终结果:
server:
  host: localhost     # from defaults
  port: 7541          # from production (overrides)
  workers: 8          # from production (overrides)
logging:
  level: WARNING      # from production
```

### 集成环境变量

```python
from uplifted.extensions import EnvConfigLoader, merge_configs

# 加载环境变量
env_loader = EnvConfigLoader(prefix="UPLIFTED__")
env_config = env_loader.load("")

# 加载文件配置
await manager.load_all()

# 合并（环境变量优先）
current_config = manager.get_all()
merged = merge_configs(current_config, env_config)
manager._config = merged
```

## 配置验证

### 添加验证规则

```python
from uplifted.extensions import ConfigValidationRule

manager = ConfigManager()

# 必需字段
manager.add_validation_rule(ConfigValidationRule(
    path="server.port",
    required=True,
    type_check=int,
    description="Server port is required"
))

# 类型检查
manager.add_validation_rule(ConfigValidationRule(
    path="server.host",
    required=True,
    type_check=str,
    description="Server host must be a string"
))

# 自定义验证
manager.add_validation_rule(ConfigValidationRule(
    path="server.port",
    validator=lambda v: 1024 <= v <= 65535,
    description="Port must be between 1024 and 65535"
))

# 默认值
manager.add_validation_rule(ConfigValidationRule(
    path="logging.level",
    default_value="INFO",
    description="Default log level"
))
```

### 验证枚举值

```python
manager.add_validation_rule(ConfigValidationRule(
    path="logging.level",
    type_check=str,
    validator=lambda v: v in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    description="Log level must be valid"
))
```

### 验证文件路径

```python
import os

manager.add_validation_rule(ConfigValidationRule(
    path="database.path",
    type_check=str,
    validator=lambda v: os.path.exists(os.path.dirname(v)) or v.startswith('./'),
    description="Database path parent directory must exist"
))
```

## 配置热重载

### 启用文件监视

```python
# 添加配置源时启用监视
manager.add_source(ConfigSource(
    name="main",
    path="config.yaml",
    format=ConfigFormat.YAML,
    priority=100,
    watch=True,  # 启用文件监视
    required=True
))

await manager.load_all()  # 自动启动文件监视
```

### 注册变更回调

```python
def on_config_change(event):
    print(f"Config changed!")
    print(f"  Source: {event.source}")
    print(f"  Path: {event.path}")
    print(f"  Old: {event.old_value}")
    print(f"  New: {event.new_value}")
    print(f"  Timestamp: {event.timestamp}")

manager.register_change_callback(on_config_change)
```

### 异步回调

```python
async def on_config_change_async(event):
    # 异步处理配置变更
    await some_async_operation()

manager.register_change_callback(on_config_change_async)
```

### 手动重新加载

```python
# 重新加载特定源
await manager.reload_source("main")

# 重新加载所有源
await manager.reload_all()
```

## 配置加密

### 生成加密密钥

```python
from uplifted.extensions import generate_encryption_key

# 生成并保存密钥
key = generate_encryption_key("encryption.key")

# 仅生成密钥（不保存）
key = generate_encryption_key()
```

### 加密敏感配置

```python
from uplifted.extensions import (
    EncryptedConfigLoader,
    JSONConfigLoader,
    load_encryption_key
)

# 加载密钥
key = load_encryption_key("encryption.key")

# 创建加密加载器
base_loader = JSONConfigLoader()
loader = EncryptedConfigLoader(base_loader, key)

# 加密并保存
sensitive_config = {
    "api_keys": {
        "openai": "sk-xxxxx",
        "anthropic": "sk-ant-xxxxx"
    },
    "database": {
        "password": "secret123"
    }
}

loader.save(sensitive_config, "secrets.json.enc")

# 加载并解密
config = loader.load("secrets.json.enc")
```

### 在配置管理器中使用

```python
from uplifted.extensions import (
    ConfigManager,
    ConfigSource,
    ConfigFormat,
    EncryptedConfigLoader,
    JSONConfigLoader,
    load_encryption_key
)

manager = ConfigManager()

# 注册加密加载器
key = load_encryption_key("encryption.key")
base_loader = JSONConfigLoader()
encrypted_loader = EncryptedConfigLoader(base_loader, key)

# 创建自定义格式
from enum import Enum
class CustomFormat(Enum):
    ENCRYPTED_JSON = "encrypted_json"

manager._loaders[CustomFormat.ENCRYPTED_JSON] = encrypted_loader

# 添加加密配置源
manager.add_source(ConfigSource(
    name="secrets",
    path="secrets.json.enc",
    format=CustomFormat.ENCRYPTED_JSON,
    priority=10,
    watch=False,  # 加密文件通常不需要监视
    required=True
))
```

**安全最佳实践**:
1. ✅ 将 `encryption.key` 添加到 `.gitignore`
2. ✅ 使用环境变量或密钥管理服务存储密钥
3. ✅ 为不同环境使用不同密钥
4. ✅ 定期轮换密钥
5. ❌ 永远不要将密钥提交到版本控制

## 配置模板

### 生成标准模板

```python
from uplifted.extensions import generate_config_template

# 默认模板（完整功能）
config = generate_config_template("default", "config.yaml")

# 最小模板（仅必需项）
config = generate_config_template("minimal", "config.yaml")

# 生产环境模板
config = generate_config_template("production", "prod.yaml")

# 开发环境模板
config = generate_config_template("development", "dev.yaml")
```

### 配置导入/导出

```python
from uplifted.extensions import export_config, import_config

# 导入配置
config = import_config("config.yaml")  # 自动检测格式

# 导出为 YAML
export_config(config, "output.yaml", format="yaml")

# 导出为 JSON
export_config(config, "output.json", format="json")

# 导出为 TOML
export_config(config, "output.toml", format="toml")
```

### 配置比较

```python
from uplifted.extensions import compare_configs, import_config

old_config = import_config("config-v1.yaml")
new_config = import_config("config-v2.yaml")

diff = compare_configs(old_config, new_config)

print(f"Added: {diff['added']}")
print(f"Removed: {diff['removed']}")
print(f"Changed: {diff['changed']}")

# Changed 示例:
# {
#   'server.port': {'old': 8080, 'new': 7541},
#   'logging.level': {'old': 'INFO', 'new': 'DEBUG'}
# }
```

### 配置合并

```python
from uplifted.extensions import merge_configs

base = {
    "server": {"host": "localhost", "port": 8080},
    "logging": {"level": "INFO"}
}

override = {
    "server": {"port": 9000},
    "custom": {"feature": "enabled"}
}

# 深度合并（默认）
merged = merge_configs(base, override, deep=True)
# 结果: {
#   "server": {"host": "localhost", "port": 9000},
#   "logging": {"level": "INFO"},
#   "custom": {"feature": "enabled"}
# }

# 浅合并
merged = merge_configs(base, override, deep=False)
# 结果: {
#   "server": {"port": 9000},  # 完全替换
#   "logging": {"level": "INFO"},
#   "custom": {"feature": "enabled"}
# }
```

## 高级用法

### 自定义配置加载器

```python
from uplifted.extensions import ConfigLoader

class CustomConfigLoader(ConfigLoader):
    """自定义配置加载器"""

    def load(self, file_path: str) -> Dict[str, Any]:
        # 实现加载逻辑
        with open(file_path, 'r') as f:
            # ... 解析文件
            pass
        return config

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        # 实现保存逻辑
        try:
            with open(file_path, 'w') as f:
                # ... 写入文件
                pass
            return True
        except:
            return False

    def validate_format(self, file_path: str) -> bool:
        # 实现格式验证
        try:
            self.load(file_path)
            return True
        except:
            return False

# 使用自定义加载器
manager = ConfigManager()
manager._loaders[ConfigFormat.CUSTOM] = CustomConfigLoader()
```

### 配置继承和覆盖

```python
# base.yaml
server:
  host: localhost
  port: 8080
  workers: 4

# production.yaml (继承 base.yaml)
# 使用 merge_configs 实现继承
from uplifted.extensions import import_config, merge_configs

base = import_config("config/base.yaml")
prod_overrides = import_config("config/production.yaml")

final_config = merge_configs(base, prod_overrides)
```

### 配置 Schema 验证

```python
from uplifted.extensions import validate_config_schema

# 定义 JSON Schema
schema = {
    "type": "object",
    "properties": {
        "server": {
            "type": "object",
            "properties": {
                "port": {
                    "type": "integer",
                    "minimum": 1024,
                    "maximum": 65535
                },
                "host": {"type": "string"}
            },
            "required": ["port", "host"]
        }
    },
    "required": ["server"]
}

# 验证配置
config = {"server": {"port": 8080, "host": "localhost"}}
valid, errors = validate_config_schema(config, schema)

if valid:
    print("✓ Configuration is valid")
else:
    print("✗ Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

## 最佳实践

### 1. 配置文件组织

```
project/
├── config/
│   ├── defaults.yaml       # 默认配置
│   ├── development.yaml    # 开发环境
│   ├── staging.yaml        # 测试环境
│   ├── production.yaml     # 生产环境
│   ├── local.yaml          # 本地覆盖（不提交）
│   └── secrets.json.enc    # 加密敏感信息
├── .env                    # 环境变量（不提交）
├── .env.example            # 环境变量模板
└── .gitignore              # 忽略 local.yaml, .env, *.key
```

### 2. 配置优先级策略

```
优先级（从高到低）:
1. 命令行参数（如果实现）
2. 环境变量
3. local.yaml（本地覆盖）
4. {environment}.yaml（环境特定）
5. defaults.yaml（默认值）
```

### 3. 敏感信息处理

```python
# ✅ 推荐：使用加密配置
from uplifted.extensions import EncryptedConfigLoader

# ✅ 推荐：使用环境变量
os.environ["DATABASE_PASSWORD"] = "secret"

# ❌ 不推荐：明文存储密码
config = {"database": {"password": "secret"}}  # 不要这样做
```

### 4. 环境特定配置

```python
import os
from uplifted.extensions import ConfigManager, ConfigSource, ConfigFormat

# 根据环境加载不同配置
env = os.getenv("UPLIFTED_ENV", "development")

manager = ConfigManager()

# 加载默认配置
manager.add_source(ConfigSource(
    name="defaults",
    path="config/defaults.yaml",
    format=ConfigFormat.YAML,
    priority=100
))

# 加载环境特定配置
manager.add_source(ConfigSource(
    name="environment",
    path=f"config/{env}.yaml",
    format=ConfigFormat.YAML,
    priority=50,
    required=False
))

# 加载本地覆盖
manager.add_source(ConfigSource(
    name="local",
    path="config/local.yaml",
    format=ConfigFormat.YAML,
    priority=10,
    required=False
))

await manager.load_all()
```

### 5. 配置验证最佳实践

```python
# 为关键配置添加验证
manager.add_validation_rule(ConfigValidationRule(
    path="server.port",
    required=True,
    type_check=int,
    validator=lambda v: 1024 <= v <= 65535,
    default_value=8080,
    description="Server port (1024-65535)"
))

manager.add_validation_rule(ConfigValidationRule(
    path="database.url",
    required=True,
    type_check=str,
    validator=lambda v: v.startswith("sqlite://") or v.startswith("postgresql://"),
    description="Valid database URL"
))
```

### 6. 配置文档化

在配置文件中添加注释：

```yaml
# Uplifted Server Configuration
# Generated: 2025-10-28

# Server settings
server:
  host: "0.0.0.0"           # Listen on all interfaces
  port: 7541                # Main API port (1024-65535)
  workers: 4                # Number of worker processes
  reload: false             # Hot reload (dev only)

# Database settings
database:
  path: "./data/uplifted.db"  # SQLite database path
  pool_size: 10                # Connection pool size
  timeout: 30                  # Query timeout (seconds)

# Plugin settings
plugins:
  enabled: true             # Enable plugin system
  auto_load: true           # Auto-load on startup
  directories:              # Plugin search paths
    - "./plugins"
    - "~/.uplifted/plugins"
```

### 7. 配置测试

```python
import pytest
from uplifted.extensions import ConfigManager, generate_config_template

def test_config_loading():
    """测试配置加载"""
    manager = ConfigManager()
    # ... 添加配置源
    assert await manager.load_all()

def test_config_validation():
    """测试配置验证"""
    manager = ConfigManager()
    # ... 添加验证规则
    # ... 测试有效和无效配置

def test_config_templates():
    """测试配置模板"""
    config = generate_config_template("default")
    assert "server" in config
    assert "database" in config
```

## 相关文档

- [配置示例](../examples/config_management_example.py)
- [插件配置](../examples/plugins/hello_world/manifest.json)
- [服务器配置](../config/production.yaml)

## 支持

- GitHub Issues: https://github.com/uplifted/uplifted/issues
- 文档: https://uplifted.ai/docs
- 示例: `examples/config_management_example.py`
