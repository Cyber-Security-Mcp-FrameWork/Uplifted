"""
测试模块
提供全面的单元测试和集成测试
"""

import os
import sys
import pytest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试配置
TEST_CONFIG = {
    "database_url": "sqlite:///:memory:",
    "redis_url": "redis://localhost:6379/1",
    "log_level": "DEBUG",
    "test_mode": True
}

# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# 确保测试目录存在
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_FIXTURES_DIR.mkdir(exist_ok=True)


def pytest_configure(config):
    """pytest配置"""
    # 设置测试环境变量
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = TEST_CONFIG["database_url"]
    os.environ["REDIS_URL"] = TEST_CONFIG["redis_url"]
    os.environ["LOG_LEVEL"] = TEST_CONFIG["log_level"]


def pytest_unconfigure(config):
    """pytest清理"""
    # 清理测试环境变量
    for key in ["TESTING", "DATABASE_URL", "REDIS_URL", "LOG_LEVEL"]:
        os.environ.pop(key, None)