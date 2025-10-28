"""
数据库模块性能测试
"""

import pytest
import asyncio
import time
from typing import List

from uplifted.database.managers import UserManager, PostManager, CommentManager
from uplifted.database.models import User, Post, Comment
from tests.performance import PerformanceBenchmark, PERFORMANCE_CONFIG, PERFORMANCE_TEST_DATA


@pytest.mark.performance
@pytest.mark.asyncio
class TestDatabasePerformance:
    """数据库模块性能测试"""
    
    @pytest.fixture
    async def db_managers(self, db_manager):
        """创建数据库管理器"""
        return {
            "user_manager": UserManager(db_manager),
            "post_manager": PostManager(db_manager),
            "comment_manager": CommentManager(db_manager)
        }
    
    async def test_user_crud_performance(self, db_managers):
        """测试用户CRUD操作性能"""
        user_manager = db_managers["user_manager"]
        benchmark = PerformanceBenchmark()
        
        # 测试用户创建性能
        created_users = []
        
        async def create_user():
            import random
            suffix = random.randint(10000, 99999)
            user = await user_manager.create_user(
                username=f"perf_user_{suffix}",
                email=f"perf{suffix}@test.com",
                password_hash="hashed_password"
            )
            created_users.append(user)
            return user
        
        create_result = await benchmark.run_benchmark(
            "user_creation",
            create_user,
            iterations=100
        )
        
        assert create_result.success_rate >= 0.9
        assert create_result.avg_time < 0.1  # 平均创建时间应该在100ms内
        print(f"User creation: {create_result.avg_time:.4f}s avg, {create_result.success_rate:.2%} success")
        
        # 测试用户查询性能
        if created_users:
            test_user = created_users[0]
            
            async def get_user():
                await user_manager.get_user(test_user.id)
            
            get_result = await benchmark.run_benchmark(
                "user_retrieval",
                get_user,
                iterations=500
            )
            
            assert get_result.success_rate == 1.0
            assert get_result.avg_time < 0.05  # 平均查询时间应该在50ms内
            print(f"User retrieval: {get_result.avg_time:.4f}s avg, {get_result.success_rate:.2%} success")
            
            # 测试用户更新性能
            async def update_user():
                await user_manager.update_user(
                    test_user.id,
                    profile={"updated": True, "timestamp": time.time()}
                )
            
            update_result = await benchmark.run_benchmark(
                "user_update",
                update_user,
                iterations=100
            )
            
            assert update_result.success_rate >= 0.9
            assert update_result.avg_time < 0.1  # 平均更新时间应该在100ms内
            print(f"User update: {update_result.avg_time:.4f}s avg, {update_result.success_rate:.2%} success")
    
    async def test_post_crud_performance(self, db_managers):
        """测试帖子CRUD操作性能"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        benchmark = PerformanceBenchmark()
        
        # 创建测试用户
        test_user = await user_manager.create_user(
            username="post_perf_user",
            email="postperf@test.com",
            password_hash="hashed_password"
        )
        
        # 测试帖子创建性能
        created_posts = []
        post_data = PERFORMANCE_TEST_DATA["posts"]
        current_index = 0
        
        async def create_post():
            nonlocal current_index
            if current_index >= len(post_data):
                current_index = 0
            
            data = post_data[current_index]
            current_index += 1
            
            post = await post_manager.create_post(
                title=data["title"],
                content=data["content"],
                author_id=test_user.id,
                tags=data["tags"]
            )
            created_posts.append(post)
            return post
        
        create_result = await benchmark.run_benchmark(
            "post_creation",
            create_post,
            iterations=200
        )
        
        assert create_result.success_rate >= 0.9
        assert create_result.avg_time < 0.15  # 平均创建时间应该在150ms内
        print(f"Post creation: {create_result.avg_time:.4f}s avg, {create_result.success_rate:.2%} success")
        
        # 测试帖子查询性能
        if created_posts:
            test_post = created_posts[0]
            
            async def get_post():
                await post_manager.get_post(test_post.id)
            
            get_result = await benchmark.run_benchmark(
                "post_retrieval",
                get_post,
                iterations=500
            )
            
            assert get_result.success_rate == 1.0
            assert get_result.avg_time < 0.05  # 平均查询时间应该在50ms内
            print(f"Post retrieval: {get_result.avg_time:.4f}s avg, {get_result.success_rate:.2%} success")
            
            # 测试按作者查询帖子性能
            async def get_posts_by_author():
                await post_manager.get_posts_by_author(test_user.id)
            
            author_result = await benchmark.run_benchmark(
                "posts_by_author",
                get_posts_by_author,
                iterations=200
            )
            
            assert author_result.success_rate == 1.0
            assert author_result.avg_time < 0.1  # 平均查询时间应该在100ms内
            print(f"Posts by author: {author_result.avg_time:.4f}s avg, {author_result.success_rate:.2%} success")
    
    async def test_comment_crud_performance(self, db_managers):
        """测试评论CRUD操作性能"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        comment_manager = db_managers["comment_manager"]
        benchmark = PerformanceBenchmark()
        
        # 创建测试数据
        test_user = await user_manager.create_user(
            username="comment_perf_user",
            email="commentperf@test.com",
            password_hash="hashed_password"
        )
        
        test_post = await post_manager.create_post(
            title="Comment Performance Test Post",
            content="This post is for testing comment performance",
            author_id=test_user.id
        )
        
        # 测试评论创建性能
        created_comments = []
        comment_data = PERFORMANCE_TEST_DATA["comments"]
        current_index = 0
        
        async def create_comment():
            nonlocal current_index
            if current_index >= len(comment_data):
                current_index = 0
            
            data = comment_data[current_index]
            current_index += 1
            
            comment = await comment_manager.create_comment(
                content=data["content"],
                author_id=test_user.id,
                post_id=test_post.id
            )
            created_comments.append(comment)
            return comment
        
        create_result = await benchmark.run_benchmark(
            "comment_creation",
            create_comment,
            iterations=300
        )
        
        assert create_result.success_rate >= 0.9
        assert create_result.avg_time < 0.1  # 平均创建时间应该在100ms内
        print(f"Comment creation: {create_result.avg_time:.4f}s avg, {create_result.success_rate:.2%} success")
        
        # 测试按帖子查询评论性能
        async def get_comments_by_post():
            await comment_manager.get_comments_by_post(test_post.id)
        
        get_result = await benchmark.run_benchmark(
            "comments_by_post",
            get_comments_by_post,
            iterations=200
        )
        
        assert get_result.success_rate == 1.0
        assert get_result.avg_time < 0.1  # 平均查询时间应该在100ms内
        print(f"Comments by post: {get_result.avg_time:.4f}s avg, {get_result.success_rate:.2%} success")
    
    async def test_search_performance(self, db_managers):
        """测试搜索性能"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        benchmark = PerformanceBenchmark()
        
        # 创建测试数据
        test_user = await user_manager.create_user(
            username="search_perf_user",
            email="searchperf@test.com",
            password_hash="hashed_password"
        )
        
        # 创建多个帖子用于搜索
        search_posts = []
        for i in range(50):
            post = await post_manager.create_post(
                title=f"Search Test Post {i}",
                content=f"This is search test content {i} with keywords performance testing",
                author_id=test_user.id,
                tags=["search", "test", f"tag{i}"]
            )
            search_posts.append(post)
        
        # 测试帖子搜索性能
        search_terms = ["search", "test", "performance", "content", "keywords"]
        current_term_index = 0
        
        async def search_posts():
            nonlocal current_term_index
            term = search_terms[current_term_index % len(search_terms)]
            current_term_index += 1
            
            await post_manager.search_posts(term)
        
        search_result = await benchmark.run_benchmark(
            "post_search",
            search_posts,
            iterations=100
        )
        
        assert search_result.success_rate == 1.0
        assert search_result.avg_time < 0.2  # 平均搜索时间应该在200ms内
        print(f"Post search: {search_result.avg_time:.4f}s avg, {search_result.success_rate:.2%} success")
        
        # 测试用户搜索性能
        async def search_users():
            await user_manager.search_users("search")
        
        user_search_result = await benchmark.run_benchmark(
            "user_search",
            search_users,
            iterations=100
        )
        
        assert user_search_result.success_rate == 1.0
        assert user_search_result.avg_time < 0.15  # 平均搜索时间应该在150ms内
        print(f"User search: {user_search_result.avg_time:.4f}s avg, {user_search_result.success_rate:.2%} success")
    
    async def test_batch_operations_performance(self, db_managers):
        """测试批量操作性能"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        
        # 创建测试用户
        test_user = await user_manager.create_user(
            username="batch_perf_user",
            email="batchperf@test.com",
            password_hash="hashed_password"
        )
        
        # 测试批量创建帖子性能
        start_time = time.perf_counter()
        
        batch_posts = []
        for i in range(100):
            post = await post_manager.create_post(
                title=f"Batch Post {i}",
                content=f"Batch content {i}",
                author_id=test_user.id,
                tags=[f"batch{i}", "performance"]
            )
            batch_posts.append(post)
        
        batch_create_time = time.perf_counter() - start_time
        
        # 测试批量查询性能
        start_time = time.perf_counter()
        
        retrieved_posts = []
        for post in batch_posts:
            retrieved_post = await post_manager.get_post(post.id)
            retrieved_posts.append(retrieved_post)
        
        batch_retrieve_time = time.perf_counter() - start_time
        
        # 测试批量删除性能
        start_time = time.perf_counter()
        
        for post in batch_posts:
            await post_manager.delete_post(post.id)
        
        batch_delete_time = time.perf_counter() - start_time
        
        # 验证批量操作性能
        assert len(batch_posts) == 100
        assert len(retrieved_posts) == 100
        assert batch_create_time < 30.0  # 批量创建应该在30秒内
        assert batch_retrieve_time < 10.0  # 批量查询应该在10秒内
        assert batch_delete_time < 15.0  # 批量删除应该在15秒内
        
        print(f"Batch create 100 posts: {batch_create_time:.2f}s")
        print(f"Batch retrieve 100 posts: {batch_retrieve_time:.2f}s")
        print(f"Batch delete 100 posts: {batch_delete_time:.2f}s")
    
    async def test_concurrent_database_operations(self, db_managers):
        """测试并发数据库操作性能"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        
        # 创建测试用户
        test_users = []
        for i in range(5):
            user = await user_manager.create_user(
                username=f"concurrent_user_{i}",
                email=f"concurrent{i}@test.com",
                password_hash="hashed_password"
            )
            test_users.append(user)
        
        # 并发创建帖子
        async def create_posts_concurrently():
            tasks = []
            for i, user in enumerate(test_users):
                for j in range(10):
                    task = post_manager.create_post(
                        title=f"Concurrent Post {i}-{j}",
                        content=f"Concurrent content {i}-{j}",
                        author_id=user.id,
                        tags=[f"concurrent{i}", f"post{j}"]
                    )
                    tasks.append(task)
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        start_time = time.perf_counter()
        results = await create_posts_concurrently()
        concurrent_time = time.perf_counter() - start_time
        
        # 统计成功率
        successful_posts = [r for r in results if isinstance(r, Post)]
        success_rate = len(successful_posts) / len(results)
        
        # 验证并发性能
        assert success_rate >= 0.8  # 至少80%成功率
        assert concurrent_time < 20.0  # 并发创建应该在20秒内完成
        assert len(successful_posts) >= 40  # 至少创建40个帖子
        
        print(f"Concurrent operations: {len(results)} tasks in {concurrent_time:.2f}s, {success_rate:.2%} success")
        
        # 并发查询测试
        async def query_posts_concurrently():
            tasks = []
            for post in successful_posts[:20]:  # 只测试前20个
                task = post_manager.get_post(post.id)
                tasks.append(task)
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        start_time = time.perf_counter()
        query_results = await query_posts_concurrently()
        query_time = time.perf_counter() - start_time
        
        query_success_rate = sum(1 for r in query_results if isinstance(r, Post)) / len(query_results)
        
        assert query_success_rate >= 0.95  # 查询成功率应该更高
        assert query_time < 5.0  # 并发查询应该在5秒内完成
        
        print(f"Concurrent queries: {len(query_results)} queries in {query_time:.2f}s, {query_success_rate:.2%} success")
    
    async def test_database_stress_test(self, db_managers):
        """数据库压力测试"""
        user_manager = db_managers["user_manager"]
        post_manager = db_managers["post_manager"]
        comment_manager = db_managers["comment_manager"]
        
        # 创建压力测试用户
        stress_user = await user_manager.create_user(
            username="stress_test_user",
            email="stress@test.com",
            password_hash="hashed_password"
        )
        
        # 压力测试：快速创建大量内容
        start_time = time.perf_counter()
        
        # 创建帖子
        stress_posts = []
        for i in range(50):
            try:
                post = await post_manager.create_post(
                    title=f"Stress Post {i}",
                    content=f"Stress test content {i}",
                    author_id=stress_user.id,
                    tags=[f"stress{i}", "test"]
                )
                stress_posts.append(post)
            except Exception as e:
                print(f"Failed to create post {i}: {e}")
        
        # 为每个帖子创建评论
        stress_comments = []
        for i, post in enumerate(stress_posts):
            for j in range(5):  # 每个帖子5个评论
                try:
                    comment = await comment_manager.create_comment(
                        content=f"Stress comment {i}-{j}",
                        author_id=stress_user.id,
                        post_id=post.id
                    )
                    stress_comments.append(comment)
                except Exception as e:
                    print(f"Failed to create comment {i}-{j}: {e}")
        
        creation_time = time.perf_counter() - start_time
        
        # 压力测试：大量查询操作
        start_time = time.perf_counter()
        
        query_count = 0
        for _ in range(100):
            try:
                # 随机查询用户
                await user_manager.get_user(stress_user.id)
                query_count += 1
                
                # 随机查询帖子
                if stress_posts:
                    import random
                    post = random.choice(stress_posts)
                    await post_manager.get_post(post.id)
                    query_count += 1
                
                # 查询用户的帖子
                await post_manager.get_posts_by_author(stress_user.id)
                query_count += 1
                
            except Exception as e:
                print(f"Query failed: {e}")
        
        query_time = time.perf_counter() - start_time
        
        # 验证压力测试结果
        assert len(stress_posts) >= 40  # 至少创建40个帖子
        assert len(stress_comments) >= 150  # 至少创建150个评论
        assert creation_time < 60.0  # 创建操作应该在60秒内完成
        assert query_time < 30.0  # 查询操作应该在30秒内完成
        
        print(f"Stress test creation: {len(stress_posts)} posts, {len(stress_comments)} comments in {creation_time:.2f}s")
        print(f"Stress test queries: {query_count} queries in {query_time:.2f}s")