import traceback
from fastapi import HTTPException
from pydantic import BaseModel
import inspect
from typing import Any, Dict, List, Type, Callable
from functools import wraps

from .api import app, timeout

prefix = "/functions"

# 用于存储已装饰函数的注册表
registered_functions: Dict[str, Dict[str, Any]] = {}

def _get_json_type(python_type: Type) -> str:
    """将 Python 类型转换为 JSON schema 类型。"""
    type_mapping = {
        str: "string",
        int: "integer",
        bool: "boolean",
        float: "number",
        list: "array",
        dict: "object",
    }
    return type_mapping.get(python_type, "string")

def tool(description: str = "", custom_properties: Dict[str, Any] = None, custom_required: List[str] = None):
    """
    装饰器，用于将函数注册为工具。

    参数：
        description: 工具的可选描述。如果未提供，则使用函数的文档字符串。
    """
    def decorator(func: Callable):
        sig = inspect.signature(func)

        # 获取参数信息
        properties = {}
        required = []

        # 如果未提供描述，则从文档字符串中提取第一行作为描述
        tool_description = description
        if not tool_description and func.__doc__:
            tool_description = func.__doc__.strip().split('\n')[0].strip()

        for param_name, param in sig.parameters.items():
            param_type = (
                param.annotation if param.annotation != inspect.Parameter.empty else Any
            )
            param_default = (
                None if param.default == inspect.Parameter.empty else param.default
            )

            properties[param_name] = {
                "type": _get_json_type(param_type),
                "description": f"参数 {param_name}",
            }

            if param_default is not None:
                properties[param_name]["default"] = param_default

            # 如果参数没有默认值，则为必需参数
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        if custom_properties is not None:
            properties = custom_properties

        if custom_required is not None:
            required = custom_required

        # 使用提取的描述注册该函数
        registered_functions[func.__name__] = {
            "function": func,
            "description": tool_description,
            "properties": properties,
            "required": required,
        }

        # 检查函数是否为异步函数
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        return wrapper

    return decorator

class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict

@app.post(f"{prefix}/tools")
@timeout(30.0)
async def list_tools():
    tools = []
    for name, info in registered_functions.items():
        # 如果描述长度超过 1024 个字符，则截断描述
        description = info["description"]
        if len(description) > 1024:
            description = description[:1020] + "..."
            
        tools.append(
            {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": info["properties"],
                    "required": info["required"],
                },
            }
        )

    print(tools)    
    return {"available_tools": {"tools": tools}}

@app.post(f"{prefix}/call_tool")
@timeout(30.0)
async def call_tool(request: ToolRequest):
    print("调用工具")
    print(request)

    if request.tool_name not in registered_functions:
        raise HTTPException(
            status_code=404, detail=f"未找到工具 {request.tool_name}"
        )

    try:
        func = registered_functions[request.tool_name]["function"]
        # 检查函数是否为异步函数
        is_async = inspect.iscoroutinefunction(func)
        
        if is_async:
            result = await func(**request.arguments)
        else:
            result = func(**request.arguments)
            
        print("工具结果")
        print(result)

        return {"result": result}
    except Exception as e:
        traceback.print_exc()
        return {"status_code": 500, "detail": f"调用工具失败: {str(e)}"}

# 示例装饰函数
# @tool()
# async def add_numbers(a: int, b: int, c: int = 0) -> int:
#     "将两个数字相加"
#     return a + b + c

# @tool()
# def concat_strings(str1: str, str2: str) -> str:
#     "连接两个字符串"
#     return str1 + str2

# @tool()
# def Search__duckduckgo(query: str, max_results: int = 20) -> list:
#     """
#     在 DuckDuckGo 上搜索查询，并返回结果。
#     """
#     try:
#         from duckduckgo_search import DDGS

#         return list(DDGS().text(query, max_results=max_results))
#     except:
#         return "发生异常"
    
# import re
# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
# @tool()
# def Search__read_website(url: str, max_content_length: int = 5000) -> dict:
#     """
#     读取网站内容并返回标题、元数据、内容和子链接。
#     """
#     try:
#         response = requests.get(url, timeout=10.0)
#         response.raise_for_status()
#         html = response.text
#     except requests.RequestException as e:
#         return {"error": f"获取网站内容失败: {e}"}

#     soup = BeautifulSoup(html, "html.parser")

#     meta_properties = [
#         "og:description",
#         "og:site_name",
#         "og:title",
#         "og:type",
#         "og:url",
#         "description",
#         "keywords",
#         "author",
#     ]
#     meta = {}
#     for property_name in meta_properties:
#         tag = soup.find("meta", property=property_name) or soup.find(
#             "meta", attrs={"name": property_name}
#         )
#         if tag:
#             meta[property_name] = tag.get("content", "")

#     for ignore_tag in soup(["script", "style"]):
#         ignore_tag.decompose()

#     title = soup.title.string.strip() if soup.title else ""
#     content = soup.body.get_text(separator="\n") if soup.body else ""

#     links = []
#     for a in soup.find_all("a", href=True):
#         link_url = urljoin(url, a["href"])
#         links.append({"title": a.text.strip(), "link": link_url})

#     content = re.sub(r"[\n\r\t]+", "\n", content)
#     content = re.sub(r" +", " ", content)
#     content = re.sub(r"[\n ]{3,}", "\n\n", content)
#     content = content.strip()

#     if len(content) > max_content_length:
#         content = content[:max_content_length].rsplit(" ", 1)[0] + "..."

#     return {"meta": meta, "title": title, "content": content, "sub_links": links}