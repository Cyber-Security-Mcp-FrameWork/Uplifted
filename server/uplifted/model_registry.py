from pydantic_ai.settings import ModelSettings
from decimal import Decimal
from pydantic_ai.models.openai import OpenAIModelSettings
from pydantic_ai.models.anthropic import AnthropicModelSettings
from functools import lru_cache


from typing import Literal

# 定义所有可用的模型名称
ModelNames = Literal[
    "openai/gpt-4o",
    "openai/gpt-4.5-preview",
    "openai/o3-mini",
    "openai/gpt-4o-mini",
    "azure/gpt-4o",
    "azure/gpt-4o-mini",
    "claude/claude-3-5-sonnet",
    "claude/claude-3-7-sonnet",
    "bedrock/claude-3-5-sonnet",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-1.5-flash",
    "ollama/llama3.2",
    "ollama/llama3.1:70b",
    "ollama/llama3.1",
    "ollama/llama3.3",
    "ollama/qwen2.5",
    "deepseek/deepseek-chat",
    "openrouter/anthropic/claude-3-sonnet",
    "openrouter/meta-llama/llama-3.1-8b-instruct",
    "openrouter/google/gemini-pro",
    "openrouter/<provider>/<model>",
]

# 将模型设置集中在一个字典中，便于维护
MODEL_SETTINGS = {
    "openai": OpenAIModelSettings(parallel_tool_calls=False),
    "anthropic": AnthropicModelSettings(parallel_tool_calls=False),
    "openrouter": OpenAIModelSettings(parallel_tool_calls=False),
    # 可根据需要添加其他提供者的设置
}

# 记录不支持并行工具调用的OpenAI模型
OPENAI_NON_PARALLEL_MODELS = {
    "o3-mini": True,
}

# 用于便于维护和扩展的全面模型注册表
MODEL_REGISTRY = {
    # OpenAI模型
    "openai/gpt-4o": {
        "provider": "openai", 
        "model_name": "gpt-4o", 
        "capabilities": [],
        "pricing": {"input": 2.50, "output": 10.00},
        "required_environment_variables": ["OPENAI_API_KEY"]
    },
    "openai/gpt-4.5-preview": {
        "provider": "openai", 
        "model_name": "gpt-4.5-preview", 
        "capabilities": [],
        "pricing": {"input": 75.00, "output": 150.00},
        "required_environment_variables": ["OPENAI_API_KEY"]
    },

    "openai/o3-mini": {
        "provider": "openai", 
        "model_name": "o3-mini", 
        "capabilities": [],
        "pricing": {"input": 1.1, "output": 4.4},
        "required_environment_variables": ["OPENAI_API_KEY"]
    },
    "openai/gpt-4o-mini": {
        "provider": "openai", 
        "model_name": "gpt-4o-mini", 
        "capabilities": [],
        "pricing": {"input": 0.15, "output": 0.60},
        "required_environment_variables": ["OPENAI_API_KEY"]
    },
    
    # Azure OpenAI模型
    "azure/gpt-4o": {
        "provider": "azure_openai", 
        "model_name": "gpt-4o", 
        "capabilities": [],
        "pricing": {"input": 2.50, "output": 10.00},
        "required_environment_variables": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_API_KEY"]
    },

    "azure/gpt-4o-mini": {
        "provider": "azure_openai", 
        "model_name": "gpt-4o-mini", 
        "capabilities": [],
        "pricing":{"input": 0.15, "output": 0.60},
        "required_environment_variables": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_API_KEY"]
    },
    
    # Deepseek模型
    "deepseek/deepseek-chat": {
        "provider": "deepseek", 
        "model_name": "deepseek-chat", 
        "capabilities": [],
        "pricing": {"input": 0.27, "output": 1.10},
        "required_environment_variables": ["DEEPSEEK_API_KEY"]
    },

    "gemini/gemini-2.0-flash": {
        "provider": "gemini", 
        "model_name": "gemini-2.0-flash", 
        "capabilities": [],
        "pricing": {"input": 0.10, "output": 0.40},
        "required_environment_variables": ["GOOGLE_GLA_API_KEY"]
    },

    "gemini/gemini-1.5-pro": {
        "provider": "gemini", 
        "model_name": "gemini-1.5-pro", 
        "capabilities": [],
        "pricing": {"input": 1.25, "output": 5.00},
        "required_environment_variables": ["GOOGLE_GLA_API_KEY"]
    },

    "gemini/gemini-1.5-flash": {
        "provider": "gemini", 
        "model_name": "gemini-1.5-flash", 
        "capabilities": [],
        "pricing": {"input": 0.075, "output": 0.30},
        "required_environment_variables": ["GOOGLE_GLA_API_KEY"]
    },
    
    "ollama/llama3.2": {
        "provider": "ollama", 
        "model_name": "llama3.2", 
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": []
    },

    "ollama/llama3.1:70b": {
        "provider": "ollama", 
        "model_name": "llama3.1:70b", 
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": []
    },

    "ollama/llama3.1": {
        "provider": "ollama", 
        "model_name": "llama3.1", 
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": []
    },

    "ollama/llama3.3": {
        "provider": "ollama", 
        "model_name": "llama3.3", 
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": []
    },

    "ollama/qwen2.5": {
        "provider": "ollama", 
        "model_name": "qwen2.5", 
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": []
    },

    # Anthropic模型
    "claude/claude-3-5-sonnet": {
        "provider": "anthropic", 
        "model_name": "claude-3-5-sonnet-latest", 
        "capabilities": ["computer_use"],
        "pricing": {"input": 3.00, "output": 15.00},
        "required_environment_variables": ["ANTHROPIC_API_KEY"]
    },
    "claude/claude-3-7-sonnet": {
        "provider": "anthropic", 
        "model_name": "claude-3-7-sonnet-latest", 
        "capabilities": ["computer_use"],
        "pricing": {"input": 3.00, "output": 15.00},
        "required_environment_variables": ["ANTHROPIC_API_KEY"]
    },

    # Bedrock Anthropic模型
    "bedrock/claude-3-5-sonnet": {
        "provider": "bedrock_anthropic", 
        "model_name": "us.anthropic.claude-3-5-sonnet-20241022-v2:0", 
        "capabilities": ["computer_use"],
        "pricing": {"input": 3.00, "output": 15.00},
        "required_environment_variables": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]
    },

    # OpenRouter模型
    "openrouter/anthropic/claude-3-sonnet": {
        "provider": "openrouter",
        "model_name": "anthropic/claude-3-sonnet",
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": ["OPENROUTER_API_KEY"]
    },
    "openrouter/meta-llama/llama-3.1-8b-instruct": {
        "provider": "openrouter",
        "model_name": "meta-llama/llama-3.1-8b-instruct",
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": ["OPENROUTER_API_KEY"]
    },
    "openrouter/google/gemini-pro": {
        "provider": "openrouter",
        "model_name": "google/gemini-pro",
        "capabilities": [],
        "pricing": {"input": 0.0, "output": 0.0},
        "required_environment_variables": ["OPENROUTER_API_KEY"]
    },
}

# 获取模型注册表条目
@lru_cache(maxsize=None)
def get_model_registry_entry(llm_model: str):
    """获取模型注册表条目，如果未找到则返回None"""
    if llm_model in MODEL_REGISTRY:
        return MODEL_REGISTRY[llm_model]
    
    # 处理动态的OpenRouter模型
    if llm_model.startswith("openrouter/"):
        # 从openrouter/后面提取模型名称
        model_name = llm_model.split("openrouter/", 1)[1]
        return {
            "provider": "openrouter",
            "model_name": model_name,  # 使用提供的完整模型名称
            "capabilities": [],
            "pricing": {"input": 0.0, "output": 0.0},
            "required_environment_variables": ["OPENROUTER_API_KEY"]
        }
    
    # 尝试不区分大小写的匹配作为回退
    llm_model_lower = llm_model.lower()
    for model_id, details in MODEL_REGISTRY.items():
        if model_id.lower() == llm_model_lower:
            return details
    
    print(f"警告: 未在注册表中找到模型 '{llm_model}'")
    return None

# 获取某一特定提供者的所有模型
def get_model_family(provider_type: str):
    """获取特定提供者类型的所有模型"""
    return [model for model, info in MODEL_REGISTRY.items() if info["provider"] == provider_type]

# 预先计算的模型系列分组
OPENAI_MODELS = [model for model, info in MODEL_REGISTRY.items() if info["provider"] in ["openai", "azure_openai", "deepseek"]]
ANTHROPIC_MODELS = [model for model, info in MODEL_REGISTRY.items() if info["provider"] in ["anthropic", "bedrock_anthropic"]]

# 获取模型设置
def get_model_settings(llm_model: str, tools=None):
    """根据模型类型获取相应的模型设置"""
    # 如果没有提供工具，则不需要模型设置
    if not tools:
        return None
    
    # 从注册表获取模型信息
    model_info = get_model_registry_entry(llm_model)
    if not model_info:
        return None

    # 如果模型不支持computer_use能力，则过滤掉此类工具
    filtered_tools = [
         t for t in tools
         if not ("ComputerUse" in t and not has_capability(llm_model, "computer_use"))
     ]
    
    # 如果没有剩余的工具，则返回None
    if not filtered_tools:
        return None

    # 特殊处理不支持并行工具调用的OpenAI模型
    if model_info["provider"] == "openai" and model_info["model_name"] in OPENAI_NON_PARALLEL_MODELS:
        return OpenAIModelSettings()
    
    # 对于所有其他模型，返回提供者设置
    provider = model_info["provider"]
    if provider in MODEL_SETTINGS:
        return MODEL_SETTINGS[provider]
    
    # 当没有找到匹配的设置时记录日志
    print(f"警告: 没有为{llm_model}找到模型设置")
    return None

# 获取模型定价信息
def get_pricing(llm_model: str):
    """获取模型的定价信息"""
    model_info = get_model_registry_entry(llm_model)
    if model_info and "pricing" in model_info:
        return model_info["pricing"]
    return None

# 计算基于输入和输出token的模型费用
def get_estimated_cost(input_tokens: int, output_tokens: int, llm_model: str):
    """计算使用特定模型时的预计费用"""
    pricing = get_pricing(llm_model)
    if not pricing:
        return "未知"
    
    # 使用Decimal进行定价计算，将token数转换为百万为单位
    input_tokens_millions = Decimal(str(input_tokens)) / Decimal('1000000')
    output_tokens_millions = Decimal(str(output_tokens)) / Decimal('1000000')
    
    input_cost = Decimal(str(pricing["input"])) * input_tokens_millions
    output_cost = Decimal(str(pricing["output"])) * output_tokens_millions
    total = input_cost + output_cost
    total = total.quantize(Decimal("0.0001"))
    # 保留4位小数
    return f"~${total}"

# 检查模型是否具有特定能力
def has_capability(llm_model: str, capability: str):
    """检查模型是否具有特定能力"""
    model_info = get_model_registry_entry(llm_model)
    if model_info and "capabilities" in model_info:
        return capability in model_info["capabilities"]
    return False


__all__ = [
    "get_model_registry_entry",
    "get_model_family",
    "get_model_settings",
    "get_pricing",
    "get_estimated_cost",
    "has_capability",
]