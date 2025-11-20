# -*- coding: utf-8 -*-
"""
Uplifted 整合框架

提供通用的工具整合能力，支持快速整合外部工具/服务到 Uplifted。
"""

from .base import BaseIntegration
from .cli import ConversationalCLI

__all__ = ["BaseIntegration", "ConversationalCLI"]
