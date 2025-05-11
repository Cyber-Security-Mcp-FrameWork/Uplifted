from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import traceback

import pydantic_ai
from ...api import app, timeout, handle_server_errors
from ..agent import Agent
import asyncio
import cloudpickle
cloudpickle.DEFAULT_PROTOCOL = 2
import base64


prefix = "/level_two"


class AgentRequest(BaseModel):
    agent_id: str
    prompt: str
    images: Optional[List[str]] = None
    response_format: Optional[Any] = []
    tools: Optional[Any] = []
    context: Optional[Any] = None
    llm_model: Optional[Any] = "openai/gpt-4o"
    system_prompt: Optional[Any] = None
    context_compress: Optional[Any] = False
    memory: Optional[Any] = False


@app.post(f"{prefix}/agent")
@handle_server_errors
async def call_agent(request: AgentRequest):
    """
    用于调用 GPT-4 的端点，支持可选工具和 MCP 服务器。

    参数：
        request: 包含提示和可选参数的 GPT4ORequest 对象

    返回：
        AI 模型的响应
    """
    try:
        # 处理 pickle 序列化的响应格式
        if request.response_format != "str":
            try:
                # 解码并反序列化响应格式
                pickled_data = base64.b64decode(request.response_format)
                response_format = cloudpickle.loads(pickled_data)
            except Exception as e:
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

        if request.context is not None:
            try:
                pickled_context = base64.b64decode(request.context)
                context = cloudpickle.loads(pickled_context)
            except Exception as e:
                context = None
        else:
            context = None

        result = await Agent.agent(
            agent_id=request.agent_id,
            prompt=request.prompt,
            images=request.images,
            response_format=response_format,
            tools=request.tools,
            context=context,
            llm_model=request.llm_model,
            system_prompt=request.system_prompt,
            context_compress=request.context_compress,
            memory=request.memory
        )

        if request.response_format != "str" and result["status_code"] == 200:
            result["result"] = cloudpickle.dumps(result["result"])
            result["result"] = base64.b64encode(result["result"]).decode('utf-8')
        return {"result": result, "status_code": 200}

    except pydantic_ai.exceptions.UnexpectedModelBehavior as e:
        return {"result": {"status_code": 500, "detail": f"请将您的响应格式更改为简单格式或者改进您的任务描述。您的响应格式对于模型来说过于复杂（不要在响应格式中使用类似 'dict' 的结构，请明确定义所有内容）。请尝试将其拆分为更小的部分。", "status_code": 500}}

    except Exception as e:
        traceback.print_exc()
        return {"result": {"status_code": 500, "detail": f"处理 Agent 请求时出错：{str(e)}"}, "status_code": 500}