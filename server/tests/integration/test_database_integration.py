"""
数据库模块集成测试
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from uplifted.database.database_manager import DatabaseManager
from uplifted.database.managers import UserManager, PostManager, CommentManager
from uplifted.database.models import User, Post, Comment
from uplifted.cache.cache_manager import MemoryCacheManager


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """数据库模块集成测试"""
    
    async def test_complete_user_lifecycle(self, db_manager):
        """测试完整的用户生命周期"""
        user_manager = UserManager(db_manager)
        
        # 创建用户
        user_data = {
            "username": "lifecycle_user",
            "email": "lifecycle@test.com",
            "password_hash": "hashed_password",
            "profile": {
                "first_name": "Lifecycle",
                "last_name": "User",
                "bio": "Test user for lifecycle testing"
            }
        }
        
        user = await user_manager.create_user(**user_data)
        
        # 验证用户创建
        assert user.id is not None
        assert user.username == user_data["username"]
        assert user.email == user_data["email"]
        assert user.profile["first_name"] == "Lifecycle"
        assert user.created_at is not None
        assert user.is_active is True
        
        # 获取用户
        retrieved_user = await user_manager.get_user(user.id)
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username
        
        # 通过用户名获取
        user_by_username = await user_manager.get_user_by_username(user.username)
        assert user_by_username.id == user.id
        
        # 通过邮箱获取
        user_by_email = await user_manager.get_user_by_email(user.email)
        assert user_by_email.id == user.id
        
        # 更新用户
        update_data = {
            "profile": {
                "first_name": "Updated",
                "last_name": "User",
                "bio": "Updated bio"
            },
            "is_active": False
        }
        
        updated_user = await user_manager.update_user(user.id, **update_data)
        assert updated_user.profile["first_name"] == "Updated"
        assert updated_user.is_active is False
        assert updated_user.updated_at > user.created_at
        
        # 删除用户
        success = await user_manager.delete_user(user.id)
        assert success is True
        
        # 验证用户已删除
        deleted_user = await user_manager.get_user(user.id)
        assert deleted_user is None
    
    async def test_complete_post_lifecycle(self, db_manager):
        """测试完整的帖子生命周期"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        
        # 先创建用户
        user = await user_manager.create_user(
            username="post_author",
            email="author@test.com",
            password_hash="hashed_password"
        )
        
        # 创建帖子
        post_data = {
            "title": "Integration Test Post",
            "content": "This is a test post for integration testing",
            "author_id": user.id,
            "tags": ["test", "integration", "database"],
            "metadata": {
                "category": "testing",
                "priority": "high"
            }
        }
        
        post = await post_manager.create_post(**post_data)
        
        # 验证帖子创建
        assert post.id is not None
        assert post.title == post_data["title"]
        assert post.content == post_data["content"]
        assert post.author_id == user.id
        assert post.tags == post_data["tags"]
        assert post.metadata["category"] == "testing"
        assert post.created_at is not None
        assert post.is_published is True
        
        # 获取帖子
        retrieved_post = await post_manager.get_post(post.id)
        assert retrieved_post.id == post.id
        assert retrieved_post.title == post.title
        
        # 按作者获取帖子
        author_posts = await post_manager.get_posts_by_author(user.id)
        assert len(author_posts) == 1
        assert author_posts[0].id == post.id
        
        # 搜索帖子
        search_results = await post_manager.search_posts("integration")
        assert len(search_results) >= 1
        assert any(p.id == post.id for p in search_results)
        
        # 更新帖子
        update_data = {
            "title": "Updated Integration Test Post",
            "content": "Updated content for testing",
            "tags": ["test", "integration", "updated"],
            "is_published": False
        }
        
        updated_post = await post_manager.update_post(post.id, **update_data)
        assert updated_post.title == "Updated Integration Test Post"
        assert updated_post.is_published is False
        assert updated_post.updated_at > post.created_at
        
        # 删除帖子
        success = await post_manager.delete_post(post.id)
        assert success is True
        
        # 验证帖子已删除
        deleted_post = await post_manager.get_post(post.id)
        assert deleted_post is None
    
    async def test_complete_comment_lifecycle(self, db_manager):
        """测试完整的评论生命周期"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        comment_manager = CommentManager(db_manager)
        
        # 创建用户和帖子
        user = await user_manager.create_user(
            username="comment_author",
            email="commenter@test.com",
            password_hash="hashed_password"
        )
        
        post = await post_manager.create_post(
            title="Post for Comments",
            content="This post will have comments",
            author_id=user.id
        )
        
        # 创建评论
        comment_data = {
            "content": "This is a test comment",
            "author_id": user.id,
            "post_id": post.id,
            "metadata": {
                "sentiment": "positive",
                "language": "en"
            }
        }
        
        comment = await comment_manager.create_comment(**comment_data)
        
        # 验证评论创建
        assert comment.id is not None
        assert comment.content == comment_data["content"]
        assert comment.author_id == user.id
        assert comment.post_id == post.id
        assert comment.metadata["sentiment"] == "positive"
        assert comment.created_at is not None
        
        # 获取评论
        retrieved_comment = await comment_manager.get_comment(comment.id)
        assert retrieved_comment.id == comment.id
        assert retrieved_comment.content == comment.content
        
        # 按帖子获取评论
        post_comments = await comment_manager.get_comments_by_post(post.id)
        assert len(post_comments) == 1
        assert post_comments[0].id == comment.id
        
        # 创建回复评论
        reply_data = {
            "content": "This is a reply to the comment",
            "author_id": user.id,
            "post_id": post.id,
            "parent_id": comment.id
        }
        
        reply = await comment_manager.create_comment(**reply_data)
        assert reply.parent_id == comment.id
        
        # 获取帖子的所有评论（包括回复）
        all_comments = await comment_manager.get_comments_by_post(post.id)
        assert len(all_comments) == 2
        
        # 删除评论
        success = await comment_manager.delete_comment(comment.id)
        assert success is True
        
        # 验证评论已删除
        deleted_comment = await comment_manager.get_comment(comment.id)
        assert deleted_comment is None
    
    async def test_user_post_comment_relationships(self, db_manager):
        """测试用户、帖子、评论之间的关系"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        comment_manager = CommentManager(db_manager)
        
        # 创建多个用户
        author = await user_manager.create_user(
            username="post_author",
            email="author@test.com",
            password_hash="hashed_password"
        )
        
        commenter1 = await user_manager.create_user(
            username="commenter1",
            email="commenter1@test.com",
            password_hash="hashed_password"
        )
        
        commenter2 = await user_manager.create_user(
            username="commenter2",
            email="commenter2@test.com",
            password_hash="hashed_password"
        )
        
        # 创建帖子
        post = await post_manager.create_post(
            title="Post with Multiple Comments",
            content="This post will have comments from different users",
            author_id=author.id
        )
        
        # 创建多个评论
        comment1 = await comment_manager.create_comment(
            content="First comment",
            author_id=commenter1.id,
            post_id=post.id
        )
        
        comment2 = await comment_manager.create_comment(
            content="Second comment",
            author_id=commenter2.id,
            post_id=post.id
        )
        
        comment3 = await comment_manager.create_comment(
            content="Reply to first comment",
            author_id=commenter2.id,
            post_id=post.id,
            parent_id=comment1.id
        )
        
        # 验证关系
        post_comments = await comment_manager.get_comments_by_post(post.id)
        assert len(post_comments) == 3
        
        # 验证作者的帖子
        author_posts = await post_manager.get_posts_by_author(author.id)
        assert len(author_posts) == 1
        assert author_posts[0].id == post.id
        
        # 验证评论者没有帖子
        commenter1_posts = await post_manager.get_posts_by_author(commenter1.id)
        assert len(commenter1_posts) == 0
        
        # 验证回复关系
        reply_comment = next(c for c in post_comments if c.parent_id == comment1.id)
        assert reply_comment.id == comment3.id
        assert reply_comment.author_id == commenter2.id
    
    async def test_database_transactions(self, db_manager):
        """测试数据库事务"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        
        # 测试成功事务
        async with db_manager.transaction():
            user = await user_manager.create_user(
                username="transaction_user",
                email="transaction@test.com",
                password_hash="hashed_password"
            )
            
            post = await post_manager.create_post(
                title="Transaction Test Post",
                content="This post is created in a transaction",
                author_id=user.id
            )
            
            # 在事务内验证数据存在
            retrieved_user = await user_manager.get_user(user.id)
            retrieved_post = await post_manager.get_post(post.id)
            assert retrieved_user is not None
            assert retrieved_post is not None
        
        # 事务提交后验证数据仍然存在
        final_user = await user_manager.get_user(user.id)
        final_post = await post_manager.get_post(post.id)
        assert final_user is not None
        assert final_post is not None
        
        # 测试失败事务（回滚）
        try:
            async with db_manager.transaction():
                user2 = await user_manager.create_user(
                    username="rollback_user",
                    email="rollback@test.com",
                    password_hash="hashed_password"
                )
                
                # 故意引发异常
                raise Exception("Intentional rollback")
        except Exception:
            pass
        
        # 验证回滚后数据不存在
        rollback_user = await user_manager.get_user_by_username("rollback_user")
        assert rollback_user is None
    
    async def test_database_with_cache_integration(self, db_manager):
        """测试数据库与缓存集成"""
        cache_manager = MemoryCacheManager(max_size=100)
        user_manager = UserManager(db_manager)
        
        # 创建用户
        user = await user_manager.create_user(
            username="cached_user",
            email="cached@test.com",
            password_hash="hashed_password"
        )
        
        # 模拟缓存用户数据
        cache_key = f"user:{user.id}"
        user_data = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
        
        await cache_manager.set(cache_key, user_data, ttl=3600)
        
        # 从缓存获取数据
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is not None
        assert cached_data["username"] == user.username
        assert cached_data["email"] == user.email
        
        # 更新用户（应该清除缓存）
        await user_manager.update_user(user.id, profile={"first_name": "Updated"})
        
        # 模拟缓存失效
        await cache_manager.delete(cache_key)
        
        # 验证缓存已清除
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is None
    
    async def test_database_performance_with_bulk_operations(self, db_manager):
        """测试数据库批量操作性能"""
        user_manager = UserManager(db_manager)
        post_manager = PostManager(db_manager)
        
        # 创建测试用户
        author = await user_manager.create_user(
            username="bulk_author",
            email="bulk@test.com",
            password_hash="hashed_password"
        )
        
        # 批量创建帖子
        posts = []
        for i in range(10):
            post = await post_manager.create_post(
                title=f"Bulk Post {i}",
                content=f"Content for bulk post {i}",
                author_id=author.id,
                tags=[f"tag{i}", "bulk", "test"]
            )
            posts.append(post)
        
        # 验证所有帖子都被创建
        author_posts = await post_manager.get_posts_by_author(author.id)
        assert len(author_posts) == 10
        
        # 批量搜索
        search_results = await post_manager.search_posts("bulk")
        assert len(search_results) >= 10
        
        # 批量删除
        for post in posts:
            await post_manager.delete_post(post.id)
        
        # 验证所有帖子都被删除
        final_posts = await post_manager.get_posts_by_author(author.id)
        assert len(final_posts) == 0
    
    async def test_database_error_handling(self, db_manager):
        """测试数据库错误处理"""
        user_manager = UserManager(db_manager)
        
        # 测试重复用户名
        await user_manager.create_user(
            username="duplicate_user",
            email="first@test.com",
            password_hash="hashed_password"
        )
        
        # 尝试创建相同用户名的用户
        with pytest.raises(Exception):  # 应该抛出完整性约束异常
            await user_manager.create_user(
                username="duplicate_user",
                email="second@test.com",
                password_hash="hashed_password"
            )
        
        # 测试重复邮箱
        with pytest.raises(Exception):  # 应该抛出完整性约束异常
            await user_manager.create_user(
                username="different_user",
                email="first@test.com",
                password_hash="hashed_password"
            )
        
        # 测试获取不存在的用户
        nonexistent_user = await user_manager.get_user(99999)
        assert nonexistent_user is None
        
        # 测试更新不存在的用户
        updated_user = await user_manager.update_user(99999, profile={"name": "test"})
        assert updated_user is None
        
        # 测试删除不存在的用户
        success = await user_manager.delete_user(99999)
        assert success is False