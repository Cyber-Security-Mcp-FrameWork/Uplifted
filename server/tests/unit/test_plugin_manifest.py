"""
插件清单（Manifest）单元测试

测试 PluginManifest 的所有核心功能：
- 数据类创建和验证
- JSON 序列化/反序列化
- 元数据验证
- 工具定义处理
- 版本兼容性检查
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from uplifted.extensions.plugin_manifest import (
    PluginManifest,
    PluginCategory,
    PermissionType,
    ResourceRequirements,
    ToolDefinition,
    ToolParameter,
    DependencyInfo,
    PluginMetadata
)


class TestResourceRequirements:
    """资源需求配置测试"""

    def test_default_values(self):
        """测试默认值"""
        resources = ResourceRequirements()

        assert resources.memory_mb == 256
        assert resources.cpu_cores == 0.5
        assert resources.disk_mb == 100
        assert resources.network_required is False
        assert resources.gpu_required is False
        assert resources.timeout_seconds == 300

    def test_custom_values(self):
        """测试自定义值"""
        resources = ResourceRequirements(
            memory_mb=1024,
            cpu_cores=2.0,
            disk_mb=500,
            network_required=True,
            gpu_required=True,
            timeout_seconds=600
        )

        assert resources.memory_mb == 1024
        assert resources.cpu_cores == 2.0
        assert resources.disk_mb == 500
        assert resources.network_required is True
        assert resources.gpu_required is True
        assert resources.timeout_seconds == 600

    def test_to_dict(self):
        """测试转换为字典"""
        resources = ResourceRequirements(
            memory_mb=512,
            cpu_cores=1.0
        )

        result = resources.to_dict()

        assert isinstance(result, dict)
        assert result["memory_mb"] == 512
        assert result["cpu_cores"] == 1.0
        assert "disk_mb" in result
        assert "network_required" in result


class TestToolParameter:
    """工具参数测试"""

    def test_required_parameter(self):
        """测试必需参数"""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )

        assert param.name == "query"
        assert param.type == "string"
        assert param.description == "Search query"
        assert param.required is True
        assert param.default is None

    def test_optional_parameter_with_default(self):
        """测试可选参数（有默认值）"""
        param = ToolParameter(
            name="limit",
            type="integer",
            description="Result limit",
            required=False,
            default=10
        )

        assert param.name == "limit"
        assert param.required is False
        assert param.default == 10

    def test_to_dict(self):
        """测试转换为字典"""
        param = ToolParameter(
            name="api_key",
            type="string",
            description="API key for authentication",
            required=True
        )

        result = param.to_dict()

        assert result["name"] == "api_key"
        assert result["type"] == "string"
        assert result["description"] == "API key for authentication"
        assert result["required"] is True


class TestToolDefinition:
    """工具定义测试"""

    def test_simple_tool(self):
        """测试简单工具定义"""
        tool = ToolDefinition(
            name="hello_world",
            description="A simple hello world tool",
            function_name="say_hello"
        )

        assert tool.name == "hello_world"
        assert tool.description == "A simple hello world tool"
        assert tool.function_name == "say_hello"
        assert tool.parameters == []
        assert tool.returns == {}

    def test_tool_with_parameters(self):
        """测试带参数的工具"""
        params = [
            ToolParameter(
                name="message",
                type="string",
                description="Message to display",
                required=True
            ),
            ToolParameter(
                name="count",
                type="integer",
                description="Repeat count",
                required=False,
                default=1
            )
        ]

        tool = ToolDefinition(
            name="repeat_message",
            description="Repeat a message",
            function_name="repeat",
            parameters=params
        )

        assert len(tool.parameters) == 2
        assert tool.parameters[0].name == "message"
        assert tool.parameters[1].name == "count"
        assert tool.parameters[1].default == 1

    def test_tool_with_returns(self):
        """测试带返回值定义的工具"""
        tool = ToolDefinition(
            name="calculate",
            description="Calculate something",
            function_name="calc",
            returns={
                "type": "number",
                "description": "Calculation result"
            }
        )

        assert tool.returns["type"] == "number"
        assert "description" in tool.returns

    def test_to_dict(self):
        """测试转换为字典"""
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool",
            function_name="test_func"
        )

        result = tool.to_dict()

        assert result["name"] == "test_tool"
        assert result["description"] == "Test tool"
        assert result["function_name"] == "test_func"
        assert "parameters" in result


class TestDependencyInfo:
    """依赖信息测试"""

    def test_python_dependency(self):
        """测试 Python 依赖"""
        dep = DependencyInfo(
            name="requests",
            version=">=2.28.0",
            optional=False
        )

        assert dep.name == "requests"
        assert dep.version == ">=2.28.0"
        assert dep.optional is False

    def test_optional_dependency(self):
        """测试可选依赖"""
        dep = DependencyInfo(
            name="redis",
            version=">=4.0.0",
            optional=True
        )

        assert dep.name == "redis"
        assert dep.optional is True

    def test_to_dict(self):
        """测试转换为字典"""
        dep = DependencyInfo(
            name="numpy",
            version=">=1.24.0"
        )

        result = dep.to_dict()

        assert result["name"] == "numpy"
        assert result["version"] == ">=1.24.0"


class TestPluginMetadata:
    """插件元数据测试"""

    def test_basic_metadata(self):
        """测试基本元数据"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            author_email="test@example.com"
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Test plugin"
        assert metadata.author == "Test Author"
        assert metadata.author_email == "test@example.com"

    def test_with_tags(self):
        """测试带标签的元数据"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            tags=["testing", "utility"]
        )

        assert len(metadata.tags) == 2
        assert "testing" in metadata.tags
        assert "utility" in metadata.tags

    def test_to_dict(self):
        """测试转换为字典"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author"
        )

        result = metadata.to_dict()

        assert result["name"] == "test_plugin"
        assert result["version"] == "1.0.0"
        assert "author" in result


class TestPluginManifest:
    """插件清单测试"""

    def test_create_manifest(self):
        """测试创建清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="hello_plugin",
                version="1.0.0",
                description="Hello world plugin",
                author="Test Author"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="HelloPlugin"
        )

        assert manifest.metadata.name == "hello_plugin"
        assert manifest.category == PluginCategory.UTILITY
        assert manifest.entry_point == "main.py"
        assert manifest.main_class == "HelloPlugin"

    def test_manifest_with_tools(self):
        """测试带工具的清单"""
        tool = ToolDefinition(
            name="greet",
            description="Greet user",
            function_name="greet_user",
            parameters=[
                ToolParameter(
                    name="name",
                    type="string",
                    description="User name",
                    required=True
                )
            ]
        )

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="greeter",
                version="1.0.0",
                description="Greeting plugin",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="GreeterPlugin",
            tools=[tool]
        )

        assert len(manifest.tools) == 1
        assert manifest.tools[0].name == "greet"

    def test_manifest_with_permissions(self):
        """测试带权限的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="network_plugin",
                version="1.0.0",
                description="Network plugin",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="NetworkPlugin",
            permissions=[
                PermissionType.NETWORK_ACCESS,
                PermissionType.API_CALL
            ]
        )

        assert len(manifest.permissions) == 2
        assert PermissionType.NETWORK_ACCESS in manifest.permissions
        assert PermissionType.API_CALL in manifest.permissions

    def test_manifest_with_dependencies(self):
        """测试带依赖的清单"""
        deps = [
            DependencyInfo(name="requests", version=">=2.28.0"),
            DependencyInfo(name="redis", version=">=4.0.0", optional=True)
        ]

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="dep_plugin",
                version="1.0.0",
                description="Plugin with dependencies",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="DepPlugin",
            dependencies=deps
        )

        assert len(manifest.dependencies) == 2
        assert manifest.dependencies[0].name == "requests"
        assert manifest.dependencies[1].optional is True

    def test_manifest_with_resources(self):
        """测试带资源需求的清单"""
        resources = ResourceRequirements(
            memory_mb=512,
            cpu_cores=1.0,
            network_required=True
        )

        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="resource_plugin",
                version="1.0.0",
                description="Resource-intensive plugin",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="ResourcePlugin",
            resources=resources
        )

        assert manifest.resources.memory_mb == 512
        assert manifest.resources.cpu_cores == 1.0
        assert manifest.resources.network_required is True

    def test_to_dict(self):
        """测试转换为字典"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="TestPlugin"
        )

        result = manifest.to_dict()

        assert isinstance(result, dict)
        assert "metadata" in result
        assert result["metadata"]["name"] == "test_plugin"
        assert result["category"] == "utility"
        assert result["entry_point"] == "main.py"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "metadata": {
                "name": "from_dict_plugin",
                "version": "1.0.0",
                "description": "Created from dict",
                "author": "Test Author",
                "author_email": "test@example.com"
            },
            "category": "utility",
            "entry_point": "main.py",
            "main_class": "FromDictPlugin",
            "tools": [],
            "permissions": [],
            "dependencies": [],
            "config_schema": {},
            "resources": {
                "memory_mb": 256,
                "cpu_cores": 0.5,
                "disk_mb": 100,
                "network_required": False,
                "gpu_required": False,
                "timeout_seconds": 300
            }
        }

        manifest = PluginManifest.from_dict(data)

        assert manifest.metadata.name == "from_dict_plugin"
        assert manifest.category == PluginCategory.UTILITY
        assert manifest.entry_point == "main.py"

    def test_json_serialization(self):
        """测试 JSON 序列化/反序列化"""
        original = PluginManifest(
            metadata=PluginMetadata(
                name="json_plugin",
                version="2.0.0",
                description="JSON test plugin",
                author="JSON Tester"
            ),
            category=PluginCategory.TOOLS,
            entry_point="plugin.py",
            main_class="JsonPlugin"
        )

        # 序列化
        json_str = original.to_json()
        assert isinstance(json_str, str)

        # 反序列化
        restored = PluginManifest.from_json(json_str)
        assert restored.metadata.name == "json_plugin"
        assert restored.metadata.version == "2.0.0"
        assert restored.category == PluginCategory.TOOLS

    def test_json_file_operations(self):
        """测试 JSON 文件操作"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="file_plugin",
                version="1.0.0",
                description="File test plugin",
                author="File Tester"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="FilePlugin"
        )

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # 保存到文件
            manifest.to_json_file(temp_path)

            # 从文件加载
            loaded = PluginManifest.from_json_file(temp_path)

            assert loaded.metadata.name == "file_plugin"
            assert loaded.metadata.version == "1.0.0"
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_success(self):
        """测试验证成功的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="valid_plugin",
                version="1.0.0",
                description="A valid plugin",
                author="Valid Author"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="ValidPlugin"
        )

        errors = manifest.validate()
        assert errors == []

    def test_validate_missing_name(self):
        """测试验证缺少名称的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="",  # 空名称
                version="1.0.0",
                description="Test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="TestPlugin"
        )

        errors = manifest.validate()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)

    def test_validate_invalid_version(self):
        """测试验证无效版本的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="invalid",  # 无效版本格式
                description="Test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="TestPlugin"
        )

        errors = manifest.validate()
        assert len(errors) > 0
        assert any("version" in error.lower() for error in errors)

    def test_validate_missing_entry_point(self):
        """测试验证缺少入口点的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="",  # 空入口点
            main_class="TestPlugin"
        )

        errors = manifest.validate()
        assert len(errors) > 0
        assert any("entry_point" in error.lower() for error in errors)


@pytest.mark.unit
@pytest.mark.plugin
class TestPluginManifestIntegration:
    """插件清单集成测试"""

    def test_complete_manifest(self):
        """测试完整的清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="complete_plugin",
                version="1.0.0",
                description="A complete plugin example",
                author="Complete Author",
                author_email="complete@example.com",
                homepage="https://example.com",
                license="MIT",
                tags=["complete", "example"]
            ),
            category=PluginCategory.UTILITY,
            entry_point="plugin.py",
            main_class="CompletePlugin",
            tools=[
                ToolDefinition(
                    name="tool1",
                    description="First tool",
                    function_name="tool1_func",
                    parameters=[
                        ToolParameter(
                            name="param1",
                            type="string",
                            description="Parameter 1",
                            required=True
                        )
                    ],
                    returns={"type": "string", "description": "Result"}
                )
            ],
            permissions=[
                PermissionType.NETWORK_ACCESS,
                PermissionType.FILE_READ
            ],
            dependencies=[
                DependencyInfo(name="requests", version=">=2.28.0")
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"}
                }
            },
            resources=ResourceRequirements(
                memory_mb=512,
                cpu_cores=1.0,
                network_required=True
            )
        )

        # 验证清单
        errors = manifest.validate()
        assert errors == []

        # 序列化和反序列化
        json_str = manifest.to_json()
        restored = PluginManifest.from_json(json_str)

        # 验证恢复的清单
        assert restored.metadata.name == "complete_plugin"
        assert len(restored.tools) == 1
        assert len(restored.permissions) == 2
        assert len(restored.dependencies) == 1
        assert restored.resources.memory_mb == 512
