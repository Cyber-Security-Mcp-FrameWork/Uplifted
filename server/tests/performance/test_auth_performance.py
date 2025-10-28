"""
认证模块性能测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock

from uplifted.auth.auth_service import AuthService
from uplifted.auth.password_service import PasswordService
from uplifted.auth.token_service import TokenService
from uplifted.database.managers import UserManager
from uplifted.cache.cache_manager import MemoryCacheManager
from tests.performance import PerformanceBenchmark, PERFORMANCE_CONFIG, PERFORMANCE_TEST_DATA


@pytest.mark.performance
@pytest.mark.asyncio
class TestAuthPerformance:
    """认证模块性能测试"""
    
    @pytest.fixture
    async def auth_services(self, test_config, db_manager):
        """创建认证服务"""
        user_manager = UserManager(db_manager)
        cache_manager = MemoryCacheManager(max_size=1000)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        return {
            "auth_service": auth_service,
            "password_service": password_service,
            "token_service": token_service,
            "user_manager": user_manager
        }
    
    async def test_password_hashing_performance(self, auth_services):
        """测试密码哈希性能"""
        password_service = auth_services["password_service"]
        benchmark = PerformanceBenchmark()
        
        # 测试密码哈希
        async def hash_password():
            password_service.hash_password("TestPassword123!")
        
        result = await benchmark.run_benchmark(
            "password_hashing",
            hash_password,
            iterations=50  # 密码哈希比较慢，减少迭代次数
        )
        
        # 验证性能要求
        assert result.success_rate == 1.0
        assert result.avg_time < 0.5  # 平均每次哈希应该在500ms内
        print(f"Password hashing: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_password_verification_performance(self, auth_services):
        """测试密码验证性能"""
        password_service = auth_services["password_service"]
        benchmark = PerformanceBenchmark()
        
        # 预先哈希一个密码
        password = "TestPassword123!"
        password_hash = password_service.hash_password(password)
        
        # 测试密码验证
        async def verify_password():
            password_service.verify_password(password, password_hash)
        
        result = await benchmark.run_benchmark(
            "password_verification",
            verify_password,
            iterations=100
        )
        
        # 验证性能要求
        assert result.success_rate == 1.0
        assert result.avg_time < 0.3  # 平均每次验证应该在300ms内
        print(f"Password verification: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_token_creation_performance(self, auth_services):
        """测试令牌创建性能"""
        token_service = auth_services["token_service"]
        benchmark = PerformanceBenchmark()
        
        # 测试令牌创建
        async def create_token():
            payload = {"user_id": "123", "username": "testuser"}
            token_service.create_token(payload)
        
        result = await benchmark.run_benchmark(
            "token_creation",
            create_token,
            iterations=1000
        )
        
        # 验证性能要求
        assert result.success_rate == 1.0
        assert result.avg_time < 0.01  # 平均每次创建应该在10ms内
        print(f"Token creation: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_token_verification_performance(self, auth_services):
        """测试令牌验证性能"""
        token_service = auth_services["token_service"]
        benchmark = PerformanceBenchmark()
        
        # 预先创建一个令牌
        payload = {"user_id": "123", "username": "testuser"}
        token = token_service.create_token(payload)
        
        # 测试令牌验证
        async def verify_token():
            token_service.verify_token(token)
        
        result = await benchmark.run_benchmark(
            "token_verification",
            verify_token,
            iterations=1000
        )
        
        # 验证性能要求
        assert result.success_rate == 1.0
        assert result.avg_time < 0.005  # 平均每次验证应该在5ms内
        print(f"Token verification: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_user_creation_performance(self, auth_services):
        """测试用户创建性能"""
        auth_service = auth_services["auth_service"]
        benchmark = PerformanceBenchmark()
        
        user_data = PERFORMANCE_TEST_DATA["users"]
        current_index = 0
        
        # 测试用户创建
        async def create_user():
            nonlocal current_index
            if current_index >= len(user_data):
                current_index = 0
            
            data = user_data[current_index]
            current_index += 1
            
            # 添加随机后缀避免重复
            import random
            suffix = random.randint(1000, 9999)
            
            await auth_service.create_user(
                username=f"{data['username']}_{suffix}",
                email=f"perf_{suffix}_{data['email']}",
                password=data["password"]
            )
        
        result = await benchmark.run_benchmark(
            "user_creation",
            create_user,
            iterations=50  # 数据库操作较慢，减少迭代次数
        )
        
        # 验证性能要求
        assert result.success_rate >= 0.9  # 允许10%的失败率（可能由于并发冲突）
        assert result.avg_time < 1.0  # 平均每次创建应该在1秒内
        print(f"User creation: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_user_authentication_performance(self, auth_services):
        """测试用户认证性能"""
        auth_service = auth_services["auth_service"]
        benchmark = PerformanceBenchmark()
        
        # 预先创建一个用户
        test_user = await auth_service.create_user(
            username="perf_auth_user",
            email="perf_auth@test.com",
            password="PerfAuthPass123!"
        )
        
        # 测试用户认证
        async def authenticate_user():
            await auth_service.authenticate_user(
                username="perf_auth_user",
                password="PerfAuthPass123!"
            )
        
        result = await benchmark.run_benchmark(
            "user_authentication",
            authenticate_user,
            iterations=100
        )
        
        # 验证性能要求
        assert result.success_rate == 1.0
        assert result.avg_time < 0.5  # 平均每次认证应该在500ms内
        print(f"User authentication: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_concurrent_authentication_performance(self, auth_services):
        """测试并发认证性能"""
        auth_service = auth_services["auth_service"]
        
        # 预先创建多个用户
        users = []
        for i in range(10):
            user = await auth_service.create_user(
                username=f"concurrent_user_{i}",
                email=f"concurrent{i}@test.com",
                password=f"ConcurrentPass{i}!"
            )
            users.append((f"concurrent_user_{i}", f"ConcurrentPass{i}!"))
        
        # 并发认证测试
        async def concurrent_auth_test():
            tasks = []
            for username, password in users:
                task = auth_service.authenticate_user(username, password)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计成功率
            successful = sum(1 for r in results if not isinstance(r, Exception))
            return successful / len(results)
        
        # 运行多次并发测试
        start_time = time.perf_counter()
        success_rates = []
        
        for _ in range(10):
            success_rate = await concurrent_auth_test()
            success_rates.append(success_rate)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_success_rate = sum(success_rates) / len(success_rates)
        
        # 验证并发性能
        assert avg_success_rate >= 0.9  # 平均成功率应该至少90%
        assert total_time < 30.0  # 总时间应该在30秒内
        print(f"Concurrent authentication: {total_time:.2f}s total, {avg_success_rate:.2%} avg success")
    
    async def test_token_refresh_performance(self, auth_services):
        """测试令牌刷新性能"""
        auth_service = auth_services["auth_service"]
        benchmark = PerformanceBenchmark()
        
        # 预先创建用户并获取令牌
        user = await auth_service.create_user(
            username="refresh_user",
            email="refresh@test.com",
            password="RefreshPass123!"
        )
        
        auth_result = await auth_service.authenticate_user(
            username="refresh_user",
            password="RefreshPass123!"
        )
        refresh_token = auth_result["refresh_token"]
        
        # 测试令牌刷新
        async def refresh_token_test():
            await auth_service.refresh_token(refresh_token)
        
        result = await benchmark.run_benchmark(
            "token_refresh",
            refresh_token_test,
            iterations=50  # 刷新令牌涉及缓存操作，适度减少迭代次数
        )
        
        # 验证性能要求
        assert result.success_rate >= 0.8  # 允许20%的失败率（令牌可能过期）
        assert result.avg_time < 0.1  # 平均每次刷新应该在100ms内
        print(f"Token refresh: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_logout_performance(self, auth_services):
        """测试登出性能"""
        auth_service = auth_services["auth_service"]
        benchmark = PerformanceBenchmark()
        
        # 预先创建用户
        user = await auth_service.create_user(
            username="logout_user",
            email="logout@test.com",
            password="LogoutPass123!"
        )
        
        # 测试登出
        async def logout_test():
            # 先认证获取令牌
            auth_result = await auth_service.authenticate_user(
                username="logout_user",
                password="LogoutPass123!"
            )
            
            # 然后登出
            await auth_service.logout_user(user.id, auth_result["access_token"])
        
        result = await benchmark.run_benchmark(
            "user_logout",
            logout_test,
            iterations=50
        )
        
        # 验证性能要求
        assert result.success_rate >= 0.9
        assert result.avg_time < 0.8  # 平均每次登出应该在800ms内（包含认证时间）
        print(f"User logout: {result.avg_time:.4f}s avg, {result.success_rate:.2%} success")
    
    async def test_auth_system_stress_test(self, auth_services):
        """认证系统压力测试"""
        auth_service = auth_services["auth_service"]
        
        # 创建大量用户进行压力测试
        stress_users = []
        creation_start = time.perf_counter()
        
        # 批量创建用户
        for i in range(20):
            try:
                user = await auth_service.create_user(
                    username=f"stress_user_{i}",
                    email=f"stress{i}@test.com",
                    password=f"StressPass{i}!"
                )
                stress_users.append((f"stress_user_{i}", f"StressPass{i}!"))
            except Exception as e:
                print(f"Failed to create user {i}: {e}")
        
        creation_time = time.perf_counter() - creation_start
        
        # 并发认证压力测试
        auth_start = time.perf_counter()
        
        async def stress_auth_batch():
            tasks = []
            for username, password in stress_users:
                task = auth_service.authenticate_user(username, password)
                tasks.append(task)
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # 运行多轮压力测试
        total_operations = 0
        total_successful = 0
        
        for round_num in range(5):
            results = await stress_auth_batch()
            total_operations += len(results)
            total_successful += sum(1 for r in results if not isinstance(r, Exception))
        
        auth_time = time.perf_counter() - auth_start
        
        # 验证压力测试结果
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        
        assert success_rate >= 0.8  # 压力测试下至少80%成功率
        assert creation_time < 20.0  # 创建20个用户应该在20秒内
        assert auth_time < 15.0  # 5轮认证应该在15秒内
        
        print(f"Stress test: {len(stress_users)} users created in {creation_time:.2f}s")
        print(f"Stress test: {total_operations} auth operations in {auth_time:.2f}s, {success_rate:.2%} success")