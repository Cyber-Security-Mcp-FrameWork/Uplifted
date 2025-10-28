"""
分布式追踪模块
提供请求追踪、性能分析和调用链监控功能
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Generator
import threading
from contextvars import ContextVar

from .logger import get_logger

logger = get_logger(__name__)


class SpanKind(Enum):
    """Span类型"""
    INTERNAL = "internal"  # 内部调用
    SERVER = "server"      # 服务端
    CLIENT = "client"      # 客户端
    PRODUCER = "producer"  # 消息生产者
    CONSUMER = "consumer"  # 消息消费者


class SpanStatus(Enum):
    """Span状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class SpanContext:
    """Span上下文"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "baggage": self.baggage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpanContext":
        """从字典创建"""
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            baggage=data.get("baggage", {})
        )


@dataclass
class Span:
    """追踪Span"""
    context: SpanContext
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # 毫秒
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, end_time: Optional[datetime] = None) -> None:
        """结束Span"""
        if self.end_time is not None:
            return
        
        self.end_time = end_time or datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds() * 1000
    
    def set_tag(self, key: str, value: Any) -> "Span":
        """设置标签"""
        self.tags[key] = value
        return self
    
    def set_tags(self, tags: Dict[str, Any]) -> "Span":
        """设置多个标签"""
        self.tags.update(tags)
        return self
    
    def log(self, message: str, level: str = "info", **kwargs) -> "Span":
        """添加日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
        return self
    
    def set_status(self, status: SpanStatus, message: Optional[str] = None) -> "Span":
        """设置状态"""
        self.status = status
        if message:
            self.set_tag("status.message", message)
        return self
    
    def set_error(self, error: Exception) -> "Span":
        """设置错误"""
        self.status = SpanStatus.ERROR
        self.set_tag("error", True)
        self.set_tag("error.type", type(error).__name__)
        self.set_tag("error.message", str(error))
        self.log(f"Error: {error}", level="error")
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "context": self.context.to_dict(),
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "kind": self.kind.value,
            "status": self.status.value,
            "tags": self.tags,
            "logs": self.logs,
            "references": self.references
        }


@dataclass
class Trace:
    """追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # 毫秒
    
    def add_span(self, span: Span) -> None:
        """添加Span"""
        self.spans.append(span)
        
        # 更新追踪的开始和结束时间
        if self.start_time is None or span.start_time < self.start_time:
            self.start_time = span.start_time
        
        if span.end_time:
            if self.end_time is None or span.end_time > self.end_time:
                self.end_time = span.end_time
        
        # 计算持续时间
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds() * 1000
    
    def get_root_span(self) -> Optional[Span]:
        """获取根Span"""
        for span in self.spans:
            if span.context.parent_span_id is None:
                return span
        return None
    
    def get_span_by_id(self, span_id: str) -> Optional[Span]:
        """根据ID获取Span"""
        for span in self.spans:
            if span.context.span_id == span_id:
                return span
        return None
    
    def get_child_spans(self, parent_span_id: str) -> List[Span]:
        """获取子Span"""
        return [span for span in self.spans if span.context.parent_span_id == parent_span_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "spans": [span.to_dict() for span in self.spans],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration
        }


class SpanExporter(ABC):
    """Span导出器抽象基类"""
    
    @abstractmethod
    async def export(self, spans: List[Span]) -> bool:
        """导出Span"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭导出器"""
        pass


class ConsoleSpanExporter(SpanExporter):
    """控制台Span导出器"""
    
    async def export(self, spans: List[Span]) -> bool:
        """导出到控制台"""
        try:
            for span in spans:
                print(f"Span: {span.operation_name}")
                print(f"  Trace ID: {span.context.trace_id}")
                print(f"  Span ID: {span.context.span_id}")
                print(f"  Parent ID: {span.context.parent_span_id}")
                print(f"  Duration: {span.duration}ms")
                print(f"  Status: {span.status.value}")
                if span.tags:
                    print(f"  Tags: {span.tags}")
                if span.logs:
                    print(f"  Logs: {len(span.logs)} entries")
                print()
            return True
        except Exception as e:
            logger.error(f"控制台导出失败: {e}", exception=e)
            return False
    
    async def shutdown(self) -> None:
        """关闭导出器"""
        pass


class FileSpanExporter(SpanExporter):
    """文件Span导出器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = threading.Lock()
    
    async def export(self, spans: List[Span]) -> bool:
        """导出到文件"""
        try:
            with self._lock:
                with open(self.file_path, 'a', encoding='utf-8') as f:
                    for span in spans:
                        f.write(json.dumps(span.to_dict(), ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            logger.error(f"文件导出失败: {e}", exception=e)
            return False
    
    async def shutdown(self) -> None:
        """关闭导出器"""
        pass


class JaegerSpanExporter(SpanExporter):
    """Jaeger Span导出器"""
    
    def __init__(self, endpoint: str, service_name: str = "uplifted"):
        self.endpoint = endpoint
        self.service_name = service_name
    
    async def export(self, spans: List[Span]) -> bool:
        """导出到Jaeger"""
        try:
            # 这里应该实现Jaeger的具体导出逻辑
            # 为了简化，这里只是记录日志
            logger.info(f"导出{len(spans)}个Span到Jaeger: {self.endpoint}")
            return True
        except Exception as e:
            logger.error(f"Jaeger导出失败: {e}", exception=e)
            return False
    
    async def shutdown(self) -> None:
        """关闭导出器"""
        pass


class Tracer:
    """追踪器"""
    
    def __init__(self, service_name: str = "uplifted"):
        self.service_name = service_name
        self.exporters: List[SpanExporter] = []
        self.active_traces: Dict[str, Trace] = {}
        self.finished_spans: List[Span] = []
        self._export_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.Lock()
        
        # 采样配置
        self.sampling_rate = 1.0  # 采样率，1.0表示100%采样
        
        # 批量导出配置
        self.batch_size = 100
        self.export_interval = 5.0  # 秒
    
    def add_exporter(self, exporter: SpanExporter) -> None:
        """添加导出器"""
        self.exporters.append(exporter)
    
    def start_span(
        self,
        operation_name: str,
        parent_context: Optional[SpanContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None
    ) -> Span:
        """开始一个新的Span"""
        # 生成Span上下文
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            trace_id = self._generate_trace_id()
            parent_span_id = None
        
        span_id = self._generate_span_id()
        
        context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        # 创建Span
        span = Span(
            context=context,
            operation_name=operation_name,
            start_time=datetime.now(),
            kind=kind
        )
        
        # 设置服务标签
        span.set_tag("service.name", self.service_name)
        
        # 设置用户标签
        if tags:
            span.set_tags(tags)
        
        # 添加到活跃追踪
        with self._lock:
            if trace_id not in self.active_traces:
                self.active_traces[trace_id] = Trace(trace_id=trace_id)
            self.active_traces[trace_id].add_span(span)
        
        return span
    
    def finish_span(self, span: Span) -> None:
        """结束Span"""
        span.finish()
        
        with self._lock:
            # 添加到已完成的Span列表
            self.finished_spans.append(span)
            
            # 检查是否需要导出
            if len(self.finished_spans) >= self.batch_size:
                asyncio.create_task(self._export_spans())
    
    @contextmanager
    def span(
        self,
        operation_name: str,
        parent_context: Optional[SpanContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None
    ) -> Generator[Span, None, None]:
        """Span上下文管理器"""
        span = self.start_span(operation_name, parent_context, kind, tags)
        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            self.finish_span(span)
    
    @asynccontextmanager
    async def async_span(
        self,
        operation_name: str,
        parent_context: Optional[SpanContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        tags: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Span, None]:
        """异步Span上下文管理器"""
        span = self.start_span(operation_name, parent_context, kind, tags)
        try:
            yield span
        except Exception as e:
            span.set_error(e)
            raise
        finally:
            self.finish_span(span)
    
    async def start_export_loop(self) -> None:
        """开始导出循环"""
        if self._running:
            return
        
        self._running = True
        self._export_task = asyncio.create_task(self._export_loop())
        logger.info("开始Span导出循环")
    
    async def stop_export_loop(self) -> None:
        """停止导出循环"""
        if not self._running:
            return
        
        self._running = False
        
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        
        # 导出剩余的Span
        await self._export_spans()
        
        # 关闭所有导出器
        for exporter in self.exporters:
            await exporter.shutdown()
        
        logger.info("停止Span导出循环")
    
    async def _export_loop(self) -> None:
        """导出循环"""
        while self._running:
            try:
                await asyncio.sleep(self.export_interval)
                await self._export_spans()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"导出循环错误: {e}", exception=e)
    
    async def _export_spans(self) -> None:
        """导出Span"""
        if not self.finished_spans:
            return
        
        with self._lock:
            spans_to_export = self.finished_spans[:self.batch_size]
            self.finished_spans = self.finished_spans[self.batch_size:]
        
        if not spans_to_export:
            return
        
        # 并行导出到所有导出器
        tasks = []
        for exporter in self.exporters:
            task = asyncio.create_task(exporter.export(spans_to_export))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for result in results if result is True)
            logger.debug(f"导出{len(spans_to_export)}个Span，成功{success_count}/{len(tasks)}个导出器")
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪"""
        return self.active_traces.get(trace_id)
    
    def get_active_traces(self) -> List[Trace]:
        """获取活跃追踪"""
        return list(self.active_traces.values())
    
    def _generate_trace_id(self) -> str:
        """生成追踪ID"""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """生成SpanID"""
        return uuid.uuid4().hex[:16]


# 上下文变量，用于存储当前的Span上下文
current_span_context: ContextVar[Optional[SpanContext]] = ContextVar('current_span_context', default=None)


class TraceContext:
    """追踪上下文管理"""
    
    @staticmethod
    def get_current() -> Optional[SpanContext]:
        """获取当前Span上下文"""
        return current_span_context.get()
    
    @staticmethod
    def set_current(context: Optional[SpanContext]) -> None:
        """设置当前Span上下文"""
        current_span_context.set(context)
    
    @staticmethod
    @contextmanager
    def with_context(context: Optional[SpanContext]) -> Generator[None, None, None]:
        """使用指定上下文"""
        token = current_span_context.set(context)
        try:
            yield
        finally:
            current_span_context.reset(token)


# 全局追踪器实例
_global_tracer: Optional[Tracer] = None


def get_global_tracer() -> Tracer:
    """获取全局追踪器实例"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


def set_global_tracer(tracer: Tracer) -> None:
    """设置全局追踪器实例"""
    global _global_tracer
    _global_tracer = tracer


# 便捷函数
def start_span(
    operation_name: str,
    parent_context: Optional[SpanContext] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None
) -> Span:
    """开始一个新的Span"""
    tracer = get_global_tracer()
    if parent_context is None:
        parent_context = TraceContext.get_current()
    return tracer.start_span(operation_name, parent_context, kind, tags)


def finish_span(span: Span) -> None:
    """结束Span"""
    tracer = get_global_tracer()
    tracer.finish_span(span)


@contextmanager
def trace_span(
    operation_name: str,
    parent_context: Optional[SpanContext] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None
) -> Generator[Span, None, None]:
    """Span上下文管理器"""
    tracer = get_global_tracer()
    if parent_context is None:
        parent_context = TraceContext.get_current()
    
    with tracer.span(operation_name, parent_context, kind, tags) as span:
        with TraceContext.with_context(span.context):
            yield span


@asynccontextmanager
async def async_trace_span(
    operation_name: str,
    parent_context: Optional[SpanContext] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[Span, None]:
    """异步Span上下文管理器"""
    tracer = get_global_tracer()
    if parent_context is None:
        parent_context = TraceContext.get_current()
    
    async with tracer.async_span(operation_name, parent_context, kind, tags) as span:
        with TraceContext.with_context(span.context):
            yield span


def trace_function(
    operation_name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    tags: Optional[Dict[str, Any]] = None
):
    """函数追踪装饰器"""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__qualname__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with async_trace_span(operation_name, kind=kind, tags=tags) as span:
                    span.set_tag("function.name", func.__name__)
                    span.set_tag("function.module", func.__module__)
                    try:
                        result = await func(*args, **kwargs)
                        span.set_tag("function.result", "success")
                        return result
                    except Exception as e:
                        span.set_error(e)
                        raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with trace_span(operation_name, kind=kind, tags=tags) as span:
                    span.set_tag("function.name", func.__name__)
                    span.set_tag("function.module", func.__module__)
                    try:
                        result = func(*args, **kwargs)
                        span.set_tag("function.result", "success")
                        return result
                    except Exception as e:
                        span.set_error(e)
                        raise
            return sync_wrapper
    
    return decorator