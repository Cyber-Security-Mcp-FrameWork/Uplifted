"""
标准化错误码体系
定义统一的错误码、错误消息和错误响应格式
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time


class ErrorCode(Enum):
    """标准化错误码"""
    
    # 成功响应 (0-999)
    SUCCESS = (0, "操作成功")
    
    # 客户端错误 (1000-1999)
    BAD_REQUEST = (1000, "请求参数错误")
    INVALID_JSON = (1001, "JSON格式错误")
    MISSING_PARAMETER = (1002, "缺少必需参数")
    INVALID_PARAMETER = (1003, "参数值无效")
    PARAMETER_TYPE_ERROR = (1004, "参数类型错误")
    PARAMETER_RANGE_ERROR = (1005, "参数值超出范围")
    
    # 认证错误 (2000-2099)
    AUTHENTICATION_REQUIRED = (2000, "需要身份认证")
    INVALID_CREDENTIALS = (2001, "认证信息无效")
    TOKEN_EXPIRED = (2002, "令牌已过期")
    TOKEN_INVALID = (2003, "令牌格式无效")
    API_KEY_INVALID = (2004, "API密钥无效")
    API_KEY_EXPIRED = (2005, "API密钥已过期")
    API_KEY_REVOKED = (2006, "API密钥已被撤销")
    
    # 授权错误 (2100-2199)
    PERMISSION_DENIED = (2100, "权限不足")
    RESOURCE_ACCESS_DENIED = (2101, "资源访问被拒绝")
    OPERATION_NOT_ALLOWED = (2102, "操作不被允许")
    INSUFFICIENT_PRIVILEGES = (2103, "权限级别不足")
    
    # 限流错误 (2200-2299)
    RATE_LIMIT_EXCEEDED = (2200, "请求频率超限")
    QUOTA_EXCEEDED = (2201, "配额已用完")
    CONCURRENT_LIMIT_EXCEEDED = (2202, "并发请求数超限")
    
    # 资源错误 (3000-3999)
    RESOURCE_NOT_FOUND = (3000, "资源不存在")
    RESOURCE_ALREADY_EXISTS = (3001, "资源已存在")
    RESOURCE_CONFLICT = (3002, "资源冲突")
    RESOURCE_LOCKED = (3003, "资源被锁定")
    RESOURCE_EXPIRED = (3004, "资源已过期")
    
    # 业务逻辑错误 (4000-4999)
    BUSINESS_RULE_VIOLATION = (4000, "违反业务规则")
    WORKFLOW_ERROR = (4001, "工作流错误")
    STATE_TRANSITION_ERROR = (4002, "状态转换错误")
    DEPENDENCY_ERROR = (4003, "依赖关系错误")
    
    # 工具相关错误 (5000-5099)
    TOOL_NOT_FOUND = (5000, "工具不存在")
    TOOL_EXECUTION_ERROR = (5001, "工具执行失败")
    TOOL_TIMEOUT = (5002, "工具执行超时")
    TOOL_PERMISSION_ERROR = (5003, "工具权限错误")
    TOOL_CONFIGURATION_ERROR = (5004, "工具配置错误")
    
    # 模型相关错误 (5100-5199)
    MODEL_NOT_FOUND = (5100, "模型不存在")
    MODEL_LOADING_ERROR = (5101, "模型加载失败")
    MODEL_INFERENCE_ERROR = (5102, "模型推理失败")
    MODEL_TIMEOUT = (5103, "模型响应超时")
    MODEL_QUOTA_EXCEEDED = (5104, "模型配额超限")
    
    # 代理相关错误 (5200-5299)
    AGENT_NOT_FOUND = (5200, "代理不存在")
    AGENT_CREATION_ERROR = (5201, "代理创建失败")
    AGENT_EXECUTION_ERROR = (5202, "代理执行失败")
    AGENT_TIMEOUT = (5203, "代理执行超时")
    AGENT_CONFIGURATION_ERROR = (5204, "代理配置错误")
    
    # 外部服务错误 (6000-6999)
    EXTERNAL_SERVICE_ERROR = (6000, "外部服务错误")
    EXTERNAL_SERVICE_TIMEOUT = (6001, "外部服务超时")
    EXTERNAL_SERVICE_UNAVAILABLE = (6002, "外部服务不可用")
    EXTERNAL_API_ERROR = (6003, "外部API错误")
    EXTERNAL_API_QUOTA_EXCEEDED = (6004, "外部API配额超限")
    
    # 系统错误 (7000-7999)
    INTERNAL_SERVER_ERROR = (7000, "内部服务器错误")
    DATABASE_ERROR = (7001, "数据库错误")
    CACHE_ERROR = (7002, "缓存错误")
    CONFIGURATION_ERROR = (7003, "配置错误")
    DEPENDENCY_INJECTION_ERROR = (7004, "依赖注入错误")
    
    # 网络错误 (8000-8999)
    NETWORK_ERROR = (8000, "网络错误")
    CONNECTION_TIMEOUT = (8001, "连接超时")
    CONNECTION_REFUSED = (8002, "连接被拒绝")
    DNS_RESOLUTION_ERROR = (8003, "DNS解析错误")
    
    # 文件系统错误 (9000-9999)
    FILE_NOT_FOUND = (9000, "文件不存在")
    FILE_ACCESS_ERROR = (9001, "文件访问错误")
    FILE_PERMISSION_ERROR = (9002, "文件权限错误")
    DISK_SPACE_ERROR = (9003, "磁盘空间不足")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
    
    @property
    def http_status(self) -> int:
        """根据错误码返回对应的HTTP状态码"""
        if self.code == 0:
            return 200
        elif 1000 <= self.code < 2000:
            return 400  # Bad Request
        elif 2000 <= self.code < 2100:
            return 401  # Unauthorized
        elif 2100 <= self.code < 2200:
            return 403  # Forbidden
        elif 2200 <= self.code < 2300:
            return 429  # Too Many Requests
        elif 3000 <= self.code < 4000:
            return 404  # Not Found
        elif 4000 <= self.code < 5000:
            return 422  # Unprocessable Entity
        elif 5000 <= self.code < 7000:
            return 500  # Internal Server Error
        elif 7000 <= self.code < 10000:
            return 500  # Internal Server Error
        else:
            return 500  # Default to Internal Server Error


@dataclass
class ErrorDetail:
    """错误详情"""
    field: Optional[str] = None
    message: str = ""
    code: Optional[str] = None


@dataclass
class ErrorResponse:
    """标准错误响应"""
    success: bool = False
    error_code: int = 0
    error_message: str = ""
    error_details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
    timestamp: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)  # 毫秒时间戳
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'success': self.success,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'timestamp': self.timestamp
        }
        
        if self.error_details:
            result['error_details'] = [
                {
                    'field': detail.field,
                    'message': detail.message,
                    'code': detail.code
                }
                for detail in self.error_details
            ]
        
        if self.request_id:
            result['request_id'] = self.request_id
        
        return result


class UpliftedError:
    """Uplifted错误工具类"""
    
    @staticmethod
    def create_response(error_code: ErrorCode, 
                       details: Optional[List[ErrorDetail]] = None,
                       request_id: Optional[str] = None) -> ErrorResponse:
        """创建错误响应"""
        return ErrorResponse(
            success=False,
            error_code=error_code.code,
            error_message=error_code.message,
            error_details=details,
            request_id=request_id
        )
    
    @staticmethod
    def create_validation_error(field: str, message: str, 
                              request_id: Optional[str] = None) -> ErrorResponse:
        """创建验证错误响应"""
        details = [ErrorDetail(field=field, message=message, code="VALIDATION_ERROR")]
        return UpliftedError.create_response(ErrorCode.INVALID_PARAMETER, details, request_id)
    
    @staticmethod
    def create_multiple_validation_errors(errors: List[tuple[str, str]], 
                                        request_id: Optional[str] = None) -> ErrorResponse:
        """创建多个验证错误响应"""
        details = [
            ErrorDetail(field=field, message=message, code="VALIDATION_ERROR")
            for field, message in errors
        ]
        return UpliftedError.create_response(ErrorCode.INVALID_PARAMETER, details, request_id)


def create_error_response(error_code: ErrorCode, 
                         details: Optional[List[ErrorDetail]] = None,
                         request_id: Optional[str] = None) -> tuple[Dict[str, Any], int]:
    """
    创建错误响应（包含HTTP状态码）
    
    Returns:
        (响应字典, HTTP状态码)
    """
    error_response = UpliftedError.create_response(error_code, details, request_id)
    return error_response.to_dict(), error_code.http_status


def create_success_response(data: Any = None, 
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


# 常用错误响应快捷方法
class CommonErrors:
    """常用错误响应"""
    
    @staticmethod
    def bad_request(message: str = None, request_id: str = None) -> tuple[Dict[str, Any], int]:
        error_code = ErrorCode.BAD_REQUEST
        if message:
            # 创建自定义消息的错误响应
            custom_response = ErrorResponse(
                success=False,
                error_code=error_code.code,
                error_message=message,
                request_id=request_id
            )
            return custom_response.to_dict(), error_code.http_status
        return create_error_response(error_code, request_id=request_id)
    
    @staticmethod
    def unauthorized(request_id: str = None) -> tuple[Dict[str, Any], int]:
        return create_error_response(ErrorCode.AUTHENTICATION_REQUIRED, request_id=request_id)
    
    @staticmethod
    def forbidden(request_id: str = None) -> tuple[Dict[str, Any], int]:
        return create_error_response(ErrorCode.PERMISSION_DENIED, request_id=request_id)
    
    @staticmethod
    def not_found(resource: str = "资源", request_id: str = None) -> tuple[Dict[str, Any], int]:
        error_response = ErrorResponse(
            success=False,
            error_code=ErrorCode.RESOURCE_NOT_FOUND.code,
            error_message=f"{resource}不存在",
            request_id=request_id
        )
        return error_response.to_dict(), ErrorCode.RESOURCE_NOT_FOUND.http_status
    
    @staticmethod
    def rate_limit_exceeded(request_id: str = None) -> tuple[Dict[str, Any], int]:
        return create_error_response(ErrorCode.RATE_LIMIT_EXCEEDED, request_id=request_id)
    
    @staticmethod
    def internal_server_error(request_id: str = None) -> tuple[Dict[str, Any], int]:
        return create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, request_id=request_id)
    
    @staticmethod
    def validation_error(field: str, message: str, request_id: str = None) -> tuple[Dict[str, Any], int]:
        error_response = UpliftedError.create_validation_error(field, message, request_id)
        return error_response.to_dict(), ErrorCode.INVALID_PARAMETER.http_status