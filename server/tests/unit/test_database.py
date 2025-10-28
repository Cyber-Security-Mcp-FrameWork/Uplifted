"""
数据库模块单元测试
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from uplifted.database.models import User, Post, Comment, UserRole
from uplifted.database.managers import DatabaseManager, UserManager, PostManager, CommentManager
from uplifted.database.exceptions import (
    DatabaseError,
    ConnectionError,
    ValidationError,
    NotFoundError,
    DuplicateError
)


@pytest.mark.asyncio
class TestDatabaseManager:
    """数据库管理器测试"""
    
    def setup_method(self):
        self.config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'pool_size': 10,
            'max_overflow': 20
        }
        self.db_manager = DatabaseManager(self.config)
    
    async def test_initialize_success(self):
        """测试成功初始化数据库连接"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            await self.db_manager.initialize()
            
            assert self.db_manager.engine is mock_engine
            mock_create_engine.assert_called_once()
    
    async def test_initialize_connection_error(self):
        """测试数据库连接失败"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_create_engine.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError, match="数据库连接失败"):
                await self.db_manager.initialize()
    
    async def test_close_connection(self):
        """测试关闭数据库连接"""
        # 先初始化
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            # 测试关闭
            await self.db_manager.close()
            
            mock_engine.dispose.assert_called_once()
            assert self.db_manager.engine is None
    
    async def test_get_session(self):
        """测试获取数据库会话"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            with patch('uplifted.database.managers.AsyncSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                async with self.db_manager.get_session() as session:
                    assert session is mock_session
    
    async def test_execute_query_success(self):
        """测试成功执行查询"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_session.execute.return_value = mock_result
            
            with patch.object(self.db_manager, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                query = "SELECT * FROM users"
                result = await self.db_manager.execute_query(query)
                
                assert result is mock_result
                mock_session.execute.assert_called_once()
    
    async def test_execute_query_error(self):
        """测试查询执行失败"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Query failed")
            
            with patch.object(self.db_manager, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                query = "SELECT * FROM users"
                
                with pytest.raises(DatabaseError, match="查询执行失败"):
                    await self.db_manager.execute_query(query)
    
    async def test_health_check_healthy(self):
        """测试健康检查 - 健康状态"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            
            with patch.object(self.db_manager, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                is_healthy = await self.db_manager.health_check()
                
                assert is_healthy is True
    
    async def test_health_check_unhealthy(self):
        """测试健康检查 - 不健康状态"""
        with patch('uplifted.database.managers.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            await self.db_manager.initialize()
            
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("Database error")
            
            with patch.object(self.db_manager, 'get_session') as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                is_healthy = await self.db_manager.health_check()
                
                assert is_healthy is False


@pytest.mark.asyncio
class TestUserManager:
    """用户管理器测试"""
    
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.user_manager = UserManager(self.mock_db)
    
    async def test_create_user_success(self):
        """测试成功创建用户"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed_password',
            'full_name': 'Test User'
        }
        
        mock_user = User(
            id='user123',
            username=user_data['username'],
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            full_name=user_data['full_name'],
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            created_at=datetime.now()
        )
        
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        with patch('uplifted.database.managers.User', return_value=mock_user):
            user = await self.user_manager.create_user(**user_data)
            
            assert user.username == user_data['username']
            assert user.email == user_data['email']
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    async def test_create_user_validation_error(self):
        """测试创建用户时验证错误"""
        invalid_user_data = {
            'username': '',  # 空用户名
            'email': 'invalid_email',  # 无效邮箱
            'password_hash': 'hash',
            'full_name': 'Test User'
        }
        
        with pytest.raises(ValidationError):
            await self.user_manager.create_user(**invalid_user_data)
    
    async def test_get_user_by_id_found(self):
        """测试根据ID获取用户 - 找到用户"""
        user_id = 'user123'
        mock_user = User(
            id=user_id,
            username='testuser',
            email='test@example.com',
            role=UserRole.USER
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_user
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        user = await self.user_manager.get_user_by_id(user_id)
        
        assert user.id == user_id
        mock_session.get.assert_called_once_with(User, user_id)
    
    async def test_get_user_by_id_not_found(self):
        """测试根据ID获取用户 - 未找到用户"""
        user_id = 'nonexistent'
        
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        user = await self.user_manager.get_user_by_id(user_id)
        
        assert user is None
    
    async def test_get_user_by_username_found(self):
        """测试根据用户名获取用户 - 找到用户"""
        username = 'testuser'
        mock_user = User(
            id='user123',
            username=username,
            email='test@example.com',
            role=UserRole.USER
        )
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        user = await self.user_manager.get_user_by_username(username)
        
        assert user.username == username
        mock_session.execute.assert_called_once()
    
    async def test_get_user_by_email_found(self):
        """测试根据邮箱获取用户 - 找到用户"""
        email = 'test@example.com'
        mock_user = User(
            id='user123',
            username='testuser',
            email=email,
            role=UserRole.USER
        )
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        user = await self.user_manager.get_user_by_email(email)
        
        assert user.email == email
        mock_session.execute.assert_called_once()
    
    async def test_update_user_success(self):
        """测试成功更新用户"""
        user_id = 'user123'
        update_data = {
            'full_name': 'Updated Name',
            'bio': 'Updated bio'
        }
        
        mock_user = User(
            id=user_id,
            username='testuser',
            email='test@example.com',
            full_name='Old Name',
            bio='Old bio',
            role=UserRole.USER
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_user
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        updated_user = await self.user_manager.update_user(user_id, **update_data)
        
        assert updated_user.full_name == update_data['full_name']
        assert updated_user.bio == update_data['bio']
        mock_session.commit.assert_called_once()
    
    async def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        user_id = 'nonexistent'
        update_data = {'full_name': 'Updated Name'}
        
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        with pytest.raises(NotFoundError, match="用户不存在"):
            await self.user_manager.update_user(user_id, **update_data)
    
    async def test_delete_user_success(self):
        """测试成功删除用户"""
        user_id = 'user123'
        
        mock_user = User(
            id=user_id,
            username='testuser',
            email='test@example.com',
            role=UserRole.USER
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_user
        mock_session.delete = Mock()
        mock_session.commit = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        result = await self.user_manager.delete_user(user_id)
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
    
    async def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        user_id = 'nonexistent'
        
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        with pytest.raises(NotFoundError, match="用户不存在"):
            await self.user_manager.delete_user(user_id)
    
    async def test_list_users_with_pagination(self):
        """测试分页获取用户列表"""
        mock_users = [
            User(id='user1', username='user1', email='user1@example.com', role=UserRole.USER),
            User(id='user2', username='user2', email='user2@example.com', role=UserRole.USER),
        ]
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        users = await self.user_manager.list_users(page=1, page_size=10)
        
        assert len(users) == 2
        assert users[0].username == 'user1'
        assert users[1].username == 'user2'
        mock_session.execute.assert_called_once()
    
    async def test_search_users(self):
        """测试搜索用户"""
        search_term = 'test'
        mock_users = [
            User(id='user1', username='testuser1', email='test1@example.com', role=UserRole.USER),
            User(id='user2', username='testuser2', email='test2@example.com', role=UserRole.USER),
        ]
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        users = await self.user_manager.search_users(search_term)
        
        assert len(users) == 2
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
class TestPostManager:
    """帖子管理器测试"""
    
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.post_manager = PostManager(self.mock_db)
    
    async def test_create_post_success(self):
        """测试成功创建帖子"""
        post_data = {
            'title': 'Test Post',
            'content': 'This is a test post content',
            'author_id': 'user123',
            'category': 'general'
        }
        
        mock_post = Post(
            id='post123',
            title=post_data['title'],
            content=post_data['content'],
            author_id=post_data['author_id'],
            category=post_data['category'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        with patch('uplifted.database.managers.Post', return_value=mock_post):
            post = await self.post_manager.create_post(**post_data)
            
            assert post.title == post_data['title']
            assert post.content == post_data['content']
            assert post.author_id == post_data['author_id']
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    async def test_create_post_validation_error(self):
        """测试创建帖子时验证错误"""
        invalid_post_data = {
            'title': '',  # 空标题
            'content': 'Content',
            'author_id': 'user123'
        }
        
        with pytest.raises(ValidationError):
            await self.post_manager.create_post(**invalid_post_data)
    
    async def test_get_post_by_id_found(self):
        """测试根据ID获取帖子 - 找到帖子"""
        post_id = 'post123'
        mock_post = Post(
            id=post_id,
            title='Test Post',
            content='Test content',
            author_id='user123'
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_post
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        post = await self.post_manager.get_post_by_id(post_id)
        
        assert post.id == post_id
        mock_session.get.assert_called_once_with(Post, post_id)
    
    async def test_get_post_by_id_not_found(self):
        """测试根据ID获取帖子 - 未找到帖子"""
        post_id = 'nonexistent'
        
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        post = await self.post_manager.get_post_by_id(post_id)
        
        assert post is None
    
    async def test_update_post_success(self):
        """测试成功更新帖子"""
        post_id = 'post123'
        update_data = {
            'title': 'Updated Title',
            'content': 'Updated content'
        }
        
        mock_post = Post(
            id=post_id,
            title='Old Title',
            content='Old content',
            author_id='user123'
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_post
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        updated_post = await self.post_manager.update_post(post_id, **update_data)
        
        assert updated_post.title == update_data['title']
        assert updated_post.content == update_data['content']
        mock_session.commit.assert_called_once()
    
    async def test_delete_post_success(self):
        """测试成功删除帖子"""
        post_id = 'post123'
        
        mock_post = Post(
            id=post_id,
            title='Test Post',
            content='Test content',
            author_id='user123'
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_post
        mock_session.delete = Mock()
        mock_session.commit = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        result = await self.post_manager.delete_post(post_id)
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_post)
        mock_session.commit.assert_called_once()
    
    async def test_list_posts_by_author(self):
        """测试根据作者获取帖子列表"""
        author_id = 'user123'
        mock_posts = [
            Post(id='post1', title='Post 1', content='Content 1', author_id=author_id),
            Post(id='post2', title='Post 2', content='Content 2', author_id=author_id),
        ]
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_posts
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        posts = await self.post_manager.list_posts_by_author(author_id)
        
        assert len(posts) == 2
        assert all(post.author_id == author_id for post in posts)
        mock_session.execute.assert_called_once()
    
    async def test_search_posts(self):
        """测试搜索帖子"""
        search_term = 'test'
        mock_posts = [
            Post(id='post1', title='Test Post 1', content='Content 1', author_id='user123'),
            Post(id='post2', title='Another Test', content='Content 2', author_id='user123'),
        ]
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_posts
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        posts = await self.post_manager.search_posts(search_term)
        
        assert len(posts) == 2
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
class TestCommentManager:
    """评论管理器测试"""
    
    def setup_method(self):
        self.mock_db = AsyncMock()
        self.comment_manager = CommentManager(self.mock_db)
    
    async def test_create_comment_success(self):
        """测试成功创建评论"""
        comment_data = {
            'content': 'This is a test comment',
            'author_id': 'user123',
            'post_id': 'post123'
        }
        
        mock_comment = Comment(
            id='comment123',
            content=comment_data['content'],
            author_id=comment_data['author_id'],
            post_id=comment_data['post_id'],
            created_at=datetime.now()
        )
        
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        with patch('uplifted.database.managers.Comment', return_value=mock_comment):
            comment = await self.comment_manager.create_comment(**comment_data)
            
            assert comment.content == comment_data['content']
            assert comment.author_id == comment_data['author_id']
            assert comment.post_id == comment_data['post_id']
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    async def test_get_comment_by_id_found(self):
        """测试根据ID获取评论 - 找到评论"""
        comment_id = 'comment123'
        mock_comment = Comment(
            id=comment_id,
            content='Test comment',
            author_id='user123',
            post_id='post123'
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_comment
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        comment = await self.comment_manager.get_comment_by_id(comment_id)
        
        assert comment.id == comment_id
        mock_session.get.assert_called_once_with(Comment, comment_id)
    
    async def test_list_comments_by_post(self):
        """测试根据帖子获取评论列表"""
        post_id = 'post123'
        mock_comments = [
            Comment(id='comment1', content='Comment 1', author_id='user1', post_id=post_id),
            Comment(id='comment2', content='Comment 2', author_id='user2', post_id=post_id),
        ]
        
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_comments
        mock_session.execute.return_value = mock_result
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        comments = await self.comment_manager.list_comments_by_post(post_id)
        
        assert len(comments) == 2
        assert all(comment.post_id == post_id for comment in comments)
        mock_session.execute.assert_called_once()
    
    async def test_delete_comment_success(self):
        """测试成功删除评论"""
        comment_id = 'comment123'
        
        mock_comment = Comment(
            id=comment_id,
            content='Test comment',
            author_id='user123',
            post_id='post123'
        )
        
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_comment
        mock_session.delete = Mock()
        mock_session.commit = AsyncMock()
        
        self.mock_db.get_session.return_value.__aenter__.return_value = mock_session
        
        result = await self.comment_manager.delete_comment(comment_id)
        
        assert result is True
        mock_session.delete.assert_called_once_with(mock_comment)
        mock_session.commit.assert_called_once()


class TestDatabaseModels:
    """数据库模型测试"""
    
    def test_user_model_creation(self):
        """测试用户模型创建"""
        user = User(
            id='user123',
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password',
            full_name='Test User',
            role=UserRole.USER,
            is_active=True,
            is_verified=False
        )
        
        assert user.id == 'user123'
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
    
    def test_user_model_validation(self):
        """测试用户模型验证"""
        # 测试邮箱验证
        user = User(
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password'
        )
        
        assert user.validate_email() is True
        
        # 测试无效邮箱
        user.email = 'invalid_email'
        assert user.validate_email() is False
    
    def test_post_model_creation(self):
        """测试帖子模型创建"""
        post = Post(
            id='post123',
            title='Test Post',
            content='This is a test post',
            author_id='user123',
            category='general'
        )
        
        assert post.id == 'post123'
        assert post.title == 'Test Post'
        assert post.content == 'This is a test post'
        assert post.author_id == 'user123'
        assert post.category == 'general'
    
    def test_comment_model_creation(self):
        """测试评论模型创建"""
        comment = Comment(
            id='comment123',
            content='This is a test comment',
            author_id='user123',
            post_id='post123'
        )
        
        assert comment.id == 'comment123'
        assert comment.content == 'This is a test comment'
        assert comment.author_id == 'user123'
        assert comment.post_id == 'post123'
    
    def test_model_relationships(self):
        """测试模型关系"""
        # 这里可以测试模型之间的关系，如外键约束等
        # 由于我们使用的是模拟对象，这里主要测试关系定义是否正确
        
        user = User(id='user123', username='testuser', email='test@example.com')
        post = Post(id='post123', title='Test', content='Content', author_id='user123')
        comment = Comment(id='comment123', content='Comment', author_id='user123', post_id='post123')
        
        # 验证关系字段
        assert post.author_id == user.id
        assert comment.author_id == user.id
        assert comment.post_id == post.id