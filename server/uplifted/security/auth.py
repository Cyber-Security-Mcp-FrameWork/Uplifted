"""
认证授权模块
提供API密钥管理、JWT令牌验证等功能
"""

import hashlib
import hmac
import time
import secrets
import jwt
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..core.interfaces import IConfiguration
from ..storage.configuration import ClientConfiguration


@dataclass
class APIKey:
    """API密钥数据类"""
    key_id: str
    key_hash: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_used: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    user_id: Optional[str] = None
    permissions: List[str] = None
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self):
        self._key_prefix = "api_key_"
        self._secret_key = self._get_or_create_secret()
    
    def _get_or_create_secret(self) -> str:
        """获取或创建密钥签名秘钥"""
        secret = ClientConfiguration.get("api_secret_key")
        if not secret:
            secret = secrets.token_urlsafe(32)
            ClientConfiguration.set("api_secret_key", secret)
        return secret
    
    def create_api_key(self, name: str, permissions: List[str], 
                      expires_days: Optional[int] = None) -> tuple[str, APIKey]:
        """
        创建新的API密钥
        
        Args:
            name: 密钥名称
            permissions: 权限列表
            expires_days: 过期天数，None表示永不过期
            
        Returns:
            (原始密钥, API密钥对象)
        """
        # 生成密钥ID和原始密钥
        key_id = secrets.token_urlsafe(16)
        raw_key = f"uplifted_{secrets.token_urlsafe(32)}"
        
        # 计算密钥哈希
        key_hash = self._hash_key(raw_key)
        
        # 计算过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # 创建API密钥对象
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        # 保存到配置
        self._save_api_key(api_key)
        
        return raw_key, api_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """验证API密钥"""
        if not raw_key or not raw_key.startswith("uplifted_"):
            return None
        
        key_hash = self._hash_key(raw_key)
        
        # 查找匹配的密钥
        all_keys = self._get_all_api_keys()
        for api_key in all_keys:
            if (api_key.key_hash == key_hash and 
                api_key.is_active and
                (not api_key.expires_at or api_key.expires_at > datetime.now())):
                
                # 更新使用统计
                api_key.last_used = datetime.now()
                api_key.usage_count += 1
                self._save_api_key(api_key)
                
                return api_key
        
        return None
    
    def revoke_api_key(self, key_id: str) -> bool:
        """撤销API密钥"""
        api_key = self._get_api_key(key_id)
        if api_key:
            api_key.is_active = False
            self._save_api_key(api_key)
            return True
        return False
    
    def list_api_keys(self) -> List[APIKey]:
        """列出所有API密钥（不包含哈希值）"""
        return self._get_all_api_keys()
    
    def _hash_key(self, raw_key: str) -> str:
        """计算密钥哈希"""
        return hmac.new(
            self._secret_key.encode(),
            raw_key.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _save_api_key(self, api_key: APIKey) -> None:
        """保存API密钥"""
        key_data = {
            'key_id': api_key.key_id,
            'key_hash': api_key.key_hash,
            'name': api_key.name,
            'permissions': api_key.permissions,
            'created_at': api_key.created_at.isoformat(),
            'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None,
            'is_active': api_key.is_active,
            'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
            'usage_count': api_key.usage_count
        }
        ClientConfiguration.set(f"{self._key_prefix}{api_key.key_id}", key_data)
    
    def _get_api_key(self, key_id: str) -> Optional[APIKey]:
        """获取单个API密钥"""
        key_data = ClientConfiguration.get(f"{self._key_prefix}{key_id}")
        if key_data:
            return self._deserialize_api_key(key_data)
        return None
    
    def _get_all_api_keys(self) -> List[APIKey]:
        """获取所有API密钥"""
        all_config = ClientConfiguration.export_all()
        api_keys = []
        
        for key, value in all_config.items():
            if key.startswith(self._key_prefix):
                api_key = self._deserialize_api_key(value)
                if api_key:
                    api_keys.append(api_key)
        
        return api_keys
    
    def _deserialize_api_key(self, data: Dict[str, Any]) -> Optional[APIKey]:
        """反序列化API密钥"""
        try:
            return APIKey(
                key_id=data['key_id'],
                key_hash=data['key_hash'],
                name=data['name'],
                permissions=data['permissions'],
                created_at=datetime.fromisoformat(data['created_at']),
                expires_at=datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None,
                is_active=data['is_active'],
                last_used=datetime.fromisoformat(data['last_used']) if data['last_used'] else None,
                usage_count=data['usage_count']
            )
        except (KeyError, ValueError):
            return None


class TokenValidator:
    """JWT令牌验证器"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self._secret_key = secret_key or self._get_jwt_secret()
    
    def _get_jwt_secret(self) -> str:
        """获取JWT密钥"""
        secret = ClientConfiguration.get("jwt_secret_key")
        if not secret:
            secret = secrets.token_urlsafe(32)
            ClientConfiguration.set("jwt_secret_key", secret)
        return secret
    
    def create_token(self, user_id: str, permissions: List[str], 
                    expires_hours: int = 24) -> str:
        """创建JWT令牌"""
        payload = {
            'user_id': user_id,
            'permissions': permissions,
            'iat': int(time.time()),
            'exp': int(time.time()) + (expires_hours * 3600)
        }
        
        return jwt.encode(payload, self._secret_key, algorithm='HS256')
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.api_key_manager = APIKeyManager()
        self.token_validator = TokenValidator()
    
    def authenticate_request(self, headers: Dict[str, str]) -> AuthResult:
        """
        认证请求
        支持API密钥和JWT令牌两种方式
        """
        # 尝试API密钥认证
        api_key = headers.get('X-API-Key') or headers.get('Authorization', '').replace('Bearer ', '')
        
        if api_key and api_key.startswith('uplifted_'):
            return self._authenticate_api_key(api_key)
        
        # 尝试JWT令牌认证
        auth_header = headers.get('Authorization', '')
        if auth_header.startswith('Bearer ') and not auth_header.replace('Bearer ', '').startswith('uplifted_'):
            token = auth_header.replace('Bearer ', '')
            return self._authenticate_jwt_token(token)
        
        return AuthResult(
            success=False,
            error_message="未提供有效的认证信息"
        )
    
    def _authenticate_api_key(self, api_key: str) -> AuthResult:
        """API密钥认证"""
        key_info = self.api_key_manager.validate_api_key(api_key)
        
        if key_info:
            return AuthResult(
                success=True,
                user_id=key_info.key_id,
                permissions=key_info.permissions
            )
        else:
            return AuthResult(
                success=False,
                error_message="无效的API密钥"
            )
    
    def _authenticate_jwt_token(self, token: str) -> AuthResult:
        """JWT令牌认证"""
        payload = self.token_validator.validate_token(token)
        
        if payload:
            return AuthResult(
                success=True,
                user_id=payload.get('user_id'),
                permissions=payload.get('permissions', [])
            )
        else:
            return AuthResult(
                success=False,
                error_message="无效或过期的令牌"
            )
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """检查权限"""
        return required_permission in user_permissions or 'admin' in user_permissions