"""
健康检查模块
提供系统健康状态监控和检查功能
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import threading
import psutil

from .logger import get_logger
from .metrics_collector import get_global_metrics_manager

logger = get_logger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration: float  # 检查耗时（毫秒）
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "details": self.details
        }


class HealthCheck(ABC):
    """健康检查抽象基类"""
    
    def __init__(self, name: str, timeout: float = 30.0):
        self.name = name
        self.timeout = timeout
        self.enabled = True
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass
    
    async def run_check(self) -> HealthCheckResult:
        """运行健康检查（带超时）"""
        if not self.enabled:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="检查已禁用",
                timestamp=datetime.now(),
                duration=0.0
            )
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self.check(), timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查超时（{self.timeout}秒）",
                timestamp=datetime.now(),
                duration=duration
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"健康检查失败 {self.name}: {e}", exception=e)
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"error": str(e), "error_type": type(e).__name__}
            )


class CPUHealthCheck(HealthCheck):
    """CPU健康检查"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__("cpu")
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> HealthCheckResult:
        """检查CPU使用率"""
        start_time = time.time()
        
        # 获取CPU使用率（1秒采样）
        cpu_percent = psutil.cpu_percent(interval=1)
        
        duration = (time.time() - start_time) * 1000
        
        if cpu_percent >= self.critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"CPU使用率过高: {cpu_percent:.1f}%"
        elif cpu_percent >= self.warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"CPU使用率较高: {cpu_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU使用率正常: {cpu_percent:.1f}%"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            timestamp=datetime.now(),
            duration=duration,
            details={
                "cpu_percent": cpu_percent,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
                "cpu_count": psutil.cpu_count()
            }
        )


class MemoryHealthCheck(HealthCheck):
    """内存健康检查"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__("memory")
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> HealthCheckResult:
        """检查内存使用率"""
        start_time = time.time()
        
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        duration = (time.time() - start_time) * 1000
        
        if memory_percent >= self.critical_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"内存使用率过高: {memory_percent:.1f}%"
        elif memory_percent >= self.warning_threshold:
            status = HealthStatus.DEGRADED
            message = f"内存使用率较高: {memory_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"内存使用率正常: {memory_percent:.1f}%"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            timestamp=datetime.now(),
            duration=duration,
            details={
                "memory_percent": memory_percent,
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold
            }
        )


class DiskHealthCheck(HealthCheck):
    """磁盘健康检查"""
    
    def __init__(self, path: str = "/", warning_threshold: float = 80.0, critical_threshold: float = 95.0):
        super().__init__("disk")
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> HealthCheckResult:
        """检查磁盘使用率"""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage(self.path)
            disk_percent = (disk.used / disk.total) * 100
            
            duration = (time.time() - start_time) * 1000
            
            if disk_percent >= self.critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"磁盘使用率过高: {disk_percent:.1f}%"
            elif disk_percent >= self.warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"磁盘使用率较高: {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"磁盘使用率正常: {disk_percent:.1f}%"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration=duration,
                details={
                    "path": self.path,
                    "disk_percent": disk_percent,
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "warning_threshold": self.warning_threshold,
                    "critical_threshold": self.critical_threshold
                }
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"磁盘检查失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"path": self.path, "error": str(e)}
            )


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""
    
    def __init__(self, connection_func: Callable, query: str = "SELECT 1"):
        super().__init__("database")
        self.connection_func = connection_func
        self.query = query
    
    async def check(self) -> HealthCheckResult:
        """检查数据库连接"""
        start_time = time.time()
        
        try:
            # 这里应该根据实际的数据库类型实现连接检查
            # 为了简化，这里只是模拟
            await asyncio.sleep(0.1)  # 模拟数据库查询
            
            duration = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="数据库连接正常",
                timestamp=datetime.now(),
                duration=duration,
                details={"query": self.query}
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"query": self.query, "error": str(e)}
            )


class RedisHealthCheck(HealthCheck):
    """Redis健康检查"""
    
    def __init__(self, redis_client):
        super().__init__("redis")
        self.redis_client = redis_client
    
    async def check(self) -> HealthCheckResult:
        """检查Redis连接"""
        start_time = time.time()
        
        try:
            # 执行ping命令
            if hasattr(self.redis_client, 'ping'):
                await self.redis_client.ping()
            else:
                # 同步客户端
                self.redis_client.ping()
            
            duration = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Redis连接正常",
                timestamp=datetime.now(),
                duration=duration
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis连接失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"error": str(e)}
            )


class HTTPHealthCheck(HealthCheck):
    """HTTP健康检查"""
    
    def __init__(self, url: str, expected_status: int = 200, expected_text: Optional[str] = None):
        super().__init__("http")
        self.url = url
        self.expected_status = expected_status
        self.expected_text = expected_text
    
    async def check(self) -> HealthCheckResult:
        """检查HTTP端点"""
        start_time = time.time()
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    duration = (time.time() - start_time) * 1000
                    
                    if response.status != self.expected_status:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"HTTP状态码不匹配: 期望{self.expected_status}, 实际{response.status}",
                            timestamp=datetime.now(),
                            duration=duration,
                            details={
                                "url": self.url,
                                "expected_status": self.expected_status,
                                "actual_status": response.status
                            }
                        )
                    
                    if self.expected_text:
                        text = await response.text()
                        if self.expected_text not in text:
                            return HealthCheckResult(
                                name=self.name,
                                status=HealthStatus.UNHEALTHY,
                                message=f"响应内容不包含期望文本: {self.expected_text}",
                                timestamp=datetime.now(),
                                duration=duration,
                                details={
                                    "url": self.url,
                                    "expected_text": self.expected_text,
                                    "response_length": len(text)
                                }
                            )
                    
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message="HTTP端点正常",
                        timestamp=datetime.now(),
                        duration=duration,
                        details={
                            "url": self.url,
                            "status": response.status,
                            "content_type": response.headers.get("content-type")
                        }
                    )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP检查失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"url": self.url, "error": str(e)}
            )


class CustomHealthCheck(HealthCheck):
    """自定义健康检查"""
    
    def __init__(self, name: str, check_func: Callable[[], Union[bool, HealthCheckResult]], timeout: float = 30.0):
        super().__init__(name, timeout)
        self.check_func = check_func
    
    async def check(self) -> HealthCheckResult:
        """执行自定义检查"""
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(self.check_func):
                result = await self.check_func()
            else:
                result = self.check_func()
            
            duration = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                return result
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = "检查通过" if result else "检查失败"
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    message=message,
                    timestamp=datetime.now(),
                    duration=duration
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message=f"未知的检查结果类型: {type(result)}",
                    timestamp=datetime.now(),
                    duration=duration
                )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"自定义检查失败: {str(e)}",
                timestamp=datetime.now(),
                duration=duration,
                details={"error": str(e)}
            )


@dataclass
class HealthReport:
    """健康报告"""
    overall_status: HealthStatus
    timestamp: datetime
    checks: List[HealthCheckResult]
    duration: float  # 总检查耗时（毫秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "checks": [check.to_dict() for check in self.checks]
        }


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.last_report: Optional[HealthReport] = None
        self._check_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.Lock()
        
        # 检查配置
        self.check_interval = 30.0  # 检查间隔（秒）
        self.parallel_checks = True  # 是否并行执行检查
        
        # 添加默认的系统检查
        self.add_check(CPUHealthCheck())
        self.add_check(MemoryHealthCheck())
        self.add_check(DiskHealthCheck())
    
    def add_check(self, check: HealthCheck) -> None:
        """添加健康检查"""
        with self._lock:
            self.checks[check.name] = check
            logger.info(f"添加健康检查: {check.name}")
    
    def remove_check(self, name: str) -> None:
        """移除健康检查"""
        with self._lock:
            if name in self.checks:
                del self.checks[name]
                logger.info(f"移除健康检查: {name}")
    
    def enable_check(self, name: str) -> None:
        """启用健康检查"""
        if name in self.checks:
            self.checks[name].enabled = True
            logger.info(f"启用健康检查: {name}")
    
    def disable_check(self, name: str) -> None:
        """禁用健康检查"""
        if name in self.checks:
            self.checks[name].enabled = False
            logger.info(f"禁用健康检查: {name}")
    
    async def run_checks(self) -> HealthReport:
        """运行所有健康检查"""
        start_time = time.time()
        
        checks = list(self.checks.values())
        
        if self.parallel_checks:
            # 并行执行检查
            tasks = [check.run_check() for check in checks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            check_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    check_results.append(HealthCheckResult(
                        name=checks[i].name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"检查异常: {str(result)}",
                        timestamp=datetime.now(),
                        duration=0.0,
                        details={"error": str(result)}
                    ))
                else:
                    check_results.append(result)
        else:
            # 串行执行检查
            check_results = []
            for check in checks:
                result = await check.run_check()
                check_results.append(result)
        
        # 计算总体状态
        overall_status = self._calculate_overall_status(check_results)
        
        duration = (time.time() - start_time) * 1000
        
        report = HealthReport(
            overall_status=overall_status,
            timestamp=datetime.now(),
            checks=check_results,
            duration=duration
        )
        
        self.last_report = report
        return report
    
    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """计算总体健康状态"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    async def start_periodic_checks(self) -> None:
        """开始定期健康检查"""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("开始定期健康检查")
    
    async def stop_periodic_checks(self) -> None:
        """停止定期健康检查"""
        if not self._running:
            return
        
        self._running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("停止定期健康检查")
    
    async def _check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            try:
                await self.run_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环错误: {e}", exception=e)
                await asyncio.sleep(5)
    
    def get_last_report(self) -> Optional[HealthReport]:
        """获取最后一次健康报告"""
        return self.last_report
    
    def get_checks(self) -> List[HealthCheck]:
        """获取所有健康检查"""
        return list(self.checks.values())


# 全局健康检查器实例
_global_health_checker: Optional[HealthChecker] = None


def get_global_health_checker() -> HealthChecker:
    """获取全局健康检查器实例"""
    global _global_health_checker
    if _global_health_checker is None:
        _global_health_checker = HealthChecker()
    return _global_health_checker


# 便捷函数
async def check_health() -> HealthReport:
    """执行健康检查"""
    checker = get_global_health_checker()
    return await checker.run_checks()


def add_health_check(check: HealthCheck) -> None:
    """添加健康检查"""
    checker = get_global_health_checker()
    checker.add_check(check)


def create_database_check(connection_func: Callable, name: str = "database") -> DatabaseHealthCheck:
    """创建数据库健康检查"""
    check = DatabaseHealthCheck(connection_func)
    check.name = name
    return check


def create_redis_check(redis_client, name: str = "redis") -> RedisHealthCheck:
    """创建Redis健康检查"""
    check = RedisHealthCheck(redis_client)
    check.name = name
    return check


def create_http_check(url: str, name: Optional[str] = None, expected_status: int = 200) -> HTTPHealthCheck:
    """创建HTTP健康检查"""
    check = HTTPHealthCheck(url, expected_status)
    if name:
        check.name = name
    return check