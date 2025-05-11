"""
用于使用 SQLite 处理数据缓存的模块。
"""

import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import dill
import base64
import time
from typing import Optional, Any
from .configuration import ClientConfiguration


def save_to_cache_with_expiry(data: Any, cache_key: str, expiry_seconds: int) -> None:
    """
    将数据保存到缓存中，并设置过期时间。
    
    参数：
        data: 要存入缓存的任意数据
        cache_key: 缓存数据的唯一标识符
        expiry_seconds: 缓存失效前的秒数
    """
    the_module = dill.detect.getmodule(data)
    if the_module is not None:
        cloudpickle.register_pickle_by_value(the_module)
        
    current_time = int(time.time())
    expiry_time = current_time + expiry_seconds
    cache_key_full = f"cache_{cache_key}"
    
    cache_data = {
        'data': data,
        'expiry_time': expiry_time,
        'created_at': current_time
    }
    
    try:
        ClientConfiguration.delete(cache_key_full)
        serialized_data = base64.b64encode(cloudpickle.dumps(cache_data)).decode('utf-8')
        ClientConfiguration.set(cache_key_full, serialized_data)
    except Exception:
        ClientConfiguration.delete(cache_key_full)
        raise


def get_from_cache_with_expiry(cache_key: str) -> Optional[Any]:
    """
    如果缓存未过期，则从缓存中获取数据。
    
    参数：
        cache_key: 缓存数据的唯一标识符
        
    返回：
        如果找到且未过期则返回缓存数据，否则返回 None
    """
    cache_key_full = f"cache_{cache_key}"
    serialized_data = ClientConfiguration.get(cache_key_full)

    if serialized_data is None:
        return None
    
    try:
        cache_data = cloudpickle.loads(base64.b64decode(serialized_data))
        current_time = int(time.time())
        
        if current_time > cache_data['expiry_time']:
            ClientConfiguration.delete(cache_key_full)
            return None

        return cache_data['data']
    except Exception:
        ClientConfiguration.delete(cache_key_full)
        return None