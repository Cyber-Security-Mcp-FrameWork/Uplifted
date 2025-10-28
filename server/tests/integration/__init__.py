"""
集成测试模块

本模块包含系统各组件之间的集成测试，验证不同模块协同工作的正确性。
"""

# 集成测试配置
INTEGRATION_TEST_CONFIG = {
    "database": {
        "url": "sqlite:///test_integration.db",
        "echo": False
    },
    "cache": {
        "type": "memory",
        "max_size": 1000
    },
    "auth": {
        "secret_key": "integration_test_secret_key",
        "token_expiry": 3600
    },
    "monitoring": {
        "enabled": True,
        "log_level": "INFO"
    }
}

# 测试数据
INTEGRATION_TEST_DATA = {
    "users": [
        {
            "username": "integration_user1",
            "email": "user1@integration.test",
            "password": "IntegrationPass123!"
        },
        {
            "username": "integration_user2", 
            "email": "user2@integration.test",
            "password": "IntegrationPass456!"
        }
    ],
    "posts": [
        {
            "title": "Integration Test Post 1",
            "content": "This is a test post for integration testing",
            "tags": ["test", "integration"]
        },
        {
            "title": "Integration Test Post 2",
            "content": "Another test post for comprehensive testing",
            "tags": ["test", "comprehensive"]
        }
    ]
}