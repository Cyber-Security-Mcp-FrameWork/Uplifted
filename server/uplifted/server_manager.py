import os
import signal
import sys
import time
import socket
import subprocess
import psutil
from pathlib import Path
from contextlib import closing
from typing import Optional


# 文件顶部新增
# ======= 超时 & 重试参数 =======
SOCKET_TIMEOUT = 0.2       # 端口探测超时
KILL_WAIT_TIMEOUT = 0.5    # 杀死进程后等待
CLEANUP_SLEEP = 0.2        # 清理端口后休眠
START_POLL_INITIAL = 0.01  # 启动后轮询初始间隔
START_POLL_MAX = 0.1       # 启动后轮询最大间隔
START_TIMEOUT = 300        # 启动超时时间（秒）
# ============================

def _terminate_process(process, timeout: float):
    try:
        process.kill()
        process.wait(timeout=timeout)
    except Exception:
        os.kill(process.pid, signal.SIGKILL)

class ServerManager:
    def __init__(self, app_path: str, host: str, port: int, name: str):
        self.app_path = app_path
        self.host = host
        self.port = port
        self.name = name
        self._process: Optional[subprocess.Popen] = None
        self._pid_file = Path.home() / f".upsonic_{name}_server.pid"
        
    def _is_port_in_use(self) -> bool:
        """检查端口是否被占用。"""
        try:
            # 更快的方法检查端口可用性
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(SOCKET_TIMEOUT)
                return sock.connect_ex((self.host, self.port)) == 0
        except Exception:
            # 回退到原始方法
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                return sock.connect_ex((self.host, self.port)) == 0

            
    def _kill_process_using_port(self) -> bool:
        """查找并终止使用指定端口的进程。"""
        killed = False
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process = psutil.Process(proc.info['pid'])
                for conn in process.net_connections():
                    if hasattr(conn, 'laddr') and len(conn.laddr) >= 2 and conn.laddr[1] == self.port:
                        _terminate_process(process, timeout=KILL_WAIT_TIMEOUT)
                        killed = True
            except Exception:
                continue
                
        return killed

    def _manage_pid_file(self, operation: str) -> Optional[int] | bool:
        """管理 PID 文件操作（读取/写入/清理）。"""
        try:
            if operation == "write" and self._process and self._process.pid:
                with open(self._pid_file, 'w') as f:
                    f.write(str(self._process.pid))
            elif operation == "read" and os.path.exists(self._pid_file):
                with open(self._pid_file, 'r') as f:
                    return int(f.read().strip())
            elif operation == "cleanup" and os.path.exists(self._pid_file):
                os.remove(self._pid_file)
        except Exception:
            pass
        
        return None if operation == "read" else False
    

    def _cleanup_port(self):
        """在启动前清理端口。"""
        if not self._is_port_in_use():
            return True
            
        # 尝试终止使用该端口的进程
        self._kill_process_using_port()
        time.sleep(0.2)  # 缩短休眠时间
        
        # 如果端口仍被占用，尝试更激进的方法
        if self._is_port_in_use():
            try:
                # 尝试绑定该端口以强制释放
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                sock.close()
            except socket.error:
                # 如果绑定失败，再尝试一次终止进程
                candidates = [
                    psutil.Process(p.info['pid'])
                    for p in psutil.process_iter(['pid'])
                    if any(conn.laddr[1]==self.port for conn in p.connections(kind='inet'))
                ]
                for process in candidates:
                    _terminate_process(process, KILL_WAIT_TIMEOUT)
                time.sleep(0.2)  # 缩短休眠时间
        
        return not self._is_port_in_use()

    def start(self, redirect_output: bool = False, force: bool = False):
        """如果服务器尚未运行，则启动服务器。"""
        if self.is_running():
            return
            
        # 清理端口
        if not self._cleanup_port() and not force:
            raise RuntimeError(f"端口 {self.port} 正被占用且无法释放")
    
        # 设置日志记录
        stdout = stderr = None
        if redirect_output:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            stdout = open(os.path.join(log_dir, f'{self.name}_server.log'), 'a')
            stderr = open(os.path.join(log_dir, f'{self.name}_server_error.log'), 'a')
    
        # 启动服务器进程
        try:
            cmd = [
                sys.executable, "-m", "uvicorn",
                self.app_path,
                "--host", self.host,
                "--port", str(self.port),
                "--log-level", "error",
                "--no-access-log"
            ]
            
            self._process = subprocess.Popen(
                cmd, stdout=stdout, stderr=stderr, start_new_session=True
            )
            self._manage_pid_file("write")
    
            # 使用优化后的轮询等待服务器启动
            # 初始快速休眠以允许进程启动
            time.sleep(0.1)
            
            # 逐步增加轮询间隔等待启动完成
            poll_interval = 0.01
            max_poll_interval = 0.1
            start_time = time.time()
            while not self._is_port_in_use() and time.time() - start_time < 300:
                if self._process.poll() is not None:
                    raise RuntimeError(f"服务器进程意外终止，退出码 {self._process.returncode}")
                time.sleep(poll_interval)
                # 逐步增加轮询间隔
                poll_interval = min(poll_interval * 1.2, max_poll_interval)
    
            if not self._is_port_in_use():
                raise RuntimeError(f"等待 {self.name} 服务器启动超时")
                
        except Exception as e:
            self.stop()
            raise RuntimeError(f"启动 {self.name} 服务器失败: {str(e)}")
    
    def stop(self):
        """如果服务器正在运行，则停止服务器。"""
        # 尝试通过 PID 文件停止进程
        pid = self._manage_pid_file("read")
        if pid:
            try:
                process = psutil.Process(pid)
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except Exception:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception:
                pass
    
        # 尝试通过实例变量停止进程
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                if self._process.poll() is None:
                    self._process.kill()
    
        self._process = None
        self._manage_pid_file("cleanup")
    
    def is_running(self) -> bool:
        """检查服务器当前是否正在运行。"""
        # 检查实例变量中的进程是否在运行
        if self._process and self._process.poll() is None:
            return True
    
        # 检查 PID 文件中的进程是否在运行
        pid = self._manage_pid_file("read")
        if pid:
            try:
                process = psutil.Process(pid)
                return process.is_running() and process.name().startswith("python")
            except psutil.NoSuchProcess:
                self._manage_pid_file("cleanup")
                
        return False 