from ..storage.configuration import Configuration
from .level_one.call import Call
from ..server_manager import ServerManager

from .api import app
from .level_one.server.server import *
from .level_two.server.server import *
from .storage.server.server import *
from .tools.server import *

import warnings
import threading
import time
import concurrent.futures
import traceback
from multiprocessing import freeze_support
from ..tools_server import run_tools_server, stop_tools_server, is_tools_server_running

# 忽略常见的警告信息，提高控制台整洁度
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

# 创建 ServerManager，用于管理主服务的启动、停止及状态检查
_server_manager = ServerManager(
    app_path="uplifted.server.api:app",  # FastAPI 应用路径
    host="localhost",                 # 绑定主机地址
    port=7541,                          # 监听端口
    name="main"                       # 服务名称
)


def run_main_server(redirect_output: bool = False):
    """
    启动主服务器（如未运行）

    参数:
        redirect_output (bool): 是否重定向输出日志，默认为 False
    返回:
        bool: 启动是否成功
    """
    return _server_manager.start(redirect_output=redirect_output)


def run_main_server_internal(reload: bool = True):
    """
    直接运行主服务器，用于开发模式

    参数:
        reload (bool): 是否启用代码热重载，默认为 True
    """
    import uvicorn
    uvicorn.run(
        "uplifted.server.api:app",  # 指定 FastAPI 应用模块
        host="0.0.0.0",              # 可通过任意地址访问
        port=7541,                     # 监听端口
        reload=reload                 # 热重载
    )


def stop_main_server():
    """
    停止正在运行的主服务器
    """
    return _server_manager.stop()


def is_main_server_running() -> bool:
    """
    检查主服务器是否正在运行

    返回:
        bool: True 表示服务器在运行，False 表示未运行
    """
    return _server_manager.is_running()


def _start_server(server_func, server_name, redirect_output=True):
    """
    启动指定服务器的通用函数，用于线程池执行

    参数:
        server_func (callable): 服务器启动函数
        server_name (str): 服务器名称，便于日志输出
        redirect_output (bool): 是否重定向输出日志

    返回:
        bool: 启动成功返回 True，失败返回 False
    """
    try:
        server_func(redirect_output=redirect_output)
        return True
    except Exception:
        print(f"启动 {server_name} 服务器时出错：")
        traceback.print_exc()
        return False


def run_dev_server(redirect_output=True):
    """
    开发模式启动：并行运行主服务器和工具服务器

    参数:
        redirect_output (bool): 是否重定向输出日志

    流程:
        1. 使用 ThreadPoolExecutor 启动主服务和工具服务
        2. 等待两者启动完成（超时 150s）
        3. 启动失败时自动停止所有服务并抛出异常
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            main_future = executor.submit(
                _start_server,
                run_main_server,
                "main",
                redirect_output
            )
            tools_future = executor.submit(
                _start_server,
                run_tools_server,
                "tools",
                redirect_output
            )
            try:
                main_ok = main_future.result(timeout=150)
                tools_ok = tools_future.result(timeout=150)
                if not (main_ok and tools_ok):
                    print("至少一个服务器启动失败，正在停止所有服务...")
                    stop_dev_server()
                    raise RuntimeError("服务器启动失败，请检查日志。")
                # 服务启动成功后，稍作延时以确保完全可用
                time.sleep(0.5)
            except concurrent.futures.TimeoutError:
                print("启动服务器超时，正在停止所有服务...")
                stop_dev_server()
                raise RuntimeError("启动服务器超时。")
    except Exception:
        print("开发模式运行时发生意外错误：")
        traceback.print_exc()
        raise


def stop_dev_server():
    """
    停止开发模式下的主服务器和工具服务器
    """
    stop_main_server()
    stop_tools_server()

if __name__ == '__main__':
    freeze_support()

__all__ = ["Configuration", "Call", "app", "run_main_server", "stop_main_server", 
           "is_main_server_running", "run_main_server_internal", "run_dev_server", "stop_dev_server"]
