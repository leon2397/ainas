"""
AI-NAS V7.0 异常类体系

定义明确的异常类，消除 detail:"1" 这类不明确的错误信息。
所有 API 错误都应抛出这些异常，由中间件统一处理。

使用方式：
    from core.exceptions import AIEngineError, DatabaseError
    
    raise AIEngineError("模型加载失败", engine="cpu_engine")
    raise DatabaseError("查询失败", table="media_files")
"""

from typing import Optional, Dict, Any


class AIError(Exception):
    """AI 相关错误基类"""
    
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.details = kwargs
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 API 响应"""
        result = {"error": self.message, "type": self.__class__.__name__}
        if self.details:
            result["details"] = self.details
        return result


class AIEngineError(AIError):
    """AI 引擎初始化或运行错误"""
    
    def __init__(self, message: str, engine: Optional[str] = None, **kwargs):
        if engine:
            kwargs["engine"] = engine
        super().__init__(message, **kwargs)


class AIModelNotFoundError(AIError):
    """AI 模型未找到"""
    
    def __init__(self, message: str, model: Optional[str] = None, **kwargs):
        if model:
            kwargs["model"] = model
        super().__init__(message, **kwargs)


class AIInferenceError(AIError):
    """AI 推理错误"""
    
    def __init__(self, message: str, file_id: Optional[int] = None, **kwargs):
        if file_id:
            kwargs["file_id"] = file_id
        super().__init__(message, **kwargs)


class DatabaseError(Exception):
    """数据库错误基类"""
    
    def __init__(self, message: str, **kwargs):
        self.message = message
        self.details = kwargs
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": self.__class__.__name__}
        if self.details:
            result["details"] = self.details
        return result


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误"""
    
    def __init__(self, message: str, database: Optional[str] = None, **kwargs):
        if database:
            kwargs["database"] = database
        super().__init__(message, **kwargs)


class DatabaseQueryError(DatabaseError):
    """数据库查询错误"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        if query:
            kwargs["query"] = query
        super().__init__(message, **kwargs)


class DatabaseNotFoundError(DatabaseError):
    """数据库表或列不存在"""
    
    def __init__(self, message: str, table: Optional[str] = None, column: Optional[str] = None, **kwargs):
        if table:
            kwargs["table"] = table
        if column:
            kwargs["column"] = column
        super().__init__(message, **kwargs)


class ConfigError(Exception):
    """配置错误"""
    
    def __init__(self, message: str, key: Optional[str] = None, **kwargs):
        self.message = message
        self.details = kwargs
        if key:
            self.details["key"] = key
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": self.__class__.__name__}
        if self.details:
            result["details"] = self.details
        return result


class AuthenticationError(Exception):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", **kwargs):
        self.message = message
        self.details = kwargs
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "AuthenticationError"}
        if self.details:
            result["details"] = self.details
        return result


class AuthorizationError(Exception):
    """授权错误（权限不足）"""
    
    def __init__(self, message: str = "权限不足", **kwargs):
        self.message = message
        self.details = kwargs
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "AuthorizationError"}
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(Exception):
    """数据验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        self.message = message
        self.details = kwargs
        if field:
            self.details["field"] = field
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "ValidationError"}
        if self.details:
            result["details"] = self.details
        return result


class StorageError(Exception):
    """存储错误"""
    
    def __init__(self, message: str, storage_type: Optional[str] = None, **kwargs):
        self.message = message
        self.details = kwargs
        if storage_type:
            self.details["storage_type"] = storage_type
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "StorageError"}
        if self.details:
            result["details"] = self.details
        return result


class MediaError(Exception):
    """媒体处理错误"""
    
    def __init__(self, message: str, file_id: Optional[int] = None, **kwargs):
        self.message = message
        self.details = kwargs
        if file_id:
            self.details["file_id"] = file_id
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "MediaError"}
        if self.details:
            result["details"] = self.details
        return result


class TaskError(Exception):
    """任务错误"""
    
    def __init__(self, message: str, task_id: Optional[str] = None, **kwargs):
        self.message = message
        self.details = kwargs
        if task_id:
            self.details["task_id"] = task_id
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"error": self.message, "type": "TaskError"}
        if self.details:
            result["details"] = self.details
        return result


# 异常类型映射（用于中间件判断 HTTP 状态码）
EXCEPTION_STATUS_MAP = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    ValidationError: 422,
    AIModelNotFoundError: 404,
    DatabaseNotFoundError: 404,
    AIError: 500,
    DatabaseError: 500,
    ConfigError: 500,
    StorageError: 500,
    MediaError: 500,
    TaskError: 500,
}


def get_status_code(exc: Exception) -> int:
    """根据异常类型获取 HTTP 状态码"""
    for exc_type, status in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return status
    return 500


# 导出
__all__ = [
    "AIError",
    "AIEngineError", 
    "AIModelNotFoundError",
    "AIInferenceError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseNotFoundError",
    "ConfigError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "StorageError",
    "MediaError",
    "TaskError",
    "EXCEPTION_STATUS_MAP",
    "get_status_code",
]
