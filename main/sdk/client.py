# -*- coding: utf-8 -*-
from __future__ import annotations

import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import asyncio
import base64
import time
import httpx

from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar
from urllib.parse import urlparse, urlunparse

T = TypeVar("T")


class UpligtedClient:
    """Upligted 基础客户端。

    参数
    ----
    url : str
        服务端地址，如 ``http://localhost:7541``。
    timeout : float, default 10.0
        请求超时时间（秒）。
    headers : Optional[Dict[str, str]], optional
        统一注入到每个请求中的 HTTP 头。
    max_retries : int, default 3
        网络异常时的最大重试次数。
    """

    def __init__(
        self,
        url: str,
        timeout: float = 60.0,
        *,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> None:
        self.url = self._normalize_url(url)
        self.timeout = timeout
        self.headers = headers or {}
        self._max_retries = max_retries

        # 客户端实例（懒初始化）
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    def _normalize_url(self, url: str) -> str:
        """规范化 URL，处理常见的 URL 格式问题。"""
        # 使用 urlparse 来规范化 URL
        parsed_url = urlparse(url)
        # 确保 scheme 和 netloc 存在，并移除尾随斜杠
        normalized_url = urlunparse((
            parsed_url.scheme.lower(),
            parsed_url.netloc.lower(),
            parsed_url.path.rstrip('/'),
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
        return normalized_url

    # --------------------------------------------------------------------- #
    # 连接管理
    # --------------------------------------------------------------------- #
    async def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.url, timeout=self.timeout, headers=self.headers
            )
        return self._async_client

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.url, timeout=self.timeout, headers=self.headers
            )
        return self._sync_client

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def close(self) -> None:
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    # 允许  `async with UpligtedClient(...) as c:` / `with UpligtedClient(...) as c:`
    async def __aenter__(self) -> "UpligtedClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        await self.aclose()

    def __enter__(self) -> "UpligtedClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: D401
        self.close()

    # --------------------------------------------------------------------- #
    # 基础能力
    # --------------------------------------------------------------------- #
    async def _send_async(
        self,
        method: str,
        endpoint: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """底层异步请求 + 简单重试"""
        client = await self._get_async_client()
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await client.request(method, endpoint, json=json, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.TimeoutException) as exc:
                if attempt >= self._max_retries:
                    raise
                await asyncio.sleep(0.5 * attempt)  # 线性退避
            except httpx.HTTPStatusError as exc:
                # 统一业务错误处理，抛出更友好的信息
                raise RuntimeError(
                    f"Server error {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except Exception as exc:
                # 捕获其他未预料的异常
                if attempt >= self._max_retries:
                    raise

    def _send_sync(
        self,
        method: str,
        endpoint: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """底层同步请求 + 简单重试"""
        client = self._get_sync_client()
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = client.request(method, endpoint, json=json, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status >= 500 and attempt < self._max_retries:
                    time.sleep(0.5 * attempt)
                    continue
                raise
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise
            except Exception as exc:
                # 捕获其他未预料的异常
                if attempt >= self._max_retries:
                    raise

    def _ensure_sync(self, coro: Coroutine[Any, Any, T]) -> T:
        """在同步环境调用协程。

        当已处于事件循环中时抛出异常，提醒用户调用异步接口。
        """
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                raise RuntimeError(
                    "检测到正在运行的事件循环，请使用对应的异步方法 *_async()"
                )
        except RuntimeError:
            # 当前线程无事件循环
            pass
        return asyncio.run(coro)

    # ------------------------------------------------------------------ #
    # 面向外部的通用请求
    # ------------------------------------------------------------------ #
    async def _send_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = "POST",
    ) -> Any:
        """通用请求方法，支持异步调用。"""
        if method.upper() == "GET":
            return await self._send_async("GET", endpoint, params=data)
        return await self._send_async("POST", endpoint, json=data)

    def send_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = "POST",
    ) -> Any:
        """通用请求方法，支持同步调用。"""
        return self._ensure_sync(self._send_request(endpoint, data, method))

    async def send_request_async(
        self,
        endpoint: str,
        data: Dict[str, Any],
        method: str = "POST",
    ) -> Any:
        """异步请求方法，调用通用请求方法。"""
        return await self._send_request(endpoint, data, method)

    # ------------------------------------------------------------------ #
    # 通用 API
    # ------------------------------------------------------------------ #
    async def status_async(self) -> bool:
        try:
            _ = await self._send_async("GET", "/status")
            return True
        except Exception:
            return False

    def status(self) -> bool:
        return self._ensure_sync(self.status_async())

    # --------------------- 业务 API (示例) --------------------- #
    def run_agent(self, **kwargs) -> Any:
        """Level One GPT-4 生成接口（同步）"""
        if kwargs.get("response_format", None) is None:
            kwargs['response_format'] = "str"
        
        if kwargs.get('images', None) is None:
            kwargs['images'] = None
        
        if kwargs.get('tools', []) == []:
            kwargs['tools'] = []

        if kwargs.get('context', None) is None:
            kwargs['context'] = None
        else:
            pickled = cloudpickle.dumps(kwargs['context'])
            encoded = base64.b64encode(pickled).decode("utf-8")
            kwargs['context'] = encoded

        if kwargs.get('llm_model', None) is None:
            kwargs['llm_model'] = 'openai/gpt-4o'
        
        if kwargs.get('system_prompt', None) is None:
            kwargs['system_prompt'] = None

        return self.send_request("/level_one/run_agent", kwargs)

    def install_library(self, library: str) -> Any:
        return self.send_request("/tools/install_library", {"library": library})

    def uninstall_library(self, library: str) -> Any:
        return self.send_request("/tools/uninstall_library", {"library": library})

    def add_tool(self, function: Callable) -> Any:
        pickled = cloudpickle.dumps(function)
        encoded = base64.b64encode(pickled).decode("utf-8")
        return self.send_request("/tools/add_tool", {"function": encoded})

    def add_mcp_tool(
        self, name: str, command: str, args: List[str], env: Dict[str, str]
    ) -> Any:
        body = {"name": name, "command": command, "args": args, "env": env}
        return self.send_request("/tools/add_mcp_tool", body)


    def add_sse_mcp_tool(self, name: str, url: str) -> Any:
        return self.send_request("/tools/add_sse_mcp", {"name": name, "url": url})


    def get_config_value(self, key: str) -> Any:
        return self.send_request("/storage/config/get", {"key": key})
    

    def set_config_value(self, key: str, value: str) -> Any:
        return self.send_request("/storage/config/set", {"key": key, "value": value})
    

    def set_bulk_config_value(self, configs: Dict[str, str]) -> Any:
        return self.send_request("/storage/config/bulk_set", configs)


class UpliftedClient(UpligtedClient):
    """对服务端各模块功能进行再封装的客户端"""

    # ------------------ 通用 call ------------------ #
    def call(
        self,
        category: str,
        sub_endpoint: str,
        data: Dict[str, Any],
        method: str = "POST",
    ) -> Any:
        return self.send_request(f"/{category}/{sub_endpoint}", data, method)

    # ---------------- 兼容旧接口 ------------------- #
    def call_level_one(self, sub_endpoint: str, data: Dict[str, Any]) -> Any:
        return self.call("level_one", sub_endpoint, data)

    def call_level_two(self, sub_endpoint: str, data: Dict[str, Any]) -> Any:
        return self.call("level_two", sub_endpoint, data)

    # ----------------- 工具相关 -------------------- #
    def call_get_tools(self) -> Dict[str, Any]:
        resp = self.send_request("/tools/list_tools", {}, method="GET")
        tools = resp.get("available_tools", {}).get("tools", [])
        return {"tools": tools, "count": len(tools)}


# --------------------------------------------------------------------- #
# 使用示例
# --------------------------------------------------------------------- #
if __name__ == "__main__":
    client = UpliftedClient("http://localhost:7541", timeout=15)

    # 1. 检查服务状态
    ok = client.status()
    print("服务可用:", ok)
    if not ok:
        exit(1)

    print(f"一共有 {client.call_get_tools()['count']} 个工具")

    #2. 添加本地工具
    def scan_bug(url: str) -> str:
        """漏洞检测工具"""
        return f"url: {url} 没有漏洞"
    
    def web_bug(url: str) -> str:
        """WEB漏洞检测工具"""
        return f"url: {url} 没有WEB漏洞"

    print("添加工具：", client.add_tool(scan_bug))
    print("添加工具：", client.add_tool(web_bug))
    print(f"一共有 {client.call_get_tools()['count']} 个工具")

    result = client.run_agent(prompt='baidu.com有没有漏洞')
    print("没有加载工具得返回：", result)
    result = client.run_agent(prompt='baidu.com有没有漏洞', tools=['scan_bug', 'web_bug'])
    print("加载工具得返回：", result)
    result = client.run_agent(prompt='什么是google', tools=['MCPRag'])
    print("测试RAG工具的返回结果", result)
    # 3. 安装 / 卸载第三方库
    print("安装 numpy：", client.install_library("numpy"))
    print("卸载 numpy：", client.uninstall_library("numpy"))
    

    # 4. 查看配置项
    result = client.get_config_value("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY: {result}")

    # 5. 设置配置项
    result = client.set_config_value(key= "OPENAI_API_KEY", value="sk-xxxxxxx")
    print(f"结果: {result}")

    

    # 4. 关闭客户端
    client.close()