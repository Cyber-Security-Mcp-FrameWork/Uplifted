"""
pytest配置文件
定义全局fixtures和测试配置
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

# 导入应用模块
from uplifted.core.database import DatabaseManager
from uplifted.core.cache import CacheManager
from uplifted.core.config import ConfigManager
from uplifted.monitoring import (
    get_global_metrics_manager,
    get_global_alert_manager,
    get_global_health_checker,
    get_global_monitoring_dashboard,
    configure_logging,
    LogLevel
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="session")
def test_config(temp_dir: Path) -> dict:
    """测试配置"""
    return {
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False,
            "pool_size": 5,
            "max_overflow": 10
        },
        "cache": {
            "backend": "memory",
            "url": "memory://",
            "default_timeout": 300
        },
        "logging": {
            "level": "DEBUG",
            "format": "json",
            "file": str(temp_dir / "test.log")
        },
        "monitoring": {
            "enabled": True,
            "metrics_interval": 1,
            "health_check_interval": 5
        },
        "security": {
            "secret_key": "test-secret-key-for-testing-only",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30
        }
    }


@pytest.fixture(scope="session")
async def app_config(test_config: dict) -> ConfigManager:
    """应用配置管理器"""
    config_manager = ConfigManager()
    config_manager.update_config(test_config)
    return config_manager


@pytest.fixture(scope="function")
async def db_manager(app_config: ConfigManager) -> AsyncGenerator[DatabaseManager, None]:
    """数据库管理器"""
    db_manager = DatabaseManager(app_config.get("database"))
    await db_manager.initialize()
    
    # 创建所有表
    await db_manager.create_tables()
    
    yield db_manager
    
    # 清理
    await db_manager.drop_tables()
    await db_manager.close()


@pytest.fixture(scope="function")
async def cache_manager(app_config: ConfigManager) -> AsyncGenerator[CacheManager, None]:
    """缓存管理器"""
    cache_manager = CacheManager(app_config.get("cache"))
    await cache_manager.initialize()
    
    yield cache_manager
    
    # 清理
    await cache_manager.clear_all()
    await cache_manager.close()


@pytest.fixture(scope="function")
async def metrics_manager():
    """指标管理器"""
    manager = get_global_metrics_manager()
    await manager.start_collection()
    
    yield manager
    
    # 清理
    await manager.stop_collection()
    manager.clear_metrics()


@pytest.fixture(scope="function")
async def alert_manager():
    """告警管理器"""
    manager = get_global_alert_manager()
    await manager.start()
    
    yield manager
    
    # 清理
    await manager.stop()
    manager.clear_rules()
    manager.clear_alerts()


@pytest.fixture(scope="function")
async def health_checker():
    """健康检查器"""
    checker = get_global_health_checker()
    
    yield checker
    
    # 清理
    await checker.stop_periodic_check()
    checker.clear_checks()


@pytest.fixture(scope="function")
def monitoring_dashboard():
    """监控仪表盘"""
    dashboard = get_global_monitoring_dashboard()
    
    yield dashboard
    
    # 清理 - 保留默认仪表盘，删除其他
    for dashboard_id in list(dashboard.dashboards.keys()):
        if dashboard_id != "default":
            dashboard.delete_dashboard(dashboard_id)


@pytest.fixture(scope="function")
def mock_logger():
    """模拟日志记录器"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture(scope="function")
def mock_async_logger():
    """模拟异步日志记录器"""
    logger = AsyncMock()
    logger.debug = AsyncMock()
    logger.info = AsyncMock()
    logger.warning = AsyncMock()
    logger.error = AsyncMock()
    logger.critical = AsyncMock()
    return logger


@pytest.fixture(scope="function")
async def sample_user_data():
    """示例用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": False
    }


@pytest.fixture(scope="function")
async def sample_post_data():
    """示例帖子数据"""
    return {
        "title": "测试帖子标题",
        "content": "这是一个测试帖子的内容，用于测试目的。",
        "tags": ["测试", "示例"],
        "is_published": True,
        "category": "技术"
    }


@pytest.fixture(scope="function")
async def sample_comment_data():
    """示例评论数据"""
    return {
        "content": "这是一个测试评论",
        "is_approved": True
    }


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging(test_config: dict):
    """配置测试日志"""
    logging_config = test_config["logging"]
    configure_logging(
        level=LogLevel.DEBUG,
        format_type=logging_config["format"],
        log_file=logging_config["file"]
    )


@pytest.fixture(scope="function")
def mock_email_service():
    """模拟邮件服务"""
    service = Mock()
    service.send_email = AsyncMock(return_value=True)
    service.send_verification_email = AsyncMock(return_value=True)
    service.send_password_reset_email = AsyncMock(return_value=True)
    return service


@pytest.fixture(scope="function")
def mock_file_storage():
    """模拟文件存储服务"""
    storage = Mock()
    storage.upload_file = AsyncMock(return_value="http://example.com/file.jpg")
    storage.delete_file = AsyncMock(return_value=True)
    storage.get_file_url = Mock(return_value="http://example.com/file.jpg")
    return storage


@pytest.fixture(scope="function")
async def authenticated_user(db_manager: DatabaseManager, sample_user_data: dict):
    """已认证的用户"""
    from uplifted.auth.models import User
    from uplifted.auth.services import AuthService
    
    # 创建用户
    auth_service = AuthService(db_manager)
    user = await auth_service.create_user(**sample_user_data)
    
    # 生成访问令牌
    access_token = await auth_service.create_access_token(user.id)
    
    return {
        "user": user,
        "access_token": access_token
    }


@pytest.fixture(scope="function")
def mock_external_api():
    """模拟外部API"""
    api = Mock()
    api.get = AsyncMock()
    api.post = AsyncMock()
    api.put = AsyncMock()
    api.delete = AsyncMock()
    return api


# 测试标记
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
pytest.mark.auth = pytest.mark.auth
pytest.mark.database = pytest.mark.database
pytest.mark.cache = pytest.mark.cache
pytest.mark.monitoring = pytest.mark.monitoring


# 测试跳过条件
def skip_if_no_redis():
    """如果没有Redis则跳过测试"""
    import redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        return False
    except:
        return True


def skip_if_no_postgres():
    """如果没有PostgreSQL则跳过测试"""
    try:
        import psycopg2
        return False
    except ImportError:
        return True


# 自定义断言
def assert_response_success(response, expected_status=200):
    """断言响应成功"""
    assert response.status_code == expected_status
    assert "error" not in response.json()


def assert_response_error(response, expected_status=400):
    """断言响应错误"""
    assert response.status_code == expected_status
    data = response.json()
    assert "error" in data or "detail" in data


def assert_valid_uuid(uuid_string):
    """断言有效的UUID"""
    import uuid
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def assert_valid_timestamp(timestamp_string):
    """断言有效的时间戳"""
    from datetime import datetime
    try:
        datetime.fromisoformat(timestamp_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False