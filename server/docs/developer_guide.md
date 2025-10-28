# Uplifted 开发者指南

欢迎来到 Uplifted 开发者指南！本文档将帮助您了解项目架构、开发流程、扩展方法和贡献指南。

## 目录

1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [开发环境搭建](#开发环境搭建)
4. [代码结构](#代码结构)
5. [核心模块](#核心模块)
6. [数据库设计](#数据库设计)
7. [API设计原则](#api设计原则)
8. [测试策略](#测试策略)
9. [性能优化](#性能优化)
10. [扩展开发](#扩展开发)
11. [部署指南](#部署指南)
12. [贡献指南](#贡献指南)
13. [最佳实践](#最佳实践)

## 项目概述

### 技术栈

- **后端框架**: Flask + SQLAlchemy
- **数据库**: PostgreSQL (主数据库) + Redis (缓存)
- **认证**: JWT (JSON Web Tokens)
- **任务队列**: Celery + Redis
- **监控**: Prometheus + Grafana
- **日志**: Structured Logging with JSON
- **测试**: pytest + coverage
- **代码质量**: black, isort, flake8, mypy, bandit

### 设计原则

1. **模块化设计**: 清晰的模块边界和职责分离
2. **可扩展性**: 支持水平扩展和功能扩展
3. **高性能**: 优化的数据库查询和缓存策略
4. **安全性**: 全面的安全措施和数据保护
5. **可维护性**: 清晰的代码结构和完善的文档
6. **可测试性**: 高测试覆盖率和自动化测试

## 架构设计

### 整体架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Mobile Client  │    │  Third-party    │
│                 │    │                 │    │     Apps        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Load Balancer        │
                    │       (Nginx)             │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      API Gateway          │
                    │    (Flask Application)    │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────┴─────────┐   ┌─────────┴─────────┐   ┌─────────┴─────────┐
│   Auth Service    │   │  Content Service  │   │  Social Service   │
│                   │   │                   │   │                   │
└─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │     Data Layer            │
                    │                           │
                    │  ┌─────────┐ ┌─────────┐  │
                    │  │PostgreSQL│ │  Redis  │  │
                    │  │         │ │ (Cache) │  │
                    │  └─────────┘ └─────────┘  │
                    └───────────────────────────┘
```

### 服务架构

#### 1. 认证服务 (Auth Service)
- 用户注册和登录
- JWT 令牌管理
- 密码重置和验证
- 权限控制

#### 2. 内容服务 (Content Service)
- 帖子管理 (CRUD)
- 媒体文件处理
- 内容审核
- 搜索功能

#### 3. 社交服务 (Social Service)
- 用户关系管理
- 互动功能 (点赞、评论、分享)
- 通知系统
- 推荐算法

#### 4. 监控服务 (Monitoring Service)
- 性能监控
- 错误追踪
- 日志聚合
- 健康检查

## 开发环境搭建

### 1. 环境要求

```bash
# Python 版本
python --version  # 3.9+

# 数据库版本
psql --version    # PostgreSQL 12+
redis-server --version  # Redis 6.0+
```

### 2. 项目克隆和设置

```bash
# 克隆项目
git clone https://github.com/your-org/uplifted.git
cd uplifted/server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. 开发工具配置

#### Pre-commit Hooks

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 hooks
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

#### IDE 配置 (VS Code)

创建 `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### 4. 数据库设置

```bash
# 创建开发数据库
createdb uplifted_dev

# 运行迁移
flask db upgrade

# 加载测试数据
python scripts/seed_data.py
```

### 5. 启动开发服务器

```bash
# 启动 Redis
redis-server

# 启动 Flask 应用
flask run --debug

# 启动 Celery worker (另一个终端)
celery -A uplifted.celery worker --loglevel=info
```

## 代码结构

```
server/
├── uplifted/                   # 主应用包
│   ├── __init__.py            # 应用工厂
│   ├── common/                # 通用模块
│   │   ├── __init__.py
│   │   ├── database.py        # 数据库管理
│   │   ├── cache.py           # 缓存管理
│   │   ├── utils.py           # 工具函数
│   │   └── exceptions.py      # 自定义异常
│   ├── core/                  # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── auth/              # 认证模块
│   │   ├── users/             # 用户管理
│   │   ├── posts/             # 帖子管理
│   │   ├── comments/          # 评论管理
│   │   └── social/            # 社交功能
│   ├── security/              # 安全模块
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证装饰器
│   │   ├── validation.py      # 输入验证
│   │   └── encryption.py      # 加密工具
│   ├── monitoring/            # 监控模块
│   │   ├── __init__.py
│   │   ├── logging.py         # 日志配置
│   │   ├── metrics.py         # 指标收集
│   │   └── health.py          # 健康检查
│   ├── server/                # 服务器配置
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── routes.py          # 路由定义
│   │   └── middleware.py      # 中间件
│   └── tools/                 # 工具和脚本
├── tests/                     # 测试代码
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   ├── performance/           # 性能测试
│   └── conftest.py           # 测试配置
├── docs/                      # 文档
├── scripts/                   # 脚本文件
├── migrations/                # 数据库迁移
├── requirements.txt           # 生产依赖
├── requirements-dev.txt       # 开发依赖
├── pytest.ini               # 测试配置
├── .env.example              # 环境变量示例
└── run_main_server.py        # 应用入口
```

## 核心模块

### 1. 数据库模块 (common/database.py)

```python
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

Base = declarative_base()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行原生SQL查询"""
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            return [dict(row) for row in result]
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
```

### 2. 缓存模块 (common/cache.py)

```python
import json
import redis
from typing import Any, Optional, Union
from abc import ABC, abstractmethod

class CacheManager(ABC):
    """缓存管理器抽象基类"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        pass

class RedisCacheManager(CacheManager):
    """Redis缓存管理器"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None):
        self.redis_client = redis.Redis(
            host=host, port=port, db=db, password=password,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except (json.JSONDecodeError, redis.RedisError):
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            serialized_value = json.dumps(value)
            return self.redis_client.set(key, serialized_value, ex=timeout)
        except (json.JSONEncodeError, redis.RedisError):
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError:
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        try:
            return self.redis_client.flushdb()
        except redis.RedisError:
            return False
```

### 3. 认证模块 (core/auth/)

```python
# core/auth/models.py
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from uplifted.common.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    bio = Column(String(500))
    avatar_url = Column(String(500))
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# core/auth/service.py
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta

class AuthService:
    """认证服务"""
    
    def __init__(self, db_manager, cache_manager, secret_key: str):
        self.db = db_manager
        self.cache = cache_manager
        self.secret_key = secret_key
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """用户注册"""
        # 检查用户名和邮箱是否已存在
        with self.db.get_session() as session:
            existing_user = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                raise ValueError("用户名或邮箱已存在")
            
            # 创建新用户
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                display_name=username
            )
            session.add(user)
            session.flush()
            
            return {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'display_name': user.display_name
            }
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        with self.db.get_session() as session:
            user = session.query(User).filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and check_password_hash(user.password_hash, password):
                return {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'display_name': user.display_name
                }
            return None
    
    def generate_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """生成访问令牌和刷新令牌"""
        now = datetime.utcnow()
        
        # 访问令牌 (1小时)
        access_payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'exp': now + timedelta(hours=1),
            'iat': now,
            'type': 'access'
        }
        access_token = jwt.encode(access_payload, self.secret_key, algorithm='HS256')
        
        # 刷新令牌 (30天)
        refresh_payload = {
            'user_id': user_data['id'],
            'exp': now + timedelta(days=30),
            'iat': now,
            'type': 'refresh'
        }
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm='HS256')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
```

### 4. 帖子模块 (core/posts/)

```python
# core/posts/models.py
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from uplifted.common.database import Base

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    media_urls = Column(ARRAY(String))
    tags = Column(ARRAY(String))
    visibility = Column(String(20), default='public')  # public, followers, private
    allow_comments = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    author = relationship("User", backref="posts")

# core/posts/service.py
from typing import List, Dict, Any, Optional
from sqlalchemy import desc, and_, or_

class PostService:
    """帖子服务"""
    
    def __init__(self, db_manager, cache_manager):
        self.db = db_manager
        self.cache = cache_manager
    
    def create_post(self, author_id: str, content: str, **kwargs) -> Dict[str, Any]:
        """创建帖子"""
        with self.db.get_session() as session:
            post = Post(
                author_id=author_id,
                content=content,
                media_urls=kwargs.get('media_urls'),
                tags=kwargs.get('tags'),
                visibility=kwargs.get('visibility', 'public'),
                allow_comments=kwargs.get('allow_comments', True)
            )
            session.add(post)
            session.flush()
            
            # 清除相关缓存
            self.cache.delete(f"user_posts:{author_id}")
            
            return self._post_to_dict(post)
    
    def get_posts(self, page: int = 1, limit: int = 20, **filters) -> Dict[str, Any]:
        """获取帖子列表"""
        cache_key = f"posts:{page}:{limit}:{hash(str(sorted(filters.items())))}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        with self.db.get_session() as session:
            query = session.query(Post)
            
            # 应用过滤器
            if filters.get('author_id'):
                query = query.filter(Post.author_id == filters['author_id'])
            if filters.get('tag'):
                query = query.filter(Post.tags.contains([filters['tag']]))
            if filters.get('visibility'):
                query = query.filter(Post.visibility == filters['visibility'])
            
            # 排序
            sort_field = filters.get('sort', 'created_at')
            order = filters.get('order', 'desc')
            if hasattr(Post, sort_field):
                sort_column = getattr(Post, sort_field)
                if order == 'desc':
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
            
            # 分页
            offset = (page - 1) * limit
            posts = query.offset(offset).limit(limit).all()
            total = query.count()
            
            result = {
                'posts': [self._post_to_dict(post) for post in posts],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'total_pages': (total + limit - 1) // limit,
                    'has_next': page * limit < total,
                    'has_prev': page > 1
                }
            }
            
            # 缓存结果
            self.cache.set(cache_key, result, timeout=300)
            return result
    
    def _post_to_dict(self, post: Post) -> Dict[str, Any]:
        """将帖子对象转换为字典"""
        return {
            'id': str(post.id),
            'author_id': str(post.author_id),
            'content': post.content,
            'media_urls': post.media_urls or [],
            'tags': post.tags or [],
            'visibility': post.visibility,
            'allow_comments': post.allow_comments,
            'stats': {
                'likes_count': post.likes_count,
                'comments_count': post.comments_count,
                'shares_count': post.shares_count
            },
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat()
        }
```

## 数据库设计

### ER 图

```
Users ||--o{ Posts : creates
Users ||--o{ Comments : writes
Users ||--o{ Likes : gives
Users ||--o{ Follows : follows/followed_by
Posts ||--o{ Comments : has
Posts ||--o{ Likes : receives
Posts ||--o{ Shares : shared
```

### 主要表结构

#### 用户表 (users)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    bio VARCHAR(500),
    avatar_url VARCHAR(500),
    location VARCHAR(100),
    website VARCHAR(255),
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    is_private BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

#### 帖子表 (posts)

```sql
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    media_urls TEXT[],
    tags TEXT[],
    visibility VARCHAR(20) DEFAULT 'public',
    allow_comments BOOLEAN DEFAULT TRUE,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_author_id ON posts(author_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_posts_visibility ON posts(visibility);
CREATE INDEX idx_posts_tags ON posts USING GIN(tags);
```

#### 关注关系表 (follows)

```sql
CREATE TABLE follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(follower_id, following_id)
);

CREATE INDEX idx_follows_follower_id ON follows(follower_id);
CREATE INDEX idx_follows_following_id ON follows(following_id);
```

### 数据库优化

#### 1. 索引策略

```sql
-- 复合索引
CREATE INDEX idx_posts_author_created ON posts(author_id, created_at DESC);
CREATE INDEX idx_posts_visibility_created ON posts(visibility, created_at DESC);

-- 部分索引
CREATE INDEX idx_posts_public ON posts(created_at DESC) WHERE visibility = 'public';

-- 表达式索引
CREATE INDEX idx_users_username_lower ON users(LOWER(username));
```

#### 2. 分区策略

```sql
-- 按时间分区帖子表
CREATE TABLE posts_2024 PARTITION OF posts
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## API设计原则

### 1. RESTful 设计

```
GET    /api/v1/posts           # 获取帖子列表
POST   /api/v1/posts           # 创建帖子
GET    /api/v1/posts/{id}      # 获取特定帖子
PUT    /api/v1/posts/{id}      # 更新帖子
DELETE /api/v1/posts/{id}      # 删除帖子
```

### 2. 统一响应格式

```python
# 成功响应
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "输入数据无效",
        "details": {...}
    }
}
```

### 3. 版本控制

```python
# URL版本控制
/api/v1/posts
/api/v2/posts

# Header版本控制
Accept: application/vnd.uplifted.v1+json
```

### 4. 分页和过滤

```python
# 分页参数
GET /api/v1/posts?page=1&limit=20

# 过滤参数
GET /api/v1/posts?author=john&tag=python&since=2024-01-01

# 排序参数
GET /api/v1/posts?sort=created_at&order=desc
```

## 测试策略

### 1. 测试金字塔

```
    /\
   /  \     E2E Tests (少量)
  /____\
 /      \   Integration Tests (适量)
/__________\ Unit Tests (大量)
```

### 2. 单元测试

```python
# tests/unit/test_auth_service.py
import pytest
from uplifted.core.auth.service import AuthService

class TestAuthService:
    
    @pytest.fixture
    def auth_service(self, db_manager, cache_manager):
        return AuthService(db_manager, cache_manager, "test_secret")
    
    def test_register_user_success(self, auth_service):
        """测试用户注册成功"""
        user_data = auth_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        
        assert user_data['username'] == "testuser"
        assert user_data['email'] == "test@example.com"
        assert 'id' in user_data
    
    def test_register_user_duplicate_username(self, auth_service):
        """测试重复用户名注册失败"""
        auth_service.register_user("testuser", "test1@example.com", "password123")
        
        with pytest.raises(ValueError, match="用户名或邮箱已存在"):
            auth_service.register_user("testuser", "test2@example.com", "password123")
```

### 3. 集成测试

```python
# tests/integration/test_post_api.py
import pytest
from flask import url_for

class TestPostAPI:
    
    def test_create_post_authenticated(self, client, auth_headers):
        """测试认证用户创建帖子"""
        response = client.post(
            url_for('api.create_post'),
            json={
                'content': '这是一个测试帖子',
                'tags': ['测试', 'API']
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['content'] == '这是一个测试帖子'
    
    def test_get_posts_pagination(self, client):
        """测试帖子列表分页"""
        response = client.get(url_for('api.get_posts', page=1, limit=10))
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'pagination' in data['data']
        assert len(data['data']['posts']) <= 10
```

### 4. 性能测试

```python
# tests/performance/test_post_performance.py
import time
import pytest
from concurrent.futures import ThreadPoolExecutor

class TestPostPerformance:
    
    def test_create_post_performance(self, auth_service, post_service):
        """测试创建帖子性能"""
        start_time = time.time()
        
        for i in range(100):
            post_service.create_post(
                author_id="test_user_id",
                content=f"测试帖子 {i}"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 100个帖子应该在5秒内创建完成
        assert duration < 5.0
    
    def test_concurrent_post_creation(self, post_service):
        """测试并发创建帖子"""
        def create_post(i):
            return post_service.create_post(
                author_id="test_user_id",
                content=f"并发测试帖子 {i}"
            )
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_post, i) for i in range(50)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 50
        assert duration < 10.0  # 50个并发请求应该在10秒内完成
```

## 性能优化

### 1. 数据库优化

#### 查询优化

```python
# 避免 N+1 查询
def get_posts_with_authors(self):
    """获取帖子及其作者信息"""
    with self.db.get_session() as session:
        posts = session.query(Post).options(
            joinedload(Post.author)  # 预加载作者信息
        ).all()
        return posts

# 使用批量查询
def get_posts_stats(self, post_ids: List[str]):
    """批量获取帖子统计信息"""
    with self.db.get_session() as session:
        stats = session.query(
            Post.id,
            Post.likes_count,
            Post.comments_count
        ).filter(Post.id.in_(post_ids)).all()
        return {str(stat.id): stat for stat in stats}
```

#### 连接池配置

```python
# 数据库连接池配置
engine = create_engine(
    database_url,
    pool_size=20,          # 连接池大小
    max_overflow=30,       # 最大溢出连接数
    pool_pre_ping=True,    # 连接前检查
    pool_recycle=3600      # 连接回收时间
)
```

### 2. 缓存策略

#### 多级缓存

```python
class MultiLevelCache:
    """多级缓存"""
    
    def __init__(self, memory_cache, redis_cache):
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
    
    def get(self, key: str):
        # 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 再查Redis缓存
        value = self.redis_cache.get(key)
        if value is not None:
            # 回写到内存缓存
            self.memory_cache.set(key, value, timeout=300)
            return value
        
        return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None):
        # 同时写入两级缓存
        self.memory_cache.set(key, value, timeout)
        self.redis_cache.set(key, value, timeout)
```

#### 缓存预热

```python
def warm_up_cache(self):
    """缓存预热"""
    # 预加载热门帖子
    popular_posts = self.get_popular_posts(limit=100)
    for post in popular_posts:
        cache_key = f"post:{post['id']}"
        self.cache.set(cache_key, post, timeout=3600)
    
    # 预加载活跃用户
    active_users = self.get_active_users(limit=50)
    for user in active_users:
        cache_key = f"user:{user['id']}"
        self.cache.set(cache_key, user, timeout=1800)
```

### 3. 异步处理

```python
# 使用Celery进行异步任务处理
from celery import Celery

celery = Celery('uplifted')

@celery.task
def send_notification_email(user_id: str, notification_type: str, data: dict):
    """异步发送通知邮件"""
    user = get_user_by_id(user_id)
    email_template = get_email_template(notification_type)
    send_email(user.email, email_template.render(data))

@celery.task
def process_media_upload(media_id: str):
    """异步处理媒体文件"""
    media = get_media_by_id(media_id)
    
    # 生成缩略图
    thumbnail = generate_thumbnail(media.file_path)
    
    # 压缩图片
    compressed = compress_image(media.file_path)
    
    # 更新媒体记录
    update_media_processing_status(media_id, 'completed')
```

## 扩展开发

### 1. 插件系统

```python
# uplifted/extensions/base.py
from abc import ABC, abstractmethod

class BaseExtension(ABC):
    """扩展基类"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    @abstractmethod
    def init_app(self, app):
        """初始化扩展"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取扩展名称"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """获取扩展版本"""
        pass

# 示例扩展：内容审核
class ContentModerationExtension(BaseExtension):
    """内容审核扩展"""
    
    def init_app(self, app):
        self.app = app
        app.extensions['content_moderation'] = self
    
    def get_name(self) -> str:
        return "Content Moderation"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def moderate_content(self, content: str) -> dict:
        """审核内容"""
        # 实现内容审核逻辑
        return {
            'is_approved': True,
            'confidence': 0.95,
            'flags': []
        }
```

### 2. 钩子系统

```python
# uplifted/hooks.py
from typing import Callable, List, Any
from collections import defaultdict

class HookManager:
    """钩子管理器"""
    
    def __init__(self):
        self._hooks: defaultdict[str, List[Callable]] = defaultdict(list)
    
    def register(self, hook_name: str, callback: Callable):
        """注册钩子"""
        self._hooks[hook_name].append(callback)
    
    def trigger(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        for callback in self._hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # 记录错误但不中断其他钩子
                logger.error(f"Hook {hook_name} callback failed: {e}")
        return results

# 使用示例
hooks = HookManager()

# 注册钩子
@hooks.register('post_created')
def notify_followers(post_data):
    """帖子创建后通知关注者"""
    send_notifications_to_followers(post_data['author_id'], post_data)

@hooks.register('post_created')
def update_user_stats(post_data):
    """帖子创建后更新用户统计"""
    increment_user_post_count(post_data['author_id'])

# 触发钩子
def create_post(self, **kwargs):
    post = Post(**kwargs)
    # ... 保存帖子逻辑
    
    # 触发钩子
    hooks.trigger('post_created', post_data=post.to_dict())
```

### 3. API扩展

```python
# uplifted/api/extensions.py
from flask import Blueprint

def create_extension_blueprint(extension_name: str) -> Blueprint:
    """创建扩展API蓝图"""
    bp = Blueprint(f'{extension_name}_api', __name__, url_prefix=f'/api/v1/extensions/{extension_name}')
    return bp

# 示例：分析扩展
analytics_bp = create_extension_blueprint('analytics')

@analytics_bp.route('/stats/posts')
def get_post_stats():
    """获取帖子统计信息"""
    return {
        'total_posts': get_total_posts(),
        'posts_today': get_posts_today(),
        'trending_tags': get_trending_tags()
    }

@analytics_bp.route('/stats/users')
def get_user_stats():
    """获取用户统计信息"""
    return {
        'total_users': get_total_users(),
        'active_users': get_active_users(),
        'new_users_today': get_new_users_today()
    }
```

## 部署指南

### 1. Docker 部署

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run_main_server:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/uplifted
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=uplifted
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

### 2. Kubernetes 部署

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uplifted-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: uplifted-app
  template:
    metadata:
      labels:
        app: uplifted-app
    spec:
      containers:
      - name: app
        image: uplifted:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: uplifted-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: uplifted-secrets
              key: redis-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 3. 监控和日志

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'uplifted'
    static_configs:
      - targets: ['app:5000']
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

```yaml
# logging/fluentd.conf
<source>
  @type tail
  path /app/logs/*.log
  pos_file /var/log/fluentd/uplifted.log.pos
  tag uplifted.*
  format json
</source>

<match uplifted.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name uplifted
  type_name _doc
</match>
```

## 贡献指南

### 1. 开发流程

1. **Fork 项目**
   ```bash
   git clone https://github.com/your-username/uplifted.git
   cd uplifted
   git remote add upstream https://github.com/original-org/uplifted.git
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **开发和测试**
   ```bash
   # 安装开发依赖
   pip install -r requirements-dev.txt
   
   # 运行测试
   pytest
   
   # 代码格式化
   black .
   isort .
   
   # 代码检查
   flake8
   mypy .
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/new-feature
   ```

5. **创建 Pull Request**

### 2. 代码规范

#### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(auth): add OAuth2 authentication

Add support for OAuth2 authentication with Google and GitHub providers.
This allows users to sign in using their existing accounts.

Closes #123
```

#### 代码风格

```python
# 使用类型提示
def create_user(username: str, email: str) -> Dict[str, Any]:
    """创建新用户
    
    Args:
        username: 用户名
        email: 邮箱地址
    
    Returns:
        用户信息字典
    
    Raises:
        ValueError: 当用户名或邮箱已存在时
    """
    pass

# 使用数据类
from dataclasses import dataclass
from typing import Optional

@dataclass
class UserProfile:
    username: str
    email: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
```

### 3. 测试要求

- 新功能必须包含单元测试
- 测试覆盖率不低于90%
- 集成测试覆盖主要API端点
- 性能测试覆盖关键路径

### 4. 文档要求

- 新功能需要更新API文档
- 重要变更需要更新用户指南
- 代码注释使用中文
- 提交信息使用中文

## 最佳实践

### 1. 安全最佳实践

```python
# 输入验证
from marshmallow import Schema, fields, validate

class CreatePostSchema(Schema):
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    tags = fields.List(fields.Str(), validate=validate.Length(max=10))
    visibility = fields.Str(validate=validate.OneOf(['public', 'followers', 'private']))

# SQL注入防护
def get_posts_by_tag(self, tag: str):
    with self.db.get_session() as session:
        # 使用参数化查询
        posts = session.query(Post).filter(Post.tags.contains([tag])).all()
        return posts

# XSS防护
import bleach

def sanitize_content(content: str) -> str:
    """清理用户输入内容"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'a']
    allowed_attributes = {'a': ['href']}
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes)
```

### 2. 性能最佳实践

```python
# 使用连接池
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30
)

# 批量操作
def bulk_create_posts(self, posts_data: List[Dict]):
    """批量创建帖子"""
    with self.db.get_session() as session:
        posts = [Post(**data) for data in posts_data]
        session.bulk_save_objects(posts)

# 异步处理
import asyncio
import aiohttp

async def send_notifications(user_ids: List[str], message: str):
    """异步发送通知"""
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_notification(session, user_id, message)
            for user_id in user_ids
        ]
        await asyncio.gather(*tasks)
```

### 3. 监控最佳实践

```python
# 指标收集
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_users = Gauge('active_users_total', 'Number of active users')

# 使用装饰器收集指标
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            request_count.labels(method='POST', endpoint='/api/posts').inc()
            return result
        finally:
            duration = time.time() - start_time
            request_duration.observe(duration)
    return wrapper

# 健康检查
@app.route('/health')
def health_check():
    """健康检查端点"""
    checks = {
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'disk_space': check_disk_space()
    }
    
    if all(checks.values()):
        return {'status': 'healthy', 'checks': checks}, 200
    else:
        return {'status': 'unhealthy', 'checks': checks}, 503
```

---

这份开发者指南涵盖了 Uplifted 项目的核心架构、开发流程和最佳实践。如果您有任何问题或建议，请随时联系开发团队或在 GitHub 上提出 Issue。

感谢您对 Uplifted 项目的贡献！