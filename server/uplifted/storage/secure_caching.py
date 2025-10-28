"""
安全的缓存管理模块

替换不安全的 Pickle 序列化，使用 JSON + HMAC 签名确保数据安全。

核心安全特性：
1. 安全序列化 - 使用 JSON 替代 Pickle
2. 数据签名 - HMAC-SHA256 防篡改
3. 类型安全 - 严格的数据类型验证
4. 审计日志 - 完整的操作追踪

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

import os
import json
import hmac
import hashlib
import base64
import time
import threading
import logging
from typing import Optional, Any, Dict, Union, List
from dataclasses import dataclass, asdict
from datetime import datetime

from ..core.interfaces import ICache


class SerializationError(Exception):
    """序列化相关异常"""
    pass


class SignatureError(Exception):
    """签名验证异常"""
    pass


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    expiry_time: int
    created_at: int
    data_type: str  # 数据类型标识


class SecureSerializer:
    """
    安全序列化器

    使用 JSON 进行序列化，支持常见 Python 类型的安全转换。
    """

    # 支持的安全数据类型
    SAFE_TYPES = {
        'str', 'int', 'float', 'bool', 'list', 'dict', 'NoneType',
        'tuple', 'set'
    }

    @staticmethod
    def serialize(data: Any) -> tuple[str, str]:
        """
        安全序列化数据

        Args:
            data: 要序列化的数据

        Returns:
            (json_str, type_name): JSON 字符串和类型名称

        Raises:
            SerializationError: 不支持的数据类型
        """
        data_type = type(data).__name__

        # 检查类型是否安全
        if data_type not in SecureSerializer.SAFE_TYPES:
            # 尝试转换为支持的类型
            if hasattr(data, '__dict__'):
                # 对象转字典
                try:
                    data = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
                    data_type = 'dict'
                except Exception as e:
                    raise SerializationError(f"无法序列化对象类型: {type(data).__name__}") from e
            else:
                raise SerializationError(f"不支持的数据类型: {data_type}")

        try:
            # 使用自定义编码器处理特殊类型
            json_str = json.dumps(data, default=SecureSerializer._json_default, ensure_ascii=False)
            return json_str, data_type

        except (TypeError, ValueError) as e:
            raise SerializationError(f"序列化失败: {e}") from e

    @staticmethod
    def deserialize(json_str: str, data_type: str) -> Any:
        """
        安全反序列化数据

        Args:
            json_str: JSON 字符串
            data_type: 数据类型名称

        Returns:
            反序列化后的数据

        Raises:
            SerializationError: 反序列化失败
        """
        try:
            data = json.loads(json_str)

            # 根据原始类型进行转换
            if data_type == 'tuple':
                return tuple(data) if isinstance(data, list) else data
            elif data_type == 'set':
                return set(data) if isinstance(data, list) else data
            else:
                return data

        except (json.JSONDecodeError, ValueError) as e:
            raise SerializationError(f"反序列化失败: {e}") from e

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """JSON 编码器的默认处理函数"""
        # 处理日期时间
        if isinstance(obj, datetime):
            return obj.isoformat()

        # 处理字节
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')

        # 处理集合
        if isinstance(obj, set):
            return list(obj)

        # 其他类型尝试转为字符串
        return str(obj)


class SignatureValidator:
    """
    数据签名验证器

    使用 HMAC-SHA256 对缓存数据进行签名，防止数据篡改。
    """

    def __init__(self, secret_key: Optional[bytes] = None, logger: Optional[logging.Logger] = None):
        """
        初始化签名验证器

        Args:
            secret_key: 密钥（用于 HMAC）
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)

        # 从环境变量或配置文件加载密钥
        if secret_key is None:
            secret_key_str = os.environ.get('UPLIFTED_CACHE_SECRET_KEY')
            if secret_key_str:
                secret_key = secret_key_str.encode('utf-8')
            else:
                # 默认密钥（生产环境必须修改！）
                self.logger.warning(
                    "使用默认缓存签名密钥，请在生产环境设置 UPLIFTED_CACHE_SECRET_KEY"
                )
                secret_key = b'uplifted-default-cache-key-change-in-production'

        self.secret_key = secret_key

    def sign(self, data: str) -> str:
        """
        生成数据签名

        Args:
            data: 要签名的数据

        Returns:
            签名字符串（十六进制）
        """
        signature = hmac.new(
            self.secret_key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify(self, data: str, signature: str) -> bool:
        """
        验证数据签名

        Args:
            data: 原始数据
            signature: 签名字符串

        Returns:
            签名是否有效
        """
        try:
            expected_signature = self.sign(data)
            # 常量时间比较（防止时序攻击）
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            self.logger.exception(f"签名验证异常: {e}")
            return False


class SecureCacheManager(ICache):
    """
    安全的缓存管理器

    使用 JSON + HMAC 替代不安全的 Pickle 序列化。

    特性：
    1. 安全序列化（JSON）
    2. 数据签名验证（HMAC-SHA256）
    3. 线程安全
    4. 统计信息
    5. 审计日志
    """

    def __init__(self,
                 storage_backend: Any = None,
                 secret_key: Optional[bytes] = None,
                 enable_signature: bool = True,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全缓存管理器

        Args:
            storage_backend: 存储后端（默认使用 ClientConfiguration）
            secret_key: 签名密钥
            enable_signature: 是否启用签名验证
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.enable_signature = enable_signature

        # 存储后端
        if storage_backend is None:
            from .configuration import ClientConfiguration
            self.storage = ClientConfiguration
        else:
            self.storage = storage_backend

        # 初始化组件
        self.serializer = SecureSerializer()
        if enable_signature:
            self.signature_validator = SignatureValidator(secret_key, logger)
        else:
            self.signature_validator = None

        # 线程锁
        self._lock = threading.RLock()

        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'signature_failures': 0,
            'serialization_errors': 0
        }

        # 审计日志
        self.audit_log: List[Dict[str, Any]] = []

        self.logger.info(
            f"SecureCacheManager initialized "
            f"(signature={'enabled' if enable_signature else 'disabled'})"
        )

    def _create_signed_payload(self, cache_entry: CacheEntry) -> str:
        """
        创建签名后的缓存数据

        Args:
            cache_entry: 缓存条目

        Returns:
            签名后的 Base64 编码字符串

        Raises:
            SerializationError: 序列化失败
        """
        try:
            # 序列化数据
            json_data, data_type = self.serializer.serialize(cache_entry.data)

            # 创建缓存条目字典
            entry_dict = {
                'data': json_data,
                'data_type': data_type,
                'expiry_time': cache_entry.expiry_time,
                'created_at': cache_entry.created_at
            }

            # 转换为 JSON
            entry_json = json.dumps(entry_dict, ensure_ascii=False)

            # 生成签名
            if self.enable_signature and self.signature_validator:
                signature = self.signature_validator.sign(entry_json)
                payload = f"{signature}:{entry_json}"
            else:
                payload = f"unsigned:{entry_json}"

            # Base64 编码
            return base64.b64encode(payload.encode('utf-8')).decode('utf-8')

        except SerializationError:
            raise
        except Exception as e:
            raise SerializationError(f"创建签名数据失败: {e}") from e

    def _parse_signed_payload(self, payload_b64: str) -> CacheEntry:
        """
        解析签名后的缓存数据

        Args:
            payload_b64: Base64 编码的签名数据

        Returns:
            CacheEntry: 缓存条目

        Raises:
            SerializationError: 反序列化失败
            SignatureError: 签名验证失败
        """
        try:
            # Base64 解码
            payload = base64.b64decode(payload_b64).decode('utf-8')

            # 分离签名和数据
            signature, entry_json = payload.split(':', 1)

            # 验证签名
            if self.enable_signature and self.signature_validator:
                if signature == 'unsigned':
                    raise SignatureError("缓存数据未签名")

                if not self.signature_validator.verify(entry_json, signature):
                    self._stats['signature_failures'] += 1
                    raise SignatureError("签名验证失败")

            # 解析 JSON
            entry_dict = json.loads(entry_json)

            # 反序列化数据
            data = self.serializer.deserialize(
                entry_dict['data'],
                entry_dict['data_type']
            )

            # 创建缓存条目
            return CacheEntry(
                data=data,
                expiry_time=entry_dict['expiry_time'],
                created_at=entry_dict['created_at'],
                data_type=entry_dict['data_type']
            )

        except (SignatureError, SerializationError):
            raise
        except Exception as e:
            self._stats['serialization_errors'] += 1
            raise SerializationError(f"解析签名数据失败: {e}") from e

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期返回 None
        """
        with self._lock:
            cache_key_full = f"cache_{key}"

            try:
                # 从存储获取数据
                serialized_data = self.storage.get(cache_key_full)

                if serialized_data is None:
                    self._stats['misses'] += 1
                    self._log_audit('get', key, success=False, reason='not_found')
                    return None

                # 解析数据
                cache_entry = self._parse_signed_payload(serialized_data)

                # 检查是否过期
                current_time = int(time.time())
                if current_time > cache_entry.expiry_time:
                    self.storage.delete(cache_key_full)
                    self._stats['misses'] += 1
                    self._log_audit('get', key, success=False, reason='expired')
                    return None

                # 命中
                self._stats['hits'] += 1
                self._log_audit('get', key, success=True)
                return cache_entry.data

            except SignatureError as e:
                # 签名验证失败，删除数据
                self.logger.error(f"缓存签名验证失败: {key} - {e}")
                self.storage.delete(cache_key_full)
                self._stats['misses'] += 1
                self._log_audit('get', key, success=False, reason='signature_error', error=str(e))
                return None

            except SerializationError as e:
                # 反序列化失败，删除数据
                self.logger.error(f"缓存反序列化失败: {key} - {e}")
                self.storage.delete(cache_key_full)
                self._stats['misses'] += 1
                self._log_audit('get', key, success=False, reason='deserialization_error', error=str(e))
                return None

            except Exception as e:
                self.logger.exception(f"获取缓存异常: {key}")
                self._stats['misses'] += 1
                self._log_audit('get', key, success=False, reason='exception', error=str(e))
                return None

    def set(self, key: str, value: Any, expiry_hours: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            expiry_hours: 过期时间（小时），默认 1 小时

        Raises:
            SerializationError: 序列化失败
        """
        with self._lock:
            cache_key_full = f"cache_{key}"

            try:
                # 计算过期时间
                expiry_seconds = (expiry_hours * 3600) if expiry_hours else 3600
                current_time = int(time.time())
                expiry_time = current_time + expiry_seconds

                # 创建缓存条目
                cache_entry = CacheEntry(
                    data=value,
                    expiry_time=expiry_time,
                    created_at=current_time,
                    data_type=type(value).__name__
                )

                # 序列化并签名
                signed_payload = self._create_signed_payload(cache_entry)

                # 保存到存储
                self.storage.delete(cache_key_full)  # 先删除旧数据
                self.storage.set(cache_key_full, signed_payload)

                self._stats['sets'] += 1
                self._log_audit('set', key, success=True)

            except SerializationError as e:
                self.logger.error(f"缓存序列化失败: {key} - {e}")
                self.storage.delete(cache_key_full)
                self._log_audit('set', key, success=False, reason='serialization_error', error=str(e))
                raise

            except Exception as e:
                self.logger.exception(f"设置缓存异常: {key}")
                self.storage.delete(cache_key_full)
                self._log_audit('set', key, success=False, reason='exception', error=str(e))
                raise

    def delete(self, key: str) -> None:
        """
        删除缓存项

        Args:
            key: 缓存键
        """
        with self._lock:
            cache_key_full = f"cache_{key}"
            self.storage.delete(cache_key_full)
            self._stats['deletes'] += 1
            self._log_audit('delete', key, success=True)

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            # 获取所有缓存键并删除
            all_config = self.storage.export_all()
            cache_keys = [k for k in all_config.keys() if k.startswith('cache_')]

            for cache_key in cache_keys:
                self.storage.delete(cache_key)

            self._stats['deletes'] += len(cache_keys)
            self._log_audit('clear', 'all', success=True, extra={'count': len(cache_keys)})

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                **self._stats,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2)
            }

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0,
                'signature_failures': 0,
                'serialization_errors': 0
            }

    def cleanup_expired(self) -> int:
        """
        清理过期缓存项

        Returns:
            清理的条目数
        """
        with self._lock:
            all_config = self.storage.export_all()
            cache_keys = [k for k in all_config.keys() if k.startswith('cache_')]
            cleaned_count = 0

            current_time = int(time.time())

            for cache_key in cache_keys:
                try:
                    serialized_data = self.storage.get(cache_key)
                    if serialized_data:
                        cache_entry = self._parse_signed_payload(serialized_data)

                        if current_time > cache_entry.expiry_time:
                            self.storage.delete(cache_key)
                            cleaned_count += 1

                except (SignatureError, SerializationError):
                    # 如果数据损坏或签名失败，也删除
                    self.storage.delete(cache_key)
                    cleaned_count += 1

                except Exception as e:
                    self.logger.warning(f"清理缓存项异常: {cache_key} - {e}")
                    # 出错也删除
                    self.storage.delete(cache_key)
                    cleaned_count += 1

            if cleaned_count > 0:
                self._log_audit('cleanup', 'expired', success=True, extra={'count': cleaned_count})

            return cleaned_count

    def _log_audit(self,
                   operation: str,
                   key: str,
                   success: bool,
                   reason: Optional[str] = None,
                   error: Optional[str] = None,
                   extra: Optional[Dict[str, Any]] = None):
        """记录审计日志"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'key': key,
            'success': success
        }

        if reason:
            audit_entry['reason'] = reason

        if error:
            audit_entry['error'] = error

        if extra:
            audit_entry.update(extra)

        self.audit_log.append(audit_entry)

        # 限制日志大小
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        with self._lock:
            return self.audit_log[-limit:]


# 便捷函数：创建安全缓存管理器
def create_secure_cache_manager(
    enable_signature: bool = True,
    storage_backend: Any = None,
    logger: Optional[logging.Logger] = None
) -> SecureCacheManager:
    """
    创建安全缓存管理器

    Args:
        enable_signature: 是否启用签名验证（生产环境推荐 True）
        storage_backend: 存储后端
        logger: 日志记录器

    Returns:
        SecureCacheManager: 安全缓存管理器实例
    """
    return SecureCacheManager(
        storage_backend=storage_backend,
        enable_signature=enable_signature,
        logger=logger
    )


# 全局安全缓存管理器实例
_global_secure_cache_manager: Optional[SecureCacheManager] = None
_cache_lock = threading.Lock()


def get_global_secure_cache_manager() -> SecureCacheManager:
    """获取全局安全缓存管理器"""
    global _global_secure_cache_manager

    if _global_secure_cache_manager is None:
        with _cache_lock:
            if _global_secure_cache_manager is None:
                _global_secure_cache_manager = create_secure_cache_manager(
                    enable_signature=True
                )

    return _global_secure_cache_manager
