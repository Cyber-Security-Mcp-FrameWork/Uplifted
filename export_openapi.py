#!/usr/bin/env python3
"""
OpenAPI Schema 导出工具

用于导出 Uplifted API 的 OpenAPI 3.0 规范到文件。

Usage:
    python export_openapi.py                          # 导出为 JSON (默认)
    python export_openapi.py --format yaml            # 导出为 YAML
    python export_openapi.py --output api-spec.json  # 自定义输出路径
    python export_openapi.py --print                  # 打印到标准输出
    python export_openapi.py --validate               # 验证 schema

作者: Uplifted Team
日期: 2025-10-28
"""

import argparse
import json
import sys
from pathlib import Path


def export_schema(output_path: str = None, format: str = "json", print_output: bool = False) -> None:
    """
    导出 OpenAPI schema

    Args:
        output_path: 输出文件路径
        format: 输出格式 (json/yaml)
        print_output: 是否打印到标准输出
    """
    try:
        # 导入 FastAPI 应用
        from server.uplifted.server.api import app
        from server.uplifted.server.openapi_config import (
            configure_openapi,
            custom_openapi_schema,
            export_openapi_schema
        )

        # 配置 OpenAPI
        configure_openapi(app)

        # 生成 schema
        schema = custom_openapi_schema(app)

        if print_output:
            # 打印到标准输出
            if format == "yaml":
                try:
                    import yaml
                    print(yaml.dump(schema, default_flow_style=False, allow_unicode=True, sort_keys=False))
                except ImportError:
                    print("错误: 需要安装 PyYAML 才能输出 YAML 格式", file=sys.stderr)
                    print("安装命令: pip install pyyaml", file=sys.stderr)
                    sys.exit(1)
            else:
                print(json.dumps(schema, indent=2, ensure_ascii=False))
        else:
            # 导出到文件
            if not output_path:
                # 默认输出路径
                if format == "yaml":
                    output_path = "openapi.yaml"
                else:
                    output_path = "openapi.json"

            export_openapi_schema(app, output_path)
            print(f"✓ OpenAPI schema 已成功导出到: {output_path}")

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def validate_schema() -> bool:
    """
    验证 OpenAPI schema 的正确性

    Returns:
        True 如果 schema 有效，否则 False
    """
    try:
        from server.uplifted.server.api import app
        from server.uplifted.server.openapi_config import configure_openapi, custom_openapi_schema

        configure_openapi(app)
        schema = custom_openapi_schema(app)

        # 基本验证
        required_fields = ["openapi", "info", "paths"]
        for field in required_fields:
            if field not in schema:
                print(f"✗ 缺少必需字段: {field}", file=sys.stderr)
                return False

        # 验证 OpenAPI 版本
        if not schema["openapi"].startswith("3."):
            print(f"✗ OpenAPI 版本不正确: {schema['openapi']}", file=sys.stderr)
            return False

        # 验证 info 字段
        info_required = ["title", "version"]
        for field in info_required:
            if field not in schema["info"]:
                print(f"✗ info 中缺少必需字段: {field}", file=sys.stderr)
                return False

        # 统计信息
        num_paths = len(schema.get("paths", {}))
        num_schemas = len(schema.get("components", {}).get("schemas", {}))
        num_tags = len(schema.get("tags", []))

        print("✓ OpenAPI schema 验证通过")
        print(f"  - OpenAPI 版本: {schema['openapi']}")
        print(f"  - API 标题: {schema['info']['title']}")
        print(f"  - API 版本: {schema['info']['version']}")
        print(f"  - 路径数量: {num_paths}")
        print(f"  - Schema 数量: {num_schemas}")
        print(f"  - 标签数量: {num_tags}")

        return True

    except Exception as e:
        print(f"✗ 验证失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def generate_markdown_docs(output_path: str = "api-docs.md") -> None:
    """
    生成 Markdown 格式的 API 文档

    Args:
        output_path: 输出文件路径
    """
    try:
        from server.uplifted.server.api import app
        from server.uplifted.server.openapi_config import configure_openapi, custom_openapi_schema

        configure_openapi(app)
        schema = custom_openapi_schema(app)

        with open(output_path, "w", encoding="utf-8") as f:
            # 写入标题和基本信息
            info = schema["info"]
            f.write(f"# {info['title']}\n\n")
            f.write(f"**版本**: {info['version']}\n\n")
            if "description" in info:
                f.write(f"{info['description']}\n\n")

            # 写入服务器信息
            if "servers" in schema:
                f.write("## 服务器\n\n")
                for server in schema["servers"]:
                    f.write(f"- **{server['description']}**: `{server['url']}`\n")
                f.write("\n")

            # 写入标签分组
            if "tags" in schema:
                f.write("## API 分组\n\n")
                for tag in schema["tags"]:
                    f.write(f"### {tag['name']}\n\n")
                    if "description" in tag:
                        f.write(f"{tag['description']}\n\n")

            # 写入端点
            f.write("## API 端点\n\n")
            paths = schema.get("paths", {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        summary = details.get("summary", "")
                        f.write(f"### `{method.upper()} {path}`\n\n")
                        if summary:
                            f.write(f"**{summary}**\n\n")
                        if "description" in details:
                            f.write(f"{details['description']}\n\n")

                        # 参数
                        if "parameters" in details:
                            f.write("**参数**:\n\n")
                            for param in details["parameters"]:
                                required = "必需" if param.get("required") else "可选"
                                f.write(f"- `{param['name']}` ({param['in']}, {required}): {param.get('description', '')}\n")
                            f.write("\n")

                        # 响应
                        if "responses" in details:
                            f.write("**响应**:\n\n")
                            for status, response in details["responses"].items():
                                f.write(f"- `{status}`: {response.get('description', '')}\n")
                            f.write("\n")

        print(f"✓ Markdown 文档已生成: {output_path}")

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="导出 Uplifted API 的 OpenAPI schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 导出为 JSON (默认)
  %(prog)s --format yaml            # 导出为 YAML
  %(prog)s --output api-spec.json   # 自定义输出路径
  %(prog)s --print                  # 打印到标准输出
  %(prog)s --validate               # 验证 schema
  %(prog)s --markdown               # 生成 Markdown 文档
        """
    )

    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（默认: openapi.json 或 openapi.yaml）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "yaml"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--print", "-p",
        action="store_true",
        help="打印到标准输出而不是文件"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="验证 OpenAPI schema 的正确性"
    )
    parser.add_argument(
        "--markdown", "-m",
        action="store_true",
        help="生成 Markdown 格式的文档"
    )
    parser.add_argument(
        "--markdown-output",
        default="api-docs.md",
        help="Markdown 文档输出路径（默认: api-docs.md）"
    )

    args = parser.parse_args()

    # 验证模式
    if args.validate:
        success = validate_schema()
        sys.exit(0 if success else 1)

    # Markdown 模式
    if args.markdown:
        generate_markdown_docs(args.markdown_output)
        return

    # 导出模式
    export_schema(
        output_path=args.output,
        format=args.format,
        print_output=args.print
    )


if __name__ == "__main__":
    main()
