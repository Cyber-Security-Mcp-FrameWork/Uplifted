"""异步执行 shell 命令，并设置超时的工具。"""

import asyncio

TRUNCATED_MESSAGE: str = "<response clipped><NOTE>为了节省上下文，仅显示了该文件的部分内容。在使用 `grep -n` 搜索您需要的行号后，请重试该工具。</NOTE>"
MAX_RESPONSE_LEN: int = 16000


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """如果内容超出指定长度，则截断内容并附加提示信息。"""
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


async def run(
    cmd: str,
    timeout: float | None = 120.0,  # 秒
    truncate_after: int | None = MAX_RESPONSE_LEN,
):
    """异步执行 shell 命令，并设置超时。"""
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return (
            process.returncode or 0,
            maybe_truncate(stdout.decode(), truncate_after=truncate_after),
            maybe_truncate(stderr.decode(), truncate_after=truncate_after),
        )
    except asyncio.TimeoutError as exc:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(
            f"命令 '{cmd}' 在 {timeout} 秒后超时"
        ) from exc