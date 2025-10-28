"""
配置管理模块
提供配置的加载、保存、热更新和验证功能
"""

import asyncio
import threading
import json
import yaml
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..core.interfaces import ILogger


class ConfigFormat(Enum):
    """配置文件格式"""
    JSON = "json"
    YAML = "yaml"
    YML = "yml"
    TOML = "toml"
    INI = "ini"


@dataclass
class ConfigSource:
    """配置源"""
    name: str
    path: str
    format: ConfigFormat
    priority: int = 100  # 数值越小优先级越高
    watch: bool = True
    required: bool = False


@dataclass
class ConfigValidationRule:
    """配置验证规则"""
    path: str  # 配置路径，如 "database.host"
    required: bool = False
    type_check: Optional[Type] = None
    validator: Optional[Callable[[Any], bool]] = None
    default_value: Any = None
    description: str = ""


class ConfigChangeEvent:
    """配置变更事件"""
    
    def __init__(self, 
                 source: str,
                 path: str,
                 old_value: Any,
                 new_value: Any,
                 timestamp: float = None):
        self.source = source
        self.path = path
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp or time.time()


class ConfigLoader(ABC):
    """配置加载器抽象基类"""
    
    @abstractmethod
    def load(self, file_path: str) -> Dict[str, Any]:
        """加载配置"""
        pass
    
    @abstractmethod
    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """保存配置"""
        pass
    
    @abstractmethod
    def validate_format(self, file_path: str) -> bool:
        """验证文件格式"""
        pass


class JSONConfigLoader(ConfigLoader):
    """JSON配置加载器"""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """加载JSON配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load JSON config from {file_path}: {e}")
    
    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """保存JSON配置"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def validate_format(self, file_path: str) -> bool:
        """验证JSON格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except Exception:
            return False


class YAMLConfigLoader(ConfigLoader):
    """YAML配置加载器"""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """加载YAML配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Failed to load YAML config from {file_path}: {e}")
    
    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """保存YAML配置"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception:
            return False
    
    def validate_format(self, file_path: str) -> bool:
        """验证YAML格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return True
        except Exception:
            return False


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监视器"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = weakref.ref(config_manager)
        self._last_modified = {}
        self._debounce_delay = 1.0  # 防抖延迟（秒）
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        current_time = time.time()
        
        # 防抖处理
        if file_path in self._last_modified:
            if current_time - self._last_modified[file_path] < self._debounce_delay:
                return
        
        self._last_modified[file_path] = current_time
        
        # 通知配置管理器
        manager = self.config_manager()
        if manager:
            asyncio.create_task(manager._handle_file_change(file_path))


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self.rules: List[ConfigValidationRule] = []
    
    def add_rule(self, rule: ConfigValidationRule) -> None:
        """添加验证规则"""
        self.rules.append(rule)
    
    def remove_rule(self, path: str) -> None:
        """移除验证规则"""
        self.rules = [rule for rule in self.rules if rule.path != path]
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        errors = []
        
        for rule in self.rules:
            try:
                value = self._get_nested_value(config, rule.path)
                
                # 检查必需字段
                if rule.required and value is None:
                    errors.append(f"Required field '{rule.path}' is missing")
                    continue
                
                # 如果值为None且有默认值，跳过验证
                if value is None and rule.default_value is not None:
                    continue
                
                # 类型检查
                if rule.type_check and value is not None:
                    if not isinstance(value, rule.type_check):
                        errors.append(
                            f"Field '{rule.path}' should be of type {rule.type_check.__name__}, "
                            f"got {type(value).__name__}"
                        )
                        continue
                
                # 自定义验证器
                if rule.validator and value is not None:
                    if not rule.validator(value):
                        errors.append(f"Field '{rule.path}' failed custom validation")
            
            except Exception as e:
                errors.append(f"Error validating field '{rule.path}': {e}")
        
        return errors
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典值"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用默认值"""
        result = config.copy()
        
        for rule in self.rules:
            if rule.default_value is not None:
                current_value = self._get_nested_value(result, rule.path)
                if current_value is None:
                    self._set_nested_value(result, rule.path, rule.default_value)
        
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套字典值"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
        self._config: Dict[str, Any] = {}
        self._sources: Dict[str, ConfigSource] = {}
        self._loaders: Dict[ConfigFormat, ConfigLoader] = {
            ConfigFormat.JSON: JSONConfigLoader(),
            ConfigFormat.YAML: YAMLConfigLoader(),
            ConfigFormat.YML: YAMLConfigLoader(),
        }
        self._validator = ConfigValidator(logger)
        self._change_callbacks: List[Callable[[ConfigChangeEvent], None]] = []
        self._observer: Optional[Observer] = None
        self._watcher = ConfigFileWatcher(self)
        self._lock = asyncio.Lock()
        self._file_timestamps: Dict[str, float] = {}
    
    def add_source(self, source: ConfigSource) -> None:
        """添加配置源"""
        self._sources[source.name] = source
        
        if self.logger:
            self.logger.info(f"Added config source: {source.name}")
    
    def remove_source(self, source_name: str) -> None:
        """移除配置源"""
        if source_name in self._sources:
            del self._sources[source_name]
            
            if self.logger:
                self.logger.info(f"Removed config source: {source_name}")
    
    def add_validation_rule(self, rule: ConfigValidationRule) -> None:
        """添加验证规则"""
        self._validator.add_rule(rule)
    
    def register_change_callback(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """注册配置变更回调"""
        self._change_callbacks.append(callback)
    
    def unregister_change_callback(self, callback: Callable[[ConfigChangeEvent], None]) -> None:
        """取消注册配置变更回调"""
        try:
            self._change_callbacks.remove(callback)
        except ValueError:
            pass
    
    async def load_all(self) -> bool:
        """加载所有配置源"""
        async with self._lock:
            try:
                # 按优先级排序
                sorted_sources = sorted(
                    self._sources.values(),
                    key=lambda x: x.priority
                )
                
                merged_config = {}
                
                for source in sorted_sources:
                    try:
                        config_data = await self._load_source(source)
                        if config_data:
                            # 深度合并配置
                            merged_config = self._deep_merge(merged_config, config_data)
                            
                            if self.logger:
                                self.logger.info(f"Loaded config from source: {source.name}")
                    
                    except Exception as e:
                        if source.required:
                            if self.logger:
                                self.logger.error(f"Failed to load required config source {source.name}: {e}")
                            return False
                        else:
                            if self.logger:
                                self.logger.warning(f"Failed to load optional config source {source.name}: {e}")
                
                # 应用默认值
                merged_config = self._validator.apply_defaults(merged_config)
                
                # 验证配置
                validation_errors = self._validator.validate(merged_config)
                if validation_errors:
                    if self.logger:
                        for error in validation_errors:
                            self.logger.error(f"Config validation error: {error}")
                    return False
                
                # 更新配置
                old_config = self._config.copy()
                self._config = merged_config
                
                # 触发变更事件
                await self._notify_config_change("system", "", old_config, merged_config)
                
                # 启动文件监视
                await self._start_file_watching()
                
                if self.logger:
                    self.logger.info("All configurations loaded successfully")
                
                return True
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error loading configurations: {e}")
                return False
    
    async def _load_source(self, source: ConfigSource) -> Optional[Dict[str, Any]]:
        """加载单个配置源"""
        if not os.path.exists(source.path):
            if source.required:
                raise FileNotFoundError(f"Required config file not found: {source.path}")
            return None
        
        loader = self._loaders.get(source.format)
        if not loader:
            raise ValueError(f"Unsupported config format: {source.format}")
        
        # 验证文件格式
        if not loader.validate_format(source.path):
            raise ValueError(f"Invalid config file format: {source.path}")
        
        # 记录文件时间戳
        self._file_timestamps[source.path] = os.path.getmtime(source.path)
        
        return loader.load(source.path)
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _start_file_watching(self) -> None:
        """启动文件监视"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        
        self._observer = Observer()
        
        # 监视所有配置文件目录
        watched_dirs = set()
        for source in self._sources.values():
            if source.watch and os.path.exists(source.path):
                dir_path = os.path.dirname(source.path)
                if dir_path not in watched_dirs:
                    self._observer.schedule(self._watcher, dir_path, recursive=False)
                    watched_dirs.add(dir_path)
        
        if watched_dirs:
            self._observer.start()
            
            if self.logger:
                self.logger.info(f"Started watching {len(watched_dirs)} config directories")
    
    async def _handle_file_change(self, file_path: str) -> None:
        """处理文件变更"""
        try:
            # 查找对应的配置源
            source = None
            for src in self._sources.values():
                if os.path.abspath(src.path) == os.path.abspath(file_path):
                    source = src
                    break
            
            if not source or not source.watch:
                return
            
            # 检查文件是否真的被修改
            if file_path in self._file_timestamps:
                current_mtime = os.path.getmtime(file_path)
                if current_mtime <= self._file_timestamps[file_path]:
                    return
            
            if self.logger:
                self.logger.info(f"Config file changed: {file_path}")
            
            # 重新加载配置
            await self.reload_source(source.name)
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error handling config file change {file_path}: {e}")
    
    async def reload_source(self, source_name: str) -> bool:
        """重新加载指定配置源"""
        async with self._lock:
            source = self._sources.get(source_name)
            if not source:
                return False
            
            try:
                old_config = self._config.copy()
                
                # 重新加载所有配置
                await self.load_all()
                
                if self.logger:
                    self.logger.info(f"Reloaded config source: {source_name}")
                
                return True
            
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error reloading config source {source_name}: {e}")
                return False
    
    async def reload_all(self) -> bool:
        """重新加载所有配置"""
        return await self.load_all()
    
    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = path.split('.')
        current = self._config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set(self, path: str, value: Any) -> None:
        """设置配置值（仅内存中）"""
        keys = path.split('.')
        current = self._config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        old_value = current.get(keys[-1])
        current[keys[-1]] = value
        
        # 触发变更事件
        event = ConfigChangeEvent("memory", path, old_value, value)
        for callback in self._change_callbacks:
            try:
                callback(event)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in config change callback: {e}")
    
    async def save_to_source(self, source_name: str) -> bool:
        """保存配置到指定源"""
        source = self._sources.get(source_name)
        if not source:
            return False
        
        loader = self._loaders.get(source.format)
        if not loader:
            return False
        
        try:
            return loader.save(self._config, source.path)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving config to {source_name}: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def get_sources(self) -> Dict[str, ConfigSource]:
        """获取所有配置源"""
        return self._sources.copy()
    
    async def _notify_config_change(self, 
                                   source: str, 
                                   path: str, 
                                   old_value: Any, 
                                   new_value: Any) -> None:
        """通知配置变更"""
        event = ConfigChangeEvent(source, path, old_value, new_value)
        
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in config change callback: {e}")
    
    async def shutdown(self) -> None:
        """关闭配置管理器"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        if self.logger:
            self.logger.info("Config manager shutdown")


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None
_manager_lock = threading.Lock()


def get_global_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _global_config_manager
    
    if _global_config_manager is None:
        with _manager_lock:
            if _global_config_manager is None:
                _global_config_manager = ConfigManager()
    
    return _global_config_manager


# 便捷函数
def get_config(path: str, default: Any = None) -> Any:
    """获取配置值"""
    return get_global_config_manager().get(path, default)


def set_config(path: str, value: Any) -> None:
    """设置配置值"""
    get_global_config_manager().set(path, value)


async def reload_config() -> bool:
    """重新加载配置"""
    return await get_global_config_manager().reload_all()