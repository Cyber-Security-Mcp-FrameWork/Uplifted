"""
安全中间件模块
提供认证、授权、限流等中间件功能
"""

import time
import json
from typing import Callable, Dict, Any, Optional, List
from functools import wraps
from flask import request, jsonify, g
from .auth import AuthManager, AuthResult
from .rate_limiter import RateLimiter, RateLimitConfig, IPRateLimiter, UserRateLimiter
from ..core.interfaces import ILogger


class SecurityMiddleware:
    """安全中间件基类"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        self.logger = logger
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """记录安全事件"""
        if self.logger:
            self.logger.warning(f"Security Event: {event_type}", extra=details)


class AuthMiddleware(SecurityMiddleware):
    """认证中间件"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None, logger: Optional[ILogger] = None):
        super().__init__(logger)
        self.auth_manager = auth_manager or AuthManager()
        self.exempt_paths = {'/health', '/metrics', '/docs'}
    
    def require_auth(self, permissions: Optional[List[str]] = None):
        """
        认证装饰器
        
        Args:
            permissions: 所需权限列表
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 检查是否为豁免路径
                if request.path in self.exempt_paths:
                    return f(*args, **kwargs)
                
                # 执行认证
                auth_result = self.auth_manager.authenticate_request(dict(request.headers))
                
                if not auth_result.success:
                    self.log_security_event('auth_failed', {
                        'ip': request.remote_addr,
                        'path': request.path,
                        'error': auth_result.error_message
                    })
                    
                    return jsonify({
                        'error': 'Authentication failed',
                        'message': auth_result.error_message
                    }), 401
                
                # 检查权限
                if permissions:
                    user_permissions = auth_result.permissions or []
                    for required_permission in permissions:
                        if not self.auth_manager.check_permission(user_permissions, required_permission):
                            self.log_security_event('permission_denied', {
                                'user_id': auth_result.user_id,
                                'ip': request.remote_addr,
                                'path': request.path,
                                'required_permission': required_permission,
                                'user_permissions': user_permissions
                            })
                            
                            return jsonify({
                                'error': 'Permission denied',
                                'message': f'Required permission: {required_permission}'
                            }), 403
                
                # 将认证信息存储到请求上下文
                g.auth_result = auth_result
                g.user_id = auth_result.user_id
                g.user_permissions = auth_result.permissions or []
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def add_exempt_path(self, path: str) -> None:
        """添加豁免路径"""
        self.exempt_paths.add(path)
    
    def remove_exempt_path(self, path: str) -> None:
        """移除豁免路径"""
        self.exempt_paths.discard(path)


class RateLimitMiddleware(SecurityMiddleware):
    """限流中间件"""
    
    def __init__(self, 
                 ip_config: Optional[RateLimitConfig] = None,
                 user_config: Optional[RateLimitConfig] = None,
                 logger: Optional[ILogger] = None):
        super().__init__(logger)
        
        # 默认配置
        default_ip_config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=2000,
            requests_per_day=20000
        )
        
        default_user_config = RateLimitConfig(
            requests_per_minute=200,
            requests_per_hour=5000,
            requests_per_day=50000
        )
        
        self.ip_limiter = IPRateLimiter(ip_config or default_ip_config)
        self.user_limiter = UserRateLimiter(user_config or default_user_config)
        self.exempt_paths = {'/health', '/metrics'}
    
    def rate_limit(self, 
                  per_ip: bool = True,
                  per_user: bool = True,
                  endpoint_specific: bool = False):
        """
        限流装饰器
        
        Args:
            per_ip: 是否启用IP限流
            per_user: 是否启用用户限流
            endpoint_specific: 是否按端点独立限流
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 检查是否为豁免路径
                if request.path in self.exempt_paths:
                    return f(*args, **kwargs)
                
                endpoint = request.endpoint if endpoint_specific else None
                ip_address = request.remote_addr
                
                # IP限流检查
                if per_ip:
                    ip_allowed, ip_remaining = self.ip_limiter.is_allowed(ip_address, endpoint)
                    if not ip_allowed:
                        self.log_security_event('ip_rate_limit_exceeded', {
                            'ip': ip_address,
                            'path': request.path,
                            'endpoint': endpoint,
                            'remaining': ip_remaining
                        })
                        
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'message': 'Too many requests from this IP address',
                            'remaining': ip_remaining
                        }), 429
                
                # 用户限流检查
                if per_user and hasattr(g, 'user_id') and g.user_id:
                    user_allowed, user_remaining = self.user_limiter.is_allowed(g.user_id, endpoint)
                    if not user_allowed:
                        self.log_security_event('user_rate_limit_exceeded', {
                            'user_id': g.user_id,
                            'ip': ip_address,
                            'path': request.path,
                            'endpoint': endpoint,
                            'remaining': user_remaining
                        })
                        
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'message': 'Too many requests from this user',
                            'remaining': user_remaining
                        }), 429
                
                # 添加限流信息到响应头
                response = f(*args, **kwargs)
                
                if hasattr(response, 'headers'):
                    if per_ip:
                        ip_status = self.ip_limiter.get_status(ip_address, endpoint)
                        response.headers['X-RateLimit-IP-Remaining-Minute'] = str(ip_status['minute'])
                        response.headers['X-RateLimit-IP-Remaining-Hour'] = str(ip_status['hour'])
                        response.headers['X-RateLimit-IP-Remaining-Day'] = str(ip_status['day'])
                    
                    if per_user and hasattr(g, 'user_id') and g.user_id:
                        user_status = self.user_limiter.get_status(g.user_id, endpoint)
                        response.headers['X-RateLimit-User-Remaining-Minute'] = str(user_status['minute'])
                        response.headers['X-RateLimit-User-Remaining-Hour'] = str(user_status['hour'])
                        response.headers['X-RateLimit-User-Remaining-Day'] = str(user_status['day'])
                
                return response
            
            return decorated_function
        return decorator
    
    def add_exempt_path(self, path: str) -> None:
        """添加豁免路径"""
        self.exempt_paths.add(path)


class SecurityHeadersMiddleware(SecurityMiddleware):
    """安全头中间件"""
    
    def __init__(self, logger: Optional[ILogger] = None):
        super().__init__(logger)
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    def add_security_headers(self, f: Callable) -> Callable:
        """添加安全头装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                for header, value in self.security_headers.items():
                    response.headers[header] = value
            
            return response
        
        return decorated_function
    
    def update_header(self, header: str, value: str) -> None:
        """更新安全头"""
        self.security_headers[header] = value
    
    def remove_header(self, header: str) -> None:
        """移除安全头"""
        self.security_headers.pop(header, None)


class RequestLoggingMiddleware(SecurityMiddleware):
    """请求日志中间件"""
    
    def __init__(self, logger: Optional[ILogger] = None, log_body: bool = False):
        super().__init__(logger)
        self.log_body = log_body
        self.sensitive_headers = {'authorization', 'x-api-key', 'cookie'}
    
    def log_requests(self, f: Callable) -> Callable:
        """请求日志装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # 记录请求信息
            request_data = {
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'user_id': getattr(g, 'user_id', None)
            }
            
            # 记录请求头（过滤敏感信息）
            headers = {}
            for key, value in request.headers:
                if key.lower() not in self.sensitive_headers:
                    headers[key] = value
                else:
                    headers[key] = '[REDACTED]'
            request_data['headers'] = headers
            
            # 记录请求体（如果启用）
            if self.log_body and request.is_json:
                try:
                    request_data['body'] = request.get_json()
                except Exception:
                    request_data['body'] = '[INVALID_JSON]'
            
            if self.logger:
                self.logger.info('Request started', extra=request_data)
            
            try:
                # 执行请求
                response = f(*args, **kwargs)
                
                # 记录响应信息
                end_time = time.time()
                response_data = {
                    **request_data,
                    'status_code': getattr(response, 'status_code', 200),
                    'duration_ms': round((end_time - start_time) * 1000, 2)
                }
                
                if self.logger:
                    self.logger.info('Request completed', extra=response_data)
                
                return response
                
            except Exception as e:
                # 记录错误信息
                end_time = time.time()
                error_data = {
                    **request_data,
                    'error': str(e),
                    'duration_ms': round((end_time - start_time) * 1000, 2)
                }
                
                if self.logger:
                    self.logger.error('Request failed', extra=error_data)
                
                raise
        
        return decorated_function