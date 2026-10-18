"""
AI-NAS V7.0 全局异常处理中间件

捕获所有异常，返回明确的结构化错误信息。
不再返回 detail:"1" 这类无意义的错误。

使用方式：
    from core.exception_handler import setup_exception_handlers
    app = FastAPI()
    setup_exception_handlers(app)
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logger import logger
from core.exceptions import (
    AIError,
    DatabaseError,
    ConfigError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    StorageError,
    MediaError,
    TaskError,
    get_status_code,
)


async def ai_nas_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理 AI-NAS 自定义异常"""
    
    # 获取状态码
    status_code = get_status_code(exc)
    
    # 构建响应
    if hasattr(exc, 'to_dict'):
        response_data = exc.to_dict()
    else:
        response_data = {
            "error": str(exc),
            "type": exc.__class__.__name__
        }
    
    # 记录日志
    logger.error(
        f"异常: {exc.__class__.__name__} | {exc.message if hasattr(exc, 'message') else str(exc)} | "
        f"path={request.url.path} | method={request.method}"
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    
    logger.warning(
        f"HTTP {exc.status_code} | {exc.detail} | "
        f"path={request.url.path} | method={request.method}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "type": "HTTPException",
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证错误"""
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"验证错误 | {len(errors)} 个字段 | "
        f"path={request.url.path} | method={request.method}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "请求数据验证失败",
            "type": "ValidationError",
            "details": errors
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常（最后的兜底）"""
    
    # 完整记录异常堆栈
    logger.exception(
        f"未处理异常: {exc.__class__.__name__} | {str(exc)} | "
        f"path={request.url.path} | method={request.method}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "服务器内部错误",
            "type": exc.__class__.__name__,
            "message": str(exc) if str(exc) else "Unknown error"
        }
    )


def setup_exception_handlers(app: FastAPI):
    """注册异常处理器"""
    
    # AI-NAS 自定义异常
    app.add_exception_handler(AIError, ai_nas_exception_handler)
    app.add_exception_handler(DatabaseError, ai_nas_exception_handler)
    app.add_exception_handler(ConfigError, ai_nas_exception_handler)
    app.add_exception_handler(AuthenticationError, ai_nas_exception_handler)
    app.add_exception_handler(AuthorizationError, ai_nas_exception_handler)
    app.add_exception_handler(ValidationError, ai_nas_exception_handler)
    app.add_exception_handler(StorageError, ai_nas_exception_handler)
    app.add_exception_handler(MediaError, ai_nas_exception_handler)
    app.add_exception_handler(TaskError, ai_nas_exception_handler)
    
    # HTTP 异常
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 请求验证错误
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # 兜底异常（放在最后）
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("异常处理器已注册")


# 导出
__all__ = ["setup_exception_handlers"]
