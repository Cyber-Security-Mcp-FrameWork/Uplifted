"""
连接池管理模块
提供HTTP连接池、数据库连接池等高性能连接管理功能
"""

import asyncio
import threading
import time
import weakref
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Generic, TypeVar, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager, contextmanager
from queue import Queue, Empty, Full
import aiohttp
import httpx
from ..core.interfaces import ILogger

T = TypeVar('T')


@dataclass
class ConnectionConfig:
    """连接配置"""
    max_connections: int = 100
    min_connections: int = 10
    max_idle_time: float = 300.0  # 5分钟
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    retry_attempts: int = 3
    health_check_interval: float = 60.0  # 健康检查间隔


@dataclass
class ConnectionStats:
    """连接统计信息"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    peak_connections: int = 0


class Connection(Generic[T]):
    """连接包装器"""
    
    def __init__(self, connection: T, created_at: float = None):
        self.connection = connection
        self.created_at = created_at or time.time()
        self.last_used = self.created_at
        self.is_active = False
        self.request_count = 0
        self.error_count = 0
    
    @property
    def idle_time(self) -> float:
        """获取空闲时间"""
        return time.time() - self.last_used
    
    @property
    def age(self) -> float:
        """获取连接年龄"""
        return time.time() - self.created_at
    
    def mark_used(self) -> None:
        """标记连接被使用"""
        self.last_used = time.time()
        self.request_count += 1
    
    def mark_error(self) -> None:
        """标记连接错误"""
        self.error_count += 1


class ConnectionPool(ABC, Generic[T]):
    """连接池基类"""
    
    def __init__(self, config: ConnectionConfig, logger: Optional[ILogger] = None):
        self.config = config
        self.logger = logger
        self._pool: Queue[Connection[T]] = Queue(maxsize=config.max_connections)
        self._active_connections: Dict[int, Connection[T]] = {}
        self._stats = ConnectionStats()
        self._lock = threading.RLock()
        self._shutdown = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 初始化最小连接数
        self._initialize_pool()
        
        # 启动健康检查
        if config.health_check_interval > 0:
            self._start_health_check()
    
    @abstractmethod
    def _create_connection(self) -> T:
        """创建新连接"""
        pass
    
    @abstractmethod
    def _validate_connection(self, connection: T) -> bool:
        """验证连接是否有效"""
        pass
    
    @abstractmethod
    def _close_connection(self, connection: T) -> None:
        """关闭连接"""
        pass
    
    def _initialize_pool(self) -> None:
        """初始化连接池"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_new_connection()
                self._pool.put_nowait(conn)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to initialize connection: {e}")
    
    def _create_new_connection(self) -> Connection[T]:
        """创建新的连接包装器"""
        raw_conn = self._create_connection()
        conn = Connection(raw_conn)
        
        with self._lock:
            self._stats.total_connections += 1
            if self._stats.total_connections > self._stats.peak_connections:
                self._stats.peak_connections = self._stats.total_connections
        
        return conn
    
    @contextmanager
    def get_connection(self, timeout: Optional[float] = None):
        """获取连接（同步版本）"""
        conn = None
        try:
            conn = self._acquire_connection(timeout)
            yield conn.connection
        finally:
            if conn:
                self._release_connection(conn)
    
    def _acquire_connection(self, timeout: Optional[float] = None) -> Connection[T]:
        """获取连接"""
        if self._shutdown:
            raise RuntimeError("Connection pool is shutdown")
        
        timeout = timeout or self.config.connection_timeout
        
        # 尝试从池中获取连接
        try:
            conn = self._pool.get(timeout=timeout)
            
            # 验证连接是否有效
            if not self._validate_connection(conn.connection):
                self._close_connection(conn.connection)
                conn = self._create_new_connection()
            
        except Empty:
            # 池中没有可用连接，创建新连接
            if len(self._active_connections) >= self.config.max_connections:
                raise RuntimeError("Connection pool exhausted")
            
            conn = self._create_new_connection()
        
        # 标记连接为活跃状态
        with self._lock:
            conn.is_active = True
            conn.mark_used()
            self._active_connections[id(conn)] = conn
            self._stats.active_connections += 1
        
        return conn
    
    def _release_connection(self, conn: Connection[T]) -> None:
        """释放连接"""
        with self._lock:
            if id(conn) in self._active_connections:
                del self._active_connections[id(conn)]
                self._stats.active_connections -= 1
            
            conn.is_active = False
            
            # 检查连接是否应该被丢弃
            if (conn.idle_time > self.config.max_idle_time or
                conn.error_count > self.config.retry_attempts or
                not self._validate_connection(conn.connection)):
                
                self._close_connection(conn.connection)
                self._stats.total_connections -= 1
                return
            
            # 将连接放回池中
            try:
                self._pool.put_nowait(conn)
                self._stats.idle_connections += 1
            except Full:
                # 池已满，关闭连接
                self._close_connection(conn.connection)
                self._stats.total_connections -= 1
    
    def _start_health_check(self) -> None:
        """启动健康检查任务"""
        async def health_check():
            while not self._shutdown:
                try:
                    await asyncio.sleep(self.config.health_check_interval)
                    self._cleanup_idle_connections()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Health check error: {e}")
        
        try:
            loop = asyncio.get_event_loop()
            self._health_check_task = loop.create_task(health_check())
        except RuntimeError:
            # 没有运行的事件循环，跳过健康检查
            pass
    
    def _cleanup_idle_connections(self) -> None:
        """清理空闲连接"""
        current_time = time.time()
        connections_to_remove = []
        
        # 从池中取出所有连接进行检查
        temp_connections = []
        while True:
            try:
                conn = self._pool.get_nowait()
                temp_connections.append(conn)
            except Empty:
                break
        
        # 检查每个连接
        for conn in temp_connections:
            if (current_time - conn.last_used > self.config.max_idle_time or
                not self._validate_connection(conn.connection)):
                connections_to_remove.append(conn)
            else:
                # 将有效连接放回池中
                try:
                    self._pool.put_nowait(conn)
                except Full:
                    connections_to_remove.append(conn)
        
        # 关闭需要移除的连接
        for conn in connections_to_remove:
            self._close_connection(conn.connection)
            with self._lock:
                self._stats.total_connections -= 1
        
        # 确保最小连接数
        current_pool_size = self._pool.qsize()
        if current_pool_size < self.config.min_connections:
            for _ in range(self.config.min_connections - current_pool_size):
                try:
                    conn = self._create_new_connection()
                    self._pool.put_nowait(conn)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to create connection during cleanup: {e}")
    
    def get_stats(self) -> ConnectionStats:
        """获取连接池统计信息"""
        with self._lock:
            stats = ConnectionStats(
                total_connections=self._stats.total_connections,
                active_connections=self._stats.active_connections,
                idle_connections=self._pool.qsize(),
                failed_connections=self._stats.failed_connections,
                total_requests=self._stats.total_requests,
                successful_requests=self._stats.successful_requests,
                failed_requests=self._stats.failed_requests,
                average_response_time=self._stats.average_response_time,
                peak_connections=self._stats.peak_connections
            )
        return stats
    
    def shutdown(self) -> None:
        """关闭连接池"""
        self._shutdown = True
        
        # 取消健康检查任务
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # 关闭所有活跃连接
        with self._lock:
            for conn in self._active_connections.values():
                self._close_connection(conn.connection)
            self._active_connections.clear()
        
        # 关闭池中的所有连接
        while True:
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn.connection)
            except Empty:
                break


class HTTPConnectionPool(ConnectionPool[httpx.Client]):
    """HTTP连接池"""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 headers: Optional[Dict[str, str]] = None,
                 config: Optional[ConnectionConfig] = None,
                 logger: Optional[ILogger] = None):
        self.base_url = base_url
        self.headers = headers or {}
        super().__init__(config or ConnectionConfig(), logger)
    
    def _create_connection(self) -> httpx.Client:
        """创建HTTP客户端连接"""
        return httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(
                connect=self.config.connection_timeout,
                read=self.config.read_timeout
            ),
            limits=httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.min_connections
            )
        )
    
    def _validate_connection(self, connection: httpx.Client) -> bool:
        """验证HTTP连接"""
        try:
            # 简单的健康检查
            return not connection.is_closed
        except Exception:
            return False
    
    def _close_connection(self, connection: httpx.Client) -> None:
        """关闭HTTP连接"""
        try:
            connection.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing HTTP connection: {e}")


class AsyncHTTPConnectionPool:
    """异步HTTP连接池"""
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 headers: Optional[Dict[str, str]] = None,
                 config: Optional[ConnectionConfig] = None,
                 logger: Optional[ILogger] = None):
        self.base_url = base_url
        self.headers = headers or {}
        self.config = config or ConnectionConfig()
        self.logger = logger
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.config.max_connections,
                        limit_per_host=self.config.max_connections // 4,
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                        keepalive_timeout=self.config.max_idle_time
                    )
                    
                    timeout = aiohttp.ClientTimeout(
                        total=self.config.read_timeout,
                        connect=self.config.connection_timeout
                    )
                    
                    self._session = aiohttp.ClientSession(
                        base_url=self.base_url,
                        headers=self.headers,
                        connector=connector,
                        timeout=timeout
                    )
        
        return self._session
    
    @asynccontextmanager
    async def get_session(self):
        """获取会话上下文管理器"""
        session = await self._get_session()
        try:
            yield session
        except Exception as e:
            if self.logger:
                self.logger.error(f"Session error: {e}")
            raise
    
    async def close(self) -> None:
        """关闭连接池"""
        if self._session and not self._session.closed:
            await self._session.close()


class DatabaseConnectionPool(ConnectionPool[Any]):
    """数据库连接池（示例实现）"""
    
    def __init__(self, 
                 connection_factory: Callable[[], Any],
                 config: Optional[ConnectionConfig] = None,
                 logger: Optional[ILogger] = None):
        self.connection_factory = connection_factory
        super().__init__(config or ConnectionConfig(), logger)
    
    def _create_connection(self) -> Any:
        """创建数据库连接"""
        return self.connection_factory()
    
    def _validate_connection(self, connection: Any) -> bool:
        """验证数据库连接"""
        try:
            # 这里应该根据具体的数据库类型实现验证逻辑
            # 例如执行一个简单的查询
            if hasattr(connection, 'ping'):
                connection.ping()
                return True
            elif hasattr(connection, 'execute'):
                connection.execute('SELECT 1')
                return True
            return True
        except Exception:
            return False
    
    def _close_connection(self, connection: Any) -> None:
        """关闭数据库连接"""
        try:
            if hasattr(connection, 'close'):
                connection.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing database connection: {e}")


class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.RLock()
    
    def register_pool(self, name: str, pool: ConnectionPool) -> None:
        """注册连接池"""
        with self._lock:
            if name in self._pools:
                # 关闭现有池
                self._pools[name].shutdown()
            self._pools[name] = pool
    
    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """获取连接池"""
        with self._lock:
            return self._pools.get(name)
    
    def get_all_stats(self) -> Dict[str, ConnectionStats]:
        """获取所有连接池的统计信息"""
        with self._lock:
            return {
                name: pool.get_stats()
                for name, pool in self._pools.items()
            }
    
    def shutdown_all(self) -> None:
        """关闭所有连接池"""
        with self._lock:
            for pool in self._pools.values():
                pool.shutdown()
            self._pools.clear()


# 全局连接池管理器实例
_global_pool_manager: Optional[ConnectionPoolManager] = None
_manager_lock = threading.Lock()


def get_global_pool_manager() -> ConnectionPoolManager:
    """获取全局连接池管理器"""
    global _global_pool_manager
    
    if _global_pool_manager is None:
        with _manager_lock:
            if _global_pool_manager is None:
                _global_pool_manager = ConnectionPoolManager()
    
    return _global_pool_manager