from fastapi import FastAPI, HTTPException, Request, Response
import asyncio
from functools import wraps
from ...exception import TimeoutException
import inspect
from starlette.responses import JSONResponse
import threading
import time
import logging

# 配置日志
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()

# 移除中间件，改用异常处理器
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logging.error(f"错误: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# 从 server_utils 导入清理函数，而非 tools
from .server_utils import cleanup_all_servers

@app.on_event("shutdown")
async def shutdown_event():
    """
    当应用程序关闭时，清理所有服务器实例。
    """
    await cleanup_all_servers()

async def timeout_handler(duration: float, coro):
    try:
        return await asyncio.wait_for(coro, timeout=duration)
    except asyncio.TimeoutError:
        raise TimeoutException(f"操作在 {duration} 秒后超时")

def timeout(seconds: float):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # 为函数创建任务
                task = asyncio.create_task(func(*args, **kwargs))
                # 等待任务在指定超时内完成
                result = await asyncio.wait_for(task, timeout=seconds)
                return result
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=408,
                    detail=f"函数在 {seconds} 秒后超时"
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，使用基于线程的方法
            result = []
            error = []
            
            def target():
                try:
                    result.append(func(*args, **kwargs))
                except Exception as e:
                    error.append(e)
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)  # 等待指定的超时时间
            
            if thread.is_alive():
                raise HTTPException(
                    status_code=408,
                    detail=f"函数在 {seconds} 秒后超时"
                )
            
            if error:
                raise error[0]
            
            return result[0]

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator

@app.get("/status")
async def get_status():
    return {"status": "Server is running"}