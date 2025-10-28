"""
异步处理模块
提供任务队列、批处理、并发控制等异步处理功能
"""

import asyncio
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Union, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import weakref

from ..core.interfaces import ILogger

T = TypeVar('T')
R = TypeVar('R')


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """获取执行时长"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == TaskStatus.COMPLETED and self.error is None


@dataclass
class Task(Generic[T, R]):
    """异步任务"""
    id: str
    func: Callable[..., Union[R, asyncio.Future[R]]]
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    created_at: float = field(default_factory=time.time)
    callback: Optional[Callable[[TaskResult], None]] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int = 100
    max_wait_time: float = 5.0  # 最大等待时间
    min_batch_size: int = 1     # 最小批次大小
    enable_partial_processing: bool = True


@dataclass
class ProcessorStats:
    """处理器统计信息"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    active_tasks: int = 0
    queue_size: int = 0
    average_processing_time: float = 0.0
    throughput: float = 0.0  # 每秒处理任务数


class AsyncTaskProcessor:
    """异步任务处理器"""
    
    def __init__(self, 
                 max_workers: int = 10,
                 max_queue_size: int = 1000,
                 logger: Optional[ILogger] = None):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.logger = logger
        
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._workers: List[asyncio.Task] = []
        self._results: Dict[str, TaskResult] = {}
        self._stats = ProcessorStats()
        self._shutdown = False
        self._lock = asyncio.Lock()
        
        # 启动工作线程
        self._start_workers()
    
    def _start_workers(self) -> None:
        """启动工作线程"""
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
    
    async def _worker(self, worker_name: str) -> None:
        """工作线程"""
        while not self._shutdown:
            try:
                # 获取任务（优先级队列）
                priority_item = await asyncio.wait_for(
                    self._queue.get(), 
                    timeout=1.0
                )
                
                # 解包优先级和任务
                priority, task_id, task = priority_item
                
                # 处理任务
                await self._process_task(task, worker_name)
                
                # 标记任务完成
                self._queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Worker {worker_name} error: {e}")
    
    async def _process_task(self, task: Task, worker_name: str) -> None:
        """处理单个任务"""
        result = TaskResult(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=time.time()
        )
        
        async with self._lock:
            self._results[task.id] = result
            self._stats.active_tasks += 1
        
        try:
            # 执行任务
            if asyncio.iscoroutinefunction(task.func):
                if task.timeout:
                    task_result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    task_result = await task.func(*task.args, **task.kwargs)
            else:
                # 同步函数在线程池中执行
                loop = asyncio.get_event_loop()
                if task.timeout:
                    task_result = await asyncio.wait_for(
                        loop.run_in_executor(None, task.func, *task.args),
                        timeout=task.timeout
                    )
                else:
                    task_result = await loop.run_in_executor(
                        None, task.func, *task.args
                    )
            
            # 更新结果
            result.status = TaskStatus.COMPLETED
            result.result = task_result
            result.completed_at = time.time()
            
            async with self._lock:
                self._stats.completed_tasks += 1
            
            if self.logger:
                self.logger.debug(
                    f"Task {task.id} completed by {worker_name} "
                    f"in {result.duration:.2f}s"
                )
        
        except asyncio.TimeoutError:
            result.status = TaskStatus.FAILED
            result.error = TimeoutError(f"Task timeout after {task.timeout}s")
            result.completed_at = time.time()
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(task.retry_delay * task.retry_count)
                await self.submit_task(task)
                return
            
            async with self._lock:
                self._stats.failed_tasks += 1
            
            if self.logger:
                self.logger.warning(f"Task {task.id} timeout by {worker_name}")
        
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = e
            result.completed_at = time.time()
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(task.retry_delay * task.retry_count)
                await self.submit_task(task)
                return
            
            async with self._lock:
                self._stats.failed_tasks += 1
            
            if self.logger:
                self.logger.error(f"Task {task.id} failed by {worker_name}: {e}")
        
        finally:
            async with self._lock:
                self._stats.active_tasks -= 1
            
            # 执行回调
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(result)
                    else:
                        task.callback(result)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Task callback error: {e}")
    
    async def submit_task(self, task: Task) -> str:
        """提交任务"""
        if self._shutdown:
            raise RuntimeError("Processor is shutdown")
        
        # 优先级队列项：(负优先级值, 任务ID, 任务)
        # 负值是因为PriorityQueue是最小堆，我们想要高优先级先执行
        priority_item = (-task.priority.value, task.id, task)
        
        try:
            await self._queue.put(priority_item)
            
            async with self._lock:
                self._stats.total_tasks += 1
                self._stats.queue_size = self._queue.qsize()
            
            return task.id
            
        except asyncio.QueueFull:
            raise RuntimeError("Task queue is full")
    
    async def submit_function(self,
                             func: Callable,
                             *args,
                             priority: TaskPriority = TaskPriority.NORMAL,
                             timeout: Optional[float] = None,
                             callback: Optional[Callable] = None,
                             **kwargs) -> str:
        """提交函数作为任务"""
        task = Task(
            id=str(uuid.uuid4()),
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            callback=callback
        )
        
        return await self.submit_task(task)
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """获取任务结果"""
        start_time = time.time()
        
        while True:
            async with self._lock:
                result = self._results.get(task_id)
            
            if result is None:
                raise ValueError(f"Task {task_id} not found")
            
            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return result
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for task {task_id}")
            
            await asyncio.sleep(0.1)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            result = self._results.get(task_id)
            if result and result.status == TaskStatus.PENDING:
                result.status = TaskStatus.CANCELLED
                self._stats.cancelled_tasks += 1
                return True
        
        return False
    
    async def wait_for_completion(self) -> None:
        """等待所有任务完成"""
        await self._queue.join()
    
    def get_stats(self) -> ProcessorStats:
        """获取统计信息"""
        return ProcessorStats(
            total_tasks=self._stats.total_tasks,
            completed_tasks=self._stats.completed_tasks,
            failed_tasks=self._stats.failed_tasks,
            cancelled_tasks=self._stats.cancelled_tasks,
            active_tasks=self._stats.active_tasks,
            queue_size=self._queue.qsize(),
            average_processing_time=self._stats.average_processing_time,
            throughput=self._stats.throughput
        )
    
    async def shutdown(self, wait: bool = True) -> None:
        """关闭处理器"""
        self._shutdown = True
        
        if wait:
            await self.wait_for_completion()
        
        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()
        
        # 等待工作线程结束
        await asyncio.gather(*self._workers, return_exceptions=True)


class BatchProcessor(Generic[T, R]):
    """批处理器"""
    
    def __init__(self,
                 batch_func: Callable[[List[T]], Union[List[R], asyncio.Future[List[R]]]],
                 config: BatchConfig,
                 logger: Optional[ILogger] = None):
        self.batch_func = batch_func
        self.config = config
        self.logger = logger
        
        self._pending_items: List[Tuple[T, asyncio.Future[R]]] = []
        self._lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def process_item(self, item: T) -> R:
        """处理单个项目"""
        if self._shutdown:
            raise RuntimeError("Batch processor is shutdown")
        
        future: asyncio.Future[R] = asyncio.Future()
        
        async with self._lock:
            self._pending_items.append((item, future))
            
            # 检查是否需要立即处理批次
            if len(self._pending_items) >= self.config.batch_size:
                await self._process_batch()
            elif not self._batch_task:
                # 启动定时批处理任务
                self._batch_task = asyncio.create_task(self._wait_and_process())
        
        return await future
    
    async def _wait_and_process(self) -> None:
        """等待并处理批次"""
        try:
            await asyncio.sleep(self.config.max_wait_time)
            
            async with self._lock:
                if (len(self._pending_items) >= self.config.min_batch_size or
                    not self.config.enable_partial_processing):
                    await self._process_batch()
                
                self._batch_task = None
        
        except asyncio.CancelledError:
            pass
    
    async def _process_batch(self) -> None:
        """处理当前批次"""
        if not self._pending_items:
            return
        
        # 取出当前批次
        batch_items = self._pending_items[:self.config.batch_size]
        self._pending_items = self._pending_items[self.config.batch_size:]
        
        items = [item for item, _ in batch_items]
        futures = [future for _, future in batch_items]
        
        try:
            # 执行批处理函数
            if asyncio.iscoroutinefunction(self.batch_func):
                results = await self.batch_func(items)
            else:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self.batch_func, items)
            
            # 设置结果
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        
        except Exception as e:
            # 设置异常
            for future in futures:
                if not future.done():
                    future.set_exception(e)
            
            if self.logger:
                self.logger.error(f"Batch processing error: {e}")
    
    async def flush(self) -> None:
        """强制处理所有待处理项目"""
        async with self._lock:
            if self._pending_items:
                await self._process_batch()
            
            if self._batch_task:
                self._batch_task.cancel()
                self._batch_task = None
    
    async def shutdown(self) -> None:
        """关闭批处理器"""
        self._shutdown = True
        await self.flush()


class ConcurrencyLimiter:
    """并发限制器"""
    
    def __init__(self, max_concurrent: int):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def acquire(self):
        """获取并发许可"""
        await self._semaphore.acquire()
        
        async with self._lock:
            self._active_count += 1
        
        try:
            yield
        finally:
            async with self._lock:
                self._active_count -= 1
            
            self._semaphore.release()
    
    @property
    def active_count(self) -> int:
        """获取当前活跃数量"""
        return self._active_count
    
    @property
    def available_permits(self) -> int:
        """获取可用许可数"""
        return self._semaphore._value


class AsyncPipeline:
    """异步处理管道"""
    
    def __init__(self, 
                 stages: List[Callable],
                 concurrency_limit: Optional[int] = None,
                 logger: Optional[ILogger] = None):
        self.stages = stages
        self.logger = logger
        self._limiter = ConcurrencyLimiter(concurrency_limit) if concurrency_limit else None
    
    async def process(self, data: Any) -> Any:
        """处理数据通过管道"""
        current_data = data
        
        async def _process_with_limit():
            nonlocal current_data
            
            for i, stage in enumerate(self.stages):
                try:
                    if asyncio.iscoroutinefunction(stage):
                        current_data = await stage(current_data)
                    else:
                        loop = asyncio.get_event_loop()
                        current_data = await loop.run_in_executor(None, stage, current_data)
                
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Pipeline stage {i} error: {e}")
                    raise
            
            return current_data
        
        if self._limiter:
            async with self._limiter.acquire():
                return await _process_with_limit()
        else:
            return await _process_with_limit()
    
    async def process_batch(self, data_list: List[Any]) -> List[Any]:
        """批量处理数据"""
        tasks = [self.process(data) for data in data_list]
        return await asyncio.gather(*tasks, return_exceptions=True)


# 全局任务处理器实例
_global_processor: Optional[AsyncTaskProcessor] = None
_processor_lock = threading.Lock()


def get_global_processor() -> AsyncTaskProcessor:
    """获取全局任务处理器"""
    global _global_processor
    
    if _global_processor is None:
        with _processor_lock:
            if _global_processor is None:
                _global_processor = AsyncTaskProcessor()
    
    return _global_processor