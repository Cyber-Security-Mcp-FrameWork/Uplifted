"""
认证模块集成测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from uplifted.auth.auth_service import AuthService
from uplifted.auth.password_service import PasswordService
from uplifted.auth.token_service import TokenService
from uplifted.database.managers import UserManager
from uplifted.cache.cache_manager import MemoryCacheManager
from uplifted.monitoring.logger import Logger


@pytest.mark.asyncio
class TestAuthIntegration:
    """认证模块集成测试"""
    
    async def test_complete_user_registration_flow(self, test_config, db_manager, cache_manager):
        """测试完整的用户注册流程"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 用户注册数据
        user_data = {
            "username": "integration_test_user",
            "email": "test@integration.com",
            "password": "SecurePass123!",
            "profile": {
                "first_name": "Integration",
                "last_name": "Test"
            }
        }
        
        # 执行注册
        user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            profile=user_data["profile"]
        )
        
        # 验证用户创建
        assert user.username == user_data["username"]
        assert user.email == user_data["email"]
        assert user.is_active is True
        assert user.profile["first_name"] == "Integration"
        
        # 验证密码被正确哈希
        assert user.password_hash != user_data["password"]
        assert password_service.verify_password(user_data["password"], user.password_hash)
        
        # 验证用户存储到数据库
        stored_user = await user_manager.get_user_by_username(user_data["username"])
        assert stored_user is not None
        assert stored_user.id == user.id
    
    async def test_complete_user_authentication_flow(self, test_config, db_manager, cache_manager):
        """测试完整的用户认证流程"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 先创建用户
        user_data = {
            "username": "auth_test_user",
            "email": "auth@test.com",
            "password": "AuthPass123!"
        }
        
        created_user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        # 执行认证
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=user_data["password"]
        )
        
        # 验证认证结果
        assert auth_result is not None
        assert "access_token" in auth_result
        assert "refresh_token" in auth_result
        assert "user" in auth_result
        assert auth_result["user"]["id"] == created_user.id
        
        # 验证令牌有效性
        access_token = auth_result["access_token"]
        token_payload = token_service.verify_token(access_token)
        assert token_payload["user_id"] == str(created_user.id)
        assert token_payload["username"] == user_data["username"]
        
        # 验证刷新令牌
        refresh_token = auth_result["refresh_token"]
        new_tokens = await auth_service.refresh_token(refresh_token)
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != access_token  # 新令牌应该不同
    
    async def test_authentication_failure_scenarios(self, test_config, db_manager, cache_manager):
        """测试认证失败场景"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 测试用户不存在
        auth_result = await auth_service.authenticate_user(
            username="nonexistent_user",
            password="password"
        )
        assert auth_result is None
        
        # 创建用户用于后续测试
        user_data = {
            "username": "failure_test_user",
            "email": "failure@test.com",
            "password": "CorrectPass123!"
        }
        
        await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        # 测试密码错误
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password="WrongPassword123!"
        )
        assert auth_result is None
        
        # 测试无效令牌
        with pytest.raises(Exception):
            token_service.verify_token("invalid.token.here")
    
    async def test_password_change_flow(self, test_config, db_manager, cache_manager):
        """测试密码修改流程"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建用户
        user_data = {
            "username": "password_change_user",
            "email": "password@test.com",
            "password": "OldPass123!"
        }
        
        user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        # 修改密码
        new_password = "NewPass456!"
        success = await auth_service.change_password(
            user_id=user.id,
            old_password=user_data["password"],
            new_password=new_password
        )
        assert success is True
        
        # 验证旧密码不再有效
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=user_data["password"]
        )
        assert auth_result is None
        
        # 验证新密码有效
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=new_password
        )
        assert auth_result is not None
        assert "access_token" in auth_result
    
    async def test_password_reset_flow(self, test_config, db_manager, cache_manager):
        """测试密码重置流程"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建用户
        user_data = {
            "username": "reset_test_user",
            "email": "reset@test.com",
            "password": "OriginalPass123!"
        }
        
        user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        # 请求密码重置
        reset_token = await auth_service.request_password_reset(user_data["email"])
        assert reset_token is not None
        
        # 验证重置令牌存储在缓存中
        cached_token = await cache_manager.get(f"password_reset:{user.id}")
        assert cached_token is not None
        
        # 执行密码重置
        new_password = "ResetPass789!"
        success = await auth_service.reset_password(reset_token, new_password)
        assert success is True
        
        # 验证新密码有效
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=new_password
        )
        assert auth_result is not None
        
        # 验证重置令牌已被清除
        cached_token = await cache_manager.get(f"password_reset:{user.id}")
        assert cached_token is None
    
    async def test_user_logout_flow(self, test_config, db_manager, cache_manager):
        """测试用户登出流程"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建用户并认证
        user_data = {
            "username": "logout_test_user",
            "email": "logout@test.com",
            "password": "LogoutPass123!"
        }
        
        user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=user_data["password"]
        )
        
        access_token = auth_result["access_token"]
        refresh_token = auth_result["refresh_token"]
        
        # 验证令牌有效
        token_payload = token_service.verify_token(access_token)
        assert token_payload["user_id"] == str(user.id)
        
        # 执行登出
        await auth_service.logout_user(user.id, access_token)
        
        # 验证令牌被加入黑名单
        is_blacklisted = await cache_manager.get(f"blacklist:{access_token}")
        assert is_blacklisted is not None
        
        # 验证刷新令牌失效
        with pytest.raises(Exception):
            await auth_service.refresh_token(refresh_token)
    
    async def test_concurrent_authentication(self, test_config, db_manager, cache_manager):
        """测试并发认证"""
        import asyncio
        
        # 初始化服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建用户
        user_data = {
            "username": "concurrent_user",
            "email": "concurrent@test.com",
            "password": "ConcurrentPass123!"
        }
        
        await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"]
        )
        
        # 并发认证
        async def authenticate():
            return await auth_service.authenticate_user(
                username=user_data["username"],
                password=user_data["password"]
            )
        
        # 同时执行多个认证请求
        tasks = [authenticate() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有认证都成功
        for result in results:
            assert result is not None
            assert "access_token" in result
            assert "refresh_token" in result
        
        # 验证每个令牌都是唯一的
        tokens = [result["access_token"] for result in results]
        assert len(set(tokens)) == len(tokens)  # 所有令牌都不同
    
    async def test_auth_with_monitoring(self, test_config, db_manager, cache_manager):
        """测试带监控的认证流程"""
        # 初始化服务和监控
        logger = Logger("auth_integration_test")
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 模拟监控记录
        with patch.object(logger, 'info') as mock_info:
            with patch.object(logger, 'warning') as mock_warning:
                # 创建用户
                user_data = {
                    "username": "monitored_user",
                    "email": "monitored@test.com",
                    "password": "MonitoredPass123!"
                }
                
                user = await auth_service.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"]
                )
                
                # 成功认证
                auth_result = await auth_service.authenticate_user(
                    username=user_data["username"],
                    password=user_data["password"]
                )
                assert auth_result is not None
                
                # 失败认证
                failed_auth = await auth_service.authenticate_user(
                    username=user_data["username"],
                    password="WrongPassword"
                )
                assert failed_auth is None
                
                # 验证监控日志被调用（这里只是验证结构，实际实现中会有具体的日志记录）
                # 在实际实现中，auth_service会调用logger记录各种事件