# 认证 API

认证系统提供用户注册、登录、令牌管理和密码重置等功能。

## 端点概览

| 方法 | 端点 | 描述 | 认证 |
|------|------|------|------|
| POST | `/auth/register` | 用户注册 | 否 |
| POST | `/auth/login` | 用户登录 | 否 |
| POST | `/auth/logout` | 用户登出 | 是 |
| POST | `/auth/refresh` | 刷新令牌 | 否 |
| POST | `/auth/forgot-password` | 忘记密码 | 否 |
| POST | `/auth/reset-password` | 重置密码 | 否 |
| POST | `/auth/change-password` | 修改密码 | 是 |
| GET | `/auth/me` | 获取当前用户 | 是 |

## 用户注册

创建新用户账户。

### 请求

```http
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "bio": "Hello, I'm John!"
  }
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `username` | string | 是 | 用户名（3-30字符，字母数字和下划线） |
| `email` | string | 是 | 邮箱地址 |
| `password` | string | 是 | 密码（至少8字符，包含大小写字母和数字） |
| `profile` | object | 否 | 用户资料 |
| `profile.first_name` | string | 否 | 名字 |
| `profile.last_name` | string | 否 | 姓氏 |
| `profile.bio` | string | 否 | 个人简介 |

### 响应

**成功响应 (201 Created)**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "johndoe",
    "email": "john@example.com",
    "profile": {
      "first_name": "John",
      "last_name": "Doe",
      "bio": "Hello, I'm John!",
      "avatar_url": null
    },
    "created_at": "2024-01-01T12:00:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

**错误响应 (400 Bad Request)**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "username",
        "message": "用户名已存在"
      }
    ]
  }
}
```

## 用户登录

使用用户名/邮箱和密码进行身份验证。

### 请求

```http
POST /auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `username` | string | 是 | 用户名或邮箱地址 |
| `password` | string | 是 | 密码 |
| `remember_me` | boolean | 否 | 是否记住登录状态（默认false） |

### 响应

**成功响应 (200 OK)**:
```json
{
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "johndoe",
    "email": "john@example.com",
    "profile": {
      "first_name": "John",
      "last_name": "Doe",
      "bio": "Hello, I'm John!",
      "avatar_url": "https://example.com/avatars/john.jpg"
    }
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

**错误响应 (401 Unauthorized)**:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "用户名或密码错误"
  }
}
```

## 用户登出

使当前访问令牌失效。

### 请求

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

### 响应

**成功响应 (200 OK)**:
```json
{
  "message": "登出成功"
}
```

## 刷新令牌

使用刷新令牌获取新的访问令牌。

### 请求

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `refresh_token` | string | 是 | 有效的刷新令牌 |

### 响应

**成功响应 (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**错误响应 (401 Unauthorized)**:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "刷新令牌无效或已过期"
  }
}
```

## 忘记密码

发送密码重置邮件。

### 请求

```http
POST /auth/forgot-password
Content-Type: application/json

{
  "email": "john@example.com"
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `email` | string | 是 | 注册邮箱地址 |

### 响应

**成功响应 (200 OK)**:
```json
{
  "message": "密码重置邮件已发送，请检查您的邮箱"
}
```

## 重置密码

使用重置令牌设置新密码。

### 请求

```http
POST /auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "password": "NewSecurePass123!"
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `token` | string | 是 | 邮件中的重置令牌 |
| `password` | string | 是 | 新密码 |

### 响应

**成功响应 (200 OK)**:
```json
{
  "message": "密码重置成功"
}
```

**错误响应 (400 Bad Request)**:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "重置令牌无效或已过期"
  }
}
```

## 修改密码

修改当前用户的密码。

### 请求

```http
POST /auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePass123!"
}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `current_password` | string | 是 | 当前密码 |
| `new_password` | string | 是 | 新密码 |

### 响应

**成功响应 (200 OK)**:
```json
{
  "message": "密码修改成功"
}
```

**错误响应 (400 Bad Request)**:
```json
{
  "error": {
    "code": "INVALID_PASSWORD",
    "message": "当前密码错误"
  }
}
```

## 获取当前用户

获取当前认证用户的详细信息。

### 请求

```http
GET /auth/me
Authorization: Bearer <access_token>
```

### 响应

**成功响应 (200 OK)**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "johndoe",
  "email": "john@example.com",
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "bio": "Hello, I'm John!",
    "avatar_url": "https://example.com/avatars/john.jpg",
    "location": "New York, USA",
    "website": "https://johndoe.com"
  },
  "stats": {
    "posts_count": 42,
    "followers_count": 128,
    "following_count": 95
  },
  "settings": {
    "email_notifications": true,
    "push_notifications": false,
    "privacy_level": "public"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## 错误代码

| 错误代码 | 描述 |
|----------|------|
| `VALIDATION_ERROR` | 请求参数验证失败 |
| `INVALID_CREDENTIALS` | 用户名或密码错误 |
| `INVALID_TOKEN` | 令牌无效或已过期 |
| `INVALID_PASSWORD` | 密码错误 |
| `USER_EXISTS` | 用户已存在 |
| `USER_NOT_FOUND` | 用户不存在 |
| `EMAIL_EXISTS` | 邮箱已被使用 |
| `WEAK_PASSWORD` | 密码强度不足 |
| `RATE_LIMITED` | 请求频率超限 |

## 安全注意事项

1. **密码要求**: 至少8个字符，包含大小写字母、数字和特殊字符
2. **令牌安全**: 访问令牌应安全存储，不要在URL中传递
3. **HTTPS**: 所有认证请求必须使用HTTPS
4. **速率限制**: 登录尝试有速率限制，防止暴力破解
5. **会话管理**: 定期刷新令牌，及时登出

## 示例代码

### Python 示例

```python
import requests

class UpliftedAuth:
    def __init__(self, base_url):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
    
    def register(self, username, email, password, profile=None):
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        if profile:
            data["profile"] = profile
        
        response = requests.post(f"{self.base_url}/auth/register", json=data)
        if response.status_code == 201:
            result = response.json()
            self.access_token = result["tokens"]["access_token"]
            self.refresh_token = result["tokens"]["refresh_token"]
            return result["user"]
        else:
            raise Exception(f"Registration failed: {response.json()}")
    
    def login(self, username, password):
        data = {"username": username, "password": password}
        response = requests.post(f"{self.base_url}/auth/login", json=data)
        
        if response.status_code == 200:
            result = response.json()
            self.access_token = result["tokens"]["access_token"]
            self.refresh_token = result["tokens"]["refresh_token"]
            return result["user"]
        else:
            raise Exception(f"Login failed: {response.json()}")
    
    def logout(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.post(f"{self.base_url}/auth/logout", headers=headers)
        
        if response.status_code == 200:
            self.access_token = None
            self.refresh_token = None
        else:
            raise Exception(f"Logout failed: {response.json()}")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

# 使用示例
auth = UpliftedAuth("https://api.uplifted.com/v1")

# 注册
user = auth.register(
    username="johndoe",
    email="john@example.com",
    password="SecurePass123!",
    profile={"first_name": "John", "last_name": "Doe"}
)

# 登录
user = auth.login("johndoe", "SecurePass123!")

# 使用认证头进行其他API调用
headers = auth.get_headers()
```

### JavaScript 示例

```javascript
class UpliftedAuth {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }
    
    async register(username, email, password, profile = null) {
        const data = { username, email, password };
        if (profile) data.profile = profile;
        
        const response = await fetch(`${this.baseUrl}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            this.setTokens(result.tokens);
            return result.user;
        } else {
            throw new Error(`Registration failed: ${await response.text()}`);
        }
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const result = await response.json();
            this.setTokens(result.tokens);
            return result.user;
        } else {
            throw new Error(`Login failed: ${await response.text()}`);
        }
    }
    
    async logout() {
        const response = await fetch(`${this.baseUrl}/auth/logout`, {
            method: 'POST',
            headers: this.getHeaders()
        });
        
        if (response.ok) {
            this.clearTokens();
        } else {
            throw new Error(`Logout failed: ${await response.text()}`);
        }
    }
    
    setTokens(tokens) {
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        localStorage.setItem('access_token', this.accessToken);
        localStorage.setItem('refresh_token', this.refreshToken);
    }
    
    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
    
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.accessToken}`
        };
    }
}

// 使用示例
const auth = new UpliftedAuth('https://api.uplifted.com/v1');

// 注册
try {
    const user = await auth.register('johndoe', 'john@example.com', 'SecurePass123!');
    console.log('Registration successful:', user);
} catch (error) {
    console.error('Registration failed:', error.message);
}
```