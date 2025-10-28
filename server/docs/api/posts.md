# 帖子管理 API

帖子管理API提供了完整的帖子生命周期管理功能，包括帖子的创建、获取、更新、删除以及互动功能（点赞、收藏、分享等）。

## 端点概览

| 方法 | 端点 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/v1/posts` | 创建新帖子 | 必需 |
| GET | `/api/v1/posts` | 获取帖子列表 | 可选 |
| GET | `/api/v1/posts/{post_id}` | 获取指定帖子 | 可选 |
| PUT | `/api/v1/posts/{post_id}` | 更新帖子 | 必需 |
| DELETE | `/api/v1/posts/{post_id}` | 删除帖子 | 必需 |
| POST | `/api/v1/posts/{post_id}/like` | 点赞帖子 | 必需 |
| DELETE | `/api/v1/posts/{post_id}/like` | 取消点赞 | 必需 |
| POST | `/api/v1/posts/{post_id}/bookmark` | 收藏帖子 | 必需 |
| DELETE | `/api/v1/posts/{post_id}/bookmark` | 取消收藏 | 必需 |
| POST | `/api/v1/posts/{post_id}/share` | 分享帖子 | 必需 |
| GET | `/api/v1/posts/{post_id}/comments` | 获取帖子评论 | 可选 |
| POST | `/api/v1/posts/{post_id}/comments` | 添加评论 | 必需 |
| GET | `/api/v1/users/{user_id}/posts` | 获取用户帖子 | 可选 |
| POST | `/api/v1/posts/upload-media` | 上传媒体文件 | 必需 |

## 详细端点说明

### 创建新帖子

创建一个新的帖子。

```http
POST /api/v1/posts
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求体：**

```json
{
  "content": "这是一个关于Python编程的精彩分享！🐍",
  "media_urls": [
    "https://api.uplifted.com/media/image1.jpg",
    "https://api.uplifted.com/media/image2.jpg"
  ],
  "tags": ["python", "编程", "技术分享"],
  "visibility": "public",
  "allow_comments": true,
  "location": {
    "name": "北京市",
    "latitude": 39.9042,
    "longitude": 116.4074
  }
}
```

**请求参数：**
- `content` (string, 必需): 帖子内容，最大5000字符
- `media_urls` (array, 可选): 媒体文件URL数组，最多9个
- `tags` (array, 可选): 标签数组，最多10个
- `visibility` (string, 可选): 可见性（public, followers, private），默认public
- `allow_comments` (boolean, 可选): 是否允许评论，默认true
- `location` (object, 可选): 地理位置信息

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "这是一个关于Python编程的精彩分享！🐍",
    "media_urls": [
      "https://api.uplifted.com/media/image1.jpg",
      "https://api.uplifted.com/media/image2.jpg"
    ],
    "tags": ["python", "编程", "技术分享"],
    "visibility": "public",
    "allow_comments": true,
    "location": {
      "name": "北京市",
      "latitude": 39.9042,
      "longitude": 116.4074
    },
    "author": {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "username": "john_doe",
      "display_name": "John Doe",
      "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
      "is_verified": false
    },
    "stats": {
      "likes_count": 0,
      "comments_count": 0,
      "shares_count": 0,
      "bookmarks_count": 0
    },
    "user_interactions": {
      "is_liked": false,
      "is_bookmarked": false
    },
    "created_at": "2024-01-21T10:30:00Z",
    "updated_at": "2024-01-21T10:30:00Z"
  }
}
```

### 获取帖子列表

获取帖子列表，支持多种过滤和排序选项。

```http
GET /api/v1/posts?page=1&limit=20&sort=created_at&order=desc&tag=python&author=john_doe
```

**查询参数：**
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100
- `sort` (string, 可选): 排序字段（created_at, likes_count, comments_count），默认为created_at
- `order` (string, 可选): 排序顺序（asc, desc），默认为desc
- `tag` (string, 可选): 按标签过滤
- `author` (string, 可选): 按作者过滤（用户名或用户ID）
- `search` (string, 可选): 搜索关键词
- `visibility` (string, 可选): 可见性过滤（public, followers）
- `since` (string, 可选): 起始时间（ISO 8601格式）
- `until` (string, 可选): 结束时间（ISO 8601格式）

**响应示例：**

```json
{
  "success": true,
  "data": {
    "posts": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "这是一个关于Python编程的精彩分享！🐍",
        "media_urls": [
          "https://api.uplifted.com/media/image1.jpg"
        ],
        "tags": ["python", "编程", "技术分享"],
        "visibility": "public",
        "allow_comments": true,
        "author": {
          "id": "456e7890-e89b-12d3-a456-426614174001",
          "username": "john_doe",
          "display_name": "John Doe",
          "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
          "is_verified": false
        },
        "stats": {
          "likes_count": 42,
          "comments_count": 8,
          "shares_count": 3,
          "bookmarks_count": 15
        },
        "user_interactions": {
          "is_liked": true,
          "is_bookmarked": false
        },
        "created_at": "2024-01-21T10:30:00Z",
        "updated_at": "2024-01-21T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 获取指定帖子

获取指定帖子的详细信息。

```http
GET /api/v1/posts/{post_id}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "这是一个关于Python编程的精彩分享！🐍\n\n今天想和大家分享一些Python编程的最佳实践...",
    "media_urls": [
      "https://api.uplifted.com/media/image1.jpg",
      "https://api.uplifted.com/media/image2.jpg"
    ],
    "tags": ["python", "编程", "技术分享", "最佳实践"],
    "visibility": "public",
    "allow_comments": true,
    "location": {
      "name": "北京市",
      "latitude": 39.9042,
      "longitude": 116.4074
    },
    "author": {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "username": "john_doe",
      "display_name": "John Doe",
      "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
      "is_verified": false
    },
    "stats": {
      "likes_count": 42,
      "comments_count": 8,
      "shares_count": 3,
      "bookmarks_count": 15,
      "views_count": 256
    },
    "user_interactions": {
      "is_liked": true,
      "is_bookmarked": false
    },
    "created_at": "2024-01-21T10:30:00Z",
    "updated_at": "2024-01-21T11:15:00Z"
  }
}
```

### 更新帖子

更新指定帖子的内容。只有帖子作者可以更新。

```http
PUT /api/v1/posts/{post_id}
Authorization: Bearer {access_token}
Content-Type: application/json
```

**路径参数：**
- `post_id` (string): 帖子ID

**请求体：**

```json
{
  "content": "更新后的帖子内容",
  "tags": ["python", "编程", "更新"],
  "visibility": "public",
  "allow_comments": true
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "content": "更新后的帖子内容",
    "tags": ["python", "编程", "更新"],
    "visibility": "public",
    "allow_comments": true,
    "updated_at": "2024-01-21T12:00:00Z"
  }
}
```

### 删除帖子

删除指定帖子。只有帖子作者可以删除。

```http
DELETE /api/v1/posts/{post_id}
Authorization: Bearer {access_token}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "message": "帖子已成功删除"
}
```

### 点赞帖子

为指定帖子点赞。

```http
POST /api/v1/posts/{post_id}/like
Authorization: Bearer {access_token}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "message": "点赞成功",
  "data": {
    "is_liked": true,
    "likes_count": 43
  }
}
```

### 取消点赞

取消对指定帖子的点赞。

```http
DELETE /api/v1/posts/{post_id}/like
Authorization: Bearer {access_token}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "message": "已取消点赞",
  "data": {
    "is_liked": false,
    "likes_count": 42
  }
}
```

### 收藏帖子

收藏指定帖子到个人收藏夹。

```http
POST /api/v1/posts/{post_id}/bookmark
Authorization: Bearer {access_token}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "message": "收藏成功",
  "data": {
    "is_bookmarked": true,
    "bookmarks_count": 16
  }
}
```

### 取消收藏

取消收藏指定帖子。

```http
DELETE /api/v1/posts/{post_id}/bookmark
Authorization: Bearer {access_token}
```

**路径参数：**
- `post_id` (string): 帖子ID

**响应示例：**

```json
{
  "success": true,
  "message": "已取消收藏",
  "data": {
    "is_bookmarked": false,
    "bookmarks_count": 15
  }
}
```

### 分享帖子

分享指定帖子，增加分享计数。

```http
POST /api/v1/posts/{post_id}/share
Authorization: Bearer {access_token}
Content-Type: application/json
```

**路径参数：**
- `post_id` (string): 帖子ID

**请求体（可选）：**

```json
{
  "platform": "twitter",
  "message": "分享一个很棒的帖子！"
}
```

**响应示例：**

```json
{
  "success": true,
  "message": "分享成功",
  "data": {
    "shares_count": 4,
    "share_url": "https://uplifted.com/posts/123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### 获取帖子评论

获取指定帖子的评论列表。

```http
GET /api/v1/posts/{post_id}/comments?page=1&limit=20&sort=created_at&order=desc
```

**路径参数：**
- `post_id` (string): 帖子ID

**查询参数：**
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100
- `sort` (string, 可选): 排序字段（created_at, likes_count），默认为created_at
- `order` (string, 可选): 排序顺序（asc, desc），默认为desc

**响应示例：**

```json
{
  "success": true,
  "data": {
    "comments": [
      {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "content": "很棒的分享！学到了很多。",
        "author": {
          "id": "abc1234-e89b-12d3-a456-426614174003",
          "username": "jane_smith",
          "display_name": "Jane Smith",
          "avatar_url": "https://api.uplifted.com/avatars/jane_smith.jpg",
          "is_verified": true
        },
        "likes_count": 5,
        "is_liked": false,
        "created_at": "2024-01-21T11:45:00Z",
        "updated_at": "2024-01-21T11:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 8,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

### 添加评论

为指定帖子添加评论。

```http
POST /api/v1/posts/{post_id}/comments
Authorization: Bearer {access_token}
Content-Type: application/json
```

**路径参数：**
- `post_id` (string): 帖子ID

**请求体：**

```json
{
  "content": "这是一个很有用的分享，谢谢！",
  "parent_id": null
}
```

**请求参数：**
- `content` (string, 必需): 评论内容，最大1000字符
- `parent_id` (string, 可选): 父评论ID（用于回复评论）

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "def5678-e89b-12d3-a456-426614174004",
    "content": "这是一个很有用的分享，谢谢！",
    "author": {
      "id": "456e7890-e89b-12d3-a456-426614174001",
      "username": "john_doe",
      "display_name": "John Doe",
      "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
      "is_verified": false
    },
    "parent_id": null,
    "likes_count": 0,
    "is_liked": false,
    "created_at": "2024-01-21T12:30:00Z",
    "updated_at": "2024-01-21T12:30:00Z"
  }
}
```

### 获取用户帖子

获取指定用户的帖子列表。

```http
GET /api/v1/users/{user_id}/posts?page=1&limit=20&sort=created_at&order=desc
```

**路径参数：**
- `user_id` (string): 用户ID或用户名

**查询参数：**
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100
- `sort` (string, 可选): 排序字段（created_at, likes_count），默认为created_at
- `order` (string, 可选): 排序顺序（asc, desc），默认为desc
- `visibility` (string, 可选): 可见性过滤（仅对自己的帖子有效）

**响应示例：**

```json
{
  "success": true,
  "data": {
    "posts": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "这是一个关于Python编程的精彩分享！🐍",
        "media_urls": ["https://api.uplifted.com/media/image1.jpg"],
        "tags": ["python", "编程", "技术分享"],
        "visibility": "public",
        "stats": {
          "likes_count": 42,
          "comments_count": 8,
          "shares_count": 3,
          "bookmarks_count": 15
        },
        "user_interactions": {
          "is_liked": true,
          "is_bookmarked": false
        },
        "created_at": "2024-01-21T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 42,
      "total_pages": 3,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 上传媒体文件

上传图片、视频等媒体文件，用于帖子内容。

```http
POST /api/v1/posts/upload-media
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**请求体：**
- `media` (file): 媒体文件（支持 JPEG, PNG, WebP, MP4, MOV）
- `type` (string): 媒体类型（image, video）

**响应示例：**

```json
{
  "success": true,
  "data": {
    "media_url": "https://api.uplifted.com/media/abc123.jpg",
    "thumbnail_url": "https://api.uplifted.com/media/thumbnails/abc123.jpg",
    "type": "image",
    "size": 1024000,
    "dimensions": {
      "width": 1920,
      "height": 1080
    }
  }
}
```

## 错误代码

| 错误代码 | HTTP状态码 | 描述 |
|----------|------------|------|
| POST_NOT_FOUND | 404 | 帖子不存在 |
| POST_ACCESS_DENIED | 403 | 无权访问帖子 |
| POST_ALREADY_LIKED | 409 | 已经点赞该帖子 |
| POST_NOT_LIKED | 409 | 未点赞该帖子 |
| POST_ALREADY_BOOKMARKED | 409 | 已经收藏该帖子 |
| POST_NOT_BOOKMARKED | 409 | 未收藏该帖子 |
| INVALID_POST_DATA | 400 | 帖子数据无效 |
| POST_TOO_LONG | 400 | 帖子内容过长 |
| TOO_MANY_TAGS | 400 | 标签数量过多 |
| TOO_MANY_MEDIA | 400 | 媒体文件数量过多 |
| MEDIA_TOO_LARGE | 413 | 媒体文件过大 |
| INVALID_MEDIA_FORMAT | 400 | 媒体格式不支持 |
| COMMENTS_DISABLED | 403 | 该帖子不允许评论 |
| COMMENT_TOO_LONG | 400 | 评论内容过长 |

## 数据模型

### Post 对象

```typescript
interface Post {
  id: string;                    // 帖子唯一标识符
  content: string;               // 帖子内容
  media_urls?: string[];         // 媒体文件URL数组
  tags?: string[];               // 标签数组
  visibility: 'public' | 'followers' | 'private'; // 可见性
  allow_comments: boolean;       // 是否允许评论
  location?: Location;           // 地理位置信息
  author: User;                  // 作者信息
  stats: PostStats;              // 统计信息
  user_interactions?: UserInteractions; // 用户交互状态
  created_at: string;            // 创建时间（ISO 8601）
  updated_at: string;            // 更新时间（ISO 8601）
}
```

### PostStats 对象

```typescript
interface PostStats {
  likes_count: number;           // 点赞数
  comments_count: number;        // 评论数
  shares_count: number;          // 分享数
  bookmarks_count: number;       // 收藏数
  views_count?: number;          // 浏览数（仅作者可见）
}
```

### UserInteractions 对象

```typescript
interface UserInteractions {
  is_liked: boolean;             // 当前用户是否已点赞
  is_bookmarked: boolean;        // 当前用户是否已收藏
}
```

### Comment 对象

```typescript
interface Comment {
  id: string;                    // 评论唯一标识符
  content: string;               // 评论内容
  author: User;                  // 评论作者
  parent_id?: string;            // 父评论ID（用于回复）
  likes_count: number;           // 点赞数
  is_liked: boolean;             // 当前用户是否已点赞
  created_at: string;            // 创建时间（ISO 8601）
  updated_at: string;            // 更新时间（ISO 8601）
}
```

### Location 对象

```typescript
interface Location {
  name: string;                  // 地点名称
  latitude: number;              // 纬度
  longitude: number;             // 经度
}
```

## 示例代码

### Python 示例

```python
import requests
from typing import List, Optional, Dict, Any

class PostsAPI:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_post(self, content: str, media_urls: Optional[List[str]] = None,
                   tags: Optional[List[str]] = None, visibility: str = 'public',
                   allow_comments: bool = True, location: Optional[Dict] = None):
        """创建新帖子"""
        data = {
            'content': content,
            'visibility': visibility,
            'allow_comments': allow_comments
        }
        if media_urls:
            data['media_urls'] = media_urls
        if tags:
            data['tags'] = tags
        if location:
            data['location'] = location
            
        response = requests.post(
            f'{self.base_url}/api/v1/posts',
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def get_posts(self, page: int = 1, limit: int = 20, sort: str = 'created_at',
                  order: str = 'desc', **filters):
        """获取帖子列表"""
        params = {
            'page': page,
            'limit': limit,
            'sort': sort,
            'order': order,
            **filters
        }
        response = requests.get(
            f'{self.base_url}/api/v1/posts',
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def get_post(self, post_id: str):
        """获取指定帖子"""
        response = requests.get(
            f'{self.base_url}/api/v1/posts/{post_id}',
            headers=self.headers
        )
        return response.json()
    
    def update_post(self, post_id: str, **updates):
        """更新帖子"""
        response = requests.put(
            f'{self.base_url}/api/v1/posts/{post_id}',
            headers=self.headers,
            json=updates
        )
        return response.json()
    
    def delete_post(self, post_id: str):
        """删除帖子"""
        response = requests.delete(
            f'{self.base_url}/api/v1/posts/{post_id}',
            headers=self.headers
        )
        return response.json()
    
    def like_post(self, post_id: str):
        """点赞帖子"""
        response = requests.post(
            f'{self.base_url}/api/v1/posts/{post_id}/like',
            headers=self.headers
        )
        return response.json()
    
    def unlike_post(self, post_id: str):
        """取消点赞"""
        response = requests.delete(
            f'{self.base_url}/api/v1/posts/{post_id}/like',
            headers=self.headers
        )
        return response.json()
    
    def bookmark_post(self, post_id: str):
        """收藏帖子"""
        response = requests.post(
            f'{self.base_url}/api/v1/posts/{post_id}/bookmark',
            headers=self.headers
        )
        return response.json()
    
    def unbookmark_post(self, post_id: str):
        """取消收藏"""
        response = requests.delete(
            f'{self.base_url}/api/v1/posts/{post_id}/bookmark',
            headers=self.headers
        )
        return response.json()
    
    def add_comment(self, post_id: str, content: str, parent_id: Optional[str] = None):
        """添加评论"""
        data = {'content': content}
        if parent_id:
            data['parent_id'] = parent_id
            
        response = requests.post(
            f'{self.base_url}/api/v1/posts/{post_id}/comments',
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def upload_media(self, file_path: str, media_type: str):
        """上传媒体文件"""
        headers = {'Authorization': f'Bearer {self.access_token}'}
        with open(file_path, 'rb') as f:
            files = {'media': f}
            data = {'type': media_type}
            response = requests.post(
                f'{self.base_url}/api/v1/posts/upload-media',
                headers=headers,
                files=files,
                data=data
            )
        return response.json()

# 使用示例
api = PostsAPI('https://api.uplifted.com', 'your_access_token')

# 创建帖子
post = api.create_post(
    content="分享一个Python技巧！",
    tags=["python", "编程"],
    visibility="public"
)

# 获取帖子列表
posts = api.get_posts(page=1, limit=10, tag="python")

# 点赞帖子
like_result = api.like_post(post['data']['id'])
```

### JavaScript 示例

```javascript
class PostsAPI {
    constructor(baseUrl, accessToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        };
    }

    async createPost(data) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }

    async getPosts(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const response = await fetch(`${this.baseUrl}/api/v1/posts?${queryString}`, {
            headers: this.headers
        });
        return response.json();
    }

    async getPost(postId) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}`, {
            headers: this.headers
        });
        return response.json();
    }

    async updatePost(postId, updates) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(updates)
        });
        return response.json();
    }

    async deletePost(postId) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}`, {
            method: 'DELETE',
            headers: this.headers
        });
        return response.json();
    }

    async likePost(postId) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}/like`, {
            method: 'POST',
            headers: this.headers
        });
        return response.json();
    }

    async unlikePost(postId) {
        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}/like`, {
            method: 'DELETE',
            headers: this.headers
        });
        return response.json();
    }

    async addComment(postId, content, parentId = null) {
        const data = { content };
        if (parentId) data.parent_id = parentId;

        const response = await fetch(`${this.baseUrl}/api/v1/posts/${postId}/comments`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }

    async uploadMedia(file, type) {
        const formData = new FormData();
        formData.append('media', file);
        formData.append('type', type);

        const response = await fetch(`${this.baseUrl}/api/v1/posts/upload-media`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.accessToken}`
            },
            body: formData
        });
        return response.json();
    }
}

// 使用示例
const api = new PostsAPI('https://api.uplifted.com', 'your_access_token');

// 创建帖子
api.createPost({
    content: "分享一个JavaScript技巧！",
    tags: ["javascript", "编程"],
    visibility: "public"
}).then(post => {
    console.log('帖子创建成功:', post);
});

// 获取帖子列表
api.getPosts({ tag: "javascript", limit: 10 }).then(posts => {
    console.log('获取到帖子:', posts.data.posts.length);
});
```

## 注意事项

1. **内容审核**: 所有帖子内容都会经过自动审核，违规内容将被拒绝或删除
2. **媒体限制**: 图片最大10MB，视频最大100MB，每个帖子最多9个媒体文件
3. **标签规范**: 标签长度不超过20字符，每个帖子最多10个标签
4. **隐私保护**: 私密帖子只有作者可见，关注者可见的帖子只对关注者开放
5. **缓存策略**: 帖子数据会被缓存，更新后可能需要几分钟才能在所有地方生效
6. **速率限制**: 创建帖子、点赞、评论等操作都有速率限制，防止滥用