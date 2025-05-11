import inspect
import traceback
import types
from itertools import chain
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel
from openai import AsyncOpenAI, NOT_GIVEN
from openai import AsyncAzureOpenAI
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
import hashlib
from pydantic_ai.messages import ImageUrl
from pydantic_ai import BinaryContent

from typing import List, Union
from pydantic import BaseModel
from fastapi import HTTPException, status
from functools import wraps
from typing import Any, Callable, Optional, Dict
from pydantic_ai import RunContext, Tool
from anthropic import AsyncAnthropicBedrock
from dataclasses import dataclass
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types import chat
from collections.abc import AsyncIterator
from typing import Literal
from openai import AsyncStream


from ...storage.configuration import Configuration
from ...storage.caching import save_to_cache_with_expiry, get_from_cache_with_expiry

from ...tools_server.function_client import FunctionToolManager

# 从集中式模型注册表中导入
from ...model_registry import (
    MODEL_SETTINGS,
    MODEL_REGISTRY,
    OPENAI_MODELS,
    ANTHROPIC_MODELS,
    get_model_registry_entry,
    get_model_settings,
    has_capability
)

class ObjectResponse(BaseModel):
    pass

class SearchResult(ObjectResponse):
    any_customers: bool
    products: List[str]
    services: List[str]
    potential_competitors: List[str]
class CompanyObjective(ObjectResponse):
    objective: str
    goals: List[str]
    state: str
class HumanObjective(ObjectResponse):
    job_title: str
    job_description: str
    job_goals: List[str]
    
class Characterization(ObjectResponse):
    website_content: Union[SearchResult, None]
    company_objective: Union[CompanyObjective, None]
    human_objective: Union[HumanObjective, None]
    name_of_the_human_of_tasks: str = None
    contact_of_the_human_of_tasks: str = None

class OtherTask(ObjectResponse):
    task: str
    result: Any

def tool_wrapper(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 记录工具调用
        tool_name = getattr(func, "__name__", str(func))
        
        try:
            # 调用原始函数
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            print("工具调用失败:", e)
            return {"status_code": 500, "detail": f"工具调用失败: {e}"}
    
    return wrapper

def summarize_text(text: str, llm_model: Any, chunk_size: int = 100000, max_size: int = 300000) -> str:
    """用于通过将文本分块并对每块生成摘要，总结任意文本的基础函数。"""
    # 若文本为 None 或为空，则提前返回
    if text is None:
        return ""
    
    if not isinstance(text, str):
        try:
            text = str(text)
        except:
            return ""

    if not text:
        return ""

    # 如果文本长度已经低于最大限制，则直接返回
    if len(text) <= max_size:
        return text

    # 根据文本内容和参数生成缓存键
    cache_key = hashlib.md5(f"{text}{llm_model}{chunk_size}{max_size}".encode()).hexdigest()
    
    # 尝试先从缓存获取结果
    cached_result = get_from_cache_with_expiry(cache_key)
    if cached_result is not None:
        print("使用缓存的摘要")
        return cached_result

    # 根据模型调整块大小
    if "gpt" in str(llm_model).lower():
        # OpenAI 模型有 100 万字符的限制，为安全起见，我们使用较小的块大小
        chunk_size = min(chunk_size, 100000)  # OpenAI 每块最多 100K 字符
    elif "claude" in str(llm_model).lower():
        chunk_size = min(chunk_size, 200000)  # Claude 每块最多 200K 字符
    
    try:
        print(f"原始文本长度: {len(text)}")
        
        # 如果文本非常长，则进行初步的激进截断（截取前 200 万字符）
        if len(text) > 2000000:
            text = text[:2000000]
            print("文本过长，已截断至 2000000 个字符")
        
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        print(f"块的数量: {len(chunks)}")
        
        model = agent_creator(response_format=str, tools=[], context=None, llm_model=llm_model, system_prompt=None)
        if isinstance(model, dict) and "status_code" in model:
            print(f"创建模型出错: {model}")
            return text[:max_size]
        
        # 如果块数过多，则分批处理
        batch_size = 5
        summarized_chunks = []
        
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch = chunks[batch_start:batch_end]
            
            for i, chunk in enumerate(batch):
                chunk_num = batch_start + i + 1
                try:
                    print(f"正在处理块 {chunk_num}/{len(chunks)}，长度: {len(chunk)}")
                    
                    # 构造更聚焦的提示以获得更好的摘要效果
                    prompt = (
                        "请提供以下文本的极其简洁的摘要。"
                        "仅关注最重要的要点和关键信息。"
                        "在保留关键信息的前提下尽可能简短：\n\n"
                    )
                    
                    message = [{"type": "text", "text": prompt + chunk}]
                    result = model.run_sync(message)
                    
                    if result and hasattr(result, 'data') and result.data:
                        # 确保摘要不至于过长
                        summary = result.data[:max_size//len(chunks)]
                        summarized_chunks.append(summary)
                    else:
                        print(f"警告: 块 {chunk_num} 的结果为空或无效")
                        # 备用方案：使用截断后的短文本
                        summarized_chunks.append(chunk[:500] + "...")
                except Exception as e:
                    print(f"块 {chunk_num} 摘要出错: {str(e)}")
                    # 出错时使用截断后的短文本作为备用摘要
                    summarized_chunks.append(chunk[:500] + "...")
        
        # 合并所有摘要块
        combined_summary = "\n\n".join(summarized_chunks)
        
        # 如果合并后的摘要仍然太长，则递归使用更小的块进行摘要
        if len(combined_summary) > max_size:
            print(f"合并后的摘要仍过长 ({len(combined_summary)} 个字符)，正在递归摘要...")
            return summarize_text(
                combined_summary, 
                llm_model, 
                chunk_size=max(5000, chunk_size//4),  # 更激进地缩小块大小
                max_size=max_size
            )
            
        print(f"最终摘要长度: {len(combined_summary)}")
        
        # 将结果缓存 1 小时（3600 秒）
        save_to_cache_with_expiry(combined_summary, cache_key, 3600)
        
        return combined_summary
    except Exception as e:
        traceback.print_exc()
        print(f"summarize_text 出错: {str(e)}")
        # 若均失败，则返回截断后的文本
        return text[:max_size]

def summarize_message_prompt(message_prompt: str, llm_model: Any) -> str:
    """对消息提示进行摘要以在保留关键信息的同时减少长度。"""
    print("\n\n\n****************正在摘要消息提示****************\n\n\n")
    if message_prompt is None:
        return ""
    
    try:
        # 对消息提示使用较小的最大长度
        max_size = 50000  # 消息最大 50K 字符
        summarized_message_prompt = summarize_text(message_prompt, llm_model, max_size=max_size)
        if summarized_message_prompt is None:
            return ""
        print("摘要前消息提示长度: ", len(message_prompt))
        print(f"摘要后消息提示长度: {len(summarized_message_prompt)}")
        return summarized_message_prompt
    except Exception as e:
        print(f"summarize_message_prompt 出错: {str(e)}")
        try:
            return str(message_prompt)[:50000] if message_prompt else ""
        except:
            return ""

def summarize_system_prompt(system_prompt: str, llm_model: Any) -> str:
    """对系统提示进行摘要以在保留关键信息的同时减少长度。"""
    print("\n\n\n****************正在摘要系统提示****************\n\n\n")
    if system_prompt is None:
        return ""
    
    try:
        # 对系统提示使用较小的最大长度
        max_size = 50000  # 系统提示最大 50K 字符
        summarized_system_prompt = summarize_text(system_prompt, llm_model, max_size=max_size)
        if summarized_system_prompt is None:
            return ""
        print("系统提示摘要前长度: ", len(system_prompt))
        print(f"系统提示摘要后长度: {len(summarized_system_prompt)}")
        return summarized_system_prompt
    except Exception as e:
        print(f"summarize_system_prompt 出错: {str(e)}")
        try:
            return str(system_prompt)[:50000] if system_prompt else ""
        except:
            return ""

def summarize_context_string(context_string: str, llm_model: Any) -> str:
    """对上下文字符串进行摘要以在保留关键信息的同时减少长度。"""
    print("\n\n\n****************正在摘要上下文字符串****************\n\n\n")
    if context_string is None or context_string == "":
        return ""
    
    try:
        # 对上下文字符串使用较小的最大长度
        max_size = 50000  # 上下文最大 50K 字符
        summarized_context = summarize_text(context_string, llm_model, max_size=max_size)
        if summarized_context is None:
            return ""
        print("上下文字符串摘要前长度: ", len(context_string))
        print(f"上下文字符串摘要后长度: {len(summarized_context)}")
        return summarized_context
    except Exception as e:
        print(f"summarize_context_string 出错: {str(e)}")
        try:
            return str(context_string)[:50000] if context_string else ""
        except:
            return ""

def process_error_traceback(e):
    """统一提取并格式化错误追踪信息。"""
    tb = traceback.extract_tb(e.__traceback__)
    file_path = tb[-1].filename
    if "pydantic_ai" in file_path:
        return {"status_code": 500, "detail": str(e)}
    if "Uplifted/src/" in file_path:
        file_path = file_path.split("Uplifted/src/")[1]
    line_number = tb[-1].lineno
    return {"status_code": 500, "detail": f"处理请求时出错，位于 {file_path} 的第 {line_number} 行: {str(e)}"}

def prepare_message_history(prompt, images=None, llm_model=None, tools=None):
    """使用提示和图片准备消息历史，对于具备 computer_use 能力的模型添加截图。"""
    message_history = [prompt]
    
    if images:
        for image in images:
            message_history.append(ImageUrl(url=f"data:image/jpeg;base64,{image}"))

    # 当请求 ComputerUse 工具时，为具备 computer_use 能力的模型添加截图
    if llm_model and tools and ("ComputerUse.*" in tools or "Screenshot.*" in tools) and has_capability(llm_model, "computer_use"):
        try:
            from .cu import ComputerUse_screenshot_tool_bytes
            result_of_screenshot = ComputerUse_screenshot_tool_bytes()
            message_history.append(BinaryContent(data=result_of_screenshot, media_type='image/png'))
            print(f"为具备 computer_use 能力的模型 {llm_model} 添加了截图")
        except Exception as e:
            print(f"为 {llm_model} 添加截图时出错: {e}")
            
    return message_history

def format_response(result):
    """统一格式化成功的响应。"""
    messages = result.all_messages()
    
    # 跟踪工具使用情况
    tool_usage = []
    current_tool = None
    
    for msg in messages:
        if msg.kind == 'request':
            for part in msg.parts:
                if part.part_kind == 'tool-return':
                    if current_tool and current_tool['tool_name'] != 'final_result':
                        current_tool['tool_result'] = part.content
                        tool_usage.append(current_tool)
                    current_tool = None
                    
        elif msg.kind == 'response':
            for part in msg.parts:
                if part.part_kind == 'tool-call' and part.tool_name != 'final_result':
                    current_tool = {
                        'tool_name': part.tool_name,
                        'params': part.args,
                        'tool_result': None
                    }

    usage = result.usage()
    return {
        "status_code": 200,
        "result": result.data,
        "usage": {
            "input_tokens": usage.request_tokens,
            "output_tokens": usage.response_tokens
        },
        "tool_usage": tool_usage
    }

async def handle_compression_retry(prompt, images, tools, llm_model, response_format, context, system_prompt=None, agent_memory=None):
    """在遇到令牌限制问题时处理压缩并重试。"""
    try:
        # 压缩提示
        compressed_system_prompt = summarize_system_prompt(system_prompt, llm_model) if system_prompt else None
        compressed_message = summarize_message_prompt(prompt, llm_model)
        
        # 准备新的消息历史
        message_history = prepare_message_history(compressed_message, images, llm_model, tools)
        
        # 使用压缩后的提示创建新的代理
        roulette_agent = agent_creator(
            response_format=response_format,
            tools=tools,
            context=context,
            llm_model=llm_model,
            system_prompt=compressed_system_prompt,
            context_compress=False
        )
        
        # 使用压缩后的输入运行代理
        print("正在发送压缩提示的请求")
        if agent_memory:
            result = await roulette_agent.run(message_history, message_history=agent_memory)
        else:
            result = await roulette_agent.run(message_history)
        print("已收到压缩提示的响应")
        
        return result
    except Exception as e:
        raise e  # 重新抛出以保持错误处理一致

def _create_openai_client(api_key_name="OPENAI_API_KEY"):
    """辅助函数，根据指定的 API 密钥创建 OpenAI 客户端。"""
    api_key = Configuration.get(api_key_name, "sk-qIGzxUcLLYxY8d6taFnVVZAw8zXhfD6vS1i4ZJvAFYxWaK9H")
    if not api_key:
        return None, {"status_code": 401, "detail": f"未提供 API 密钥。请在配置中设置 {api_key_name}。"}
    
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.302.ai/v1")
    return client, None

def _create_azure_openai_client():
    """辅助函数，创建 Azure OpenAI 客户端。"""
    azure_endpoint = Configuration.get("AZURE_OPENAI_ENDPOINT")
    azure_api_version = Configuration.get("AZURE_OPENAI_API_VERSION")
    azure_api_key = Configuration.get("AZURE_OPENAI_API_KEY")

    missing_keys = []
    if not azure_endpoint:
        missing_keys.append("AZURE_OPENAI_ENDPOINT")
    if not azure_api_version:
        missing_keys.append("AZURE_OPENAI_API_VERSION")
    if not azure_api_key:
        missing_keys.append("AZURE_OPENAI_API_KEY")

    if missing_keys:
        return None, {
            "status_code": 401,
            "detail": f"未提供 API 密钥。请在配置中设置 {', '.join(missing_keys)}。"
        }

    client = AsyncAzureOpenAI(
        api_version=azure_api_version, 
        azure_endpoint=azure_endpoint, 
        api_key=azure_api_key
    )
    return client, None

def _create_openai_model(model_name: str, api_key_name: str = "OPENAI_API_KEY"):
    """辅助函数，根据指定的模型名称和 API 密钥创建 OpenAI 模型。"""
    client, error = _create_openai_client(api_key_name)
    if error:
        return None, error
    return OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client)), None

def _create_azure_openai_model(model_name: str):
    """辅助函数，根据指定的模型名称创建 Azure OpenAI 模型。"""
    client, error = _create_azure_openai_client()
    if error:
        return None, error
    return OpenAIModel(model_name, provider=OpenAIProvider(openai_client=client)), None

def _create_deepseek_model():
    """辅助函数，创建 Deepseek 模型。"""
    deepseek_api_key = Configuration.get("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        return None, {"status_code": 401, "detail": "未提供 API 密钥。请在配置中设置 DEEPSEEK_API_KEY。"}

    return OpenAIModel(
        'deepseek-chat',
        provider=OpenAIProvider(
            base_url='https://api.deepseek.com',
            api_key=deepseek_api_key
        )
    ), None

def _create_ollama_model(model_name: str):
    """辅助函数，根据指定的模型名称创建 Ollama 模型。"""
    # Ollama 在本地运行，因此不需要 API 密钥
    base_url = Configuration.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return OpenAIModel(
        model_name,
        provider=OpenAIProvider(base_url=base_url)
    ), None

def _create_openrouter_model(model_name: str):
    """辅助函数，根据指定的模型名称创建 OpenRouter 模型。"""
    api_key = Configuration.get("OPENROUTER_API_KEY")
    if not api_key:
        return None, {"status_code": 401, "detail": "未提供 API 密钥。请在配置中设置 OPENROUTER_API_KEY。"}
    
    # 如果模型名称以 openrouter/ 开头，则移除该前缀
    if model_name.startswith("openrouter/"):
        model_name = model_name.split("openrouter/", 1)[1]
    
    return OpenAIModel(
        model_name,
        provider=OpenAIProvider(
            base_url='https://openrouter.ai/api/v1',
            api_key=api_key
        )
    ), None

def _create_gemini_model(model_name: str):
    """辅助函数，创建 Gemini 模型。"""
    api_key = Configuration.get("GOOGLE_GLA_API_KEY")
    if not api_key:
        return None, {"status_code": 401, "detail": "未提供 API 密钥。请在配置中设置 GOOGLE_GLA_API_KEY。"}
    
    return GeminiModel(
        model_name,
        provider=GoogleGLAProvider(api_key=api_key)
    ), None

def _create_anthropic_model(model_name: str):
    """辅助函数，根据指定的模型名称创建 Anthropic 模型。"""
    anthropic_api_key = Configuration.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        return None, {"status_code": 401, "detail": "未提供 API 密钥。请在配置中设置 ANTHROPIC_API_KEY。"}
    return AnthropicModel(model_name, provider=AnthropicProvider(api_key=anthropic_api_key)), None

def _create_bedrock_anthropic_model(model_name: str):
    """辅助函数，根据指定的模型名称创建 AWS Bedrock Anthropic 模型。"""
    aws_access_key_id = Configuration.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = Configuration.get("AWS_SECRET_ACCESS_KEY")
    aws_region = Configuration.get("AWS_REGION")

    if not aws_access_key_id or not aws_secret_access_key or not aws_region:
        return None, {"status_code": 401, "detail": "未提供 AWS 凭证。请在配置中设置 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 和 AWS_REGION。"}
    
    bedrock_client = AsyncAnthropicBedrock(
        aws_access_key=aws_access_key_id,
        aws_secret_key=aws_secret_access_key,
        aws_region=aws_region
    )

    return AnthropicModel(model_name, provider=AnthropicProvider(anthropic_client=bedrock_client)), None

def _process_context(context):
    """将上下文数据处理为格式化的上下文字符串。"""
    if context is None:
        return ""
        
    if not isinstance(context, list):
        context = [context]
        
    context_string = ""
    for each in context:
        # from ...client.level_two.agent import Characterization
        # from ...client.level_two.agent import OtherTask
        # from ...client.tasks.tasks import Task
        # from ...client.tasks.task_response import ObjectResponse
        # from ...client.knowledge_base.knowledge_base import KnowledgeBase
        type_string = type(each).__name__
        the_class_string = None
        try:
            the_class_string = each.__bases__[0].__name__
        except:
            pass
        
        if type_string == 'Characterization':
            context_string += f"\n\n这是你的角色 ```角色 {each.model_dump()}```"
        elif type_string == 'OtherTask':
            context_string += f"\n\n来自问答的上下文: ```question_answering question: {each.task} answer: {each.result}```"
        elif type_string == 'Task':
            response = None
            description = each.description
            try:
                response = each.response.dict()
            except:
                try:
                    response = each.response.model_dump()
                except:
                    response = each.response
                    
            context_string += f"\n\n来自问答的上下文: ```question_answering question: {description} answer: {response}```   "
        elif the_class_string == 'ObjectResponse' or the_class_string == BaseModel.__name__:
            context_string += f"\n\n来自对象响应的上下文: ```Requested Output {each.model_fields}```"
        else:
            context_string += f"\n\n上下文 ```context {each}```"
            
    return context_string

def _setup_tools(roulette_agent, tools, llm_model):
    """为代理设置工具。"""
    the_wrapped_tools = []

    # 首先检查 ComputerUse 工具的兼容性
    if "ComputerUse.*" in tools:
        if not has_capability(llm_model, "computer_use"):
            return {
                "status_code": 405,
                "detail": f"模型 {llm_model} 不支持 ComputerUse 工具。请使用支持 computer_use 能力的模型。"
            }

    # 设置函数工具
    with FunctionToolManager() as function_client:
        the_list_of_tools = function_client.get_tools_by_name(tools)

        for each in the_list_of_tools:
            wrapped_tool = tool_wrapper(each)
            the_wrapped_tools.append(wrapped_tool)
        
    for each in the_wrapped_tools:
        signature = inspect.signature(each)
        roulette_agent.tool_plain(each, retries=5)

    # 为具备该能力的模型设置 ComputerUse 工具
    if "ComputerUse.*" in tools:
        try:
            from .cu import ComputerUse_tools
            for each in ComputerUse_tools:
                roulette_agent.tool_plain(each, retries=5)
        except Exception as e:
            print(f"设置 ComputerUse 工具时出错: {e}")

    # 设置 BrowserUse 工具
    if "BrowserUse.*" in tools:
        try:
            from .bu import BrowserUse_tools
            from .bu.browseruse import LLMManager
            LLMManager.set_model(llm_model)

            for each in BrowserUse_tools:
                roulette_agent.tool_plain(each, retries=5)
        except Exception as e:
            print(f"设置 BrowserUse 工具时出错: {e}")
            
    return roulette_agent

def _create_model_from_registry(llm_model: str):
    """根据注册表条目创建模型实例。"""
    registry_entry = get_model_registry_entry(llm_model)
    if not registry_entry:
        return None, {"status_code": 400, "detail": f"不支持的 LLM 模型: {llm_model}"}
    
    provider = registry_entry["provider"]
    model_name = registry_entry["model_name"]
    
    if provider == "openai":
        api_key = registry_entry.get("api_key", "OPENAI_API_KEY")
        return _create_openai_model(model_name, api_key)
    elif provider == "azure_openai":
        return _create_azure_openai_model(model_name)
    elif provider == "deepseek":
        return _create_deepseek_model()
    elif provider == "anthropic":
        return _create_anthropic_model(model_name)
    elif provider == "bedrock_anthropic":
        return _create_bedrock_anthropic_model(model_name)
    elif provider == "ollama":
        return _create_ollama_model(model_name)
    elif provider == "openrouter":
        return _create_openrouter_model(model_name)
    elif provider == "gemini":
        return _create_gemini_model(model_name)
    else:
        return None, {"status_code": 400, "detail": f"不支持的提供者: {provider}"}

def agent_creator(
        response_format: BaseModel = str,
        tools: list[str] = [],
        context: Any = None,
        llm_model: str = None,
        system_prompt: Optional[Any] = None,
        context_compress: bool = False
    ):
        # 若未指定模型，则使用默认模型
        if llm_model is None:
            llm_model = "openai/gpt-4o"
            print(f"未指定模型，使用默认模型: {llm_model}")
        
        # 从注册表中获取模型
        model, error = _create_model_from_registry(llm_model)
        if error:
            return error

        # 处理上下文
        context_string = _process_context(context)

        # 若启用压缩且上下文不为空，则压缩上下文字符串
        if context_compress and context_string:
            context_string = summarize_context_string(context_string, llm_model)

        # 准备系统提示
        system_prompt_ = ()
        if system_prompt is not None:
            system_prompt_ = system_prompt + f"上下文为: {context_string}"
        elif context_string != "":
            system_prompt_ = f"你是一个乐于助人的助手。用户想为任务添加上下文。上下文为: {context_string}"
        
        # 根据模型类型获取相应的模型设置
        model_settings = get_model_settings(llm_model, tools)

        # 创建代理
        roulette_agent = Agent(
            model,
            result_type=response_format,
            retries=5,
            system_prompt=system_prompt_,
            model_settings=model_settings
        )

        # 设置工具并检查错误
        result = _setup_tools(roulette_agent, tools, llm_model)
        
        # 如果 result 为字典，则表示出错
        if isinstance(result, dict) and "status_code" in result:
            return result

        return result