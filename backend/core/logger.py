"""
AI-NAS V7.0 统一日志系统

基于 loguru 实现的结构化日志系统，支持：
- 控制台彩色输出
- 文件轮转日志
- 不同模块独立日志级别
- 异常堆栈完整记录

使用方式：
    from core.logger import logger
    
    logger.info("服务启动")
    logger.debug("调试信息")
    logger.error("错误信息", exc_info=True)
"""

import sys
import os
from pathlib import Path
from loguru import logger

# 移除默认 handler
logger.remove()

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# Windows 控制台编码处理
if sys.platform == 'win32':
    import io
    # 使用 UTF-8 编码的 stdout
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 控制台输出（开发环境）
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level="DEBUG",
    colorize=True,
    enqueue=True,
)

# 主日志文件（INFO 及以上）
logger.add(
    LOG_DIR / "ai_nas_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format=FILE_FORMAT,
    enqueue=True,
    encoding="utf-8",
)

# 错误日志文件（ERROR 及以上）
logger.add(
    LOG_DIR / "ai_nas_error_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="30 days",
    level="ERROR",
    format=FILE_FORMAT,
    enqueue=True,
    encoding="utf-8",
    backtrace=True,
    diagnose=True,
)

# API 访问日志
logger.add(
    LOG_DIR / "access_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="3 days",
    level="INFO",
    format=FILE_FORMAT,
    enqueue=True,
    encoding="utf-8",
    filter=lambda record: record["extra"].get("type") == "access",
)

# AI 模块日志
logger.add(
    LOG_DIR / "ai_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format=FILE_FORMAT,
    enqueue=True,
    encoding="utf-8",
    filter=lambda record: record["extra"].get("type") == "ai",
)


def get_logger(name: str = None):
    """
    获取带模块名的 logger
    
    Args:
        name: 模块名称，如 "ai", "media", "auth"
    
    Returns:
        logger 实例
    """
    if name:
        return logger.bind(module=name)
    return logger


def log_api_request(method: str, path: str, status_code: int, duration_ms: float, client_ip: str = None):
    """
    记录 API 请求日志
    
    Args:
        method: HTTP 方法
        path: 请求路径
        status_code: 响应状态码
        duration_ms: 处理耗时（毫秒）
        client_ip: 客户端 IP
    """
    logger.bind(type="access").info(
        f"{method} {path} | {status_code} | {duration_ms:.2f}ms | {client_ip or '-'}"
    )


def log_ai_operation(operation: str, file_id: int = None, duration_ms: float = None, success: bool = True, error: str = None):
    """
    记录 AI 操作日志
    
    Args:
        operation: 操作类型（如 "classify", "tag", "face_detect"）
        file_id: 文件 ID
        duration_ms: 处理耗时
        success: 是否成功
        error: 错误信息
    """
    msg = f"[{operation}]"
    if file_id:
        msg += f" file_id={file_id}"
    if duration_ms:
        msg += f" {duration_ms:.2f}ms"
    msg += f" {'✓' if success else '✗'}"
    if error:
        msg += f" | error: {error}"
    
    if success:
        logger.bind(type="ai").info(msg)
    else:
        logger.bind(type="ai").error(msg)


# 导出
__all__ = ["logger", "get_logger", "log_api_request", "log_ai_operation"]
