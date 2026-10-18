"""
管理员路由初始化
"""

from fastapi import APIRouter
from .users import router as users_router

router = APIRouter()
router.include_router(users_router)

__all__ = ['router']
