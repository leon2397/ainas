"""
Frontend Routes - Serve static files
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import os

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
        return FileResponse(path=__file__, media_type="text/plain")  # fallback
    return FileResponse(
        path=favicon_file,
        media_type="image/x-icon"
    )
