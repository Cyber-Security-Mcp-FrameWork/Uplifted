# Uplifted 用户使用指南

欢迎使用 Uplifted！这是一个现代化的社交平台，专注于提供优质的用户体验和强大的功能。本指南将帮助您快速上手并充分利用平台的各项功能。

## 目录

1. [快速开始](#快速开始)
2. [系统要求](#系统要求)
3. [安装部署](#安装部署)
4. [基本配置](#基本配置)
5. [用户功能](#用户功能)
6. [API使用](#api使用)
7. [常见问题](#常见问题)
8. [故障排除](#故障排除)
9. [获取帮助](#获取帮助)

## 快速开始

### 第一次使用

1. **注册账户**
   - 访问 Uplifted 平台
   - 点击"注册"按钮
   - 填写用户名、邮箱和密码
   - 验证邮箱地址

2. **完善个人资料**
   - 上传头像
   - 填写个人简介
   - 设置地理位置（可选）
   - 添加个人网站（可选）

3. **开始使用**
   - 发布第一条帖子
   - 关注感兴趣的用户
   - 浏览和互动内容

## 系统要求

### 服务器端要求

- **操作系统**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows (10+)
- **Python**: 3.9 或更高版本
- **内存**: 最低 2GB RAM，推荐 4GB+
- **存储**: 最低 10GB 可用空间
- **网络**: 稳定的互联网连接

### 数据库要求

- **PostgreSQL**: 12.0 或更高版本
- **Redis**: 6.0 或更高版本（用于缓存）

### 客户端要求

- **浏览器**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **移动设备**: iOS 13+, Android 8.0+

## 安装部署

### 1. 环境准备

#### 安装 Python 依赖

```bash
# 克隆项目
git clone https://github.com/your-org/uplifted.git
cd uplifted/server

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 安装数据库

**PostgreSQL 安装**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (使用 Homebrew)
brew install postgresql

# Windows
# 下载并安装 PostgreSQL 官方安装包
```

**Redis 安装**

```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS (使用 Homebrew)
brew install redis

# Windows
# 下载并安装 Redis 官方安装包
```

### 2. 数据库配置

#### PostgreSQL 配置

```bash
# 创建数据库用户
sudo -u postgres createuser --interactive uplifted_user

# 创建数据库
sudo -u postgres createdb uplifted_db -O uplifted_user

# 设置密码
sudo -u postgres psql
ALTER USER uplifted_user PASSWORD 'your_password';
\q
```

#### Redis 配置

```bash
# 启动 Redis 服务
sudo systemctl start redis-server

# 设置开机自启
sudo systemctl enable redis-server
```

### 3. 应用配置

创建配置文件 `.env`：

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置文件
nano .env
```

配置文件内容：

```env
# 应用配置
APP_NAME=Uplifted
APP_ENV=production
APP_DEBUG=false
APP_URL=https://your-domain.com

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=uplifted_db
DB_USER=uplifted_user
DB_PASSWORD=your_password

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT 配置
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# 邮件配置
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# 文件存储配置
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,mp4,mov

# 安全配置
SECRET_KEY=your-super-secret-key
BCRYPT_LOG_ROUNDS=12

# 监控配置
ENABLE_MONITORING=true
LOG_LEVEL=INFO
```

### 4. 数据库初始化

```bash
# 运行数据库迁移
python manage.py db upgrade

# 创建初始数据（可选）
python manage.py seed
```

### 5. 启动应用

#### 开发环境

```bash
# 启动开发服务器
python run_main_server.py

# 或使用 Flask 命令
flask run --host=0.0.0.0 --port=5000
```

#### 生产环境

使用 Gunicorn 部署：

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用
gunicorn --bind 0.0.0.0:5000 --workers 4 run_main_server:app
```

使用 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/uplifted/server/static;
    }

    location /uploads {
        alias /path/to/uplifted/server/uploads;
    }
}
```

## 基本配置

### 管理员账户

创建第一个管理员账户：

```bash
python manage.py create-admin
```

按提示输入管理员信息：
- 用户名
- 邮箱地址
- 密码

### 系统设置

通过管理界面或配置文件调整以下设置：

1. **用户注册设置**
   - 是否允许公开注册
   - 邮箱验证要求
   - 用户名规则

2. **内容设置**
   - 帖子最大长度
   - 允许的媒体类型
   - 文件大小限制

3. **隐私设置**
   - 默认帖子可见性
   - 用户搜索权限
   - 数据导出选项

4. **通知设置**
   - 邮件通知模板
   - 推送通知配置
   - 通知频率限制

## 用户功能

### 账户管理

#### 注册和登录

1. **用户注册**
   ```http
   POST /api/v1/auth/register
   Content-Type: application/json

   {
     "username": "your_username",
     "email": "your@email.com",
     "password": "secure_password"
   }
   ```

2. **用户登录**
   ```http
   POST /api/v1/auth/login
   Content-Type: application/json

   {
     "username": "your_username",
     "password": "your_password"
   }
   ```

3. **邮箱验证**
   - 注册后检查邮箱
   - 点击验证链接
   - 完成账户激活

#### 个人资料管理

1. **查看个人资料**
   ```http
   GET /api/v1/users/me
   Authorization: Bearer {access_token}
   ```

2. **更新个人资料**
   ```http
   PUT /api/v1/users/me
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "display_name": "Your Display Name",
     "bio": "Your bio here",
     "location": "Your Location",
     "website": "https://your-website.com"
   }
   ```

3. **上传头像**
   ```http
   POST /api/v1/users/upload-avatar
   Authorization: Bearer {access_token}
   Content-Type: multipart/form-data

   avatar: [image file]
   ```

### 内容创建

#### 发布帖子

1. **创建文本帖子**
   ```http
   POST /api/v1/posts
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "content": "这是我的第一条帖子！",
     "visibility": "public",
     "allow_comments": true
   }
   ```

2. **创建带媒体的帖子**
   ```http
   POST /api/v1/posts
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "content": "分享一张美丽的照片",
     "media_urls": ["https://api.uplifted.com/media/photo.jpg"],
     "tags": ["摄影", "风景"],
     "visibility": "public"
   }
   ```

3. **上传媒体文件**
   ```http
   POST /api/v1/posts/upload-media
   Authorization: Bearer {access_token}
   Content-Type: multipart/form-data

   media: [image/video file]
   type: "image"
   ```

#### 管理帖子

1. **编辑帖子**
   ```http
   PUT /api/v1/posts/{post_id}
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "content": "更新后的内容",
     "tags": ["新标签"]
   }
   ```

2. **删除帖子**
   ```http
   DELETE /api/v1/posts/{post_id}
   Authorization: Bearer {access_token}
   ```

### 社交互动

#### 关注用户

1. **关注用户**
   ```http
   POST /api/v1/users/{user_id}/follow
   Authorization: Bearer {access_token}
   ```

2. **取消关注**
   ```http
   DELETE /api/v1/users/{user_id}/follow
   Authorization: Bearer {access_token}
   ```

3. **查看关注列表**
   ```http
   GET /api/v1/users/{user_id}/following
   ```

4. **查看粉丝列表**
   ```http
   GET /api/v1/users/{user_id}/followers
   ```

#### 帖子互动

1. **点赞帖子**
   ```http
   POST /api/v1/posts/{post_id}/like
   Authorization: Bearer {access_token}
   ```

2. **收藏帖子**
   ```http
   POST /api/v1/posts/{post_id}/bookmark
   Authorization: Bearer {access_token}
   ```

3. **评论帖子**
   ```http
   POST /api/v1/posts/{post_id}/comments
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "content": "很棒的分享！"
   }
   ```

4. **分享帖子**
   ```http
   POST /api/v1/posts/{post_id}/share
   Authorization: Bearer {access_token}
   ```

### 内容发现

#### 浏览帖子

1. **获取时间线**
   ```http
   GET /api/v1/posts?page=1&limit=20&sort=created_at&order=desc
   Authorization: Bearer {access_token}
   ```

2. **搜索帖子**
   ```http
   GET /api/v1/posts?search=python&tag=编程
   ```

3. **按标签浏览**
   ```http
   GET /api/v1/posts?tag=摄影
   ```

#### 发现用户

1. **搜索用户**
   ```http
   GET /api/v1/users?search=john&page=1&limit=20
   ```

2. **推荐用户**
   ```http
   GET /api/v1/users/recommendations
   Authorization: Bearer {access_token}
   ```

## API使用

### 认证

Uplifted 使用 JWT (JSON Web Token) 进行身份认证。

1. **获取访问令牌**
   ```python
   import requests

   response = requests.post('https://api.uplifted.com/api/v1/auth/login', json={
       'username': 'your_username',
       'password': 'your_password'
   })
   
   data = response.json()
   access_token = data['data']['access_token']
   ```

2. **使用访问令牌**
   ```python
   headers = {
       'Authorization': f'Bearer {access_token}',
       'Content-Type': 'application/json'
   }
   
   response = requests.get('https://api.uplifted.com/api/v1/users/me', headers=headers)
   ```

### SDK 使用

#### Python SDK

```python
from uplifted_sdk import UpliftedClient

# 初始化客户端
client = UpliftedClient(
    base_url='https://api.uplifted.com',
    access_token='your_access_token'
)

# 获取当前用户信息
user = client.users.get_current_user()
print(f"欢迎, {user['display_name']}!")

# 创建帖子
post = client.posts.create(
    content="Hello from Python SDK!",
    tags=["python", "sdk"]
)

# 获取帖子列表
posts = client.posts.list(limit=10, tag="python")
```

#### JavaScript SDK

```javascript
import { UpliftedClient } from 'uplifted-sdk';

// 初始化客户端
const client = new UpliftedClient({
    baseUrl: 'https://api.uplifted.com',
    accessToken: 'your_access_token'
});

// 获取当前用户信息
const user = await client.users.getCurrentUser();
console.log(`欢迎, ${user.display_name}!`);

// 创建帖子
const post = await client.posts.create({
    content: "Hello from JavaScript SDK!",
    tags: ["javascript", "sdk"]
});

// 获取帖子列表
const posts = await client.posts.list({ limit: 10, tag: "javascript" });
```

### 速率限制

API 请求受到速率限制保护：

- **认证端点**: 每分钟 10 次请求
- **读取端点**: 每分钟 100 次请求
- **写入端点**: 每分钟 30 次请求
- **上传端点**: 每分钟 5 次请求

超出限制时，API 将返回 `429 Too Many Requests` 状态码。

## 常见问题

### Q: 如何重置密码？

A: 有两种方式重置密码：

1. **通过邮箱重置**
   ```http
   POST /api/v1/auth/forgot-password
   Content-Type: application/json

   {
     "email": "your@email.com"
   }
   ```

2. **通过当前密码修改**
   ```http
   POST /api/v1/auth/change-password
   Authorization: Bearer {access_token}
   Content-Type: application/json

   {
     "current_password": "old_password",
     "new_password": "new_password"
   }
   ```

### Q: 如何删除账户？

A: 删除账户是不可逆操作，请谨慎操作：

```http
DELETE /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "password": "your_password",
  "confirmation": "DELETE"
}
```

### Q: 如何导出个人数据？

A: 可以请求导出个人数据：

```http
POST /api/v1/users/me/export
Authorization: Bearer {access_token}
```

导出完成后会收到邮件通知，包含下载链接。

### Q: 如何举报不当内容？

A: 可以举报违规内容：

```http
POST /api/v1/reports
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "type": "post",
  "target_id": "post_id",
  "reason": "spam",
  "description": "详细描述"
}
```

### Q: 如何设置隐私权限？

A: 可以调整各种隐私设置：

```http
PUT /api/v1/users/me/privacy
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "is_private": false,
  "allow_search": true,
  "show_online_status": true,
  "allow_message_from_strangers": false
}
```

## 故障排除

### 常见错误

#### 1. 认证失败 (401 Unauthorized)

**原因**: 访问令牌无效或已过期

**解决方案**:
- 检查令牌是否正确
- 使用刷新令牌获取新的访问令牌
- 重新登录获取新令牌

#### 2. 权限不足 (403 Forbidden)

**原因**: 没有执行操作的权限

**解决方案**:
- 确认是否为资源的所有者
- 检查账户权限设置
- 联系管理员确认权限

#### 3. 资源不存在 (404 Not Found)

**原因**: 请求的资源不存在或已被删除

**解决方案**:
- 检查资源ID是否正确
- 确认资源是否仍然存在
- 检查是否有访问权限

#### 4. 请求过于频繁 (429 Too Many Requests)

**原因**: 超出API速率限制

**解决方案**:
- 等待一段时间后重试
- 实现指数退避重试机制
- 优化请求频率

#### 5. 服务器错误 (500 Internal Server Error)

**原因**: 服务器内部错误

**解决方案**:
- 检查服务器日志
- 确认数据库连接正常
- 联系技术支持

### 日志查看

#### 应用日志

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看访问日志
tail -f logs/access.log
```

#### 数据库日志

```bash
# PostgreSQL 日志
sudo tail -f /var/log/postgresql/postgresql-*.log

# Redis 日志
sudo tail -f /var/log/redis/redis-server.log
```

### 性能优化

#### 数据库优化

1. **索引优化**
   ```sql
   -- 创建常用查询的索引
   CREATE INDEX idx_posts_created_at ON posts(created_at);
   CREATE INDEX idx_posts_author_id ON posts(author_id);
   CREATE INDEX idx_users_username ON users(username);
   ```

2. **查询优化**
   ```sql
   -- 分析慢查询
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

#### 缓存优化

1. **Redis 配置优化**
   ```redis
   # 设置最大内存
   maxmemory 2gb
   maxmemory-policy allkeys-lru
   
   # 启用持久化
   save 900 1
   save 300 10
   save 60 10000
   ```

2. **应用缓存策略**
   ```python
   # 缓存用户信息
   @cache.memoize(timeout=300)
   def get_user_profile(user_id):
       return User.query.get(user_id)
   
   # 缓存热门帖子
   @cache.memoize(timeout=600)
   def get_trending_posts():
       return Post.query.filter_by(is_trending=True).all()
   ```

## 获取帮助

### 技术支持

- **邮箱**: support@uplifted.com
- **在线文档**: https://docs.uplifted.com
- **GitHub Issues**: https://github.com/your-org/uplifted/issues
- **社区论坛**: https://community.uplifted.com

### 开发者资源

- **API 文档**: https://api.uplifted.com/docs
- **SDK 下载**: https://github.com/your-org/uplifted-sdk
- **示例代码**: https://github.com/your-org/uplifted-examples
- **开发者博客**: https://blog.uplifted.com/developers

### 社区支持

- **Discord**: https://discord.gg/uplifted
- **Telegram**: https://t.me/uplifted_community
- **Reddit**: https://reddit.com/r/uplifted
- **Stack Overflow**: 使用标签 `uplifted`

### 反馈和建议

我们非常重视用户反馈，请通过以下方式联系我们：

- **功能建议**: features@uplifted.com
- **Bug 报告**: bugs@uplifted.com
- **用户体验**: ux@uplifted.com
- **安全问题**: security@uplifted.com

---

感谢您选择 Uplifted！我们致力于为您提供最佳的社交平台体验。如果您在使用过程中遇到任何问题，请随时联系我们的支持团队。