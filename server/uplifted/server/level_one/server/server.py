from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import traceback
from ...api import app, timeout, handle_server_errors
from ..call import Call
import asyncio
import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import base64
import os


prefix = "/level_one"


class GPT4ORequest(BaseModel):
    prompt: str
    images: Optional[List[str]] = None
    response_format: Optional[Any] = []
    tools: Optional[Any] = []
    context: Optional[Any] = None
    llm_model: Optional[Any] = "openai/gpt-4o"
    system_prompt: Optional[Any] = None


@app.post(f"{prefix}/run_agent")
@handle_server_errors
async def call_run_agent(request: GPT4ORequest):
    """
    用于调用 GPT-4（含可选工具和 MCP 服务器）的端点。

    参数：
        request：包含提示及可选参数的 GPT4ORequest 对象

    返回：
        AI 模型的响应
    """
    try:
        # 处理 pickled 的响应格式
        if request.response_format != "str":
            try:
                # 解码并反序列化响应格式
                pickled_data = base64.b64decode(request.response_format)
                response_format = cloudpickle.loads(pickled_data)
            except Exception as e:
                tb = traceback.extract_tb(e.__traceback__)
                file_path = tb[-1].filename
                if "Uplifted/src/" in file_path:
                    file_path = file_path.split("Uplifted/src/")[1]
                line_number = tb[-1].lineno
                traceback.print_exc()
                # 如果反序列化失败，则回退到基础类型映射
                type_mapping = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                }
                response_format = type_mapping.get(request.response_format, str)
        else:
            response_format = str

        # 处理上下文（如果存在）
        if request.context is not None:
            try:
                pickled_context = base64.b64decode(request.context)
                context = cloudpickle.loads(pickled_context)
            except Exception as e:
                tb = traceback.extract_tb(e.__traceback__)
                file_path = tb[-1].filename
                if "Uplifted/src/" in file_path:
                    file_path = file_path.split("Uplifted/src/")[1]
                line_number = tb[-1].lineno
                traceback.print_exc()
                context = None
        else:
            context = None

        result = await Call.gpt_4o(
            prompt=request.prompt,
            images=request.images,
            response_format=response_format,
            tools=request.tools,
            context=context,
            llm_model=request.llm_model,
            system_prompt=request.system_prompt
        )

        if request.response_format != "str" and result["status_code"] == 200:
            result["result"] = cloudpickle.dumps(result["result"])
            result["result"] = base64.b64encode(result["result"]).decode('utf-8')
        return {"result": result, "status_code": 200}
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        file_path = tb[-1].filename
        if "Uplifted/src/" in file_path:
            file_path = file_path.split("Uplifted/src/")[1]
        line_number = tb[-1].lineno
        traceback.print_exc()
        print(f"Unexpected type for request.response_format: {request.response_format}")
        return {"result": {"status_code": 500, "detail": f"处理调用请求时出错，位于 {file_path} 的第 {line_number} 行：{str(e)}"}, "status_code": 500}