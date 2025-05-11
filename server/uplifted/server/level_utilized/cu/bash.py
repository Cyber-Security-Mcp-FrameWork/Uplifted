import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult


class _BashSession:
    """一个 bash shell 会话。"""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # 秒
    _timeout: float = 120.0  # 秒
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """终止 bash shell。"""
        if not self._started:
            raise ToolError("会话尚未启动。")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """在 bash shell 中执行命令。"""
        if not self._started:
            raise ToolError("会话尚未启动。")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash 已退出，返回码为 {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"超时：bash 在 {self._timeout} 秒内未返回，必须重启",
            )

        # 由于我们使用 PIPE 创建进程，所以这些不会是 None
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # 将命令发送给进程
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # 从进程中读取输出，直到找到哨兵字符串
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # 如果直接从 stdout/stderr 读取，会无限等待 EOF，
                    # 因此直接使用 StreamReader 缓冲区读取。
                    output = self._process.stdout._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # 移除哨兵字符串并退出循环
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"超时：bash 在 {self._timeout} 秒内未返回，必须重启",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = self._process.stderr._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # 清空缓冲区，确保下次可以正确读取输出
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class BashTool(BaseAnthropicTool):
    """
    一个允许代理执行 bash 命令的工具。
    该工具的参数由 Anthropic 定义且不可编辑。
    """

    _session: _BashSession | None
    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20241022"]] = "bash_20241022"

    def __init__(self):
        self._session = None
        super().__init__()

    async def __call__(
        self, command: str | None = None, restart: bool = False, **kwargs
    ):
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.", error="")  # 工具已重启。

        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        if command is not None:
            return await self._session.run(command)

        raise ToolError("未提供任何命令。")

    def to_params(self) -> BetaToolBash20241022Param:
        return {
            "type": self.api_type,
            "name": self.name,
        }