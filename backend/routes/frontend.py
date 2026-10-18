"""
Frontend Routes - Serve static files
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import mimetypes

router = APIRouter(tags=["Frontend"])

# 前端文件路径：backend/routes/../.. = 项目根目录/frontend
FRONTEND_PATH = Path(__file__).parent.parent.parent / "frontend"


@router.get("/")
async def root():
    """Serve main HTML page"""
    index_file = FRONTEND_PATH / "index.html"
    if not index_file.exists():
        return HTMLResponse(content="<h1>Frontend not found</h1><p>Please run from project root</p>", status_code=404)
    return HTMLResponse(
        content=open(index_file, encoding='utf-8').read(),
        headers={"Content-Type": "text/html; charset=utf-8"}
    )


@router.get("/index.html")
async def index_html():
    """Serve main HTML page"""
    index_file = FRONTEND_PATH / "index.html"
    if not index_file.exists():
        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)
    return HTMLResponse(
        content=open(index_file, encoding='utf-8').read(),
        headers={"Content-Type": "text/html; charset=utf-8"}
    )


@router.get("/favicon.ico")
async def favicon():
    """Serve favicon"""
    favicon_file = FRONTEND_PATH / "favicon.ico"
    if not favicon_file.exists():
        # 安全：绝不能用 __file__ 兜底——那会把本文件源码当 text/plain
        # 无认证返回（未授权源码泄露）。favicon 缺失时返回 404 即可。
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(
        path=favicon_file,
        media_type="image/x-icon"
    )


# ============ 静态资源路由（css / js / pages）============
# 背景：index.html 以相对路径引用 css/ 与 js/，且 app.js 为 ES Module，
# 动态 import('./pages/*.js') 基于 /js/app.js 解析。此前这些路径未注册，
# 浏览器只拿到裸 HTML（仅 CDN 的 Bootstrap/FontAwesome 生效），
# 登录与仪表盘逻辑全部不执行。
#
# 注意：刻意使用显式子目录路由而非 catch-all——frontend.router 在 main.py
# 中很早就被 include，catch-all 会遮蔽其后注册的全部 /api/* 路由。

_STATIC_MEDIA_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".map": "application/json",
}


def _serve_frontend_file(rel_path: str):
    """安全地服务 frontend/ 下的静态文件（含路径穿越防护）"""
    base = FRONTEND_PATH.resolve()
    target = (base / rel_path).resolve()
    # 路径穿越防护：目标必须位于 frontend/ 目录内
    if target != base and base not in target.parents:
        raise HTTPException(status_code=404, detail="Not Found")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    media_type = _STATIC_MEDIA_TYPES.get(target.suffix.lower())
    if media_type is None:
        media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(path=target, media_type=media_type)


@router.get("/css/{file_path:path}")
async def serve_css(file_path: str):
    """Serve frontend CSS assets"""
    return _serve_frontend_file(f"css/{file_path}")


@router.get("/js/{file_path:path}")
async def serve_js(file_path: str):
    """Serve frontend JS assets（含 js/pages/ 下懒加载的页面模块）"""
    return _serve_frontend_file(f"js/{file_path}")


@router.get("/pages/{file_path:path}")
async def serve_pages(file_path: str):
    """Serve frontend page fragments"""
    return _serve_frontend_file(f"pages/{file_path}")


@router.get("/vendor/{file_path:path}")
async def serve_vendor(file_path: str):
    """Serve vendored third-party assets (Bootstrap / FontAwesome)"""
    return _serve_frontend_file(f"vendor/{file_path}")
