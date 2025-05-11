from dotenv import load_dotenv
load_dotenv()

from ....storage.configuration import Configuration

import asyncio
import atexit



class BrowserManager:
    _instance = None
    _browser = None
    _loop = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            # 注册清理函数
            atexit.register(cls._cleanup)
        return cls._instance

    @classmethod
    async def initialize(cls):
        instance = cls.get_instance()
        if instance._browser is None:
            from browser_use import Browser
            browser = Browser()
            instance._browser = browser
            instance._loop = asyncio.get_event_loop()
            return browser
        return instance._browser

    @classmethod
    async def get_context(cls):
        """获取用于隔离的新浏览器上下文"""
        instance = cls.get_instance()
        if instance._browser:
            context = await instance._browser.new_context()
            return context
        return None

    @classmethod
    def _cleanup(cls):
        """当 Python 进程退出时调用的清理函数"""
        instance = cls.get_instance()
        if instance._browser and instance._loop:
            # 如果主事件循环已关闭，则创建一个新的事件循环
            try:
                loop = instance._loop if instance._loop.is_running() else asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(instance._browser.close())
            except:
                pass  # 关闭期间忽略所有错误

    @classmethod
    async def close(cls):
        """手动关闭方法 - 仅在明确需要关闭浏览器时使用"""
        instance = cls.get_instance()
        if instance._browser:
            await instance._browser.close()
            instance._browser = None

    @classmethod
    def get_browser(cls):
        instance = cls.get_instance()
        return instance._browser


class LLMManager:
    _instance = None
    _llm_model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_model(cls, model):
        instance = cls.get_instance()
        instance._llm_model = model
        print("设置 LLM 模型为:", model)

    @classmethod
    def get_model(cls):
        instance = cls.get_instance()
        print("正在获取 LLM 模型:", instance._llm_model)
        return instance._llm_model


def get_llm():
    llm_model = LLMManager.get_model()
    print("LLM 模型为", llm_model)
    
    if not llm_model:
        raise ValueError("调用 get_llm() 前未设置 LLM 模型")
    
    # 将我们的模型名称映射到标准模型名称
    openai_model_mapping = {
        "openai/gpt-4o": "gpt-4o",
        "gpt-4o": "gpt-4o",
        "openai/o3-mini": "o3-mini",
        "openai/gpt-4o-mini": "gpt-4o",
        "azure/gpt-4o": "gpt-4o",
        "azure/gpt-4o-mini": "gpt-4o-mini",
        "gpt-4o-azure": "gpt-4o"
    }

    claude_model_mapping = {
        "claude/claude-3-5-sonnet": "claude-3-5-sonnet-latest",
        "claude-3-5-sonnet": "claude-3-5-sonnet-latest",
        "bedrock/claude-3-5-sonnet": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-5-sonnet-aws": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    }

    deepseek_model_mapping = {
        "deepseek/deepseek-chat": "deepseek-chat"
    }
    
    # 处理 Azure OpenAI
    if llm_model in ["azure/gpt-4o", "gpt-4o-azure", "azure/gpt-4o-mini"]:
        azure_endpoint = Configuration.get("AZURE_OPENAI_ENDPOINT")
        azure_api_key = Configuration.get("AZURE_OPENAI_API_KEY")
        azure_api_version = Configuration.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
            
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            model="gpt-4o",
            api_version=azure_api_version,
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key
        )
    
    # 处理常规 OpenAI
    elif llm_model in openai_model_mapping:
        openai_api_key = Configuration.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("在配置中未找到 OpenAI API 密钥")
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model_name=openai_model_mapping[llm_model],
            openai_api_key=openai_api_key,
        )

    # 处理 Claude（Anthropic）
    elif llm_model in claude_model_mapping:
        if llm_model in ["bedrock/claude-3-5-sonnet", "claude-3-5-sonnet-aws"]:
            # AWS Bedrock 配置
            aws_access_key_id = Configuration.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = Configuration.get("AWS_SECRET_ACCESS_KEY")
            aws_region = Configuration.get("AWS_REGION")
            
            if not all([aws_access_key_id, aws_secret_access_key, aws_region]):
                raise ValueError("在配置中未找到 AWS 凭证")
            from langchain_community.chat_models import BedrockChat
            llm = BedrockChat(
                model_id=claude_model_mapping[llm_model],
                credentials_profile_name=None,
                region_name=aws_region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            # 常规 Anthropic 配置
            anthropic_api_key = Configuration.get("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("在配置中未找到 Anthropic API 密钥")
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=claude_model_mapping[llm_model],
                anthropic_api_key=anthropic_api_key,
                temperature=0.0,
                timeout=100
            )

    # 处理 DeepSeek 模型
    elif llm_model in deepseek_model_mapping:
        deepseek_api_key = Configuration.get("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            raise ValueError("在配置中未找到 DeepSeek API 密钥")
            
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model_name=deepseek_model_mapping[llm_model],
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
    
    else:
        raise ValueError(f"不支持用于浏览器的模型: {llm_model}")
    
    return llm


async def BrowserUse__browser_agent(task: str, expected_output: str):
    """一个能够浏览网页、提取信息并执行操作的 AI 代理"""
    from browser_use import Agent
    
    # 获取或创建浏览器实例
    browser = await BrowserManager.initialize()
    
    # 为该代理运行创建新的上下文
    context = await BrowserManager.get_context()
    
    # 使用浏览器上下文创建代理
    agent = Agent(
        task=task+"\n\nExpected Output: "+expected_output,
        llm=get_llm(),
        browser=browser,
        browser_context=context,  # 使用持久化上下文
        generate_gif=False
    )
    
    try:
        result = await agent.run()
        return result.final_result()
    finally:
        # 代理完成后清理上下文
        if context:
            await context.close()


# 浏览器使用工具列表
BrowserUse_tools = [
    BrowserUse__browser_agent
]