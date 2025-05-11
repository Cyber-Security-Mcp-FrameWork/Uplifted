from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import traceback
from ...api import app, timeout

import asyncio
from concurrent.futures import ThreadPoolExecutor
import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import base64
from ....storage.configuration import Configuration

prefix = "/storage"


# 请求模型：获取配置
class ConfigGetRequest(BaseModel):
    key: str  # 配置项的键

# 请求模型：设置单个配置
class ConfigSetRequest(BaseModel):
    key: str    # 配置项的键
    value: str  # 配置项的值

# 请求模型：批量设置配置
class BulkConfigSetRequest(BaseModel):
    configs: Dict[str, str]  # {键: 值} 字典


@app.post(f"{prefix}/config/get")
async def get_config(request: ConfigGetRequest):
    """
    获取指定配置项的值。

    参数:
        request.key (str): 配置项的键

    返回:
        包含键和值的 JSON 对象
    """
    # 从配置存储中读取值，如果不存在则返回 None 或默认信息
    value = Configuration.get(request.key)
    return {"key": request.key, "value": value}


@app.post(f"{prefix}/config/set")
async def set_config(request: ConfigSetRequest):
    """
    设置单个配置项的值。

    参数:
        request.key (str): 配置项的键
        request.value (str): 配置项的值

    返回:
        操作结果消息
    """
    # 将新的配置写入存储
    Configuration.set(request.key, request.value)
    return {"message": "配置更新成功"}


@app.post(f"{prefix}/config/bulk_set")
async def bulk_set_config(request: BulkConfigSetRequest):
    """
    批量设置多个配置项的值。

    参数:
        request.configs (Dict[str, str]): 包含多个键值对的字典

    返回:
        操作结果消息
    """
    # 遍历字典，逐一保存配置
    for key, value in request.configs.items():
        Configuration.set(key, value)
    return {"message": "Bulk配置更新成功"}

