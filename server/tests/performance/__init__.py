"""
性能测试模块

提供性能测试的配置和工具
"""

import time
import asyncio
from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager


@dataclass
class PerformanceResult:
    """性能测试结果"""
    operation: str
    duration: float
    iterations: int
    avg_time: float
    min_time: float
    max_time: float
    success_rate: float
    errors: List[str]


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.perf_counter()
    
    def stop(self):
        """停止计时"""
        self.end_time = time.perf_counter()
        return self.duration
    
    @property
    def duration(self) -> float:
        """获取持续时间"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.perf_counter()
        return end - self.start_time
    
    @asynccontextmanager
    async def async_timer(self):
        """异步计时器上下文管理器"""
        self.start()
        try:
            yield self
        finally:
            self.stop()


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.results: List[PerformanceResult] = []
    
    async def run_benchmark(
        self,
        operation_name: str,
        operation: Callable,
        iterations: int = 100,
        warmup_iterations: int = 10
    ) -> PerformanceResult:
        """运行性能基准测试"""
        # 预热
        for _ in range(warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    operation()
            except Exception:
                pass  # 忽略预热阶段的错误
        
        # 实际测试
        times = []
        errors = []
        successful_operations = 0
        
        for i in range(iterations):
            timer = PerformanceTimer()
            try:
                timer.start()
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    operation()
                timer.stop()
                times.append(timer.duration)
                successful_operations += 1
            except Exception as e:
                timer.stop()
                errors.append(f"Iteration {i}: {str(e)}")
        
        # 计算统计信息
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            total_duration = sum(times)
        else:
            avg_time = min_time = max_time = total_duration = 0.0
        
        success_rate = successful_operations / iterations if iterations > 0 else 0.0
        
        result = PerformanceResult(
            operation=operation_name,
            duration=total_duration,
            iterations=iterations,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            success_rate=success_rate,
            errors=errors
        )
        
        self.results.append(result)
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能测试摘要"""
        if not self.results:
            return {"total_tests": 0}
        
        total_operations = sum(r.iterations for r in self.results)
        total_duration = sum(r.duration for r in self.results)
        avg_success_rate = sum(r.success_rate for r in self.results) / len(self.results)
        
        return {
            "total_tests": len(self.results),
            "total_operations": total_operations,
            "total_duration": total_duration,
            "avg_success_rate": avg_success_rate,
            "results": [
                {
                    "operation": r.operation,
                    "avg_time": r.avg_time,
                    "success_rate": r.success_rate,
                    "error_count": len(r.errors)
                }
                for r in self.results
            ]
        }


# 性能测试配置
PERFORMANCE_CONFIG = {
    "default_iterations": 100,
    "warmup_iterations": 10,
    "timeout_seconds": 30,
    "max_concurrent_operations": 50,
    "memory_threshold_mb": 500,
    "cpu_threshold_percent": 80
}

# 性能测试数据
PERFORMANCE_TEST_DATA = {
    "users": [
        {
            "username": f"perf_user_{i}",
            "email": f"perf{i}@test.com",
            "password": f"PerfPass{i}123!"
        }
        for i in range(100)
    ],
    "posts": [
        {
            "title": f"Performance Test Post {i}",
            "content": f"This is performance test post number {i} with some content to test.",
            "tags": [f"perf{i}", "test", "performance"]
        }
        for i in range(200)
    ],
    "comments": [
        {
            "content": f"Performance test comment {i}"
        }
        for i in range(500)
    ]
}