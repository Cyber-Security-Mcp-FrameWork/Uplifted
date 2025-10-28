"""
高级日志记录模块
提供结构化日志、多种输出格式和日志轮转等功能
"""

import json
import logging
import logging.handlers
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union
from contextlib import contextmanager

import asyncio


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogRecord:
    """日志记录"""
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class LogFormatter(ABC):
    """日志格式化器抽象基类"""
    
    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """格式化日志记录"""
        pass


class TextLogFormatter(LogFormatter):
    """文本日志格式化器"""
    
    def __init__(self, format_string: Optional[str] = None):
        self.format_string = format_string or (
            "{timestamp} [{level}] {logger_name} - {message}"
        )
    
    def format(self, record: LogRecord) -> str:
        """格式化为文本"""
        return self.format_string.format(
            timestamp=record.timestamp.isoformat(),
            level=record.level.name,
            message=record.message,
            logger_name=record.logger_name,
            module=record.module,
            function=record.function,
            line_number=record.line_number,
            thread_id=record.thread_id,
            process_id=record.process_id,
            **record.extra
        )


class JSONLogFormatter(LogFormatter):
    """JSON日志格式化器"""
    
    def __init__(self, include_extra: bool = True):
        self.include_extra = include_extra
    
    def format(self, record: LogRecord) -> str:
        """格式化为JSON"""
        log_data = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "logger": record.logger_name,
            "module": record.module,
            "function": record.function,
            "line": record.line_number,
            "thread_id": record.thread_id,
            "process_id": record.process_id
        }
        
        if record.exception:
            log_data["exception"] = record.exception
        
        if record.trace_id:
            log_data["trace_id"] = record.trace_id
        
        if record.span_id:
            log_data["span_id"] = record.span_id
        
        if self.include_extra and record.extra:
            log_data["extra"] = record.extra
        
        return json.dumps(log_data, ensure_ascii=False)


class LogHandler(ABC):
    """日志处理器抽象基类"""
    
    def __init__(self, formatter: LogFormatter, level: LogLevel = LogLevel.INFO):
        self.formatter = formatter
        self.level = level
        self._lock = threading.Lock()
    
    @abstractmethod
    def emit(self, record: LogRecord) -> None:
        """输出日志记录"""
        pass
    
    def should_emit(self, record: LogRecord) -> bool:
        """判断是否应该输出此日志记录"""
        return record.level.value >= self.level.value


class ConsoleLogHandler(LogHandler):
    """控制台日志处理器"""
    
    def __init__(self, formatter: LogFormatter, stream: TextIO = sys.stdout):
        super().__init__(formatter)
        self.stream = stream
    
    def emit(self, record: LogRecord) -> None:
        """输出到控制台"""
        if not self.should_emit(record):
            return
        
        with self._lock:
            formatted_message = self.formatter.format(record)
            self.stream.write(formatted_message + "\n")
            self.stream.flush()


class FileLogHandler(LogHandler):
    """文件日志处理器"""
    
    def __init__(self, formatter: LogFormatter, file_path: Union[str, Path]):
        super().__init__(formatter)
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file: Optional[TextIO] = None
    
    def emit(self, record: LogRecord) -> None:
        """输出到文件"""
        if not self.should_emit(record):
            return
        
        with self._lock:
            if self._file is None:
                self._file = open(self.file_path, 'a', encoding='utf-8')
            
            formatted_message = self.formatter.format(record)
            self._file.write(formatted_message + "\n")
            self._file.flush()
    
    def close(self) -> None:
        """关闭文件"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class RotatingFileLogHandler(LogHandler):
    """轮转文件日志处理器"""
    
    def __init__(
        self,
        formatter: LogFormatter,
        file_path: Union[str, Path],
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        super().__init__(formatter)
        self.file_path = Path(file_path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file: Optional[TextIO] = None
        self._current_size = 0
    
    def emit(self, record: LogRecord) -> None:
        """输出到轮转文件"""
        if not self.should_emit(record):
            return
        
        with self._lock:
            formatted_message = self.formatter.format(record)
            message_size = len(formatted_message.encode('utf-8'))
            
            # 检查是否需要轮转
            if self._current_size + message_size > self.max_bytes:
                self._rotate()
            
            if self._file is None:
                self._file = open(self.file_path, 'a', encoding='utf-8')
                self._current_size = self._file.tell()
            
            self._file.write(formatted_message + "\n")
            self._file.flush()
            self._current_size += message_size + 1  # +1 for newline
    
    def _rotate(self) -> None:
        """执行文件轮转"""
        if self._file:
            self._file.close()
            self._file = None
        
        # 移动现有文件
        for i in range(self.backup_count - 1, 0, -1):
            old_file = self.file_path.with_suffix(f"{self.file_path.suffix}.{i}")
            new_file = self.file_path.with_suffix(f"{self.file_path.suffix}.{i + 1}")
            if old_file.exists():
                if new_file.exists():
                    new_file.unlink()
                old_file.rename(new_file)
        
        # 移动当前文件
        if self.file_path.exists():
            backup_file = self.file_path.with_suffix(f"{self.file_path.suffix}.1")
            if backup_file.exists():
                backup_file.unlink()
            self.file_path.rename(backup_file)
        
        self._current_size = 0


class TimedRotatingFileLogHandler(LogHandler):
    """按时间轮转的文件日志处理器"""
    
    def __init__(
        self,
        formatter: LogFormatter,
        file_path: Union[str, Path],
        when: str = 'midnight',  # 'midnight', 'H', 'D', 'W0'-'W6'
        interval: int = 1,
        backup_count: int = 7
    ):
        super().__init__(formatter)
        self.file_path = Path(file_path)
        self.when = when
        self.interval = interval
        self.backup_count = backup_count
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file: Optional[TextIO] = None
        self._next_rotation = self._calculate_next_rotation()
    
    def emit(self, record: LogRecord) -> None:
        """输出到按时间轮转的文件"""
        if not self.should_emit(record):
            return
        
        with self._lock:
            current_time = time.time()
            
            # 检查是否需要轮转
            if current_time >= self._next_rotation:
                self._rotate()
                self._next_rotation = self._calculate_next_rotation()
            
            if self._file is None:
                self._file = open(self.file_path, 'a', encoding='utf-8')
            
            formatted_message = self.formatter.format(record)
            self._file.write(formatted_message + "\n")
            self._file.flush()
    
    def _calculate_next_rotation(self) -> float:
        """计算下次轮转时间"""
        current_time = time.time()
        
        if self.when == 'midnight':
            # 下一个午夜
            import datetime
            now = datetime.datetime.fromtimestamp(current_time)
            next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_midnight += datetime.timedelta(days=1)
            return next_midnight.timestamp()
        elif self.when == 'H':
            # 下一个小时
            return current_time + 3600 * self.interval
        elif self.when == 'D':
            # 下一天
            return current_time + 86400 * self.interval
        else:
            # 默认为小时
            return current_time + 3600 * self.interval
    
    def _rotate(self) -> None:
        """执行时间轮转"""
        if self._file:
            self._file.close()
            self._file = None
        
        # 生成时间戳后缀
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.file_path.with_suffix(f".{timestamp}{self.file_path.suffix}")
        
        if self.file_path.exists():
            self.file_path.rename(backup_file)
        
        # 清理旧文件
        self._cleanup_old_files()
    
    def _cleanup_old_files(self) -> None:
        """清理旧的备份文件"""
        pattern = f"{self.file_path.stem}.*{self.file_path.suffix}"
        backup_files = sorted(
            self.file_path.parent.glob(pattern),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # 保留最新的backup_count个文件
        for old_file in backup_files[self.backup_count:]:
            old_file.unlink()


class Logger:
    """高级日志记录器"""
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[LogHandler] = []
        self.level = LogLevel.INFO
        self._context: Dict[str, Any] = {}
    
    def add_handler(self, handler: LogHandler) -> None:
        """添加日志处理器"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler) -> None:
        """移除日志处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    def set_level(self, level: LogLevel) -> None:
        """设置日志级别"""
        self.level = level
    
    def set_context(self, **kwargs: Any) -> None:
        """设置日志上下文"""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """清除日志上下文"""
        self._context.clear()
    
    @contextmanager
    def context(self, **kwargs: Any):
        """临时日志上下文"""
        old_context = self._context.copy()
        self._context.update(kwargs)
        try:
            yield
        finally:
            self._context = old_context
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """内部日志记录方法"""
        if level.value < self.level.value:
            return
        
        import inspect
        import os
        import threading
        
        # 获取调用信息
        frame = inspect.currentframe()
        try:
            # 跳过当前帧和调用帧
            caller_frame = frame.f_back.f_back
            module = os.path.basename(caller_frame.f_code.co_filename)
            function = caller_frame.f_code.co_name
            line_number = caller_frame.f_lineno
        finally:
            del frame
        
        # 合并上下文和额外信息
        combined_extra = self._context.copy()
        if extra:
            combined_extra.update(extra)
        
        # 创建日志记录
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.name,
            module=module,
            function=function,
            line_number=line_number,
            thread_id=threading.get_ident(),
            process_id=os.getpid(),
            extra=combined_extra,
            exception=str(exception) if exception else None
        )
        
        # 发送到所有处理器
        for handler in self.handlers:
            try:
                handler.emit(record)
            except Exception as e:
                # 避免日志记录本身出错
                print(f"日志处理器错误: {e}", file=sys.stderr)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试日志"""
        self._log(LogLevel.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """记录信息日志"""
        self._log(LogLevel.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告日志"""
        self._log(LogLevel.WARNING, message, kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """记录错误日志"""
        self._log(LogLevel.ERROR, message, kwargs, exception)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """记录严重错误日志"""
        self._log(LogLevel.CRITICAL, message, kwargs, exception)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常日志"""
        import sys
        exc_info = sys.exc_info()
        if exc_info[1]:
            self.error(message, exc_info[1], **kwargs)
        else:
            self.error(message, **kwargs)


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def log_event(
        self,
        event_type: str,
        level: LogLevel = LogLevel.INFO,
        **data: Any
    ) -> None:
        """记录结构化事件"""
        message = f"Event: {event_type}"
        self.logger._log(level, message, {"event_type": event_type, **data})
    
    def log_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """记录指标"""
        extra = {
            "metric_name": metric_name,
            "metric_value": value,
            "metric_type": "gauge"
        }
        
        if unit:
            extra["metric_unit"] = unit
        
        if tags:
            extra["metric_tags"] = tags
        
        message = f"Metric: {metric_name}={value}"
        if unit:
            message += f" {unit}"
        
        self.logger.info(message, **extra)
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **metadata: Any
    ) -> None:
        """记录性能数据"""
        extra = {
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            "performance_log": True,
            **metadata
        }
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Performance: {operation} took {duration_ms:.2f}ms"
        
        self.logger._log(level, message, extra)
    
    def log_audit(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        result: str = "success",
        **details: Any
    ) -> None:
        """记录审计日志"""
        extra = {
            "audit_action": action,
            "audit_result": result,
            "audit_timestamp": datetime.now().isoformat(),
            **details
        }
        
        if user_id:
            extra["user_id"] = user_id
        
        if resource:
            extra["resource"] = resource
        
        message = f"Audit: {action} - {result}"
        self.logger.info(message, **extra)


# 全局日志记录器注册表
_loggers: Dict[str, Logger] = {}
_default_handlers: List[LogHandler] = []


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    console_output: bool = True,
    file_output: Optional[str] = None,
    json_format: bool = False,
    rotation: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> None:
    """配置全局日志设置"""
    global _default_handlers
    
    # 清除现有处理器
    _default_handlers.clear()
    
    # 选择格式化器
    if json_format:
        formatter = JSONLogFormatter()
    else:
        formatter = TextLogFormatter()
    
    # 添加控制台处理器
    if console_output:
        console_handler = ConsoleLogHandler(formatter)
        console_handler.level = level
        _default_handlers.append(console_handler)
    
    # 添加文件处理器
    if file_output:
        if rotation:
            file_handler = RotatingFileLogHandler(
                formatter, file_output, max_bytes, backup_count
            )
        else:
            file_handler = FileLogHandler(formatter, file_output)
        
        file_handler.level = level
        _default_handlers.append(file_handler)
    
    # 更新现有日志记录器
    for logger in _loggers.values():
        logger.handlers.clear()
        for handler in _default_handlers:
            logger.add_handler(handler)
        logger.set_level(level)


def get_logger(name: str) -> Logger:
    """获取日志记录器"""
    if name not in _loggers:
        logger = Logger(name)
        
        # 添加默认处理器
        for handler in _default_handlers:
            logger.add_handler(handler)
        
        _loggers[name] = logger
    
    return _loggers[name]


def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    logger = get_logger(name)
    return StructuredLogger(logger)


# 默认配置
configure_logging(
    level=LogLevel.INFO,
    console_output=True,
    json_format=False
)