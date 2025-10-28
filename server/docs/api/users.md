# 用户管理 API

用户管理API提供了完整的用户生命周期管理功能，包括用户信息的获取、更新、删除以及用户关系管理。

## 端点概览

| 方法 | 端点 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/v1/users/me` | 获取当前用户信息 | 必需 |
| PUT | `/api/v1/users/me` | 更新当前用户信息 | 必需 |
| DELETE | `/api/v1/users/me` | 删除当前用户账户 | 必需 |
| GET | `/api/v1/users/{user_id}` | 获取指定用户信息 | 可选 |
| GET | `/api/v1/users` | 获取用户列表 | 可选 |
| POST | `/api/v1/users/{user_id}/follow` | 关注用户 | 必需 |
| DELETE | `/api/v1/users/{user_id}/follow` | 取消关注用户 | 必需 |
| GET | `/api/v1/users/{user_id}/followers` | 获取用户粉丝列表 | 可选 |
| GET | `/api/v1/users/{user_id}/following` | 获取用户关注列表 | 可选 |
| POST | `/api/v1/users/upload-avatar` | 上传用户头像 | 必需 |

## 详细端点说明

### 获取当前用户信息

获取当前认证用户的详细信息。

```http
GET /api/v1/users/me
Authorization: Bearer {access_token}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "bio": "Software developer passionate about clean code",
    "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
    "location": "San Francisco, CA",
    "website": "https://johndoe.dev",
    "followers_count": 150,
    "following_count": 75,
    "posts_count": 42,
    "is_verified": false,
    "is_private": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-20T14:45:00Z"
  }
}
```

### 更新当前用户信息

更新当前认证用户的个人信息。

```http
PUT /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求体：**

```json
{
  "display_name": "John Smith",
  "bio": "Full-stack developer and tech enthusiast",
  "location": "New York, NY",
  "website": "https://johnsmith.dev",
  "is_private": false
}
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "john_doe",
    "email": "john@example.com",
    "display_name": "John Smith",
    "bio": "Full-stack developer and tech enthusiast",
    "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
    "location": "New York, NY",
    "website": "https://johnsmith.dev",
    "followers_count": 150,
    "following_count": 75,
    "posts_count": 42,
    "is_verified": false,
    "is_private": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-21T09:15:00Z"
  }
}
```

### 删除当前用户账户

永久删除当前认证用户的账户及所有相关数据。

```http
DELETE /api/v1/users/me
Authorization: Bearer {access_token}
```

**请求体（可选）：**

```json
{
  "password": "current_password",
  "confirmation": "DELETE"
}
```

**响应示例：**

```json
{
  "success": true,
  "message": "用户账户已成功删除"
}
```

### 获取指定用户信息

获取指定用户的公开信息。

```http
GET /api/v1/users/{user_id}
```

**路径参数：**
- `user_id` (string): 用户ID或用户名

**响应示例：**

```json
{
  "success": true,
  "data": {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "username": "jane_smith",
    "display_name": "Jane Smith",
    "bio": "UI/UX Designer creating beautiful experiences",
    "avatar_url": "https://api.uplifted.com/avatars/jane_smith.jpg",
    "location": "Los Angeles, CA",
    "website": "https://janesmith.design",
    "followers_count": 320,
    "following_count": 180,
    "posts_count": 89,
    "is_verified": true,
    "is_private": false,
    "is_following": false,
    "is_followed_by": false,
    "created_at": "2024-01-10T08:20:00Z"
  }
}
```

### 获取用户列表

获取用户列表，支持搜索和分页。

```http
GET /api/v1/users?search=john&page=1&limit=20&sort=created_at&order=desc
```

**查询参数：**
- `search` (string, 可选): 搜索关键词（用户名、显示名称）
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100
- `sort` (string, 可选): 排序字段（created_at, followers_count, posts_count），默认为created_at
- `order` (string, 可选): 排序顺序（asc, desc），默认为desc

**响应示例：**

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "john_doe",
        "display_name": "John Doe",
        "bio": "Software developer passionate about clean code",
        "avatar_url": "https://api.uplifted.com/avatars/john_doe.jpg",
        "followers_count": 150,
        "following_count": 75,
        "posts_count": 42,
        "is_verified": false,
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

### 关注用户

关注指定用户。

```http
POST /api/v1/users/{user_id}/follow
Authorization: Bearer {access_token}
```

**路径参数：**
- `user_id` (string): 要关注的用户ID

**响应示例：**

```json
{
  "success": true,
  "message": "已成功关注用户",
  "data": {
    "is_following": true,
    "followers_count": 321
  }
}
```

### 取消关注用户

取消关注指定用户。

```http
DELETE /api/v1/users/{user_id}/follow
Authorization: Bearer {access_token}
```

**路径参数：**
- `user_id` (string): 要取消关注的用户ID

**响应示例：**

```json
{
  "success": true,
  "message": "已取消关注用户",
  "data": {
    "is_following": false,
    "followers_count": 320
  }
}
```

### 获取用户粉丝列表

获取指定用户的粉丝列表。

```http
GET /api/v1/users/{user_id}/followers?page=1&limit=20
```

**路径参数：**
- `user_id` (string): 用户ID

**查询参数：**
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100

**响应示例：**

```json
{
  "success": true,
  "data": {
    "followers": [
      {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "username": "alice_wonder",
        "display_name": "Alice Wonder",
        "avatar_url": "https://api.uplifted.com/avatars/alice_wonder.jpg",
        "is_verified": false,
        "followed_at": "2024-01-18T16:20:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 320,
      "total_pages": 16,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 获取用户关注列表

获取指定用户的关注列表。

```http
GET /api/v1/users/{user_id}/following?page=1&limit=20
```

**路径参数：**
- `user_id` (string): 用户ID

**查询参数：**
- `page` (integer, 可选): 页码，默认为1
- `limit` (integer, 可选): 每页数量，默认为20，最大100

**响应示例：**

```json
{
  "success": true,
  "data": {
    "following": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "username": "jane_smith",
        "display_name": "Jane Smith",
        "avatar_url": "https://api.uplifted.com/avatars/jane_smith.jpg",
        "is_verified": true,
        "followed_at": "2024-01-12T11:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 180,
      "total_pages": 9,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 上传用户头像

上传或更新用户头像图片。

```http
POST /api/v1/users/upload-avatar
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**请求体：**
- `avatar` (file): 头像图片文件（支持 JPEG, PNG, WebP，最大 5MB）

**响应示例：**

```json
{
  "success": true,
  "message": "头像上传成功",
  "data": {
    "avatar_url": "https://api.uplifted.com/avatars/john_doe_new.jpg",
    "thumbnail_url": "https://api.uplifted.com/avatars/thumbnails/john_doe_new.jpg"
  }
}
```

## 错误代码

| 错误代码 | HTTP状态码 | 描述 |
|----------|------------|------|
| USER_NOT_FOUND | 404 | 用户不存在 |
| USER_ALREADY_FOLLOWED | 409 | 已经关注该用户 |
| USER_NOT_FOLLOWED | 409 | 未关注该用户 |
| CANNOT_FOLLOW_SELF | 400 | 不能关注自己 |
| INVALID_USER_DATA | 400 | 用户数据无效 |
| USERNAME_TAKEN | 409 | 用户名已被占用 |
| EMAIL_TAKEN | 409 | 邮箱已被占用 |
| AVATAR_TOO_LARGE | 413 | 头像文件过大 |
| INVALID_AVATAR_FORMAT | 400 | 头像格式不支持 |
| ACCOUNT_DELETION_FAILED | 500 | 账户删除失败 |

## 数据模型

### User 对象

```typescript
interface User {
  id: string;                    // 用户唯一标识符
  username: string;              // 用户名（唯一）
  email?: string;                // 邮箱地址（仅自己可见）
  display_name: string;          // 显示名称
  bio?: string;                  // 个人简介
  avatar_url?: string;           // 头像URL
  location?: string;             // 地理位置
  website?: string;              // 个人网站
  followers_count: number;       // 粉丝数量
  following_count: number;       // 关注数量
  posts_count: number;           // 帖子数量
  is_verified: boolean;          // 是否已验证
  is_private: boolean;           // 是否私密账户
  is_following?: boolean;        // 当前用户是否关注（仅在查看他人资料时）
  is_followed_by?: boolean;      // 是否被当前用户关注（仅在查看他人资料时）
  created_at: string;            // 创建时间（ISO 8601）
  updated_at?: string;           // 更新时间（ISO 8601）
}
```

### Follow 对象

```typescript
interface Follow {
  id: string;                    // 关注关系唯一标识符
  follower_id: string;           // 关注者用户ID
  following_id: string;          // 被关注者用户ID
  followed_at: string;           // 关注时间（ISO 8601）
}
```

## 示例代码

### Python 示例

```python
import requests

class UserAPI:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_current_user(self):
        """获取当前用户信息"""
        response = requests.get(
            f'{self.base_url}/api/v1/users/me',
            headers=self.headers
        )
        return response.json()
    
    def update_profile(self, **kwargs):
        """更新用户资料"""
        response = requests.put(
            f'{self.base_url}/api/v1/users/me',
            headers=self.headers,
            json=kwargs
        )
        return response.json()
    
    def get_user(self, user_id: str):
        """获取指定用户信息"""
        response = requests.get(
            f'{self.base_url}/api/v1/users/{user_id}',
            headers=self.headers
        )
        return response.json()
    
    def follow_user(self, user_id: str):
        """关注用户"""
        response = requests.post(
            f'{self.base_url}/api/v1/users/{user_id}/follow',
            headers=self.headers
        )
        return response.json()
    
    def unfollow_user(self, user_id: str):
        """取消关注用户"""
        response = requests.delete(
            f'{self.base_url}/api/v1/users/{user_id}/follow',
            headers=self.headers
        )
        return response.json()
    
    def upload_avatar(self, file_path: str):
        """上传头像"""
        headers = {'Authorization': f'Bearer {self.access_token}'}
        with open(file_path, 'rb') as f:
            files = {'avatar': f}
            response = requests.post(
                f'{self.base_url}/api/v1/users/upload-avatar',
                headers=headers,
                files=files
            )
        return response.json()

# 使用示例
api = UserAPI('https://api.uplifted.com', 'your_access_token')

# 获取当前用户信息
user = api.get_current_user()
print(f"当前用户: {user['data']['display_name']}")

# 更新个人资料
updated_user = api.update_profile(
    display_name="新的显示名称",
    bio="更新后的个人简介"
)

# 关注用户
follow_result = api.follow_user('user_id_to_follow')
```

### JavaScript 示例

```javascript
class UserAPI {
    constructor(baseUrl, accessToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        };
    }

    async getCurrentUser() {
        const response = await fetch(`${this.baseUrl}/api/v1/users/me`, {
            headers: this.headers
        });
        return response.json();
    }

    async updateProfile(data) {
        const response = await fetch(`${this.baseUrl}/api/v1/users/me`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }

    async getUser(userId) {
        const response = await fetch(`${this.baseUrl}/api/v1/users/${userId}`, {
            headers: this.headers
        });
        return response.json();
    }

    async followUser(userId) {
        const response = await fetch(`${this.baseUrl}/api/v1/users/${userId}/follow`, {
            method: 'POST',
            headers: this.headers
        });
        return response.json();
    }

    async unfollowUser(userId) {
        const response = await fetch(`${this.baseUrl}/api/v1/users/${userId}/follow`, {
            method: 'DELETE',
            headers: this.headers
        });
        return response.json();
    }

    async uploadAvatar(file) {
        const formData = new FormData();
        formData.append('avatar', file);
        
        const response = await fetch(`${this.baseUrl}/api/v1/users/upload-avatar`, {
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
const api = new UserAPI('https://api.uplifted.com', 'your_access_token');

// 获取当前用户信息
api.getCurrentUser().then(user => {
    console.log(`当前用户: ${user.data.display_name}`);
});

// 更新个人资料
api.updateProfile({
    display_name: "新的显示名称",
    bio: "更新后的个人简介"
}).then(result => {
    console.log('资料更新成功:', result);
});
```

## 注意事项

1. **隐私设置**: 私密账户的信息只对关注者可见
2. **速率限制**: 关注/取消关注操作有速率限制，防止滥用
3. **头像上传**: 支持的格式为 JPEG、PNG、WebP，最大文件大小为 5MB
4. **数据验证**: 所有用户输入都会进行严格的验证和清理
5. **缓存**: 用户信息会被缓存以提高性能，更新后可能需要几分钟才能在所有地方生效