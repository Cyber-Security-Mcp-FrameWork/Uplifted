import time
import signal
import sys
from multiprocessing import Process
from uplifted.server import run_main_server, _server_manager as main_server_manager
from uplifted.tools_server import run_tools_server, _server_manager as tools_server_manager

def start_main_server():
    """
    在子进程中运行主服务
    """
    run_main_server()
    # 保持进程运行，等待服务进程
    try:
        while main_server_manager._process and main_server_manager._process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def start_tools_server():
    """
    在主进程中运行工具服务
    """
    run_tools_server()
    # 保持进程运行，等待服务进程
    try:
        while tools_server_manager._process and tools_server_manager._process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    # 启动工具服务子进程
    main_proc = Process(target=start_main_server, name="MainsServer")
    # main_proc.daemon = True
    main_proc.start()
    print(f"主接口服务已在子进程 (PID: {main_proc.pid}) 中启动")

    # 启动主服务
    print("主服务启动中...")
    start_tools_server()

    print("所有服务已启动成功。")

    # 保持主进程运行，等待子进程结束
    try:
        main_proc.join()
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        main_proc.terminate()
        main_proc.join(timeout=5)
        print("服务已关闭")
