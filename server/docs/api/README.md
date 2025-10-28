# Uplifted API 文档

## 概述

Uplifted 是一个现代化的社交平台 API，提供用户管理、内容发布、社交互动等功能。本文档详细介绍了所有可用的 API 端点、请求格式、响应格式和使用示例。

## 基本信息

- **基础URL**: `https://api.uplifted.com/v1`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

所有需要认证的 API 请求都必须在请求头中包含有效的访问令牌：

```http
Authorization: Bearer <access_token>
```

### 获取访问令牌

```http
POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 错误处理

API 使用标准的 HTTP 状态码来表示请求的结果：

- `200 OK` - 请求成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 请求参数错误
- `401 Unauthorized` - 未认证或认证失败
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `422 Unprocessable Entity` - 请求格式正确但包含语义错误
- `500 Internal Server Error` - 服务器内部错误

**错误响应格式**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "email",
        "message": "邮箱格式不正确"
      }
    ]
  }
}
```

## 分页

对于返回列表数据的 API，支持分页查询：

**请求参数**:
- `page`: 页码（从1开始，默认为1）
- `limit`: 每页数量（默认为20，最大为100）
- `sort`: 排序字段
- `order`: 排序方向（asc/desc，默认为desc）

**响应格式**:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

## 速率限制

为了保护服务稳定性，API 实施了速率限制：

- **未认证用户**: 每小时100次请求
- **已认证用户**: 每小时1000次请求
- **高级用户**: 每小时5000次请求

当达到速率限制时，API 将返回 `429 Too Many Requests` 状态码。

**响应头**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## API 端点概览

### 认证相关
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `POST /auth/refresh` - 刷新令牌
- `POST /auth/forgot-password` - 忘记密码
- `POST /auth/reset-password` - 重置密码

### 用户管理
- `GET /users/me` - 获取当前用户信息
- `PUT /users/me` - 更新当前用户信息
- `GET /users/{id}` - 获取用户信息
- `GET /users` - 搜索用户
- `DELETE /users/me` - 删除当前用户

### 帖子管理
- `GET /posts` - 获取帖子列表
- `POST /posts` - 创建帖子
- `GET /posts/{id}` - 获取帖子详情
- `PUT /posts/{id}` - 更新帖子
- `DELETE /posts/{id}` - 删除帖子
- `GET /posts/search` - 搜索帖子

### 评论管理
- `GET /posts/{id}/comments` - 获取帖子评论
- `POST /posts/{id}/comments` - 创建评论
- `PUT /comments/{id}` - 更新评论
- `DELETE /comments/{id}` - 删除评论

### 社交功能
- `POST /posts/{id}/like` - 点赞帖子
- `DELETE /posts/{id}/like` - 取消点赞
- `POST /users/{id}/follow` - 关注用户
- `DELETE /users/{id}/follow` - 取消关注
- `GET /users/me/followers` - 获取粉丝列表
- `GET /users/me/following` - 获取关注列表

### 文件上传
- `POST /upload/image` - 上传图片
- `POST /upload/file` - 上传文件
- `GET /files/{id}` - 获取文件信息

### 系统监控
- `GET /health` - 健康检查
- `GET /metrics` - 系统指标
- `GET /status` - 系统状态

## 数据模型

### 用户模型
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "profile": {
    "first_name": "string",
    "last_name": "string",
    "bio": "string",
    "avatar_url": "string",
    "location": "string",
    "website": "string"
  },
  "stats": {
    "posts_count": "integer",
    "followers_count": "integer",
    "following_count": "integer"
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 帖子模型
```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "author": {
    "id": "uuid",
    "username": "string",
    "profile": {
      "first_name": "string",
      "last_name": "string",
      "avatar_url": "string"
    }
  },
  "tags": ["string"],
  "stats": {
    "likes_count": "integer",
    "comments_count": "integer",
    "views_count": "integer"
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 评论模型
```json
{
  "id": "uuid",
  "content": "string",
  "author": {
    "id": "uuid",
    "username": "string",
    "profile": {
      "first_name": "string",
      "last_name": "string",
      "avatar_url": "string"
    }
  },
  "post_id": "uuid",
  "parent_id": "uuid",
  "replies": ["Comment"],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 示例代码

### Python 示例

```python
import requests

# 配置
BASE_URL = "https://api.uplifted.com/v1"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}

# 获取用户信息
response = requests.get(f"{BASE_URL}/users/me", headers=headers)
user = response.json()

# 创建帖子
post_data = {
    "title": "我的第一篇帖子",
    "content": "这是我在 Uplifted 上的第一篇帖子！",
    "tags": ["介绍", "新手"]
}
response = requests.post(f"{BASE_URL}/posts", json=post_data, headers=headers)
post = response.json()

# 获取帖子列表
response = requests.get(f"{BASE_URL}/posts?page=1&limit=10", headers=headers)
posts = response.json()
```

### JavaScript 示例

```javascript
const BASE_URL = "https://api.uplifted.com/v1";
const headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
};

// 获取用户信息
async function getUser() {
    const response = await fetch(`${BASE_URL}/users/me`, { headers });
    return await response.json();
}

// 创建帖子
async function createPost(title, content, tags) {
    const response = await fetch(`${BASE_URL}/posts`, {
        method: "POST",
        headers,
        body: JSON.stringify({ title, content, tags })
    });
    return await response.json();
}

// 获取帖子列表
async function getPosts(page = 1, limit = 10) {
    const response = await fetch(`${BASE_URL}/posts?page=${page}&limit=${limit}`, { headers });
    return await response.json();
}
```

### cURL 示例

```bash
# 用户登录
curl -X POST https://api.uplifted.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# 获取用户信息
curl -X GET https://api.uplifted.com/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 创建帖子
curl -X POST https://api.uplifted.com/v1/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"title": "我的帖子", "content": "帖子内容", "tags": ["标签1", "标签2"]}'
```

## 版本控制

API 使用语义化版本控制。当前版本为 v1。

- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

## 支持

如果您在使用 API 时遇到问题，请通过以下方式联系我们：

- **邮箱**: support@uplifted.com
- **文档**: https://docs.uplifted.com
- **GitHub**: https://github.com/uplifted/api

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基础用户管理功能
- 帖子和评论系统
- 认证和授权
- 文件上传功能