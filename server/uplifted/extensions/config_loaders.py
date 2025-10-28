"""
高级配置加载器

扩展配置加载器，支持环境变量、SQLite、加密配置等。

提供的加载器:
- EnvConfigLoader: 环境变量加载器
- SQLiteConfigLoader: SQLite 数据库配置加载器
- EncryptedConfigLoader: 加密配置加载器（装饰器模式）
- TOMLConfigLoader: TOML 配置加载器
- INIConfigLoader: INI 配置加载器

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import os
import sqlite3
import configparser
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading
from contextlib import contextmanager

from .config_manager import ConfigLoader

# 尝试导入可选依赖
try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class EnvConfigLoader(ConfigLoader):
    """
    环境变量配置加载器

    从环境变量加载配置，支持前缀过滤和类型转换。

    使用示例:
        # 加载所有 UPLIFTED_ 开头的环境变量
        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load("")

        # 环境变量 UPLIFTED_DATABASE_HOST=localhost
        # 转换为: {"database": {"host": "localhost"}}

    特性:
        - 自动类型推断（字符串、数字、布尔值）
        - 分隔符支持（__ 转换为嵌套结构）
        - 前缀过滤
        - 大小写转换
    """

    def __init__(self,
                 prefix: str = "",
                 separator: str = "__",
                 lowercase_keys: bool = True):
        """
        初始化环境变量加载器

        参数:
            prefix: 环境变量前缀（如 "UPLIFTED_"）
            separator: 嵌套分隔符（如 "__" 表示嵌套）
            lowercase_keys: 是否将键转换为小写
        """
        self.prefix = prefix
        self.separator = separator
        self.lowercase_keys = lowercase_keys

    def load(self, file_path: str = "") -> Dict[str, Any]:
        """
        从环境变量加载配置

        参数:
            file_path: 未使用（环境变量加载器不需要文件路径）

        返回:
            配置字典
        """
        config = {}

        for key, value in os.environ.items():
            # 检查前缀
            if self.prefix and not key.startswith(self.prefix):
                continue

            # 移除前缀
            config_key = key[len(self.prefix):] if self.prefix else key

            # 转换为小写
            if self.lowercase_keys:
                config_key = config_key.lower()

            # 处理嵌套键
            if self.separator in config_key:
                keys = config_key.split(self.separator)
                self._set_nested_value(config, keys, self._parse_value(value))
            else:
                config[config_key] = self._parse_value(value)

        return config

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        保存配置（环境变量不支持保存）

        返回:
            False（环境变量加载器不支持保存）
        """
        return False

    def validate_format(self, file_path: str) -> bool:
        """
        验证格式（环境变量总是有效的）

        返回:
            True
        """
        return True

    def _parse_value(self, value: str) -> Any:
        """
        解析值类型

        支持:
        - 布尔值: "true", "false" (大小写不敏感)
        - 整数: "123"
        - 浮点数: "123.45"
        - JSON 数组/对象: '["a","b"]', '{"key":"value"}'
        - 字符串: 其他所有值
        """
        # 布尔值
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False

        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON
        if value.startswith(('[', '{')):
            try:
                import json
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # JSON 解析失败，继续作为字符串处理
                pass

        # 字符串
        return value

    def _set_nested_value(self, data: Dict[str, Any], keys: List[str], value: Any) -> None:
        """设置嵌套字典值"""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


class SQLiteConfigLoader(ConfigLoader):
    """
    SQLite 配置加载器

    从 SQLite 数据库加载和保存配置。

    数据库结构:
        CREATE TABLE config_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

    使用示例:
        loader = SQLiteConfigLoader(db_path="config.db")
        config = loader.load("config.db")
        loader.save(config, "config.db")

    特性:
        - 线程安全
        - 自动创建数据库和表
        - JSON 序列化存储
        - 时间戳记录
    """

    def __init__(self, table_name: str = "config_store"):
        """
        初始化 SQLite 配置加载器

        参数:
            table_name: 配置表名
        """
        self.table_name = table_name
        self._local = threading.local()

    @contextmanager
    def _get_connection(self, db_path: str):
        """获取数据库连接（线程局部）"""
        if not hasattr(self._local, 'connections'):
            self._local.connections = {}

        if db_path not in self._local.connections:
            conn = sqlite3.connect(db_path)
            self._local.connections[db_path] = conn
            self._setup_database(conn)

        try:
            yield self._local.connections[db_path]
        except sqlite3.Error as e:
            raise ValueError(f"SQLite error: {e}")

    def _setup_database(self, conn: sqlite3.Connection) -> None:
        """创建数据库表"""
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

    def load(self, file_path: str) -> Dict[str, Any]:
        """
        从 SQLite 加载配置

        参数:
            file_path: 数据库文件路径

        返回:
            配置字典
        """
        import json

        if not os.path.exists(file_path):
            return {}

        config = {}

        with self._get_connection(file_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT key, value FROM {self.table_name}')
            rows = cursor.fetchall()

            for key, value_json in rows:
                try:
                    value = json.loads(value_json)

                    # 支持嵌套键（如 "database.host"）
                    if '.' in key:
                        keys = key.split('.')
                        self._set_nested_value(config, keys, value)
                    else:
                        config[key] = value
                except json.JSONDecodeError:
                    # 如果不是 JSON，存储为字符串
                    config[key] = value_json

        return config

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        保存配置到 SQLite

        参数:
            data: 配置字典
            file_path: 数据库文件路径

        返回:
            是否成功
        """
        import json

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

            # 扁平化配置
            flat_config = self._flatten_dict(data)

            with self._get_connection(file_path) as conn:
                cursor = conn.cursor()

                for key, value in flat_config.items():
                    value_json = json.dumps(value)
                    cursor.execute(
                        f'REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)',
                        (key, value_json)
                    )

                conn.commit()

            return True

        except Exception:
            return False

    def validate_format(self, file_path: str) -> bool:
        """
        验证数据库格式

        参数:
            file_path: 数据库文件路径

        返回:
            是否有效
        """
        if not os.path.exists(file_path):
            return True  # 不存在的文件将被创建

        try:
            with self._get_connection(file_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                ''', (self.table_name,))
                return cursor.fetchone() is not None
        except (sqlite3.Error, OSError, ValueError) as e:
            # 数据库错误、文件访问错误或值错误
            return False

    def _flatten_dict(self, data: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """扁平化嵌套字典"""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key).items())
            else:
                items.append((new_key, value))

        return dict(items)

    def _set_nested_value(self, data: Dict[str, Any], keys: List[str], value: Any) -> None:
        """设置嵌套字典值"""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


class TOMLConfigLoader(ConfigLoader):
    """
    TOML 配置加载器

    需要安装: pip install toml

    使用示例:
        loader = TOMLConfigLoader()
        config = loader.load("config.toml")
    """

    def load(self, file_path: str) -> Dict[str, Any]:
        """加载 TOML 配置"""
        if not TOML_AVAILABLE:
            raise ImportError("toml package is not installed. Install with: pip install toml")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load TOML config from {file_path}: {e}")

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """保存 TOML 配置"""
        if not TOML_AVAILABLE:
            return False

        try:
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                toml.dump(data, f)
            return True
        except (OSError, IOError, TypeError) as e:
            # 文件操作错误或序列化错误
            return False

    def validate_format(self, file_path: str) -> bool:
        """验证 TOML 格式"""
        if not TOML_AVAILABLE:
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                toml.load(f)
            return True
        except (OSError, IOError, ValueError) as e:
            # 文件访问错误或TOML解析错误
            return False


class INIConfigLoader(ConfigLoader):
    """
    INI 配置加载器

    使用示例:
        loader = INIConfigLoader()
        config = loader.load("config.ini")
        # 结果: {"section1": {"key1": "value1"}, ...}
    """

    def load(self, file_path: str) -> Dict[str, Any]:
        """加载 INI 配置"""
        try:
            parser = configparser.ConfigParser()
            parser.read(file_path, encoding='utf-8')

            config = {}
            for section in parser.sections():
                config[section] = dict(parser[section])

            return config
        except Exception as e:
            raise ValueError(f"Failed to load INI config from {file_path}: {e}")

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """保存 INI 配置"""
        try:
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

            parser = configparser.ConfigParser()

            for section, values in data.items():
                if isinstance(values, dict):
                    parser[section] = {k: str(v) for k, v in values.items()}

            with open(file_path, 'w', encoding='utf-8') as f:
                parser.write(f)

            return True
        except (OSError, IOError, configparser.Error) as e:
            # 文件操作错误或INI格式错误
            return False

    def validate_format(self, file_path: str) -> bool:
        """验证 INI 格式"""
        try:
            parser = configparser.ConfigParser()
            parser.read(file_path, encoding='utf-8')
            return True
        except (OSError, IOError, configparser.Error) as e:
            # 文件访问错误或INI解析错误
            return False


class EncryptedConfigLoader(ConfigLoader):
    """
    加密配置加载器（装饰器模式）

    装饰其他加载器，添加加密/解密功能。

    需要安装: pip install cryptography

    使用示例:
        # 生成密钥
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()

        # 创建加密加载器
        base_loader = JSONConfigLoader()
        loader = EncryptedConfigLoader(base_loader, key)

        # 保存加密配置
        loader.save({"secret": "password"}, "config.json.enc")

        # 加载解密配置
        config = loader.load("config.json.enc")
    """

    def __init__(self, base_loader: ConfigLoader, encryption_key: bytes):
        """
        初始化加密配置加载器

        参数:
            base_loader: 基础加载器
            encryption_key: 加密密钥（使用 Fernet.generate_key() 生成）
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography package is not installed. "
                "Install with: pip install cryptography"
            )

        self.base_loader = base_loader
        self.cipher = Fernet(encryption_key)

    def load(self, file_path: str) -> Dict[str, Any]:
        """加载并解密配置"""
        import json

        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            # 解密
            decrypted_data = self.cipher.decrypt(encrypted_data)

            # 解析 JSON
            return json.loads(decrypted_data.decode('utf-8'))

        except Exception as e:
            raise ValueError(f"Failed to load encrypted config from {file_path}: {e}")

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """加密并保存配置"""
        import json

        try:
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

            # 序列化为 JSON
            json_data = json.dumps(data, indent=2, ensure_ascii=False)

            # 加密
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))

            # 保存
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)

            return True
        except (OSError, IOError, Exception) as e:
            # 文件操作错误或加密错误
            return False

    def validate_format(self, file_path: str) -> bool:
        """验证加密文件格式"""
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            # 尝试解密
            self.cipher.decrypt(encrypted_data)
            return True
        except (OSError, IOError, Exception) as e:
            # 文件访问错误或解密错误
            return False


# 导出所有加载器
__all__ = [
    'EnvConfigLoader',
    'SQLiteConfigLoader',
    'TOMLConfigLoader',
    'INIConfigLoader',
    'EncryptedConfigLoader',
    'TOML_AVAILABLE',
    'CRYPTO_AVAILABLE'
]
