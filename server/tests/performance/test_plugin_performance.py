"""
插件系统性能测试

测试插件加载、工具执行等操作的性能
"""

import pytest
import tempfile
import os
from pathlib import Path
from uplifted.extensions.plugin_manifest import (
    PluginManifest,
    PluginMetadata,
    PluginCategory,
    ToolDefinition,
    ToolParameter
)


@pytest.mark.performance
@pytest.mark.plugin
class TestPluginManifestPerformance:
    """插件清单性能测试"""

    def test_manifest_creation_performance(self, benchmark):
        """测试清单创建性能"""

        def create_manifest():
            return PluginManifest(
                metadata=PluginMetadata(
                    name="perf_test_plugin",
                    version="1.0.0",
                    description="Performance test plugin",
                    author="Perf Tester"
                ),
                category=PluginCategory.UTILITY,
                entry_point="plugin.py",
                main_class="PerfPlugin"
            )

        result = benchmark(create_manifest)
        assert result.metadata.name == "perf_test_plugin"

    def test_manifest_with_tools_creation(self, benchmark):
        """测试带多个工具的清单创建性能"""

        def create_manifest_with_tools():
            tools = [
                ToolDefinition(
                    name=f"tool_{i}",
                    description=f"Tool number {i}",
                    function_name=f"func_{i}",
                    parameters=[
                        ToolParameter(
                            name=f"param_{j}",
                            type="string",
                            description=f"Parameter {j}",
                            required=True
                        )
                        for j in range(3)
                    ]
                )
                for i in range(10)
            ]

            return PluginManifest(
                metadata=PluginMetadata(
                    name="multi_tool_plugin",
                    version="1.0.0",
                    description="Plugin with multiple tools",
                    author="Test"
                ),
                category=PluginCategory.TOOLS,
                entry_point="plugin.py",
                main_class="MultiToolPlugin",
                tools=tools
            )

        result = benchmark(create_manifest_with_tools)
        assert len(result.tools) == 10

    def test_manifest_serialization_performance(self, benchmark):
        """测试清单序列化性能"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="serialization_test",
                version="1.0.0",
                description="Serialization test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="SerializationPlugin"
        )

        result = benchmark(manifest.to_json)
        assert isinstance(result, str)
        assert "serialization_test" in result

    def test_manifest_deserialization_performance(self, benchmark):
        """测试清单反序列化性能"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="deserialization_test",
                version="1.0.0",
                description="Deserialization test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="DeserializationPlugin"
        )

        json_str = manifest.to_json()

        result = benchmark(PluginManifest.from_json, json_str)
        assert result.metadata.name == "deserialization_test"

    def test_manifest_validation_performance(self, benchmark):
        """测试清单验证性能"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="validation_test",
                version="1.0.0",
                description="Validation test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="ValidationPlugin"
        )

        result = benchmark(manifest.validate)
        assert result == []


@pytest.mark.performance
@pytest.mark.plugin
class TestPluginFileOperationsPerformance:
    """插件文件操作性能测试"""

    def setup_method(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理临时目录"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_manifest_file_write_performance(self, benchmark):
        """测试清单文件写入性能"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="file_write_test",
                version="1.0.0",
                description="File write test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="FileWritePlugin"
        )

        file_path = os.path.join(self.temp_dir, "test_manifest.json")

        benchmark(manifest.to_json_file, file_path)

        assert os.path.exists(file_path)

    def test_manifest_file_read_performance(self, benchmark):
        """测试清单文件读取性能"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="file_read_test",
                version="1.0.0",
                description="File read test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="FileReadPlugin"
        )

        file_path = os.path.join(self.temp_dir, "test_manifest.json")
        manifest.to_json_file(file_path)

        result = benchmark(PluginManifest.from_json_file, file_path)
        assert result.metadata.name == "file_read_test"


@pytest.mark.performance
@pytest.mark.config
class TestConfigLoaderPerformance:
    """配置加载器性能测试"""

    def setup_method(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理临时目录"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_env_loader_performance(self, benchmark):
        """测试环境变量加载器性能"""
        from uplifted.extensions.config_loaders import EnvConfigLoader

        # 设置测试环境变量
        os.environ["PERF_TEST_KEY1"] = "value1"
        os.environ["PERF_TEST_KEY2"] = "value2"
        os.environ["PERF_TEST_NESTED__KEY"] = "nested_value"

        loader = EnvConfigLoader(prefix="PERF_TEST_")

        result = benchmark(loader.load, "")

        assert "key1" in result or "KEY1" in result

    def test_sqlite_loader_write_performance(self, benchmark):
        """测试 SQLite 加载器写入性能"""
        from uplifted.extensions.config_loaders import SQLiteConfigLoader

        loader = SQLiteConfigLoader()
        db_path = os.path.join(self.temp_dir, "perf_test.db")

        test_data = {
            "key1": "value1",
            "key2": 123,
            "nested": {
                "key3": "value3",
                "key4": 456
            }
        }

        benchmark(loader.save, test_data, db_path)

        assert os.path.exists(db_path)

    def test_sqlite_loader_read_performance(self, benchmark):
        """测试 SQLite 加载器读取性能"""
        from uplifted.extensions.config_loaders import SQLiteConfigLoader

        loader = SQLiteConfigLoader()
        db_path = os.path.join(self.temp_dir, "perf_test.db")

        test_data = {
            "key1": "value1",
            "key2": 123,
            "nested": {"key3": "value3"}
        }

        loader.save(test_data, db_path)

        result = benchmark(loader.load, db_path)

        assert result["key1"] == "value1"

    def test_large_config_performance(self, benchmark):
        """测试大配置性能"""
        from uplifted.extensions.config_loaders import SQLiteConfigLoader

        loader = SQLiteConfigLoader()
        db_path = os.path.join(self.temp_dir, "large_config.db")

        # 创建大配置（1000 个键）
        large_config = {
            f"key_{i}": {
                "value": f"value_{i}",
                "number": i,
                "enabled": i % 2 == 0
            }
            for i in range(1000)
        }

        # 测试保存性能
        save_result = benchmark(loader.save, large_config, db_path)
        assert save_result is True


@pytest.mark.performance
@pytest.mark.slow
class TestBulkOperationsPerformance:
    """批量操作性能测试"""

    def test_create_multiple_manifests(self, benchmark):
        """测试批量创建清单性能"""

        def create_100_manifests():
            manifests = []
            for i in range(100):
                manifest = PluginManifest(
                    metadata=PluginMetadata(
                        name=f"plugin_{i}",
                        version="1.0.0",
                        description=f"Plugin number {i}",
                        author="Bulk Test"
                    ),
                    category=PluginCategory.UTILITY,
                    entry_point="plugin.py",
                    main_class=f"Plugin{i}"
                )
                manifests.append(manifest)
            return manifests

        result = benchmark(create_100_manifests)
        assert len(result) == 100

    def test_serialize_multiple_manifests(self, benchmark):
        """测试批量序列化性能"""
        manifests = [
            PluginManifest(
                metadata=PluginMetadata(
                    name=f"plugin_{i}",
                    version="1.0.0",
                    description=f"Plugin number {i}",
                    author="Bulk Test"
                ),
                category=PluginCategory.UTILITY,
                entry_point="plugin.py",
                main_class=f"Plugin{i}"
            )
            for i in range(100)
        ]

        def serialize_all():
            return [m.to_json() for m in manifests]

        result = benchmark(serialize_all)
        assert len(result) == 100


@pytest.mark.performance
@pytest.mark.plugin
class TestMemoryUsage:
    """内存使用测试"""

    def test_manifest_memory_footprint(self):
        """测试清单内存占用"""
        import sys

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="memory_test",
                version="1.0.0",
                description="Memory footprint test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="MemoryTestPlugin"
        )

        # 获取对象大小（近似）
        size = sys.getsizeof(manifest)

        # 验证大小合理（应该小于 1KB）
        assert size < 1024, f"Manifest size too large: {size} bytes"

    def test_large_manifest_memory(self):
        """测试大清单内存占用"""
        import sys

        # 创建带 100 个工具的大清单
        tools = [
            ToolDefinition(
                name=f"tool_{i}",
                description=f"Tool {i}",
                function_name=f"func_{i}",
                parameters=[
                    ToolParameter(
                        name=f"param_{j}",
                        type="string",
                        description=f"Param {j}",
                        required=True
                    )
                    for j in range(5)
                ]
            )
            for i in range(100)
        ]

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="large_manifest",
                version="1.0.0",
                description="Large manifest test",
                author="Test"
            ),
            category=PluginCategory.TOOLS,
            entry_point="plugin.py",
            main_class="LargeManifestPlugin",
            tools=tools
        )

        size = sys.getsizeof(manifest)

        # 验证大小合理（应该小于 10KB）
        assert size < 10240, f"Large manifest size too large: {size} bytes"


@pytest.mark.performance
class TestConcurrentOperations:
    """并发操作测试"""

    def test_concurrent_manifest_creation(self):
        """测试并发创建清单"""
        import threading

        results = []
        lock = threading.Lock()

        def create_manifest(thread_id):
            manifest = PluginManifest(
                metadata=PluginMetadata(
                    name=f"concurrent_plugin_{thread_id}",
                    version="1.0.0",
                    description=f"Concurrent test {thread_id}",
                    author="Concurrent Test"
                ),
                category=PluginCategory.UTILITY,
                entry_point="plugin.py",
                main_class=f"ConcurrentPlugin{thread_id}"
            )

            with lock:
                results.append(manifest)

        # 创建 10 个线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_manifest, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(results) == 10
        assert all(isinstance(m, PluginManifest) for m in results)
