"""
AI-NAS Media Manager - Backend
FastAPI Application Entry Point
Version: V7.0.0

⚠️ 开发提醒：直接用系统 Python 运行，不要创建 venv
   原因：opencv/onnxruntime 等重型依赖已预装在系统环境
   venv 仅用于部署/交接场景
   启动命令: python backend/main.py
"""

# 开发环境检查（venv 提醒）
import sys
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("=" * 50)
    print("⚠️  警告：检测到你在虚拟环境中运行")
    print("=" * 50)
    print()
    print("开发阶段建议直接用系统 Python：")
    print("  退出 venv: deactivate")
    print("  直接运行: python backend/main.py")
    print()
    print("原因：opencv/onnxruntime 等依赖已预装在系统环境")
    print("      venv 里重装这些重型依赖耗时且无意义")
    print()
    print("venv 仅用于：部署/交接场景")
    print()
    input("按回车继续（或 Ctrl+C 退出）...")

import os
import sys
import hashlib
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from starlette.responses import Response

# FastAPI 0.115.5 + 补丁（status_code UnboundLocalError bug）
from core.patch_fastapi import ensure_fastapi_patch
ensure_fastapi_patch()

# V7.0: 引入统一日志系统
from core.logger import logger, log_api_request
from core.exception_handler import setup_exception_handlers


# ============ UTF-8 JSON Encoder ============

class UTF8JSONResponse(JSONResponse):
    """Custom JSON Response with UTF-8 charset for proper Chinese character encoding"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('media_type', 'application/json; charset=utf-8')
        super().__init__(*args, **kwargs)


# ============ Cache-Enabled Static Files ============

class CachedStaticFiles(StaticFiles):
    """Static files with ETag and Cache-Control headers"""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)

        # Add cache headers for immutable assets (JS, CSS)
        if path.endswith(('.js', '.css')):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            # Generate ETag from file content
            file_path = self.directory / path
            if file_path.exists():
                content = file_path.read_bytes()
                etag = hashlib.md5(content).hexdigest()
                response.headers['ETag'] = f'"{etag}"'

        return response


def json_response(content, status_code=200):
    """Helper function to return JSON with proper UTF-8 encoding"""
    return UTF8JSONResponse(content=content, status_code=status_code)


from database.db import db
from routes import media, albums, devices, tasks, frontend
from routes import websocket as ws
from routes import actions
from routes import monitor
from routes import archive
from routes import auth
from routes import alerts
from routes import cloud
from routes import ocr
from routes import ai
from routes import sysadmin
from routes import settings  # 系统设置API
from routes import ecosystem  # 生态系统路由（移动端等）
from routes.admin import router as admin_router
from services.discovery import device_discovery, discovery_router
from routes import cache
from routes import performance
from routes import plugins
from routes import enterprise
from routes import media_edit
from routes import share_protection
from routes import npu_accelerator
from core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from core.config_manager import config

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 60)
    logger.info("AI-NAS Media Manager V7.0.0 启动中...")
    logger.info("=" * 60)

    # Create data directories first (synchronous)
    os.makedirs("./data/uploads", exist_ok=True)
    os.makedirs("./data/thumbnails", exist_ok=True)
    os.makedirs("./data/original", exist_ok=True)
    os.makedirs("./data/albums", exist_ok=True)
    os.makedirs("./data/chroma", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    logger.info("✓ 数据目录创建完成")

    # Initialize database
    try:
        await db.init()
        logger.info("✓ 数据库初始化完成")
        # 初始化认证系统
        from core.auth import auth_manager
        auth_manager.set_db(db)
        await db.init_default_admin()
        logger.info("✓ 认证系统初始化完成")
    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("AI-NAS Media Manager V7.0.0 启动成功！")
    logger.info(f"   前端访问: http://localhost:8000")
    logger.info(f"   API 文档: http://localhost:8000/docs")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("AI-NAS Media Manager 关闭中...")
    try:
        await device_discovery.stop_listening()
        logger.info("✓ 设备发现服务已停止")
    except Exception as e:
        logger.debug(f"设备发现服务停止时出错: {e}")
    try:
        await db.close()
        logger.info("✓ 数据库连接已关闭")
    except Exception as e:
        logger.debug(f"数据库关闭时出错: {e}")
    logger.info("AI-NAS Media Manager 已停止")


# ============ App ============

app = FastAPI(
    title="AI-NAS Media Manager",
    description="AI-NAS Media Manager - 通用插件化媒体管理工具 | V7.0.0",
    version="7.0.0",
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse
)

# V7.0: 注册统一异常处理器
setup_exception_handlers(app)


# Security Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting - 按配置决定是否启用
if config.get_bool('rate_limit.enabled', False):
    app.add_middleware(RateLimitMiddleware)
    logger.info("✓ 请求限流已启用")
else:
    logger.info("○ 请求限流未启用 (config: rate_limit.enabled = false)")

# CORS - 从环境变量读取，支持任意域名
def get_cors_origins() -> list:
    """从环境变量读取 CORS 白名单，支持多域名逗号分隔"""
    cors_env = os.getenv("AI_NAS_CORS_ORIGINS", "")
    if cors_env:
        # 支持逗号分隔的多个域名，也可以用空格分隔
        origins = [o.strip() for o in cors_env.replace(",", " ").split() if o.strip()]
        if origins:
            return origins
    # 默认允许的来源（开发环境）
    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

cors_origins = get_cors_origins()
logger.info(f"CORS 允许的来源: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)  # 认证路由（公开）
app.include_router(frontend.router)
app.include_router(ws.ws_router)
app.include_router(media.router)
app.include_router(albums.router)
app.include_router(devices.router)
app.include_router(tasks.router)
app.include_router(actions.router)
app.include_router(monitor.router)
app.include_router(archive.router)
app.include_router(alerts.router)
app.include_router(cloud.router)
app.include_router(ocr.router)
app.include_router(ai.router)  # AI功能路由
app.include_router(sysadmin.router)  # 系统管理路由
app.include_router(settings.router)  # 系统设置API
app.include_router(admin_router)  # 管理员路由
app.include_router(discovery_router)  # 设备发现路由
app.include_router(cache.router)  # 缓存管理路由
app.include_router(performance.router)  # 性能监控路由
app.include_router(plugins.router)  # 插件管理路由
app.include_router(enterprise.router)  # 企业功能路由
app.include_router(media_edit.router)  # 媒体编辑路由
app.include_router(share_protection.router)  # 分享保护路由
app.include_router(npu_accelerator.router)  # NPU加速路由
app.include_router(ecosystem.router)  # 生态系统路由（移动端等）


# ============ Static Files ============

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", CachedStaticFiles(directory=frontend_path), name="static")


# ============ Root ============

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "discovery": "active"
    }


@app.get("/status")
async def get_status():
    """Get system status"""
    try:
        from routes.websocket import manager
        from services.monitor import get_monitor

        monitor_svc = get_monitor()
        sys_info = monitor_svc.get_full_status()

        return {
            "version": "0.5.0",
            "database": {
                "connected": True,
                "path": db.db_path
            },
            "websocket": {
                "connections": manager.connection_count,
                "listening": True
            },
            "system": {
                "cpu": sys_info.get("cpu", {}).get("usage", 0),
                "memory": sys_info.get("memory", {}).get("percent", 0),
                "disk": sys_info.get("disk", {}).get("percent", 0)
            }
        }
    except Exception as e:
        return {
            "version": "0.5.0",
            "status": "running",
            "error": str(e)
        }


# ============ Main ============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4  # 多进程处理，提升并发能力
    )
