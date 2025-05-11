import base64
import inspect
import subprocess
import traceback
import asyncio
import logging
import os
import shutil
from typing import List, Dict, Any, Optional, Union, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from pydantic import BaseModel

from fastapi import HTTPException
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.stdio import get_default_environment
from mcp.client.sse import sse_client

# 配置日志记录
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 导入共享的服务器实例字典
from .server_utils import _server_instances

class Server:
    """管理 MCP 服务器连接和工具执行。"""

    def __init__(self, command: str, args: list, env: dict | None = None, name: str = "default") -> None:
        """使用连接参数初始化服务器实例。
        
        参数：
            command: 待执行的命令。
            args: 命令的参数列表。
            env: 命令所需的环境变量（可选）。
            name: 此服务器实例的名称。
        """
        self.name: str = name
        self.command: str = command
        self.args: list = args
        
        if env is None:
            self.env = get_default_environment()
        else:
            default_env = get_default_environment()
            default_env.update(env)
            self.env = default_env
            
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """初始化服务器连接。"""
        if self.command is None:
            raise ValueError("命令必须为有效字符串，且不能为 None。")

        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )
        
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
            logging.info(f"服务器 {self.name} 初始化成功")
        except Exception as e:
            logging.error(f"服务器 {self.name} 初始化时出错: {e}")
            await self.cleanup()
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """通过重试机制执行一个工具。

        参数：
            tool_name: 要执行的工具名称。
            arguments: 工具调用参数。
            retries: 重试次数（初始尝试不计重试）。
            delay: 重试之间的延迟（秒）。

        返回：
            工具执行结果。

        异常：
            RuntimeError: 如果服务器未初始化。
            Exception: 如果在所有重试后工具执行仍失败。
        """
        if not self.session:
            raise RuntimeError(f"服务器 {self.name} 未初始化")

        attempt = 0
        while attempt < retries + 1:  # +1 表示第一次尝试不计为重试
            try:
                logging.info(f"正在执行 {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)
                return result
            except Exception as e:
                attempt += 1
                if attempt <= retries:
                    logging.warning(
                        f"执行工具时出错: {e}。第 {attempt} 次尝试，共 {retries} 次重试。"
                    )
                    logging.info(f"{delay} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("达到最大重试次数，执行失败。")
                    raise

    async def list_tools(self) -> Any:
        """列出服务器上可用的工具。

        返回：
            一个包含可用工具的列表。

        异常：
            RuntimeError: 如果服务器未初始化。
        """
        if not self.session:
            raise RuntimeError(f"服务器 {self.name} 未初始化")

        return await self.session.list_tools()

    async def cleanup(self) -> None:
        """清理服务器资源。"""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                
                # 从全局实例字典中移除此服务器实例
                for key, srv in list(_server_instances.items()):
                    if srv is self:
                        del _server_instances[key]
                        logging.info(f"已从实例注册表中移除服务器 {self.name}")
                        break
            except Exception as e:
                logging.error(f"清理服务器 {self.name} 时出错: {e}")

class SSEServer:
    """管理基于 SSE 的 MCP 服务器连接和工具执行。"""

    def __init__(self, url: str, name: str = "default") -> None:
        """使用连接参数初始化 SSE 服务器实例。
        
        参数：
            url: SSE 服务器的 URL。
            name: 此服务器实例的名称。
        """
        self.name: str = name
        self.url: str = url
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """初始化 SSE 服务器连接。"""
        try:
            sse_transport = await self.exit_stack.enter_async_context(
                sse_client(self.url)
            )
            read, write = sse_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
            logging.info(f"SSE 服务器 {self.name} 初始化成功")
        except Exception as e:
            logging.error(f"SSE 服务器 {self.name} 初始化时出错: {e}")
            await self.cleanup()
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """通过重试机制执行一个工具。

        参数：
            tool_name: 要执行的工具名称。
            arguments: 工具调用参数。
            retries: 重试次数。
            delay: 重试之间的延迟（秒）。

        返回：
            工具执行结果。

        异常：
            RuntimeError: 如果服务器未初始化。
            Exception: 如果所有重试后工具执行仍失败。
        """
        if not self.session:
            raise RuntimeError(f"SSE 服务器 {self.name} 未初始化")

        attempt = 0
        while attempt < retries + 1:
            try:
                logging.info(f"正在执行 {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)
                return result
            except Exception as e:
                attempt += 1
                if attempt <= retries:
                    logging.warning(
                        f"执行工具时出错: {e}。第 {attempt} 次尝试，共 {retries} 次重试。"
                    )
                    logging.info(f"{delay} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("达到最大重试次数，执行失败。")
                    raise

    async def list_tools(self) -> Any:
        """列出服务器上可用的工具。

        返回：
            一个包含可用工具的列表。

        异常：
            RuntimeError: 如果服务器未初始化。
        """
        if not self.session:
            raise RuntimeError(f"SSE 服务器 {self.name} 未初始化")

        return await self.session.list_tools()

    async def cleanup(self) -> None:
        """清理服务器资源。"""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                
                # 从全局实例字典中移除此服务器实例
                for key, srv in list(_server_instances.items()):
                    if srv is self:
                        del _server_instances[key]
                        logging.info(f"已从实例注册表中移除 SSE 服务器 {self.name}")
                        break
            except Exception as e:
                logging.error(f"清理 SSE 服务器 {self.name} 时出错: {e}")

def install_library_(library):
    try:
        result = subprocess.run(
            ["uv", "pip", "install", library],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def uninstall_library_(library):
    try:
        result = subprocess.run(
            ["uv", "pip", "uninstall", "-y", library],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def add_tool_(function, description: str = "", properties: Dict[str, Any] = None, required: List[str] = None):
    """
    将一个函数添加到已注册工具中。
    
    参数：
        function: 要注册为工具的函数。
    """
    from ..server.function_tools import tool
    # 使用空描述应用 tool 装饰器
    decorated_function = tool(description=description, custom_properties=properties, custom_required=required)(function)
    return decorated_function

import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
from fastapi import HTTPException
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters

import asyncio
from contextlib import asynccontextmanager
# 创建标准输入输出连接的服务器参数

from .api import app, timeout

from ...tools import MCPRag

try:
    add_tool_(MCPRag)
except Exception as e:
    logging.error(f"添加 MCPRag 工具时出错: {e}")
    raise  

prefix = "/tools"

class InstallLibraryRequest(BaseModel):
    library: str

@app.post(f"{prefix}/install_library")
@timeout(30.0)
async def install_library(request: InstallLibraryRequest):
    """
    安装库的端点。

    参数：
        library: 要安装的库名称

    返回：
        一个成功消息
    """
    install_library_(request.library)
    return {"message": "Library installed successfully"}

@app.post(f"{prefix}/uninstall_library")
@timeout(30.0)
async def uninstall_library(request: InstallLibraryRequest):
    """
    卸载库的端点。
    """
    uninstall_library_(request.library)
    return {"message": "Library uninstalled successfully"}

class AddToolRequest(BaseModel):
    function: str

@app.post(f"{prefix}/add_tool")
@timeout(30.0)
async def add_tool(request: AddToolRequest):
    """
    添加工具的端点。
    """
    # 对函数进行 cloudpickle 编码
    decoded_function = base64.b64decode(request.function)
    deserialized_function = cloudpickle.loads(decoded_function)
    add_tool_(deserialized_function)
    return {"message": "Tool added successfully"}

class AddMCPToolRequest(BaseModel):
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]

class AddSSEMCPToolRequest(BaseModel):
    name: str
    url: str

async def add_mcp_tool_(name: str, command: str, args: List[str], env: Dict[str, str]):
    """
    从 MCP 服务器添加工具。
    
    参数：
        name: 工具的名称前缀。
        command: 待执行的命令。
        args: 命令的参数列表。
        env: 命令的环境变量。
    """
    def get_python_type(schema_type: str, format: Optional[str] = None) -> type:
        """将 JSON schema 类型转换为 Python 类型。"""
        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "number": float,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(schema_type, Any)

    # 为服务器实例创建一个可哈希的键
    env_items = frozenset(env.items()) if env else frozenset()
    server_key = (name, command, tuple(args), env_items)
    
    # 检查是否已经存在配置相同的服务器实例
    if server_key in _server_instances:
        server = _server_instances[server_key]
        logging.info(f"重用已有的服务器实例 {name}")
    else:
        # 创建新的服务器实例
        server = Server(command=command, args=args, env=env, name=name)
        _server_instances[server_key] = server
        if server.session is None:
            await server.initialize()
        logging.info(f"为 {name} 创建了新的服务器实例")
    
    try:
        tools_response = await server.list_tools()
        tools = tools_response.tools
        for tool in tools:
            tool_name: str = tool.name
            tool_desc: str = tool.description
            input_schema: Dict[str, Any] = tool.inputSchema
            properties: Dict[str, Dict[str, Any]] = input_schema.get("properties", {})
            required: List[str] = input_schema.get("required", [])

            def create_tool_function(
                tool_name: str,
                properties: Dict[str, Dict[str, Any]],
                required: List[str],
            ) -> Callable[..., Dict[str, Any]]:
                # 创建函数参数的类型注解
                annotations = {}
                defaults = {}

                # 首先添加必需参数
                for param_name in required:
                    param_info = properties[param_name]
                    param_type = get_python_type(param_info.get("type", "any"))
                    annotations[param_name] = param_type

                # 然后添加可选参数
                for param_name, param_info in properties.items():
                    if param_name not in required:
                        param_type = get_python_type(param_info.get("type", "any"))
                        annotations[param_name] = param_type
                        defaults[param_name] = param_info.get("default", None)

                # 创建函数签名的参数列表
                from inspect import Parameter, Signature
                parameters = []
                # 先添加必需参数
                for param_name in required:
                    param_type = annotations[param_name]
                    parameters.append(
                        Parameter(
                            name=param_name,
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=param_type
                        )
                    )
                
                # 然后添加可选参数
                for param_name, param_type in annotations.items():
                    if param_name not in required:
                        parameters.append(
                            Parameter(
                                name=param_name,
                                kind=Parameter.POSITIONAL_OR_KEYWORD,
                                annotation=param_type,
                                default=defaults[param_name]
                            )
                        )

                async def tool_function(*args: Any, **kwargs: Any) -> Dict[str, Any]:
                    # 将位置参数转换为关键字参数
                    if len(args) > len(required):
                        raise TypeError(
                            f"{tool_name}() 需要 {len(required)} 个位置参数，但给定了 {len(args)} 个"
                        )

                    # 合并位置参数与关键字参数
                    all_kwargs = kwargs.copy()
                    for i, arg in enumerate(args):
                        if i < len(required):
                            all_kwargs[required[i]] = arg

                    # 验证必需参数
                    for req in required:
                        if req not in all_kwargs:
                            raise ValueError(f"缺少必需参数: {req}")

                    # 为可选参数添加默认值
                    for param, default in defaults.items():
                        if param not in all_kwargs:
                            all_kwargs[param] = default

                    try:
                        # 移除值为 None 的关键字参数
                        all_kwargs = {k: v for k, v in all_kwargs.items() if v is not None}
                        result = await server.execute_tool(tool_name=tool_name, arguments=all_kwargs)
                        return {"result": result}
                    except Exception as e:
                        logging.error(f"执行工具 {tool_name} 时出错: {str(e)}")
                        raise

                # 设置函数名称和注解
                tool_function.__name__ = tool_name
                tool_function.__annotations__ = {
                    **annotations,
                    "return": Dict[str, Any],
                }
                tool_function.__doc__ = f"{tool_desc}\n\nReturns:\n    Tool execution results"
                # 为函数创建并设置签名
                tool_function.__signature__ = Signature(
                    parameters=parameters,
                    return_annotation=Dict[str, Any]
                )
                # 将会话参数作为函数的属性存储
                tool_function.command = command
                tool_function.args = args
                tool_function.env = env

                return tool_function

            # 使用适当的注解创建函数
            func = create_tool_function(tool_name, properties, required)
            # 函数名称应为 name__function_name
            full_name = f"{name}__{tool_name}"
            func.__name__ = full_name

            add_tool_(func, description=tool_desc, properties=properties, required=required)
    except Exception as e:
        logging.error(f"add_mcp_tool_ 出错: {e}")
        await server.cleanup()
        raise
    # 此处不清理服务器以便后续使用

@app.post(f"{prefix}/add_mcp_tool")
@timeout(60.0)
async def add_mcp_tool(request: AddMCPToolRequest):
    """
    添加工具的端点。
    """
    await add_mcp_tool_(request.name, request.command, request.args, request.env)
    return {"message": "Tool added successfully"}

@app.post(f"{prefix}/add_sse_mcp")
@timeout(60.0)
async def add_sse_mcp(request: AddSSEMCPToolRequest):
    """
    添加工具的端点（通过 SSE MCP）。
    """
    await add_sse_mcp_(request.name, request.url)
    return {"message": "Tool added successfully"}

async def add_sse_mcp_(name: str, url: str):
    """
    从 SSE MCP 服务器添加工具。
    
    参数：
        name: 工具的名称前缀。
        url: SSE 服务器的 URL。
    """
    def get_python_type(schema_type: str, format: Optional[str] = None) -> type:
        """将 JSON schema 类型转换为 Python 类型。"""
        type_mapping = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "number": float,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(schema_type, Any)

    # 为服务器实例创建一个可哈希的键
    server_key = (name, url)
    
    # 检查是否已存在该配置的服务器实例
    if server_key in _server_instances:
        server = _server_instances[server_key]
        logging.info(f"重用已有的 SSE 服务器实例 {name}")
    else:
        # 创建新的 SSE 服务器实例
        server = SSEServer(url=url, name=name)
        _server_instances[server_key] = server
        if server.session is None:
            await server.initialize()
        logging.info(f"为 {name} 创建了新的 SSE 服务器实例")
    
    try:
        tools_response = await server.list_tools()
        tools = tools_response.tools
        for tool in tools:
            tool_name: str = tool.name
            tool_desc: str = tool.description
            input_schema: Dict[str, Any] = tool.inputSchema
            properties: Dict[str, Dict[str, Any]] = input_schema.get("properties", {})
            required: List[str] = input_schema.get("required", [])

            def create_tool_function(
                tool_name: str,
                properties: Dict[str, Dict[str, Any]],
                required: List[str],
            ) -> Callable[..., Dict[str, Any]]:
                # 创建函数参数的类型注解
                annotations = {}
                defaults = {}
                # 先添加必需参数
                for param_name in required:
                    param_info = properties[param_name]
                    param_type = get_python_type(param_info.get("type", "any"))
                    annotations[param_name] = param_type
                # 然后添加可选参数
                for param_name, param_info in properties.items():
                    if param_name not in required:
                        param_type = get_python_type(param_info.get("type", "any"))
                        annotations[param_name] = param_type
                        defaults[param_name] = param_info.get("default", None)
                # 创建函数签名
                from inspect import Parameter, Signature
                parameters = []
                # 先添加必需参数
                for param_name in required:
                    param_type = annotations[param_name]
                    parameters.append(
                        Parameter(
                            name=param_name,
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=param_type
                        )
                    )
                # 然后添加可选参数
                for param_name, param_type in annotations.items():
                    if param_name not in required:
                        parameters.append(
                            Parameter(
                                name=param_name,
                                kind=Parameter.POSITIONAL_OR_KEYWORD,
                                annotation=param_type,
                                default=defaults[param_name]
                            )
                        )
                async def tool_function(*args: Any, **kwargs: Any) -> Dict[str, Any]:
                    # 将位置参数转换为关键字参数
                    if len(args) > len(required):
                        raise TypeError(
                            f"{tool_name}() 需要 {len(required)} 个位置参数，但给定了 {len(args)} 个"
                        )
                    # 合并位置参数和关键字参数
                    all_kwargs = kwargs.copy()
                    for i, arg in enumerate(args):
                        if i < len(required):
                            all_kwargs[required[i]] = arg
                    # 验证必需参数
                    for req in required:
                        if req not in all_kwargs:
                            raise ValueError(f"缺少必需参数: {req}")
                    # 为可选参数添加默认值
                    for param, default in defaults.items():
                        if param not in all_kwargs:
                            all_kwargs[param] = default
                    try:
                        # 移除值为 None 的关键字参数
                        all_kwargs = {k: v for k, v in all_kwargs.items() if v is not None}
                        result = await server.execute_tool(tool_name=tool_name, arguments=all_kwargs)
                        return {"result": result}
                    except Exception as e:
                        logging.error(f"执行工具 {tool_name} 时出错: {str(e)}")
                        raise
                # 设置函数名称和注解
                tool_function.__name__ = tool_name
                tool_function.__annotations__ = {
                    **annotations,
                    "return": Dict[str, Any],
                }
                tool_function.__doc__ = f"{tool_desc}\n\nReturns:\n    Tool execution results"
                # 创建并设置函数签名
                tool_function.__signature__ = Signature(
                    parameters=parameters,
                    return_annotation=Dict[str, Any]
                )
                # 将服务器 URL 存储为函数属性
                tool_function.url = url
                return tool_function

            # 使用适当的注解创建函数
            func = create_tool_function(tool_name, properties, required)
            # 函数名称应为 name__function_name
            full_name = f"{name}__{tool_name}"
            func.__name__ = full_name

            add_tool_(func, description=tool_desc, properties=properties, required=required)
    except Exception as e:
        logging.error(f"add_sse_mcp_ 出错: {e}")
        await server.cleanup()
        raise
    # 此处不清理服务器以便后续使用