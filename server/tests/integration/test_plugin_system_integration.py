"""
插件系统集成测试

测试完整的插件加载、激活、工具注册和执行流程
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any

from uplifted.extensions.plugin_manifest import (
    PluginManifest,
    PluginMetadata,
    PluginCategory,
    ToolDefinition,
    ToolParameter
)


class MockPlugin:
    """模拟插件类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = "mock_plugin"
        self.is_activated = False

    def activate(self) -> None:
        """激活插件"""
        self.is_activated = True

    def deactivate(self) -> None:
        """停用插件"""
        self.is_activated = False

    def greet(self, name: str) -> str:
        """问候功能"""
        return f"Hello, {name}!"

    def calculate(self, a: int, b: int, operation: str = "add") -> int:
        """计算功能"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a // b if b != 0 else 0
        return 0


def create_plugin(config: Dict[str, Any] = None):
    """插件工厂函数"""
    return MockPlugin(config)


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginLoadingFlow:
    """插件加载流程测试"""

    def setup_method(self):
        """创建测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = Path(self.temp_dir) / "test_plugin"
        self.plugin_dir.mkdir(parents=True)

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_plugin_directory(self):
        """测试创建插件目录结构"""
        # 创建插件文件
        (self.plugin_dir / "__init__.py").write_text("")

        # 创建插件主文件
        plugin_code = '''
"""测试插件"""

class TestPlugin:
    def __init__(self, config=None):
        self.config = config or {}
        self.name = "test_plugin"

    def activate(self):
        pass

    def deactivate(self):
        pass

    def echo(self, message: str) -> str:
        return message

def create_plugin(config=None):
    return TestPlugin(config)
'''
        (self.plugin_dir / "plugin.py").write_text(plugin_code)

        # 创建 manifest.json
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test plugin",
                author="Test Author"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="TestPlugin",
            tools=[
                ToolDefinition(
                    name="echo",
                    description="Echo a message",
                    function_name="echo",
                    parameters=[
                        ToolParameter(
                            name="message",
                            type="string",
                            description="Message to echo",
                            required=True
                        )
                    ]
                )
            ]
        )

        manifest.to_json_file(str(self.plugin_dir / "manifest.json"))

        # 验证文件存在
        assert (self.plugin_dir / "__init__.py").exists()
        assert (self.plugin_dir / "plugin.py").exists()
        assert (self.plugin_dir / "manifest.json").exists()

        # 验证 manifest 内容
        loaded_manifest = PluginManifest.from_json_file(
            str(self.plugin_dir / "manifest.json")
        )

        assert loaded_manifest.metadata.name == "test_plugin"
        assert len(loaded_manifest.tools) == 1
        assert loaded_manifest.tools[0].name == "echo"

    def test_plugin_manifest_validation(self):
        """测试插件清单验证"""
        # 创建有效清单
        valid_manifest = PluginManifest(
            metadata=PluginMetadata(
                name="valid_plugin",
                version="1.0.0",
                description="Valid plugin",
                author="Author"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="ValidPlugin"
        )

        errors = valid_manifest.validate()
        assert errors == []

        # 创建无效清单（缺少名称）
        invalid_manifest = PluginManifest(
            metadata=PluginMetadata(
                name="",  # 空名称
                version="1.0.0",
                description="Invalid plugin",
                author="Author"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="InvalidPlugin"
        )

        errors = invalid_manifest.validate()
        assert len(errors) > 0

    def test_plugin_tool_registration(self):
        """测试插件工具注册"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="tool_plugin",
                version="1.0.0",
                description="Plugin with tools",
                author="Test"
            ),
            category=PluginCategory.TOOLS,
            entry_point="plugin.py",
            main_class="ToolPlugin",
            tools=[
                ToolDefinition(
                    name="tool1",
                    description="First tool",
                    function_name="func1",
                    parameters=[
                        ToolParameter(
                            name="param1",
                            type="string",
                            description="Parameter 1",
                            required=True
                        )
                    ]
                ),
                ToolDefinition(
                    name="tool2",
                    description="Second tool",
                    function_name="func2",
                    parameters=[]
                )
            ]
        )

        # 验证工具数量
        assert len(manifest.tools) == 2

        # 验证工具属性
        assert manifest.tools[0].name == "tool1"
        assert manifest.tools[0].function_name == "func1"
        assert len(manifest.tools[0].parameters) == 1

        assert manifest.tools[1].name == "tool2"
        assert manifest.tools[1].function_name == "func2"
        assert len(manifest.tools[1].parameters) == 0

    def test_plugin_configuration(self):
        """测试插件配置"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="configurable_plugin",
                version="1.0.0",
                description="Configurable plugin",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="ConfigurablePlugin",
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "API key for external service"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 30
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable this feature",
                        "default": True
                    }
                },
                "required": ["api_key"]
            }
        )

        # 验证配置 schema
        assert "properties" in manifest.config_schema
        assert "api_key" in manifest.config_schema["properties"]
        assert manifest.config_schema["properties"]["timeout"]["default"] == 30
        assert manifest.config_schema["required"] == ["api_key"]


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginLifecycle:
    """插件生命周期测试"""

    def test_plugin_activation_deactivation(self):
        """测试插件激活和停用"""
        plugin = MockPlugin()

        assert plugin.is_activated is False

        # 激活
        plugin.activate()
        assert plugin.is_activated is True

        # 停用
        plugin.deactivate()
        assert plugin.is_activated is False

    def test_plugin_with_configuration(self):
        """测试带配置的插件"""
        config = {
            "api_key": "test_key_123",
            "timeout": 60,
            "debug": True
        }

        plugin = MockPlugin(config)

        assert plugin.config["api_key"] == "test_key_123"
        assert plugin.config["timeout"] == 60
        assert plugin.config["debug"] is True

    def test_plugin_factory_function(self):
        """测试插件工厂函数"""
        config = {"setting": "value"}

        plugin = create_plugin(config)

        assert isinstance(plugin, MockPlugin)
        assert plugin.config["setting"] == "value"


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginToolExecution:
    """插件工具执行测试"""

    def setup_method(self):
        """创建插件实例"""
        self.plugin = MockPlugin()
        self.plugin.activate()

    def test_execute_simple_tool(self):
        """测试执行简单工具"""
        result = self.plugin.greet("Alice")

        assert result == "Hello, Alice!"

    def test_execute_tool_with_parameters(self):
        """测试执行带参数的工具"""
        # 加法
        result_add = self.plugin.calculate(10, 5, "add")
        assert result_add == 15

        # 减法
        result_subtract = self.plugin.calculate(10, 5, "subtract")
        assert result_subtract == 5

        # 乘法
        result_multiply = self.plugin.calculate(10, 5, "multiply")
        assert result_multiply == 50

        # 除法
        result_divide = self.plugin.calculate(10, 5, "divide")
        assert result_divide == 2

    def test_tool_error_handling(self):
        """测试工具错误处理"""
        # 除以零
        result = self.plugin.calculate(10, 0, "divide")
        assert result == 0  # 我们的实现返回 0

        # 无效操作
        result_invalid = self.plugin.calculate(10, 5, "invalid")
        assert result_invalid == 0


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginDependencies:
    """插件依赖测试"""

    def test_plugin_with_python_dependencies(self):
        """测试带 Python 依赖的插件"""
        from uplifted.extensions.plugin_manifest import DependencyInfo

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="dep_plugin",
                version="1.0.0",
                description="Plugin with dependencies",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="DepPlugin",
            dependencies=[
                DependencyInfo(
                    name="requests",
                    version=">=2.28.0",
                    optional=False
                ),
                DependencyInfo(
                    name="redis",
                    version=">=4.0.0",
                    optional=True
                )
            ]
        )

        # 验证依赖
        assert len(manifest.dependencies) == 2

        # 必需依赖
        assert manifest.dependencies[0].name == "requests"
        assert manifest.dependencies[0].optional is False

        # 可选依赖
        assert manifest.dependencies[1].name == "redis"
        assert manifest.dependencies[1].optional is True

    def test_dependency_validation(self):
        """测试依赖验证"""
        from uplifted.extensions.plugin_manifest import DependencyInfo

        # 有效依赖
        valid_dep = DependencyInfo(
            name="numpy",
            version=">=1.24.0"
        )

        assert valid_dep.name == "numpy"
        assert valid_dep.version == ">=1.24.0"

        # 可选依赖
        optional_dep = DependencyInfo(
            name="pandas",
            version=">=1.5.0",
            optional=True
        )

        assert optional_dep.optional is True


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginPermissions:
    """插件权限测试"""

    def test_plugin_with_permissions(self):
        """测试带权限的插件"""
        from uplifted.extensions.plugin_manifest import PermissionType

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="secure_plugin",
                version="1.0.0",
                description="Plugin with permissions",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="SecurePlugin",
            permissions=[
                PermissionType.NETWORK_ACCESS,
                PermissionType.FILE_READ,
                PermissionType.API_CALL
            ]
        )

        # 验证权限
        assert len(manifest.permissions) == 3
        assert PermissionType.NETWORK_ACCESS in manifest.permissions
        assert PermissionType.FILE_READ in manifest.permissions
        assert PermissionType.API_CALL in manifest.permissions

    def test_permission_types(self):
        """测试所有权限类型"""
        from uplifted.extensions.plugin_manifest import PermissionType

        all_permissions = [
            PermissionType.NETWORK_ACCESS,
            PermissionType.FILE_READ,
            PermissionType.FILE_WRITE,
            PermissionType.PROCESS_SPAWN,
            PermissionType.SYSTEM_INFO,
            PermissionType.DATABASE_ACCESS,
            PermissionType.API_CALL
        ]

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="full_permission_plugin",
                version="1.0.0",
                description="Plugin with all permissions",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="FullPermissionPlugin",
            permissions=all_permissions
        )

        assert len(manifest.permissions) == 7
        for perm in all_permissions:
            assert perm in manifest.permissions


@pytest.mark.integration
@pytest.mark.plugin
@pytest.mark.slow
class TestPluginResourceManagement:
    """插件资源管理测试"""

    def test_plugin_with_resource_limits(self):
        """测试带资源限制的插件"""
        from uplifted.extensions.plugin_manifest import ResourceRequirements

        resources = ResourceRequirements(
            memory_mb=1024,
            cpu_cores=2.0,
            disk_mb=500,
            network_required=True,
            gpu_required=False,
            timeout_seconds=600
        )

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="resource_limited_plugin",
                version="1.0.0",
                description="Plugin with resource limits",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="ResourceLimitedPlugin",
            resources=resources
        )

        # 验证资源配置
        assert manifest.resources.memory_mb == 1024
        assert manifest.resources.cpu_cores == 2.0
        assert manifest.resources.disk_mb == 500
        assert manifest.resources.network_required is True
        assert manifest.resources.gpu_required is False
        assert manifest.resources.timeout_seconds == 600

    def test_default_resource_requirements(self):
        """测试默认资源需求"""
        from uplifted.extensions.plugin_manifest import ResourceRequirements

        default_resources = ResourceRequirements()

        assert default_resources.memory_mb == 256
        assert default_resources.cpu_cores == 0.5
        assert default_resources.disk_mb == 100
        assert default_resources.network_required is False
        assert default_resources.gpu_required is False
        assert default_resources.timeout_seconds == 300


@pytest.mark.integration
@pytest.mark.plugin
class TestPluginSerialization:
    """插件序列化测试"""

    def setup_method(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理临时目录"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_complete_plugin_serialization(self):
        """测试完整插件序列化"""
        from uplifted.extensions.plugin_manifest import (
            PermissionType,
            ResourceRequirements,
            DependencyInfo
        )

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="complete_plugin",
                version="2.0.0",
                description="Complete plugin with all features",
                author="Complete Author",
                author_email="complete@example.com",
                homepage="https://example.com",
                license="MIT",
                tags=["complete", "test", "example"]
            ),
            category=PluginCategory.TOOLS,
            entry_point="complete.py",
            main_class="CompletePlugin",
            tools=[
                ToolDefinition(
                    name="advanced_tool",
                    description="An advanced tool",
                    function_name="advanced_func",
                    parameters=[
                        ToolParameter(
                            name="input_data",
                            type="object",
                            description="Input data",
                            required=True
                        ),
                        ToolParameter(
                            name="options",
                            type="object",
                            description="Processing options",
                            required=False,
                            default={}
                        )
                    ],
                    returns={
                        "type": "object",
                        "description": "Processed result"
                    }
                )
            ],
            permissions=[
                PermissionType.NETWORK_ACCESS,
                PermissionType.DATABASE_ACCESS
            ],
            dependencies=[
                DependencyInfo(name="requests", version=">=2.28.0"),
                DependencyInfo(name="sqlalchemy", version=">=2.0.0")
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "api_url": {"type": "string"},
                    "api_key": {"type": "string"},
                    "debug": {"type": "boolean", "default": False}
                },
                "required": ["api_url", "api_key"]
            },
            resources=ResourceRequirements(
                memory_mb=2048,
                cpu_cores=4.0,
                disk_mb=1000,
                network_required=True
            )
        )

        # 保存到文件
        manifest_path = os.path.join(self.temp_dir, "complete_manifest.json")
        manifest.to_json_file(manifest_path)

        # 从文件加载
        loaded_manifest = PluginManifest.from_json_file(manifest_path)

        # 验证所有属性
        assert loaded_manifest.metadata.name == "complete_plugin"
        assert loaded_manifest.metadata.version == "2.0.0"
        assert len(loaded_manifest.metadata.tags) == 3
        assert loaded_manifest.category == PluginCategory.TOOLS
        assert len(loaded_manifest.tools) == 1
        assert loaded_manifest.tools[0].name == "advanced_tool"
        assert len(loaded_manifest.permissions) == 2
        assert len(loaded_manifest.dependencies) == 2
        assert loaded_manifest.resources.memory_mb == 2048
        assert "api_url" in loaded_manifest.config_schema["properties"]
