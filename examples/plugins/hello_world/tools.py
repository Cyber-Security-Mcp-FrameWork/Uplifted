"""
Hello World Plugin - 工具实现

提供示例工具函数，展示如何实现插件工具。
"""

from typing import Dict, Any


def greet(name: str, language: str = "en") -> Dict[str, Any]:
    """
    向用户问好

    参数:
        name: 用户名称
        language: 问候语言 (en, es, fr, zh)

    返回:
        包含问候消息和语言的字典

    示例:
        >>> greet("Alice")
        {'greeting': 'Hello, Alice!', 'language': 'en'}

        >>> greet("Bob", "es")
        {'greeting': '¡Hola, Bob!', 'language': 'es'}
    """
    greetings = {
        'en': f"Hello, {name}!",
        'es': f"¡Hola, {name}!",
        'fr': f"Bonjour, {name}!",
        'zh': f"你好，{name}！"
    }

    greeting = greetings.get(language, greetings['en'])

    return {
        'greeting': greeting,
        'language': language
    }


def echo(message: str) -> Dict[str, str]:
    """
    回显消息

    简单地将输入消息原样返回。

    参数:
        message: 要回显的消息

    返回:
        包含回显消息的字典

    示例:
        >>> echo("Hello, World!")
        {'echo': 'Hello, World!'}
    """
    return {
        'echo': message
    }
