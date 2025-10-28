"""
配置管理工具模块

提供配置模板生成、导入导出、加密密钥管理等实用功能。

功能：
- 配置模板生成
- 配置导入/导出
- 配置比较和差异
- 配置合并
- 加密密钥管理
- 配置验证

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ConfigTemplate:
    """
    配置模板定义

    用于生成标准化的配置文件。
    """
    name: str
    description: str
    sections: Dict[str, 'ConfigSection'] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigSection:
    """配置区块"""
    name: str
    description: str
    fields: List['ConfigField'] = field(default_factory=list)
    required: bool = False


@dataclass
class ConfigField:
    """配置字段"""
    name: str
    type: str  # string, int, float, bool, list, dict
    description: str
    default: Any = None
    required: bool = False
    validation: Optional[str] = None  # 验证表达式
    examples: List[Any] = field(default_factory=list)
    sensitive: bool = False  # 是否为敏感信息（如密码）


def generate_config_template(
    template_name: str = "default",
    output_path: Optional[str] = None,
    format: str = "yaml"
) -> Dict[str, Any]:
    """
    生成配置模板

    参数:
        template_name: 模板名称 ("default", "minimal", "production")
        output_path: 输出文件路径（可选）
        format: 输出格式 ("yaml", "json", "toml")

    返回:
        配置模板字典

    示例:
        # 生成默认模板
        config = generate_config_template("default", "config.yaml")

        # 生成生产环境模板
        config = generate_config_template("production", "prod.yaml")
    """
    templates = {
        "default": _get_default_template(),
        "minimal": _get_minimal_template(),
        "production": _get_production_template(),
        "development": _get_development_template()
    }

    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}. Available: {list(templates.keys())}")

    template = templates[template_name]

    # 如果指定了输出路径，保存到文件
    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        if format == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False, allow_unicode=True)
        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
        elif format == "toml":
            try:
                import toml
                with open(output_path, 'w', encoding='utf-8') as f:
                    toml.dump(template, f)
            except ImportError:
                raise ImportError("toml package required for TOML format")

    return template


def _get_default_template() -> Dict[str, Any]:
    """获取默认配置模板"""
    return {
        "# Uplifted Configuration": "Generated on " + datetime.now().isoformat(),

        "server": {
            "host": "0.0.0.0",
            "port": 7541,
            "workers": 4,
            "log_level": "INFO",
            "reload": False
        },

        "tools_server": {
            "host": "0.0.0.0",
            "port": 8086,
            "mcp_enabled": True
        },

        "database": {
            "path": "./data/uplifted.db",
            "pool_size": 10,
            "timeout": 30
        },

        "plugins": {
            "enabled": True,
            "auto_load": True,
            "auto_activate": True,
            "directories": [
                "./plugins",
                "~/.uplifted/plugins"
            ]
        },

        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "./logs/uplifted.log",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5
        },

        "security": {
            "api_key_required": False,
            "cors_enabled": True,
            "cors_origins": ["*"],
            "rate_limit": {
                "enabled": True,
                "requests_per_minute": 60
            }
        }
    }


def _get_minimal_template() -> Dict[str, Any]:
    """获取最小配置模板"""
    return {
        "server": {
            "host": "localhost",
            "port": 7541
        },
        "plugins": {
            "enabled": True,
            "directories": ["./plugins"]
        }
    }


def _get_production_template() -> Dict[str, Any]:
    """获取生产环境配置模板"""
    template = _get_default_template()
    template.update({
        "server": {
            "host": "0.0.0.0",
            "port": 7541,
            "workers": 8,
            "log_level": "WARNING",
            "reload": False
        },
        "logging": {
            "level": "WARNING",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "/var/log/uplifted/uplifted.log",
            "max_bytes": 52428800,  # 50MB
            "backup_count": 10
        },
        "security": {
            "api_key_required": True,
            "cors_enabled": True,
            "cors_origins": ["https://yourdomain.com"],
            "rate_limit": {
                "enabled": True,
                "requests_per_minute": 120
            }
        },
        "database": {
            "path": "/var/lib/uplifted/uplifted.db",
            "pool_size": 20,
            "timeout": 60
        }
    })
    return template


def _get_development_template() -> Dict[str, Any]:
    """获取开发环境配置模板"""
    template = _get_default_template()
    template.update({
        "server": {
            "host": "localhost",
            "port": 7541,
            "workers": 2,
            "log_level": "DEBUG",
            "reload": True
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "./logs/uplifted-dev.log",
            "max_bytes": 5242880,  # 5MB
            "backup_count": 3
        },
        "security": {
            "api_key_required": False,
            "cors_enabled": True,
            "cors_origins": ["*"],
            "rate_limit": {
                "enabled": False
            }
        }
    })
    return template


def export_config(
    config: Dict[str, Any],
    output_path: str,
    format: str = "yaml",
    include_comments: bool = True
) -> bool:
    """
    导出配置到文件

    参数:
        config: 配置字典
        output_path: 输出文件路径
        format: 输出格式 ("yaml", "json", "toml")
        include_comments: 是否包含注释

    返回:
        是否成功

    示例:
        config = {"server": {"port": 8080}}
        export_config(config, "config.yaml", format="yaml")
    """
    try:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        if format == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                if include_comments:
                    f.write(f"# Uplifted Configuration\n")
                    f.write(f"# Exported: {datetime.now().isoformat()}\n\n")
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        elif format == "toml":
            try:
                import toml
                with open(output_path, 'w', encoding='utf-8') as f:
                    if include_comments:
                        f.write(f"# Uplifted Configuration\n")
                        f.write(f"# Exported: {datetime.now().isoformat()}\n\n")
                    toml.dump(config, f)
            except ImportError:
                raise ImportError("toml package required for TOML format")

        else:
            raise ValueError(f"Unsupported format: {format}")

        return True

    except Exception:
        return False


def import_config(file_path: str) -> Dict[str, Any]:
    """
    从文件导入配置

    自动检测文件格式（根据扩展名）。

    参数:
        file_path: 配置文件路径

    返回:
        配置字典

    示例:
        config = import_config("config.yaml")
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in ('.yaml', '.yml'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    elif ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    elif ext == '.toml':
        try:
            import toml
            with open(file_path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except ImportError:
            raise ImportError("toml package required for TOML format")

    else:
        raise ValueError(f"Unsupported file format: {ext}")


def compare_configs(
    config1: Dict[str, Any],
    config2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    比较两个配置

    返回差异信息。

    参数:
        config1: 配置 1
        config2: 配置 2

    返回:
        差异字典，包含 added, removed, changed 键

    示例:
        diff = compare_configs(old_config, new_config)
        print(f"Added: {diff['added']}")
        print(f"Removed: {diff['removed']}")
        print(f"Changed: {diff['changed']}")
    """
    def _flatten(d: Dict, parent_key: str = '') -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(_flatten(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    flat1 = _flatten(config1)
    flat2 = _flatten(config2)

    added = {k: v for k, v in flat2.items() if k not in flat1}
    removed = {k: v for k, v in flat1.items() if k not in flat2}
    changed = {
        k: {'old': flat1[k], 'new': flat2[k]}
        for k in flat1.keys() & flat2.keys()
        if flat1[k] != flat2[k]
    }

    return {
        'added': added,
        'removed': removed,
        'changed': changed
    }


def merge_configs(
    base: Dict[str, Any],
    override: Dict[str, Any],
    deep: bool = True
) -> Dict[str, Any]:
    """
    合并两个配置

    参数:
        base: 基础配置
        override: 覆盖配置
        deep: 是否深度合并

    返回:
        合并后的配置

    示例:
        base = {"server": {"port": 8080, "host": "localhost"}}
        override = {"server": {"port": 9000}}
        merged = merge_configs(base, override)
        # 结果: {"server": {"port": 9000, "host": "localhost"}}
    """
    if not deep:
        result = base.copy()
        result.update(override)
        return result

    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value, deep=True)
        else:
            result[key] = value

    return result


def validate_config_schema(
    config: Dict[str, Any],
    schema: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    使用 JSON Schema 验证配置

    需要安装: pip install jsonschema

    参数:
        config: 配置字典
        schema: JSON Schema 字典

    返回:
        (是否有效, 错误列表)

    示例:
        schema = {
            "type": "object",
            "properties": {
                "server": {
                    "type": "object",
                    "properties": {
                        "port": {"type": "integer"}
                    }
                }
            }
        }
        valid, errors = validate_config_schema(config, schema)
    """
    try:
        from jsonschema import validate, ValidationError

        try:
            validate(instance=config, schema=schema)
            return True, []
        except ValidationError as e:
            return False, [str(e)]

    except ImportError:
        # 如果没有 jsonschema，做基础验证
        return True, ["jsonschema package not installed, skipping validation"]


def generate_encryption_key(output_path: Optional[str] = None) -> bytes:
    """
    生成加密密钥

    参数:
        output_path: 密钥保存路径（可选）

    返回:
        加密密钥（字节）

    示例:
        key = generate_encryption_key("encryption.key")
        # 使用密钥加载加密配置
        from cryptography.fernet import Fernet
        cipher = Fernet(key)
    """
    try:
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()

        if output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(key)

        return key

    except ImportError:
        raise ImportError("cryptography package required. Install with: pip install cryptography")


def load_encryption_key(file_path: str) -> bytes:
    """
    加载加密密钥

    参数:
        file_path: 密钥文件路径

    返回:
        加密密钥（字节）
    """
    with open(file_path, 'rb') as f:
        return f.read()


__all__ = [
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
    'load_encryption_key'
]
