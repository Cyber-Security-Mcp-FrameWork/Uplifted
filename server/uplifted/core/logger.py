"""
结构化日志系统
提供统一的日志管理和格式化输出
"""

import logging
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from .interfaces import ILogger


class StructuredLogger(ILogger):
    """结构化日志记录器"""
    
    def __init__(self, name: str = "uplifted", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler('logs/uplifted.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 错误文件处理器
        error_handler = logging.FileHandler('logs/uplifted_error.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        
        # 设置格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """格式化日志消息"""
        if kwargs:
            log_data = {
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'data': kwargs
            }
            return json.dumps(log_data, ensure_ascii=False, indent=2)
        return message
    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试信息"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.debug(formatted_message)
    
    def info(self, message: str, **kwargs) -> None:
        """记录信息"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.info(formatted_message)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录警告"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.warning(formatted_message)
    
    def error(self, message: str, **kwargs) -> None:
        """记录错误"""
        # 自动添加堆栈跟踪
        if 'traceback' not in kwargs:
            kwargs['traceback'] = traceback.format_exc()
        
        formatted_message = self._format_message(message, **kwargs)
        self.logger.error(formatted_message)
    
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误"""
        # 自动添加堆栈跟踪
        if 'traceback' not in kwargs:
            kwargs['traceback'] = traceback.format_exc()
        
        formatted_message = self._format_message(message, **kwargs)
        self.logger.critical(formatted_message)
    
    def log_request(self, method: str, path: str, status_code: int, 
                   duration: float, **kwargs) -> None:
        """记录API请求"""
        self.info(
            f"API Request: {method} {path}",
            status_code=status_code,
            duration_ms=duration * 1000,
            **kwargs
        )
    
    def log_performance(self, operation: str, duration: float, **kwargs) -> None:
        """记录性能指标"""
        self.info(
            f"Performance: {operation}",
            duration_ms=duration * 1000,
            **kwargs
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """记录安全事件"""
        self.warning(
            f"Security Event: {event_type}",
            event_type=event_type,
            details=details,
            severity="security"
        )


class LoggerFactory:
    """日志工厂"""
    
    _loggers: Dict[str, StructuredLogger] = {}
    
    @classmethod
    def get_logger(cls, name: str, level: str = "INFO") -> StructuredLogger:
        """获取日志记录器"""
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name, level)
        return cls._loggers[name]
    
    @classmethod
    def configure_logging(cls, level: str = "INFO", 
                         log_file: Optional[str] = None) -> None:
        """配置全局日志设置"""
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file
        )