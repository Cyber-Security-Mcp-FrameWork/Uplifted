"""
标准化异常体系
定义统一的异常类和异常处理机制
"""

from typing import Optional, List, Dict, Any
from .errors import ErrorCode, ErrorDetail


class UpliftedBaseException(Exception):
    """Uplifted基础异常类"""
    
    def __init__(self, 
                 error_code: ErrorCode,
                 message: Optional[str] = None,
                 details: Optional[List[ErrorDetail]] = None,
                 cause: Optional[Exception] = None):
        self.error_code = error_code
        self.message = message or error_code.message
        self.details = details or []
        self.cause = cause
        
        super().__init__(self.message)
    
    @property
    def http_status(self) -> int:
        """获取HTTP状态码"""
        return self.error_code.http_status
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'error_code': self.error_code.code,
            'error_message': self.message,
        }
        
        if self.details:
            result['error_details'] = [
                {
                    'field': detail.field,
                    'message': detail.message,
                    'code': detail.code
                }
                for detail in self.details
            ]
        
        return result


class ValidationError(UpliftedBaseException):
    """验证错误"""
    
    def __init__(self, 
                 message: str = "验证失败",
                 field: Optional[str] = None,
                 details: Optional[List[ErrorDetail]] = None):
        
        if field and not details:
            details = [ErrorDetail(field=field, message=message, code="VALIDATION_ERROR")]
        
        super().__init__(
            error_code=ErrorCode.INVALID_PARAMETER,
            message=message,
            details=details
        )
    
    @classmethod
    def from_field_errors(cls, field_errors: List[tuple[str, str]]) -> 'ValidationError':
        """从字段错误列表创建验证错误"""
        details = [
            ErrorDetail(field=field, message=message, code="VALIDATION_ERROR")
            for field, message in field_errors
        ]
        
        return cls(
            message="请求参数验证失败",
            details=details
        )


class AuthenticationError(UpliftedBaseException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", error_code: ErrorCode = ErrorCode.AUTHENTICATION_REQUIRED):
        super().__init__(error_code=error_code, message=message)


class AuthorizationError(UpliftedBaseException):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足", required_permission: Optional[str] = None):
        details = []
        if required_permission:
            details.append(ErrorDetail(
                field="permission",
                message=f"需要权限: {required_permission}",
                code="PERMISSION_REQUIRED"
            ))
        
        super().__init__(
            error_code=ErrorCode.PERMISSION_DENIED,
            message=message,
            details=details
        )


class RateLimitError(UpliftedBaseException):
    """限流错误"""
    
    def __init__(self, 
                 message: str = "请求频率超限",
                 retry_after: Optional[int] = None,
                 limit_type: Optional[str] = None):
        details = []
        
        if retry_after:
            details.append(ErrorDetail(
                field="retry_after",
                message=f"请在 {retry_after} 秒后重试",
                code="RETRY_AFTER"
            ))
        
        if limit_type:
            details.append(ErrorDetail(
                field="limit_type",
                message=f"限制类型: {limit_type}",
                code="LIMIT_TYPE"
            ))
        
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details
        )


class ResourceNotFoundError(UpliftedBaseException):
    """资源不存在错误"""
    
    def __init__(self, resource_type: str = "资源", resource_id: Optional[str] = None):
        message = f"{resource_type}不存在"
        details = []
        
        if resource_id:
            message = f"{resource_type} (ID: {resource_id}) 不存在"
            details.append(ErrorDetail(
                field="resource_id",
                message=resource_id,
                code="RESOURCE_ID"
            ))
        
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            details=details
        )


class ResourceConflictError(UpliftedBaseException):
    """资源冲突错误"""
    
    def __init__(self, message: str = "资源冲突", conflicting_field: Optional[str] = None):
        details = []
        
        if conflicting_field:
            details.append(ErrorDetail(
                field=conflicting_field,
                message="该值已存在",
                code="DUPLICATE_VALUE"
            ))
        
        super().__init__(
            error_code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            details=details
        )


class BusinessRuleViolationError(UpliftedBaseException):
    """业务规则违反错误"""
    
    def __init__(self, message: str = "违反业务规则", rule_name: Optional[str] = None):
        details = []
        
        if rule_name:
            details.append(ErrorDetail(
                field="rule",
                message=rule_name,
                code="BUSINESS_RULE"
            ))
        
        super().__init__(
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            message=message,
            details=details
        )


class ToolError(UpliftedBaseException):
    """工具相关错误"""
    
    def __init__(self, 
                 message: str = "工具执行失败",
                 tool_name: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.TOOL_EXECUTION_ERROR):
        details = []
        
        if tool_name:
            details.append(ErrorDetail(
                field="tool_name",
                message=tool_name,
                code="TOOL_NAME"
            ))
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details
        )


class ModelError(UpliftedBaseException):
    """模型相关错误"""
    
    def __init__(self, 
                 message: str = "模型执行失败",
                 model_name: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.MODEL_INFERENCE_ERROR):
        details = []
        
        if model_name:
            details.append(ErrorDetail(
                field="model_name",
                message=model_name,
                code="MODEL_NAME"
            ))
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details
        )


class AgentError(UpliftedBaseException):
    """代理相关错误"""
    
    def __init__(self, 
                 message: str = "代理执行失败",
                 agent_id: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.AGENT_EXECUTION_ERROR):
        details = []
        
        if agent_id:
            details.append(ErrorDetail(
                field="agent_id",
                message=agent_id,
                code="AGENT_ID"
            ))
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details
        )


class ExternalServiceError(UpliftedBaseException):
    """外部服务错误"""
    
    def __init__(self, 
                 message: str = "外部服务错误",
                 service_name: Optional[str] = None,
                 status_code: Optional[int] = None,
                 error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR):
        details = []
        
        if service_name:
            details.append(ErrorDetail(
                field="service_name",
                message=service_name,
                code="SERVICE_NAME"
            ))
        
        if status_code:
            details.append(ErrorDetail(
                field="status_code",
                message=str(status_code),
                code="HTTP_STATUS"
            ))
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details
        )


class InternalServerError(UpliftedBaseException):
    """内部服务器错误"""
    
    def __init__(self, 
                 message: str = "内部服务器错误",
                 component: Optional[str] = None,
                 error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR):
        details = []
        
        if component:
            details.append(ErrorDetail(
                field="component",
                message=component,
                code="COMPONENT"
            ))
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details
        )


class ConfigurationError(UpliftedBaseException):
    """配置错误"""
    
    def __init__(self, 
                 message: str = "配置错误",
                 config_key: Optional[str] = None):
        details = []
        
        if config_key:
            details.append(ErrorDetail(
                field="config_key",
                message=config_key,
                code="CONFIG_KEY"
            ))
        
        super().__init__(
            error_code=ErrorCode.CONFIGURATION_ERROR,
            message=message,
            details=details
        )


class TimeoutError(UpliftedBaseException):
    """超时错误"""
    
    def __init__(self, 
                 message: str = "操作超时",
                 timeout_seconds: Optional[float] = None,
                 operation: Optional[str] = None):
        details = []
        
        if timeout_seconds:
            details.append(ErrorDetail(
                field="timeout",
                message=f"{timeout_seconds}秒",
                code="TIMEOUT_DURATION"
            ))
        
        if operation:
            details.append(ErrorDetail(
                field="operation",
                message=operation,
                code="OPERATION_TYPE"
            ))
        
        super().__init__(
            error_code=ErrorCode.CONNECTION_TIMEOUT,
            message=message,
            details=details
        )


# 异常映射字典，用于将标准异常转换为Uplifted异常
EXCEPTION_MAPPING = {
    ValueError: lambda e: ValidationError(str(e)),
    TypeError: lambda e: ValidationError(f"类型错误: {str(e)}"),
    KeyError: lambda e: ValidationError(f"缺少必需参数: {str(e)}"),
    FileNotFoundError: lambda e: ResourceNotFoundError("文件", str(e)),
    PermissionError: lambda e: AuthorizationError(f"权限错误: {str(e)}"),
    ConnectionError: lambda e: ExternalServiceError(f"连接错误: {str(e)}"),
    TimeoutError: lambda e: TimeoutError(str(e)),
}


def convert_exception(exc: Exception) -> UpliftedBaseException:
    """将标准异常转换为Uplifted异常"""
    if isinstance(exc, UpliftedBaseException):
        return exc
    
    exc_type = type(exc)
    if exc_type in EXCEPTION_MAPPING:
        return EXCEPTION_MAPPING[exc_type](exc)
    
    # 默认转换为内部服务器错误
    return InternalServerError(
        message=f"未处理的异常: {str(exc)}",
        component=exc_type.__name__
    )