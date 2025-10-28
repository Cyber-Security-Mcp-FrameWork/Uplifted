"""
OpenAPI 文档配置和增强

为 Uplifted API 提供完整的 OpenAPI 3.0 规范配置，包括：
- 详细的 API 元数据
- 服务器配置
- 安全方案
- 标签分组
- 外部文档链接
- 联系信息

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def get_openapi_metadata() -> Dict[str, Any]:
    """
    获取 OpenAPI 元数据配置

    Returns:
        包含完整 OpenAPI 元数据的字典
    """
    return {
        "title": "Uplifted API",
        "version": "1.0.0",
        "description": """
# Uplifted API 文档

**Uplifted** 是一款企业级安全智能框架，专注于黑客领域的 Agent 安全智能。

## 功能特性

- 🔌 **插件系统**: 动态加载和管理安全工具插件
- 🛠️ **MCP 集成**: 支持 Model Context Protocol 工具桥接
- ⚙️ **配置管理**: 灵活的配置加载和管理系统
- 📊 **监控和日志**: 完整的系统状态监控

## API 分组

本 API 按照功能分为以下几个主要部分：

### 🔌 插件管理 (Plugins)
管理系统中的插件，包括列出、查询、激活和停用插件。

### 🛠️ 工具管理 (Tools)
管理 MCP 工具，包括查询工具信息、输入schema和来源。

### 📊 系统监控 (System)
获取系统状态、健康检查和运行时信息。

## 认证

部分端点可能需要 API 密钥认证。请在请求头中包含：

```
X-API-Key: your-api-key
```

## 速率限制

默认速率限制为每分钟 60 个请求。超过限制将返回 429 状态码。

## 错误处理

所有错误响应遵循统一格式：

```json
{
    "detail": "错误描述信息"
}
```

常见 HTTP 状态码：
- `200`: 成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 无权限
- `404`: 资源不存在
- `408`: 请求超时
- `429`: 速率限制
- `500`: 服务器内部错误

## 版本历史

- **v1.0.0** (2025-10-28): 初始版本
  - 插件管理 API
  - 工具查询 API
  - 系统状态 API

## 支持

- 文档: https://uplifted.ai/docs
- GitHub: https://github.com/uplifted/uplifted
- Issues: https://github.com/uplifted/uplifted/issues
        """,
        "terms_of_service": "https://uplifted.ai/terms",
        "contact": {
            "name": "Uplifted Team",
            "url": "https://uplifted.ai",
            "email": "support@uplifted.ai"
        },
        "license_info": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
    }


def get_openapi_servers() -> List[Dict[str, Any]]:
    """
    获取 API 服务器配置

    Returns:
        服务器配置列表
    """
    return [
        {
            "url": "http://localhost:7541",
            "description": "本地开发服务器"
        },
        {
            "url": "https://api.uplifted.ai",
            "description": "生产环境"
        },
        {
            "url": "https://staging-api.uplifted.ai",
            "description": "测试环境"
        }
    ]


def get_openapi_tags() -> List[Dict[str, Any]]:
    """
    获取 API 标签分组配置

    Returns:
        标签配置列表
    """
    return [
        {
            "name": "plugins",
            "description": """
## 插件管理

插件是 Uplifted 系统的核心扩展机制。通过这些端点，您可以：

- 📋 列出所有已安装的插件
- 🔍 查询特定插件的详细信息
- 🛠️ 获取插件提供的工具列表
- ⚙️ 管理插件状态（激活/停用）

每个插件都包含完整的元数据，包括版本、作者、依赖关系等。
            """,
            "externalDocs": {
                "description": "插件开发指南",
                "url": "https://uplifted.ai/docs/plugin-development"
            }
        },
        {
            "name": "tools",
            "description": """
## 工具管理

工具是插件提供的具体功能实现。通过这些端点，您可以：

- 📋 列出所有可用工具
- 🔍 查询工具的详细信息
- 📝 获取工具的输入 schema
- 🔗 追踪工具的来源插件

所有工具都遵循 MCP (Model Context Protocol) 标准。
            """,
            "externalDocs": {
                "description": "MCP 协议规范",
                "url": "https://modelcontextprotocol.io"
            }
        },
        {
            "name": "system",
            "description": """
## 系统监控

系统监控端点提供实时的运行状态信息：

- ✅ 健康检查
- 📊 系统统计
- 🔌 插件统计
- 🛠️ 工具统计
- 📈 性能指标

用于监控、告警和负载均衡。
            """,
            "externalDocs": {
                "description": "监控指南",
                "url": "https://uplifted.ai/docs/monitoring"
            }
        }
    ]


def get_openapi_security_schemes() -> Dict[str, Any]:
    """
    获取安全方案配置

    Returns:
        安全方案字典
    """
    return {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API 密钥认证。在请求头中包含 `X-API-Key: your-api-key`"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer Token 认证（未来支持）"
        }
    }


def get_openapi_external_docs() -> Dict[str, str]:
    """
    获取外部文档链接

    Returns:
        外部文档配置
    """
    return {
        "description": "完整文档",
        "url": "https://uplifted.ai/docs"
    }


def custom_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """
    生成自定义的 OpenAPI schema

    Args:
        app: FastAPI 应用实例

    Returns:
        完整的 OpenAPI 3.0 schema
    """
    if app.openapi_schema:
        return app.openapi_schema

    # 获取基本的 OpenAPI schema
    metadata = get_openapi_metadata()
    openapi_schema = get_openapi(
        title=metadata["title"],
        version=metadata["version"],
        description=metadata["description"],
        routes=app.routes,
        terms_of_service=metadata.get("terms_of_service"),
        contact=metadata.get("contact"),
        license_info=metadata.get("license_info"),
    )

    # 添加服务器配置
    openapi_schema["servers"] = get_openapi_servers()

    # 添加标签配置
    openapi_schema["tags"] = get_openapi_tags()

    # 添加安全方案
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = get_openapi_security_schemes()

    # 添加外部文档
    openapi_schema["externalDocs"] = get_openapi_external_docs()

    # 添加 x-logo 扩展（用于某些文档生成器）
    openapi_schema["info"]["x-logo"] = {
        "url": "https://uplifted.ai/logo.png",
        "altText": "Uplifted Logo"
    }

    # 缓存 schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def configure_openapi(app: FastAPI) -> None:
    """
    配置 FastAPI 应用的 OpenAPI 设置

    Args:
        app: FastAPI 应用实例
    """
    # 设置自定义 OpenAPI schema 生成函数
    app.openapi = lambda: custom_openapi_schema(app)

    # 配置文档 URLs
    app.docs_url = "/docs"  # Swagger UI
    app.redoc_url = "/redoc"  # ReDoc
    app.openapi_url = "/openapi.json"  # OpenAPI JSON


def export_openapi_schema(app: FastAPI, output_path: str) -> None:
    """
    导出 OpenAPI schema 到文件

    Args:
        app: FastAPI 应用实例
        output_path: 输出文件路径（JSON 或 YAML）
    """
    import json
    from pathlib import Path

    schema = custom_openapi_schema(app)
    output_file = Path(output_path)

    if output_file.suffix == ".json":
        # 导出为 JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
    elif output_file.suffix in (".yaml", ".yml"):
        # 导出为 YAML
        try:
            import yaml
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(schema, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except ImportError:
            raise ImportError("需要安装 PyYAML 才能导出 YAML 格式: pip install pyyaml")
    else:
        raise ValueError(f"不支持的文件格式: {output_file.suffix}。支持 .json, .yaml, .yml")

    print(f"OpenAPI schema 已导出到: {output_file}")


# ============================================================================
# API 响应示例
# ============================================================================

OPENAPI_EXAMPLES = {
    "plugin_info": {
        "summary": "插件信息示例",
        "value": {
            "name": "security_scanner",
            "version": "1.2.0",
            "description": "安全扫描插件，提供漏洞检测工具",
            "author": "Security Team",
            "status": "active",
            "dependencies": ["base_plugin"]
        }
    },
    "plugin_detail": {
        "summary": "插件详细信息示例",
        "value": {
            "name": "security_scanner",
            "version": "1.2.0",
            "description": "安全扫描插件，提供漏洞检测工具",
            "author": "Security Team",
            "status": "active",
            "dependencies": ["base_plugin"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "scan_depth": {"type": "integer", "default": 3},
                    "timeout": {"type": "integer", "default": 300}
                }
            },
            "min_api_version": "1.0.0",
            "max_api_version": "2.0.0",
            "tools_count": 5
        }
    },
    "tool_info": {
        "summary": "工具信息示例",
        "value": {
            "name": "security_scanner.port_scan",
            "plugin_id": "security_scanner",
            "description": "端口扫描工具",
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "目标 IP 或域名"},
                    "ports": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["target"]
            },
            "registered_at": "2025-10-28T10:00:00Z",
            "active": True
        }
    },
    "system_status": {
        "summary": "系统状态示例",
        "value": {
            "plugin_count": 12,
            "active_plugin_count": 10,
            "total_tools": 45,
            "active_tools": 42,
            "mcp_available": True
        }
    },
    "error": {
        "summary": "错误响应示例",
        "value": {
            "detail": "插件 'unknown_plugin' 不存在"
        }
    }
}
