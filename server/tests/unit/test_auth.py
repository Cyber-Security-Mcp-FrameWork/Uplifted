"""
认证模块单元测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from uplifted.auth.models import User, UserRole
from uplifted.auth.services import AuthService, PasswordService, TokenService
from uplifted.auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
    InvalidTokenError,
    PasswordValidationError
)


class TestPasswordService:
    """密码服务测试"""
    
    def setup_method(self):
        self.password_service = PasswordService()
    
    def test_hash_password(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = self.password_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "testpassword123"
        hashed = self.password_service.hash_password(password)
        
        assert self.password_service.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = self.password_service.hash_password(password)
        
        assert self.password_service.verify_password(wrong_password, hashed) is False
    
    def test_validate_password_strength_valid(self):
        """测试有效密码强度验证"""
        valid_passwords = [
            "StrongPass123!",
            "MySecure@Pass1",
            "Complex#Password9"
        ]
        
        for password in valid_passwords:
            # 不应该抛出异常
            self.password_service.validate_password_strength(password)
    
    def test_validate_password_strength_invalid(self):
        """测试无效密码强度验证"""
        invalid_passwords = [
            "weak",  # 太短
            "nouppercaseordigits",  # 没有大写字母和数字
            "NOLOWERCASEORDIGITS",  # 没有小写字母和数字
            "NoDigitsHere",  # 没有数字
            "12345678",  # 只有数字
            "password123"  # 常见密码
        ]
        
        for password in invalid_passwords:
            with pytest.raises(PasswordValidationError):
                self.password_service.validate_password_strength(password)


class TestTokenService:
    """令牌服务测试"""
    
    def setup_method(self):
        self.token_service = TokenService(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "user123"
        token = self.token_service.create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT令牌长度
    
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "user123"
        token = self.token_service.create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        user_id = "user123"
        token = self.token_service.create_access_token(user_id)
        
        payload = self.token_service.verify_token(token)
        
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        invalid_tokens = [
            "invalid.token.here",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            ""
        ]
        
        for token in invalid_tokens:
            with pytest.raises(InvalidTokenError):
                self.token_service.verify_token(token)
    
    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        # 创建一个立即过期的令牌
        token_service = TokenService(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=-1  # 负数表示已过期
        )
        
        user_id = "user123"
        token = token_service.create_access_token(user_id)
        
        with pytest.raises(InvalidTokenError):
            self.token_service.verify_token(token)
    
    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        user_id = "user123"
        refresh_token = self.token_service.create_refresh_token(user_id)
        
        new_access_token = self.token_service.refresh_access_token(refresh_token)
        
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 50
        
        # 验证新令牌
        payload = self.token_service.verify_token(new_access_token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"


@pytest.mark.asyncio
class TestAuthService:
    """认证服务测试"""
    
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.mock_cache = AsyncMock()
        self.auth_service = AuthService(self.mock_db, self.mock_cache)
    
    async def test_create_user_success(self):
        """测试成功创建用户"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User"
        }
        
        # 模拟数据库操作
        self.mock_db.get_user_by_username.return_value = None
        self.mock_db.get_user_by_email.return_value = None
        self.mock_db.create_user.return_value = User(
            id="user123",
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            created_at=datetime.now()
        )
        
        user = await self.auth_service.create_user(**user_data)
        
        assert user.username == user_data["username"]
        assert user.email == user_data["email"]
        assert user.full_name == user_data["full_name"]
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
        
        # 验证数据库调用
        self.mock_db.get_user_by_username.assert_called_once_with(user_data["username"])
        self.mock_db.get_user_by_email.assert_called_once_with(user_data["email"])
        self.mock_db.create_user.assert_called_once()
    
    async def test_create_user_duplicate_username(self):
        """测试创建重复用户名的用户"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User"
        }
        
        # 模拟用户名已存在
        self.mock_db.get_user_by_username.return_value = User(
            id="existing_user",
            username=user_data["username"],
            email="existing@example.com",
            role=UserRole.USER
        )
        
        with pytest.raises(AuthenticationError, match="用户名已存在"):
            await self.auth_service.create_user(**user_data)
    
    async def test_create_user_duplicate_email(self):
        """测试创建重复邮箱的用户"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User"
        }
        
        # 模拟邮箱已存在
        self.mock_db.get_user_by_username.return_value = None
        self.mock_db.get_user_by_email.return_value = User(
            id="existing_user",
            username="existing_user",
            email=user_data["email"],
            role=UserRole.USER
        )
        
        with pytest.raises(AuthenticationError, match="邮箱已存在"):
            await self.auth_service.create_user(**user_data)
    
    async def test_create_user_weak_password(self):
        """测试创建弱密码用户"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",  # 弱密码
            "full_name": "Test User"
        }
        
        with pytest.raises(PasswordValidationError):
            await self.auth_service.create_user(**user_data)
    
    async def test_authenticate_user_success(self):
        """测试成功认证用户"""
        username = "testuser"
        password = "StrongPass123!"
        
        # 创建模拟用户
        mock_user = User(
            id="user123",
            username=username,
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True
        )
        
        self.mock_db.get_user_by_username.return_value = mock_user
        
        # 模拟密码验证成功
        with patch.object(self.auth_service.password_service, 'verify_password', return_value=True):
            user = await self.auth_service.authenticate_user(username, password)
        
        assert user.id == mock_user.id
        assert user.username == username
        
        self.mock_db.get_user_by_username.assert_called_once_with(username)
    
    async def test_authenticate_user_not_found(self):
        """测试认证不存在的用户"""
        username = "nonexistent"
        password = "password"
        
        self.mock_db.get_user_by_username.return_value = None
        
        with pytest.raises(AuthenticationError, match="用户名或密码错误"):
            await self.auth_service.authenticate_user(username, password)
    
    async def test_authenticate_user_wrong_password(self):
        """测试认证错误密码"""
        username = "testuser"
        password = "wrongpassword"
        
        mock_user = User(
            id="user123",
            username=username,
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            role=UserRole.USER,
            is_active=True,
            is_verified=True
        )
        
        self.mock_db.get_user_by_username.return_value = mock_user
        
        # 模拟密码验证失败
        with patch.object(self.auth_service.password_service, 'verify_password', return_value=False):
            with pytest.raises(AuthenticationError, match="用户名或密码错误"):
                await self.auth_service.authenticate_user(username, password)
    
    async def test_authenticate_user_inactive(self):
        """测试认证未激活用户"""
        username = "testuser"
        password = "StrongPass123!"
        
        mock_user = User(
            id="user123",
            username=username,
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            role=UserRole.USER,
            is_active=False,  # 未激活
            is_verified=True
        )
        
        self.mock_db.get_user_by_username.return_value = mock_user
        
        with patch.object(self.auth_service.password_service, 'verify_password', return_value=True):
            with pytest.raises(AuthenticationError, match="账户已被禁用"):
                await self.auth_service.authenticate_user(username, password)
    
    async def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "user123"
        
        token = await self.auth_service.create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    async def test_verify_access_token_valid(self):
        """测试验证有效访问令牌"""
        user_id = "user123"
        
        # 创建令牌
        token = await self.auth_service.create_access_token(user_id)
        
        # 模拟用户存在
        mock_user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
            is_active=True
        )
        self.mock_db.get_user_by_id.return_value = mock_user
        
        # 验证令牌
        user = await self.auth_service.verify_access_token(token)
        
        assert user.id == user_id
        self.mock_db.get_user_by_id.assert_called_once_with(user_id)
    
    async def test_verify_access_token_invalid(self):
        """测试验证无效访问令牌"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(InvalidTokenError):
            await self.auth_service.verify_access_token(invalid_token)
    
    async def test_verify_access_token_user_not_found(self):
        """测试验证令牌但用户不存在"""
        user_id = "user123"
        
        # 创建令牌
        token = await self.auth_service.create_access_token(user_id)
        
        # 模拟用户不存在
        self.mock_db.get_user_by_id.return_value = None
        
        with pytest.raises(UserNotFoundError):
            await self.auth_service.verify_access_token(token)
    
    async def test_change_password_success(self):
        """测试成功修改密码"""
        user_id = "user123"
        old_password = "OldPass123!"
        new_password = "NewPass123!"
        
        mock_user = User(
            id=user_id,
            username="testuser",
            password_hash="$2b$12$old_hashed_password",
            role=UserRole.USER,
            is_active=True
        )
        
        self.mock_db.get_user_by_id.return_value = mock_user
        self.mock_db.update_user_password.return_value = True
        
        # 模拟旧密码验证成功
        with patch.object(self.auth_service.password_service, 'verify_password', return_value=True):
            result = await self.auth_service.change_password(user_id, old_password, new_password)
        
        assert result is True
        self.mock_db.get_user_by_id.assert_called_once_with(user_id)
        self.mock_db.update_user_password.assert_called_once()
    
    async def test_change_password_wrong_old_password(self):
        """测试修改密码时旧密码错误"""
        user_id = "user123"
        old_password = "WrongOldPass"
        new_password = "NewPass123!"
        
        mock_user = User(
            id=user_id,
            username="testuser",
            password_hash="$2b$12$old_hashed_password",
            role=UserRole.USER,
            is_active=True
        )
        
        self.mock_db.get_user_by_id.return_value = mock_user
        
        # 模拟旧密码验证失败
        with patch.object(self.auth_service.password_service, 'verify_password', return_value=False):
            with pytest.raises(AuthenticationError, match="当前密码错误"):
                await self.auth_service.change_password(user_id, old_password, new_password)
    
    async def test_reset_password_request(self):
        """测试请求重置密码"""
        email = "test@example.com"
        
        mock_user = User(
            id="user123",
            username="testuser",
            email=email,
            role=UserRole.USER,
            is_active=True
        )
        
        self.mock_db.get_user_by_email.return_value = mock_user
        
        # 模拟邮件服务
        with patch('uplifted.auth.services.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            result = await self.auth_service.request_password_reset(email)
        
        assert result is True
        self.mock_db.get_user_by_email.assert_called_once_with(email)
        mock_send_email.assert_called_once()
    
    async def test_logout_user(self):
        """测试用户登出"""
        user_id = "user123"
        token = "access_token_here"
        
        # 模拟将令牌加入黑名单
        result = await self.auth_service.logout_user(user_id, token)
        
        assert result is True
        # 验证令牌被加入缓存黑名单
        self.mock_cache.set.assert_called_once()


@pytest.mark.asyncio
class TestAuthMiddleware:
    """认证中间件测试"""
    
    def setup_method(self):
        from uplifted.auth.middleware import AuthMiddleware
        
        self.mock_auth_service = AsyncMock()
        self.middleware = AuthMiddleware(self.mock_auth_service)
    
    async def test_authenticate_request_with_valid_token(self):
        """测试有效令牌的请求认证"""
        token = "Bearer valid_token_here"
        
        mock_user = User(
            id="user123",
            username="testuser",
            role=UserRole.USER,
            is_active=True
        )
        
        self.mock_auth_service.verify_access_token.return_value = mock_user
        
        user = await self.middleware.authenticate_request(token)
        
        assert user.id == "user123"
        self.mock_auth_service.verify_access_token.assert_called_once_with("valid_token_here")
    
    async def test_authenticate_request_without_token(self):
        """测试无令牌的请求认证"""
        with pytest.raises(AuthenticationError, match="缺少认证令牌"):
            await self.middleware.authenticate_request(None)
    
    async def test_authenticate_request_invalid_format(self):
        """测试无效格式的令牌"""
        invalid_tokens = [
            "invalid_format",
            "Basic username:password",
            "Bearer",
            ""
        ]
        
        for token in invalid_tokens:
            with pytest.raises(AuthenticationError, match="无效的令牌格式"):
                await self.middleware.authenticate_request(token)
    
    async def test_check_permission_admin(self):
        """测试管理员权限检查"""
        admin_user = User(
            id="admin123",
            username="admin",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        # 管理员应该有所有权限
        assert self.middleware.check_permission(admin_user, "read") is True
        assert self.middleware.check_permission(admin_user, "write") is True
        assert self.middleware.check_permission(admin_user, "delete") is True
        assert self.middleware.check_permission(admin_user, "admin") is True
    
    async def test_check_permission_moderator(self):
        """测试版主权限检查"""
        moderator_user = User(
            id="mod123",
            username="moderator",
            role=UserRole.MODERATOR,
            is_active=True
        )
        
        # 版主应该有读写权限，但没有管理员权限
        assert self.middleware.check_permission(moderator_user, "read") is True
        assert self.middleware.check_permission(moderator_user, "write") is True
        assert self.middleware.check_permission(moderator_user, "moderate") is True
        assert self.middleware.check_permission(moderator_user, "admin") is False
    
    async def test_check_permission_user(self):
        """测试普通用户权限检查"""
        regular_user = User(
            id="user123",
            username="user",
            role=UserRole.USER,
            is_active=True
        )
        
        # 普通用户只有基本权限
        assert self.middleware.check_permission(regular_user, "read") is True
        assert self.middleware.check_permission(regular_user, "write") is True
        assert self.middleware.check_permission(regular_user, "moderate") is False
        assert self.middleware.check_permission(regular_user, "admin") is False
    
    async def test_check_permission_inactive_user(self):
        """测试未激活用户权限检查"""
        inactive_user = User(
            id="user123",
            username="user",
            role=UserRole.USER,
            is_active=False
        )
        
        # 未激活用户没有任何权限
        assert self.middleware.check_permission(inactive_user, "read") is False
        assert self.middleware.check_permission(inactive_user, "write") is False