"""
标准响应格式模块
定义统一的API响应格式和数据模型
"""

from typing import Any, Optional, Dict, List, Generic, TypeVar
from dataclasses import dataclass
from pydantic import BaseModel, Field
import time

T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(description="操作是否成功")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="时间戳（毫秒）")
    request_id: Optional[str] = Field(None, description="请求ID")


class SuccessResponse(BaseResponse, Generic[T]):
    """成功响应模型"""
    success: bool = Field(True, description="操作成功")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {},
                "timestamp": 1640995200000,
                "request_id": "req_123456789"
            }
        }


class ErrorDetail(BaseModel):
    """错误详情模型"""
    field: Optional[str] = Field(None, description="错误字段")
    message: str = Field(description="错误消息")
    code: Optional[str] = Field(None, description="错误代码")


class ErrorResponseModel(BaseResponse):
    """错误响应模型"""
    success: bool = Field(False, description="操作失败")
    error_code: int = Field(description="错误码")
    error_message: str = Field(description="错误消息")
    error_details: Optional[List[ErrorDetail]] = Field(None, description="错误详情列表")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": 1000,
                "error_message": "请求参数错误",
                "error_details": [
                    {
                        "field": "email",
                        "message": "邮箱格式不正确",
                        "code": "INVALID_EMAIL"
                    }
                ],
                "timestamp": 1640995200000,
                "request_id": "req_123456789"
            }
        }


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total: int = Field(description="总记录数")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")


class PaginatedResponse(SuccessResponse[List[T]]):
    """分页响应模型"""
    data: List[T] = Field(description="数据列表")
    pagination: PaginationMeta = Field(description="分页信息")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "获取数据成功",
                "data": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                },
                "timestamp": 1640995200000,
                "request_id": "req_123456789"
            }
        }


@dataclass
class StandardResponse:
    """标准响应工具类"""
    
    @staticmethod
    def success(data: Any = None, 
               message: str = "操作成功",
               request_id: Optional[str] = None) -> Dict[str, Any]:
        """创建成功响应"""
        response = {
            'success': True,
            'message': message,
            'timestamp': int(time.time() * 1000)
        }
        
        if data is not None:
            response['data'] = data
        
        if request_id:
            response['request_id'] = request_id
        
        return response
    
    @staticmethod
    def paginated_success(data: List[Any],
                         page: int,
                         page_size: int,
                         total: int,
                         message: str = "获取数据成功",
                         request_id: Optional[str] = None) -> Dict[str, Any]:
        """创建分页成功响应"""
        total_pages = (total + page_size - 1) // page_size
        
        pagination = {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        response = {
            'success': True,
            'message': message,
            'data': data,
            'pagination': pagination,
            'timestamp': int(time.time() * 1000)
        }
        
        if request_id:
            response['request_id'] = request_id
        
        return response
    
    @staticmethod
    def created(data: Any = None,
               message: str = "创建成功",
               request_id: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """创建资源成功响应（HTTP 201）"""
        response = StandardResponse.success(data, message, request_id)
        return response, 201
    
    @staticmethod
    def accepted(data: Any = None,
                message: str = "请求已接受",
                request_id: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """请求已接受响应（HTTP 202）"""
        response = StandardResponse.success(data, message, request_id)
        return response, 202
    
    @staticmethod
    def no_content(request_id: Optional[str] = None) -> tuple[Dict[str, Any], int]:
        """无内容响应（HTTP 204）"""
        response = {
            'success': True,
            'message': "操作成功",
            'timestamp': int(time.time() * 1000)
        }
        
        if request_id:
            response['request_id'] = request_id
        
        return response, 204


class ResponseBuilder:
    """响应构建器"""
    
    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id
    
    def success(self, data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """构建成功响应"""
        return StandardResponse.success(data, message, self.request_id)
    
    def created(self, data: Any = None, message: str = "创建成功") -> tuple[Dict[str, Any], int]:
        """构建创建成功响应"""
        return StandardResponse.created(data, message, self.request_id)
    
    def accepted(self, data: Any = None, message: str = "请求已接受") -> tuple[Dict[str, Any], int]:
        """构建请求已接受响应"""
        return StandardResponse.accepted(data, message, self.request_id)
    
    def no_content(self) -> tuple[Dict[str, Any], int]:
        """构建无内容响应"""
        return StandardResponse.no_content(self.request_id)
    
    def paginated(self, data: List[Any], page: int, page_size: int, total: int,
                 message: str = "获取数据成功") -> Dict[str, Any]:
        """构建分页响应"""
        return StandardResponse.paginated_success(data, page, page_size, total, message, self.request_id)


# 常用响应模型
class HealthCheckResponse(SuccessResponse[Dict[str, Any]]):
    """健康检查响应"""
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "服务运行正常",
                "data": {
                    "status": "healthy",
                    "version": "1.0.0",
                    "uptime": 3600,
                    "dependencies": {
                        "database": "healthy",
                        "cache": "healthy",
                        "external_api": "healthy"
                    }
                },
                "timestamp": 1640995200000
            }
        }


class MetricsResponse(SuccessResponse[Dict[str, Any]]):
    """指标响应"""
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "获取指标成功",
                "data": {
                    "requests_total": 1000,
                    "requests_per_second": 10.5,
                    "error_rate": 0.01,
                    "response_time_avg": 150.5,
                    "active_connections": 25
                },
                "timestamp": 1640995200000
            }
        }


class TokenResponse(SuccessResponse[Dict[str, str]]):
    """令牌响应"""
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "令牌生成成功",
                "data": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 3600
                },
                "timestamp": 1640995200000
            }
        }