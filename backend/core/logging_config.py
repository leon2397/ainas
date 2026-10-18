"""
AI-NAS Media Manager - Unified Logging Configuration
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(level: str = "INFO", log_file: bool = True) -> logging.Logger:
    """
    配置统一日志
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 是否写入文件
    
    Returns:
        根日志器
    """
    # 创建根日志器
    root_logger = logging.getLogger("ai_nas")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除已有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_filename = LOG_DIR / f"ai_nas_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取子日志器
    
    Args:
        name: 模块名 (如 'auth', 'db', 'scanner')
    
    Returns:
        子日志器
    """
    return logging.getLogger(f"ai_nas.{name}")


# 便捷方法：模块级日志器
class LoggerMixin:
    """为类提供日志功能的混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__.lower())
        return self._logger
