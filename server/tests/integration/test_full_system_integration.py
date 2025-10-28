"""
完整系统集成测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from uplifted.auth.auth_service import AuthService
from uplifted.auth.password_service import PasswordService
from uplifted.auth.token_service import TokenService
from uplifted.database.managers import UserManager, PostManager, CommentManager
from uplifted.cache.cache_manager import MemoryCacheManager
from uplifted.monitoring.logger import Logger
from uplifted.monitoring.metrics_collector import MetricsManager, SystemMetricsCollector
from uplifted.monitoring.alerting import AlertManager
from uplifted.monitoring.health_check import HealthChecker
from uplifted.utils.validators import validate_email, validate_password


@pytest.mark.asyncio
class TestFullSystemIntegration:
    """完整系统集成测试"""
    
    async def test_complete_user_journey(self, test_config, db_manager, cache_manager):
        """测试完整的用户旅程"""
        # 初始化所有服务
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        comment_manager = CommentManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        logger = Logger("system_integration")
        
        # 1. 用户注册
        user_data = {
            "username": "journey_user",
            "email": "journey@test.com",
            "password": "JourneyPass123!",
            "profile": {
                "first_name": "Journey",
                "last_name": "User",
                "bio": "Testing complete user journey"
            }
        }
        
        # 验证输入数据
        assert validate_email(user_data["email"]) is True
        assert validate_password(user_data["password"]) is True
        
        # 创建用户
        user = await auth_service.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            profile=user_data["profile"]
        )
        
        assert user.id is not None
        assert user.username == user_data["username"]
        
        # 2. 用户登录
        auth_result = await auth_service.authenticate_user(
            username=user_data["username"],
            password=user_data["password"]
        )
        
        assert auth_result is not None
        access_token = auth_result["access_token"]
        refresh_token = auth_result["refresh_token"]
        
        # 验证令牌
        token_payload = token_service.verify_token(access_token)
        assert token_payload["user_id"] == str(user.id)
        
        # 3. 用户创建帖子
        post_data = {
            "title": "My First Post",
            "content": "This is my first post in the system!",
            "author_id": user.id,
            "tags": ["first", "introduction", "test"]
        }
        
        post = await post_manager.create_post(**post_data)
        assert post.id is not None
        assert post.author_id == user.id
        
        # 4. 用户创建评论
        comment_data = {
            "content": "This is a comment on my own post",
            "author_id": user.id,
            "post_id": post.id
        }
        
        comment = await comment_manager.create_comment(**comment_data)
        assert comment.id is not None
        assert comment.post_id == post.id
        
        # 5. 用户更新个人资料
        updated_profile = {
            "first_name": "Updated",
            "last_name": "User",
            "bio": "Updated bio after creating content"
        }
        
        updated_user = await user_manager.update_user(user.id, profile=updated_profile)
        assert updated_user.profile["first_name"] == "Updated"
        
        # 6. 用户搜索内容
        search_results = await post_manager.search_posts("first")
        assert len(search_results) >= 1
        assert any(p.id == post.id for p in search_results)
        
        # 7. 用户刷新令牌
        new_tokens = await auth_service.refresh_token(refresh_token)
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != access_token
        
        # 8. 用户登出
        await auth_service.logout_user(user.id, new_tokens["access_token"])
        
        # 验证令牌被加入黑名单
        is_blacklisted = await cache_manager.get(f"blacklist:{new_tokens['access_token']}")
        assert is_blacklisted is not None
    
    async def test_multi_user_interaction(self, test_config, db_manager, cache_manager):
        """测试多用户交互"""
        # 初始化服务
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        comment_manager = CommentManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建多个用户
        users = []
        for i in range(3):
            user_data = {
                "username": f"user_{i}",
                "email": f"user{i}@test.com",
                "password": f"UserPass{i}23!"
            }
            
            user = await auth_service.create_user(**user_data)
            users.append(user)
        
        # 第一个用户创建帖子
        post = await post_manager.create_post(
            title="Multi-user Discussion Post",
            content="Let's discuss this topic together!",
            author_id=users[0].id,
            tags=["discussion", "community"]
        )
        
        # 其他用户添加评论
        comments = []
        for i in range(1, 3):
            comment = await comment_manager.create_comment(
                content=f"Great post! This is comment from user {i}",
                author_id=users[i].id,
                post_id=post.id
            )
            comments.append(comment)
        
        # 第一个用户回复评论
        reply = await comment_manager.create_comment(
            content="Thanks for your feedback!",
            author_id=users[0].id,
            post_id=post.id,
            parent_id=comments[0].id
        )
        
        # 验证交互结果
        post_comments = await comment_manager.get_comments_by_post(post.id)
        assert len(post_comments) == 3  # 2个评论 + 1个回复
        
        # 验证回复关系
        reply_comment = next(c for c in post_comments if c.parent_id == comments[0].id)
        assert reply_comment.author_id == users[0].id
        
        # 验证每个用户的内容
        user0_posts = await post_manager.get_posts_by_author(users[0].id)
        assert len(user0_posts) == 1
        
        user1_posts = await post_manager.get_posts_by_author(users[1].id)
        assert len(user1_posts) == 0  # 只有评论，没有帖子
    
    async def test_system_with_monitoring(self, test_config, db_manager, cache_manager):
        """测试带监控的系统运行"""
        # 初始化监控组件
        logger = Logger("system_monitoring")
        metrics_manager = MetricsManager()
        alert_manager = AlertManager()
        health_checker = HealthChecker()
        
        # 添加系统指标收集器
        system_collector = SystemMetricsCollector()
        metrics_manager.register_collector("system", system_collector)
        
        # 添加健康检查
        from uplifted.monitoring.health_check import CPUHealthCheck, MemoryHealthCheck
        health_checker.add_check("cpu", CPUHealthCheck(threshold=90.0))
        health_checker.add_check("memory", MemoryHealthCheck(threshold=90.0))
        
        # 初始化业务服务
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 模拟系统负载
        with patch('psutil.cpu_percent', return_value=45.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                
                # 执行业务操作
                user = await auth_service.create_user(
                    username="monitored_user",
                    email="monitored@test.com",
                    password="MonitoredPass123!"
                )
                
                # 收集指标
                metrics = await metrics_manager.collect_all()
                assert "cpu_usage" in metrics
                assert metrics["cpu_usage"].value == 45.0
                
                # 运行健康检查
                health_report = await health_checker.run_all_checks()
                assert health_report.overall_status.value in ["healthy", "degraded"]
                
                # 验证业务操作成功
                assert user.id is not None
    
    async def test_system_error_recovery(self, test_config, db_manager, cache_manager):
        """测试系统错误恢复"""
        user_manager = UserManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建用户
        user = await auth_service.create_user(
            username="recovery_user",
            email="recovery@test.com",
            password="RecoveryPass123!"
        )
        
        # 模拟数据库连接错误
        with patch.object(db_manager, 'execute_query', side_effect=Exception("Database error")):
            # 尝试获取用户（应该失败）
            with pytest.raises(Exception):
                await user_manager.get_user(user.id)
        
        # 数据库恢复后，操作应该正常
        retrieved_user = await user_manager.get_user(user.id)
        assert retrieved_user.id == user.id
        
        # 模拟缓存错误
        with patch.object(cache_manager, 'get', side_effect=Exception("Cache error")):
            # 认证应该仍然工作（降级到数据库）
            auth_result = await auth_service.authenticate_user(
                username="recovery_user",
                password="RecoveryPass123!"
            )
            assert auth_result is not None
    
    async def test_concurrent_system_operations(self, test_config, db_manager, cache_manager):
        """测试并发系统操作"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 并发创建用户
        async def create_user(index):
            return await auth_service.create_user(
                username=f"concurrent_user_{index}",
                email=f"concurrent{index}@test.com",
                password=f"ConcurrentPass{index}!"
            )
        
        # 同时创建多个用户
        user_tasks = [create_user(i) for i in range(5)]
        users = await asyncio.gather(*user_tasks)
        
        # 验证所有用户都被创建
        assert len(users) == 5
        for user in users:
            assert user.id is not None
        
        # 并发创建帖子
        async def create_post(user, index):
            return await post_manager.create_post(
                title=f"Concurrent Post {index}",
                content=f"Content for concurrent post {index}",
                author_id=user.id
            )
        
        # 每个用户创建一个帖子
        post_tasks = [create_post(users[i], i) for i in range(5)]
        posts = await asyncio.gather(*post_tasks)
        
        # 验证所有帖子都被创建
        assert len(posts) == 5
        for i, post in enumerate(posts):
            assert post.author_id == users[i].id
        
        # 并发认证
        async def authenticate_user(user, index):
            return await auth_service.authenticate_user(
                username=f"concurrent_user_{index}",
                password=f"ConcurrentPass{index}!"
            )
        
        auth_tasks = [authenticate_user(users[i], i) for i in range(5)]
        auth_results = await asyncio.gather(*auth_tasks)
        
        # 验证所有认证都成功
        for result in auth_results:
            assert result is not None
            assert "access_token" in result
    
    async def test_system_performance_under_load(self, test_config, db_manager, cache_manager):
        """测试系统负载性能"""
        import time
        
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        password_service = PasswordService()
        token_service = TokenService(test_config["auth"]["secret_key"])
        auth_service = AuthService(user_manager, password_service, token_service, cache_manager)
        
        # 创建测试用户
        user = await auth_service.create_user(
            username="performance_user",
            email="performance@test.com",
            password="PerformancePass123!"
        )
        
        # 测试批量帖子创建性能
        start_time = time.time()
        
        posts = []
        for i in range(20):
            post = await post_manager.create_post(
                title=f"Performance Test Post {i}",
                content=f"Content for performance test post {i}",
                author_id=user.id,
                tags=[f"perf{i}", "test", "performance"]
            )
            posts.append(post)
        
        creation_time = time.time() - start_time
        
        # 验证创建性能（应该在合理时间内完成）
        assert creation_time < 10.0  # 20个帖子应该在10秒内创建完成
        assert len(posts) == 20
        
        # 测试搜索性能
        start_time = time.time()
        
        search_results = await post_manager.search_posts("performance")
        
        search_time = time.time() - start_time
        
        # 验证搜索性能和结果
        assert search_time < 1.0  # 搜索应该在1秒内完成
        assert len(search_results) >= 20
        
        # 测试批量删除性能
        start_time = time.time()
        
        for post in posts:
            await post_manager.delete_post(post.id)
        
        deletion_time = time.time() - start_time
        
        # 验证删除性能
        assert deletion_time < 5.0  # 删除应该在5秒内完成
        
        # 验证所有帖子都被删除
        remaining_posts = await post_manager.get_posts_by_author(user.id)
        assert len(remaining_posts) == 0
    
    async def test_system_data_consistency(self, test_config, db_manager, cache_manager):
        """测试系统数据一致性"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        comment_manager = CommentManager(db_manager)
        
        # 创建用户
        user = await user_manager.create_user(
            username="consistency_user",
            email="consistency@test.com",
            password_hash="hashed_password"
        )
        
        # 创建帖子
        post = await post_manager.create_post(
            title="Consistency Test Post",
            content="Testing data consistency",
            author_id=user.id
        )
        
        # 创建评论
        comment = await comment_manager.create_comment(
            content="Test comment",
            author_id=user.id,
            post_id=post.id
        )
        
        # 验证数据一致性
        # 1. 用户应该能通过不同方式获取
        user_by_id = await user_manager.get_user(user.id)
        user_by_username = await user_manager.get_user_by_username(user.username)
        user_by_email = await user_manager.get_user_by_email(user.email)
        
        assert user_by_id.id == user_by_username.id == user_by_email.id
        
        # 2. 帖子应该与作者关联
        author_posts = await post_manager.get_posts_by_author(user.id)
        assert len(author_posts) == 1
        assert author_posts[0].id == post.id
        
        # 3. 评论应该与帖子关联
        post_comments = await comment_manager.get_comments_by_post(post.id)
        assert len(post_comments) == 1
        assert post_comments[0].id == comment.id
        
        # 4. 删除用户应该处理关联数据
        # 注意：在实际实现中，可能需要级联删除或软删除
        await user_manager.delete_user(user.id)
        
        # 验证用户被删除
        deleted_user = await user_manager.get_user(user.id)
        assert deleted_user is None
        
        # 根据业务逻辑，帖子和评论可能被删除或保留
        # 这里假设它们被保留但标记为孤儿数据
        orphaned_post = await post_manager.get_post(post.id)
        # 具体行为取决于实现策略