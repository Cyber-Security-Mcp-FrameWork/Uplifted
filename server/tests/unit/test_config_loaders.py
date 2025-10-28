"""
配置加载器单元测试

测试所有高级配置加载器：
- EnvConfigLoader: 环境变量加载器
- SQLiteConfigLoader: SQLite 配置加载器
- TOMLConfigLoader: TOML 配置加载器
- INIConfigLoader: INI 配置加载器
- EncryptedConfigLoader: 加密配置加载器
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, Any

from uplifted.extensions.config_loaders import (
    EnvConfigLoader,
    SQLiteConfigLoader,
    TOML_AVAILABLE,
    CRYPTO_AVAILABLE
)

# 条件导入
if TOML_AVAILABLE:
    from uplifted.extensions.config_loaders import TOMLConfigLoader

if CRYPTO_AVAILABLE:
    from uplifted.extensions.config_loaders import EncryptedConfigLoader
    from cryptography.fernet import Fernet


class TestEnvConfigLoader:
    """环境变量配置加载器测试"""

    def setup_method(self):
        """设置测试环境变量"""
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """恢复原始环境变量"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_load_basic(self):
        """测试基本加载"""
        os.environ["UPLIFTED_KEY1"] = "value1"
        os.environ["UPLIFTED_KEY2"] = "value2"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["key1"] == "value1"
        assert config["key2"] == "value2"

    def test_load_without_prefix(self):
        """测试无前缀加载"""
        os.environ["KEY1"] = "value1"
        os.environ["KEY2"] = "value2"

        loader = EnvConfigLoader(prefix="")
        config = loader.load()

        assert "KEY1" in config or "key1" in config

    def test_nested_keys(self):
        """测试嵌套键"""
        os.environ["UPLIFTED_DATABASE__HOST"] = "localhost"
        os.environ["UPLIFTED_DATABASE__PORT"] = "5432"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert "database" in config
        assert config["database"]["host"] == "localhost"
        assert config["database"]["port"] == 5432

    def test_boolean_values(self):
        """测试布尔值解析"""
        os.environ["UPLIFTED_BOOL_TRUE1"] = "true"
        os.environ["UPLIFTED_BOOL_TRUE2"] = "yes"
        os.environ["UPLIFTED_BOOL_TRUE3"] = "1"
        os.environ["UPLIFTED_BOOL_FALSE1"] = "false"
        os.environ["UPLIFTED_BOOL_FALSE2"] = "no"
        os.environ["UPLIFTED_BOOL_FALSE3"] = "0"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["bool_true1"] is True
        assert config["bool_true2"] is True
        assert config["bool_true3"] is True
        assert config["bool_false1"] is False
        assert config["bool_false2"] is False
        assert config["bool_false3"] is False

    def test_integer_values(self):
        """测试整数解析"""
        os.environ["UPLIFTED_INT1"] = "123"
        os.environ["UPLIFTED_INT2"] = "-456"
        os.environ["UPLIFTED_INT3"] = "0"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["int1"] == 123
        assert config["int2"] == -456
        assert config["int3"] == 0
        assert isinstance(config["int1"], int)

    def test_float_values(self):
        """测试浮点数解析"""
        os.environ["UPLIFTED_FLOAT1"] = "123.45"
        os.environ["UPLIFTED_FLOAT2"] = "-67.89"
        os.environ["UPLIFTED_FLOAT3"] = "0.0"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["float1"] == 123.45
        assert config["float2"] == -67.89
        assert config["float3"] == 0.0
        assert isinstance(config["float1"], float)

    def test_json_values(self):
        """测试 JSON 解析"""
        os.environ["UPLIFTED_JSON_ARRAY"] = '["a","b","c"]'
        os.environ["UPLIFTED_JSON_OBJECT"] = '{"key":"value"}'

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["json_array"] == ["a", "b", "c"]
        assert config["json_object"] == {"key": "value"}

    def test_string_values(self):
        """测试字符串值"""
        os.environ["UPLIFTED_STR1"] = "hello world"
        os.environ["UPLIFTED_STR2"] = "path/to/file"

        loader = EnvConfigLoader(prefix="UPLIFTED_")
        config = loader.load()

        assert config["str1"] == "hello world"
        assert config["str2"] == "path/to/file"

    def test_lowercase_keys(self):
        """测试键小写转换"""
        os.environ["UPLIFTED_UPPERCASE_KEY"] = "value"

        loader = EnvConfigLoader(prefix="UPLIFTED_", lowercase_keys=True)
        config = loader.load()

        assert "uppercase_key" in config
        assert config["uppercase_key"] == "value"

    def test_preserve_case(self):
        """测试保留大小写"""
        os.environ["UPLIFTED_MixedCase"] = "value"

        loader = EnvConfigLoader(prefix="UPLIFTED_", lowercase_keys=False)
        config = loader.load()

        assert "MixedCase" in config

    def test_custom_separator(self):
        """测试自定义分隔符"""
        os.environ["UPLIFTED_DB-HOST"] = "localhost"
        os.environ["UPLIFTED_DB-PORT"] = "5432"

        loader = EnvConfigLoader(prefix="UPLIFTED_", separator="-")
        config = loader.load()

        assert "db" in config
        assert config["db"]["host"] == "localhost"

    def test_save_not_supported(self):
        """测试保存操作（不支持）"""
        loader = EnvConfigLoader()
        result = loader.save({}, "")

        assert result is False

    def test_validate_format(self):
        """测试格式验证"""
        loader = EnvConfigLoader()

        assert loader.validate_format("") is True


class TestSQLiteConfigLoader:
    """SQLite 配置加载器测试"""

    def setup_method(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_config.db")

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_database(self):
        """测试创建数据库"""
        loader = SQLiteConfigLoader()
        config = loader.load(self.db_path)

        assert config == {}
        assert os.path.exists(self.db_path)

    def test_save_and_load_basic(self):
        """测试基本保存和加载"""
        loader = SQLiteConfigLoader()

        test_data = {
            "key1": "value1",
            "key2": 123,
            "key3": True
        }

        # 保存
        result = loader.save(test_data, self.db_path)
        assert result is True

        # 加载
        loaded_data = loader.load(self.db_path)

        assert loaded_data["key1"] == "value1"
        assert loaded_data["key2"] == 123
        assert loaded_data["key3"] is True

    def test_save_nested_config(self):
        """测试保存嵌套配置"""
        loader = SQLiteConfigLoader()

        test_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "admin",
                    "password": "secret"
                }
            },
            "cache": {
                "enabled": True,
                "ttl": 300
            }
        }

        # 保存
        loader.save(test_data, self.db_path)

        # 加载
        loaded_data = loader.load(self.db_path)

        assert loaded_data["database"]["host"] == "localhost"
        assert loaded_data["database"]["port"] == 5432
        assert loaded_data["database"]["credentials"]["username"] == "admin"
        assert loaded_data["cache"]["enabled"] is True

    def test_update_existing_key(self):
        """测试更新现有键"""
        loader = SQLiteConfigLoader()

        # 初始保存
        loader.save({"key1": "value1"}, self.db_path)

        # 更新
        loader.save({"key1": "updated_value"}, self.db_path)

        # 验证
        loaded_data = loader.load(self.db_path)
        assert loaded_data["key1"] == "updated_value"

    def test_complex_data_types(self):
        """测试复杂数据类型"""
        loader = SQLiteConfigLoader()

        test_data = {
            "list": [1, 2, 3, "four", True],
            "dict": {"nested": {"deep": "value"}},
            "mixed": [{"a": 1}, {"b": 2}]
        }

        loader.save(test_data, self.db_path)
        loaded_data = loader.load(self.db_path)

        assert loaded_data["list"] == [1, 2, 3, "four", True]
        assert loaded_data["dict"]["nested"]["deep"] == "value"
        assert loaded_data["mixed"][0]["a"] == 1

    def test_custom_table_name(self):
        """测试自定义表名"""
        loader = SQLiteConfigLoader(table_name="custom_config")

        loader.save({"key": "value"}, self.db_path)

        # 验证表存在
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='custom_config'")
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_thread_safety(self):
        """测试线程安全"""
        import threading

        loader = SQLiteConfigLoader()

        def save_data(thread_id):
            data = {f"thread_{thread_id}": thread_id}
            loader.save(data, self.db_path)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_data, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证数据
        loaded_data = loader.load(self.db_path)
        for i in range(5):
            assert f"thread_{i}" in loaded_data

    def test_validate_format(self):
        """测试格式验证"""
        loader = SQLiteConfigLoader()

        # SQLite 文件
        assert loader.validate_format(self.db_path) is True

        # 非 SQLite 文件
        text_file = os.path.join(self.temp_dir, "test.txt")
        with open(text_file, 'w') as f:
            f.write("not a database")

        assert loader.validate_format(text_file) is False

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        loader = SQLiteConfigLoader()

        config = loader.load("nonexistent.db")
        assert config == {}


@pytest.mark.skipif(not TOML_AVAILABLE, reason="TOML not available")
class TestTOMLConfigLoader:
    """TOML 配置加载器测试"""

    def setup_method(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.toml_path = os.path.join(self.temp_dir, "test_config.toml")

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_basic_toml(self):
        """测试加载基本 TOML"""
        toml_content = """
title = "Test Config"
debug = true
port = 8080

[database]
host = "localhost"
port = 5432
"""

        with open(self.toml_path, 'w') as f:
            f.write(toml_content)

        loader = TOMLConfigLoader()
        config = loader.load(self.toml_path)

        assert config["title"] == "Test Config"
        assert config["debug"] is True
        assert config["port"] == 8080
        assert config["database"]["host"] == "localhost"
        assert config["database"]["port"] == 5432

    def test_save_toml(self):
        """测试保存 TOML"""
        loader = TOMLConfigLoader()

        test_data = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000
            }
        }

        result = loader.save(test_data, self.toml_path)
        assert result is True

        # 验证文件内容
        loaded_data = loader.load(self.toml_path)
        assert loaded_data["app"]["name"] == "TestApp"
        assert loaded_data["server"]["port"] == 8000

    def test_validate_format(self):
        """测试格式验证"""
        loader = TOMLConfigLoader()

        # 有效 TOML
        valid_toml = """
key = "value"
"""
        with open(self.toml_path, 'w') as f:
            f.write(valid_toml)

        assert loader.validate_format(self.toml_path) is True

        # 无效 TOML
        invalid_toml = """
[section
invalid
"""
        with open(self.toml_path, 'w') as f:
            f.write(invalid_toml)

        assert loader.validate_format(self.toml_path) is False


@pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="Cryptography not available")
class TestEncryptedConfigLoader:
    """加密配置加载器测试"""

    def setup_method(self):
        """创建临时目录和加密密钥"""
        self.temp_dir = tempfile.mkdtemp()
        self.encrypted_path = os.path.join(self.temp_dir, "encrypted_config.enc")

        # 生成加密密钥
        self.key = Fernet.generate_key()

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_encrypt_and_decrypt(self):
        """测试加密和解密"""
        from uplifted.extensions.config_loaders import JSONConfigLoader

        # 创建加密加载器（装饰 JSON 加载器）
        base_loader = JSONConfigLoader()
        encrypted_loader = EncryptedConfigLoader(base_loader, self.key)

        test_data = {
            "secret_key": "very_secret",
            "database_password": "db_password_123",
            "nested": {
                "api_token": "token_xyz"
            }
        }

        # 保存加密数据
        result = encrypted_loader.save(test_data, self.encrypted_path)
        assert result is True

        # 验证文件是加密的（不是纯文本）
        with open(self.encrypted_path, 'rb') as f:
            content = f.read()
            # 加密内容不应包含明文
            assert b"very_secret" not in content
            assert b"db_password_123" not in content

        # 加载并解密
        decrypted_data = encrypted_loader.load(self.encrypted_path)

        assert decrypted_data["secret_key"] == "very_secret"
        assert decrypted_data["database_password"] == "db_password_123"
        assert decrypted_data["nested"]["api_token"] == "token_xyz"

    def test_wrong_key(self):
        """测试使用错误的密钥解密"""
        from uplifted.extensions.config_loaders import JSONConfigLoader

        # 使用密钥1加密
        base_loader = JSONConfigLoader()
        encrypted_loader1 = EncryptedConfigLoader(base_loader, self.key)

        test_data = {"secret": "value"}
        encrypted_loader1.save(test_data, self.encrypted_path)

        # 使用密钥2尝试解密
        wrong_key = Fernet.generate_key()
        encrypted_loader2 = EncryptedConfigLoader(base_loader, wrong_key)

        with pytest.raises(Exception):  # Fernet 会抛出异常
            encrypted_loader2.load(self.encrypted_path)

    def test_encryption_with_different_base_loaders(self):
        """测试不同基础加载器的加密"""
        from uplifted.extensions.config_loaders import JSONConfigLoader
        import json

        # JSON 加载器 + 加密
        json_loader = JSONConfigLoader()
        encrypted_json = EncryptedConfigLoader(json_loader, self.key)

        test_data = {"key": "value", "number": 123}

        # 保存和加载
        encrypted_json.save(test_data, self.encrypted_path)
        loaded_data = encrypted_json.load(self.encrypted_path)

        assert loaded_data == test_data


@pytest.mark.unit
@pytest.mark.config
class TestConfigLoadersIntegration:
    """配置加载器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()

    def teardown_method(self):
        """清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        os.environ.clear()
        os.environ.update(self.original_env)

    def test_multi_loader_scenario(self):
        """测试多加载器场景"""
        # 场景：从环境变量加载基础配置，从 SQLite 加载详细配置

        # 1. 环境变量设置
        os.environ["UPLIFTED_DEBUG"] = "true"
        os.environ["UPLIFTED_LOG_LEVEL"] = "INFO"

        env_loader = EnvConfigLoader(prefix="UPLIFTED_")
        env_config = env_loader.load()

        assert env_config["debug"] is True
        assert env_config["log_level"] == "INFO"

        # 2. SQLite 详细配置
        db_path = os.path.join(self.temp_dir, "config.db")
        sqlite_loader = SQLiteConfigLoader()

        detailed_config = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "cache": {
                "ttl": 300
            }
        }

        sqlite_loader.save(detailed_config, db_path)
        loaded_detailed = sqlite_loader.load(db_path)

        # 3. 合并配置
        final_config = {**env_config, **loaded_detailed}

        assert final_config["debug"] is True
        assert final_config["log_level"] == "INFO"
        assert final_config["database"]["host"] == "localhost"
        assert final_config["cache"]["ttl"] == 300

    def test_config_migration(self):
        """测试配置迁移场景"""
        # 场景：从 JSON 迁移到 SQLite

        from uplifted.extensions.config_loaders import JSONConfigLoader

        # 1. 原始 JSON 配置
        json_path = os.path.join(self.temp_dir, "old_config.json")
        json_loader = JSONConfigLoader()

        old_config = {
            "app_name": "OldApp",
            "version": "1.0.0",
            "settings": {
                "debug": True
            }
        }

        json_loader.save(old_config, json_path)

        # 2. 迁移到 SQLite
        db_path = os.path.join(self.temp_dir, "new_config.db")
        sqlite_loader = SQLiteConfigLoader()

        # 加载旧配置
        loaded_old = json_loader.load(json_path)

        # 保存到新格式
        sqlite_loader.save(loaded_old, db_path)

        # 3. 验证迁移
        migrated_config = sqlite_loader.load(db_path)

        assert migrated_config["app_name"] == "OldApp"
        assert migrated_config["version"] == "1.0.0"
        assert migrated_config["settings"]["debug"] is True
