"""
通用模块
提供错误码、响应格式、异常处理等通用功能
"""

from .errors import ErrorCode, ErrorResponse, UpliftedError, create_error_response
from .responses import StandardResponse, SuccessResponse, ErrorResponseModel
from .exceptions import (
    UpliftedBaseException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    InternalServerError,
    ExternalServiceError
)

__all__ = [
    'ErrorCode',
    'ErrorResponse', 
    'UpliftedError',
    'create_error_response',
    'StandardResponse',
    'SuccessResponse',
    'ErrorResponseModel',
    'UpliftedBaseException',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'ResourceNotFoundError',
    'InternalServerError',
    'ExternalServiceError'
]