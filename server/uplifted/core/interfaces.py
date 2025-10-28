"""
核心接口定义
实现依赖倒置原则，减少模块间的直接依赖
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import logging


class IConfiguration(ABC):
    """配置管理接口"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """删除配置项"""
        pass
    
    @abstractmethod
    def export_all(self) -> Dict[str, Any]:
        """导出所有配置"""
        pass


class ICache(ABC):
    """缓存管理接口"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, expiry_hours: Optional[int] = None) -> None:
        """设置缓存值"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存项"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass


class ILogger(ABC):
    """日志管理接口"""
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """记录调试信息"""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """记录信息"""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """记录警告"""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """记录错误"""
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误"""
        pass


class IModelRegistry(ABC):
    """模型注册表接口"""
    
    @abstractmethod
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    def list_models_by_provider(self, provider: str) -> List[str]:
        """按提供商列出模型"""
        pass
    
    @abstractmethod
    def is_model_supported(self, model_name: str) -> bool:
        """检查模型是否支持"""
        pass


class IToolManager(ABC):
    """工具管理接口"""
    
    @abstractmethod
    async def add_tool(self, tool_config: Dict[str, Any]) -> bool:
        """添加工具"""
        pass
    
    @abstractmethod
    async def remove_tool(self, tool_name: str) -> bool:
        """移除工具"""
        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        pass


class IAgentFactory(ABC):
    """代理工厂接口"""
    
    @abstractmethod
    async def create_agent(self, agent_config: Dict[str, Any]) -> Any:
        """创建代理"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass