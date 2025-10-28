"""
插件清单（Manifest）模块

提供标准化的插件元数据格式，用于描述插件的所有属性、依赖、工具和权限。

核心设计原则：
1. 声明式配置 - 所有插件信息通过 manifest.json 声明
2. 强类型验证 - 使用 dataclass 和类型注解确保数据正确性
3. 向后兼容 - 与现有 PluginInfo 兼容
4. 可扩展性 - 易于添加新的元数据字段

使用示例：
    # 从 JSON 文件加载
    manifest = PluginManifest.from_json_file("plugins/my_plugin/manifest.json")

    # 验证清单
    errors = manifest.validate()
    if errors:
        print(f"Validation errors: {errors}")

    # 获取工具定义
    for tool in manifest.tools:
        print(f"Tool: {tool.name}")

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class PluginCategory(str, Enum):
    """
    插件类别枚举

    用于对插件进行分类，便于用户查找和管理。
    """
    SECURITY = "security"           # 安全工具（扫描、审计、渗透测试等）
    TOOLS = "tools"                 # 通用工具
    MONITORING = "monitoring"       # 监控和可观测性
    STORAGE = "storage"             # 数据存储
    INTEGRATION = "integration"     # 第三方集成
    UTILITY = "utility"             # 实用工具
    CUSTOM = "custom"               # 自定义类别


class PermissionType(str, Enum):
    """
    权限类型枚举

    定义插件可以申请的权限类型，用于安全控制。
    """
    NETWORK_ACCESS = "network.access"          # 网络访问
    FILE_READ = "file.read"                    # 文件读取
    FILE_WRITE = "file.write"                  # 文件写入
    PROCESS_SPAWN = "process.spawn"            # 进程创建
    SYSTEM_INFO = "system.info"                # 系统信息读取
    DATABASE_ACCESS = "database.access"        # 数据库访问
    API_CALL = "api.call"                      # 外部 API 调用


@dataclass
class ResourceRequirements:
    """
    资源需求配置

    定义插件运行所需的系统资源，用于资源调度和限制。

    属性:
        memory_mb: 内存需求（MB）
        cpu_cores: CPU 核心数（可以是小数，如 0.5）
        disk_mb: 磁盘空间需求（MB）
        network_required: 是否需要网络连接
        gpu_required: 是否需要 GPU
        timeout_seconds: 执行超时时间（秒）

    示例:
        resources = ResourceRequirements(
            memory_mb=512,
            cpu_cores=1.0,
            network_required=True
        )
    """
    memory_mb: int = 256
    cpu_cores: float = 0.5
    disk_mb: int = 100
    network_required: bool = False
    gpu_required: bool = False
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceRequirements':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ToolDefinition:
    """
    工具定义

    描述插件提供的单个工具的所有信息。

    属性:
        name: 工具名称（唯一标识）
        display_name: 显示名称（可选，默认使用 name）
        description: 工具描述
        entry_point: Python 入口点（如 "my_plugin.tools.scan"）
        input_schema: 输入参数的 JSON Schema
        output_schema: 输出数据的 JSON Schema
        examples: 使用示例列表

        # MCP 工具配置（如果是 MCP 工具）
        mcp_command: MCP 命令（如 "python", "node"）
        mcp_args: MCP 命令参数列表
        mcp_env: MCP 环境变量

        # 元数据
        tags: 标签列表
        version: 工具版本
        deprecated: 是否已废弃

    示例:
        tool = ToolDefinition(
            name="port_scan",
            description="Scan network ports",
            entry_point="nmap_plugin.tools.port_scan",
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "ports": {"type": "string"}
                },
                "required": ["target"]
            },
            mcp_command="python",
            mcp_args=["-m", "nmap_plugin.mcp_server"]
        )
    """
    name: str
    description: str
    entry_point: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    # 显示信息
    display_name: Optional[str] = None

    # MCP 配置
    mcp_command: Optional[str] = None
    mcp_args: Optional[List[str]] = None
    mcp_env: Optional[Dict[str, str]] = None

    # 元数据
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False

    def __post_init__(self):
        """初始化后处理"""
        if self.display_name is None:
            self.display_name = self.name.replace('_', ' ').title()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolDefinition':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def validate(self) -> List[str]:
        """
        验证工具定义

        返回:
            错误列表，空列表表示验证通过
        """
        errors = []

        # 验证必需字段
        if not self.name:
            errors.append("Tool name is required")

        if not self.description:
            errors.append("Tool description is required")

        if not self.entry_point:
            errors.append("Tool entry_point is required")

        # 验证 input_schema
        if not isinstance(self.input_schema, dict):
            errors.append("input_schema must be a dictionary")
        elif 'type' not in self.input_schema:
            errors.append("input_schema must have 'type' field")

        # 验证 MCP 配置的一致性
        if self.mcp_command and not self.mcp_args:
            errors.append("mcp_args is required when mcp_command is specified")

        return errors


@dataclass
class PluginManifest:
    """
    插件清单（Manifest）

    标准化的插件元数据格式，包含插件的所有配置信息。

    核心属性:
        id: 唯一标识符（推荐使用反向域名，如 "com.uplifted.security.nmap"）
        name: 插件名称
        version: 版本号（遵循语义化版本）
        description: 插件描述
        author: 作者信息
        license: 许可证（默认 MIT）

    分类和标签:
        category: 插件类别
        tags: 标签列表

    依赖管理:
        dependencies: 其他插件依赖（插件 ID 列表）
        python_requirements: Python 包依赖（pip 格式）
        system_requirements: 系统工具依赖（如 ["nmap", "nikto"]）
        min_api_version: 最小 API 版本
        max_api_version: 最大 API 版本

    入口点:
        entry_point: 主类路径（如 "my_plugin.MyPlugin"）

    工具和功能:
        tools: 工具定义列表

    权限和资源:
        permissions: 所需权限列表
        resources: 资源需求配置

    配置:
        config_schema: 配置的 JSON Schema
        default_config: 默认配置值

    钩子:
        hooks: 钩子声明（如 {"before_request": ["validate_token"]}）

    元数据:
        homepage: 主页 URL
        repository_url: 代码仓库 URL
        documentation_url: 文档 URL
        icon_url: 图标 URL
        screenshot_urls: 截图 URL 列表

    使用示例:
        # 从文件加载
        manifest = PluginManifest.from_json_file("manifest.json")

        # 验证
        errors = manifest.validate()
        if errors:
            print(f"Invalid manifest: {errors}")

        # 检查兼容性
        if not manifest.is_compatible_with("1.0.0"):
            print("API version incompatible")
    """
    # 基本信息
    id: str
    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"

    # 分类和标签
    category: PluginCategory = PluginCategory.UTILITY
    tags: List[str] = field(default_factory=list)

    # 依赖
    dependencies: List[str] = field(default_factory=list)
    python_requirements: List[str] = field(default_factory=list)
    system_requirements: List[str] = field(default_factory=list)
    min_api_version: str = "0.1.0"
    max_api_version: str = "2.0.0"

    # 入口点
    entry_point: str = ""

    # 工具定义
    tools: List[ToolDefinition] = field(default_factory=list)

    # 权限声明
    permissions: List[str] = field(default_factory=list)

    # 资源需求
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)

    # 配置
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # 钩子声明
    hooks: Dict[str, List[str]] = field(default_factory=dict)

    # 元数据
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None
    screenshot_urls: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        # 确保 category 是枚举类型
        if isinstance(self.category, str):
            self.category = PluginCategory(self.category)

        # 确保 resources 是 ResourceRequirements 类型
        if isinstance(self.resources, dict):
            self.resources = ResourceRequirements.from_dict(self.resources)

        # 确保 tools 是 ToolDefinition 列表
        self.tools = [
            ToolDefinition.from_dict(tool) if isinstance(tool, dict) else tool
            for tool in self.tools
        ]

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        返回:
            字典表示
        """
        data = asdict(self)
        # 转换枚举为字符串
        data['category'] = self.category.value
        return data

    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 字符串

        参数:
            indent: 缩进空格数

        返回:
            JSON 字符串
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, file_path: str) -> None:
        """
        保存到 JSON 文件

        参数:
            file_path: 文件路径
        """
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginManifest':
        """
        从字典创建清单

        参数:
            data: 字典数据

        返回:
            PluginManifest 实例
        """
        # 提取字段
        kwargs = {}
        for field_name in cls.__annotations__:
            if field_name in data:
                kwargs[field_name] = data[field_name]

        return cls(**kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> 'PluginManifest':
        """
        从 JSON 字符串创建清单

        参数:
            json_str: JSON 字符串

        返回:
            PluginManifest 实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> 'PluginManifest':
        """
        从 JSON 文件加载清单

        参数:
            file_path: 文件路径

        返回:
            PluginManifest 实例

        异常:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """
        验证清单完整性和正确性

        返回:
            错误列表，空列表表示验证通过

        示例:
            errors = manifest.validate()
            if errors:
                for error in errors:
                    print(f"Error: {error}")
        """
        errors = []

        # 验证必需字段
        if not self.id:
            errors.append("Plugin id is required")

        if not self.name:
            errors.append("Plugin name is required")

        if not self.version:
            errors.append("Plugin version is required")

        if not self.description:
            errors.append("Plugin description is required")

        if not self.author:
            errors.append("Plugin author is required")

        # 验证 ID 格式（推荐反向域名）
        if self.id and '.' not in self.id:
            errors.append(
                f"Plugin id '{self.id}' should use reverse domain notation "
                "(e.g., 'com.example.plugin')"
            )

        # 验证版本格式（简单的语义化版本检查）
        if self.version:
            parts = self.version.split('.')
            if len(parts) < 2 or len(parts) > 3:
                errors.append(f"Invalid version format: {self.version}")

        # 验证工具定义
        for i, tool in enumerate(self.tools):
            tool_errors = tool.validate()
            for error in tool_errors:
                errors.append(f"Tool #{i+1} ({tool.name}): {error}")

        # 验证权限
        valid_permissions = [p.value for p in PermissionType]
        for perm in self.permissions:
            if perm not in valid_permissions:
                errors.append(f"Unknown permission: {perm}")

        # 验证入口点格式
        if self.entry_point and '.' not in self.entry_point:
            errors.append(
                f"Invalid entry_point format: {self.entry_point}. "
                "Expected 'module.ClassName'"
            )

        return errors

    def is_compatible_with(self, api_version: str) -> bool:
        """
        检查是否与指定 API 版本兼容

        参数:
            api_version: API 版本字符串

        返回:
            是否兼容

        示例:
            if manifest.is_compatible_with("1.0.0"):
                print("Compatible!")
        """
        try:
            # 简单的版本比较（实际应使用 packaging.version）
            def version_tuple(v: str) -> tuple:
                return tuple(map(int, v.split('.')))

            min_ver = version_tuple(self.min_api_version)
            max_ver = version_tuple(self.max_api_version)
            api_ver = version_tuple(api_version)

            return min_ver <= api_ver <= max_ver

        except (ValueError, AttributeError):
            return False

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        根据名称获取工具定义

        参数:
            tool_name: 工具名称

        返回:
            工具定义，如果不存在则返回 None
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def has_permission(self, permission: str) -> bool:
        """
        检查是否拥有指定权限

        参数:
            permission: 权限名称

        返回:
            是否拥有权限
        """
        return permission in self.permissions

    def get_summary(self) -> Dict[str, Any]:
        """
        获取清单摘要信息

        返回:
            摘要字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'category': self.category.value,
            'tools_count': len(self.tools),
            'permissions_count': len(self.permissions),
            'dependencies_count': len(self.dependencies)
        }


def generate_manifest_template(
    plugin_id: str,
    plugin_name: str,
    output_path: str = "manifest.json"
) -> PluginManifest:
    """
    生成插件清单模板

    用于快速创建新插件的清单文件。

    参数:
        plugin_id: 插件 ID（如 "com.example.my_plugin"）
        plugin_name: 插件名称
        output_path: 输出文件路径

    返回:
        生成的清单实例

    示例:
        manifest = generate_manifest_template(
            "com.example.scanner",
            "Network Scanner"
        )
        manifest.save("plugins/scanner/manifest.json")
    """
    manifest = PluginManifest(
        id=plugin_id,
        name=plugin_name,
        version="1.0.0",
        description="Plugin description here",
        author="Your Name",
        license="MIT",
        category=PluginCategory.UTILITY,
        tags=["example"],
        entry_point=f"{plugin_id.split('.')[-1]}.Plugin",
        tools=[
            ToolDefinition(
                name="example_tool",
                description="Tool description here",
                entry_point=f"{plugin_id.split('.')[-1]}.tools.example_tool",
                input_schema={
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Parameter description"
                        }
                    },
                    "required": ["param1"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            )
        ],
        permissions=[PermissionType.NETWORK_ACCESS.value],
        resources=ResourceRequirements(
            memory_mb=256,
            cpu_cores=0.5
        ),
        config_schema={
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "API key for authentication"
                }
            }
        },
        default_config={
            "timeout": 30
        }
    )

    manifest.save(output_path)
    return manifest


# 向后兼容：提供与旧 PluginInfo 的转换
def manifest_to_plugin_info(manifest: PluginManifest) -> 'PluginInfo':
    """
    将 PluginManifest 转换为旧的 PluginInfo 格式

    用于向后兼容现有代码。

    参数:
        manifest: 插件清单

    返回:
        PluginInfo 实例
    """
    from .plugin_manager import PluginInfo

    return PluginInfo(
        name=manifest.id,
        version=manifest.version,
        description=manifest.description,
        author=manifest.author,
        dependencies=manifest.dependencies,
        entry_point=manifest.entry_point,
        config_schema=manifest.config_schema,
        min_api_version=manifest.min_api_version,
        max_api_version=manifest.max_api_version
    )
