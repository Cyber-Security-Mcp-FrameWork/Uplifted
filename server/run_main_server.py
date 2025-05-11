from multiprocessing import Process
from uplifted.server import run_main_server
from uplifted.tools_server import run_tools_server

def start_main_server():
    """
    在子进程中运行主服务
    """
    run_main_server()


def start_tools_server():
    """
    在主进程中运行工具服务
    """
    run_tools_server()

if __name__ == "__main__":
    # 启动工具服务子进程
    main_proc = Process(target=start_main_server, name="MainsServer")
    # main_proc.daemon = True
    main_proc.start()
    print(f"主接口服务已在子进程 (PID: {main_proc.pid}) 中启动")

    # 启动主服务
    print("主服务启动中...")
    start_tools_server()

    main_proc.join()
    print("所有服务已启动成功。")
    # 等待子进程结束（可选）
