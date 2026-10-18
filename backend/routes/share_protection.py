"""
分享保护API路由
支持密码保护、限时分享、一次性链接、私密分享
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.share_protection import (
    get_share_service,
    ShareType,
    ShareStatus
)

router = APIRouter(prefix="/api/share", tags=["Share Protection"])


# ============ Request Models ============

class CreateShareRequest(BaseModel):
    resource_type: str          # media / album
    resource_ids: List[int]     # 资源ID列表
    share_type: str = "public"  # public / password / timed / onetime / private
    password: Optional[str] = None
    expire_hours: Optional[int] = None
    max_views: Optional[int] = None
    allowed_users: Optional[List[int]] = None


class VerifyAccessRequest(BaseModel):
    share_code: str
    password: Optional[str] = None
    user_id: Optional[int] = None


class UpdateShareRequest(BaseModel):
    password: Optional[str] = None
    expire_hours: Optional[int] = None
    max_views: Optional[int] = None


# ============ Routes ============

@router.post("/create")
async def create_share(request: CreateShareRequest):
    """
    创建分享链接
    
    分享类型:
    - public: 公开分享，任何人可访问
    - password: 密码保护，需要输入密码
    - timed: 限时分享，指定时间后过期
    - onetime: 一次性链接，访问一次后失效
    - private: 私密分享，仅指定用户可访问
    """
    # 验证分享类型
    try:
        share_type = ShareType(request.share_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的分享类型: {request.share_type}")
    
    # 密码保护必须提供密码
    if share_type == ShareType.PASSWORD and not request.password:
        raise HTTPException(status_code=400, detail="密码保护分享需要提供密码")
    
    # 私密分享必须指定用户
    if share_type == ShareType.PRIVATE and not request.allowed_users:
        raise HTTPException(status_code=400, detail="私密分享需要指定允许访问的用户")
    
    # 限时分享必须指定过期时间
    if share_type == ShareType.TIMED and not request.expire_hours:
        raise HTTPException(status_code=400, detail="限时分享需要指定过期时间")
    
    try:
        service = get_share_service()
        share = service.create_share(
            resource_type=request.resource_type,
            resource_ids=request.resource_ids,
            share_type=share_type,
            password=request.password,
            expire_hours=request.expire_hours,
            max_views=request.max_views,
            allowed_users=request.allowed_users
        )
        
        return {
            "status": "success",
            "share_id": share.share_id,
            "share_code": share.share_code,
            "share_url": f"/s/{share.share_code}",
            "share_type": share.share_type.value,
            "expire_at": share.expire_at.isoformat() if share.expire_at else None,
            "max_views": share.max_views,
            "message": "分享链接创建成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建分享失败: {str(e)}")


@router.post("/verify")
async def verify_access(request: VerifyAccessRequest):
    """
    验证分享链接访问权限
    
    返回:
    - valid: 是否可访问
    - need_password: 是否需要密码
    - need_login: 是否需要登录
    - error: 错误信息
    - share: 分享详情（验证通过时）
    """
    try:
        service = get_share_service()
        result = service.verify_access(
            share_code=request.share_code,
            password=request.password,
            user_id=request.user_id
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.get("/{share_code}")
async def get_share_info(share_code: str):
    """获取分享链接信息（不验证权限）"""
    service = get_share_service()
    share = service.get_share(share_code)
    
    if not share:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    
    # 不返回敏感信息
    return {
        "share_code": share.share_code,
        "share_type": share.share_type.value,
        "resource_type": share.resource_type,
        "status": share.status.value,
        "expire_at": share.expire_at.isoformat() if share.expire_at else None,
        "need_password": share.share_type == ShareType.PASSWORD,
        "need_login": share.share_type == ShareType.PRIVATE
    }


@router.post("/{share_id}/revoke")
async def revoke_share(share_id: str):
    """撤销分享链接"""
    service = get_share_service()
    
    share = service.get_share_by_id(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    
    if service.revoke_share(share_id):
        return {"status": "success", "message": "分享链接已撤销"}
    else:
        raise HTTPException(status_code=500, detail="撤销失败")


@router.delete("/{share_id}")
async def delete_share(share_id: str):
    """删除分享链接"""
    service = get_share_service()
    
    if service.delete_share(share_id):
        return {"status": "success", "message": "分享链接已删除"}
    else:
        raise HTTPException(status_code=404, detail="分享链接不存在")


@router.patch("/{share_id}")
async def update_share(share_id: str, request: UpdateShareRequest):
    """更新分享设置"""
    service = get_share_service()
    
    share = service.update_share(
        share_id=share_id,
        password=request.password,
        expire_hours=request.expire_hours,
        max_views=request.max_views
    )
    
    if not share:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    
    return {
        "status": "success",
        "share_id": share.share_id,
        "expire_at": share.expire_at.isoformat() if share.expire_at else None,
        "max_views": share.max_views,
        "message": "分享设置已更新"
    }


@router.get("/list/my")
async def list_my_shares(
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: int = Query(..., description="用户ID")
):
    """列出我的分享链接"""
    service = get_share_service()
    
    status_enum = None
    if status:
        try:
            status_enum = ShareStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    shares = service.list_shares(
        user_id=user_id,
        resource_type=resource_type,
        status=status_enum
    )
    
    return {
        "shares": [s.to_dict() for s in shares],
        "count": len(shares)
    }


@router.get("/list/all")
async def list_all_shares(
    resource_type: Optional[str] = None,
    status: Optional[str] = None
):
    """列出所有分享链接（管理员）"""
    service = get_share_service()
    
    status_enum = None
    if status:
        try:
            status_enum = ShareStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    shares = service.list_shares(
        resource_type=resource_type,
        status=status_enum
    )
    
    return {
        "shares": [s.to_dict() for s in shares],
        "count": len(shares)
    }


@router.post("/cleanup")
async def cleanup_expired():
    """清理过期的分享链接"""
    service = get_share_service()
    count = service.cleanup_expired()
    
    return {
        "status": "success",
        "cleaned_count": count,
        "message": f"已清理 {count} 个过期分享链接"
    }


# ============ 分享资源访问 ============

@router.get("/s/{share_code}/resources")
async def get_share_resources(
    share_code: str,
    password: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None)
):
    """
    获取分享的资源列表
    
    需要先验证访问权限
    """
    service = get_share_service()
    result = service.verify_access(
        share_code=share_code,
        password=password,
        user_id=user_id
    )
    
    if not result.get("valid"):
        raise HTTPException(
            status_code=403,
            detail=result.get("error", "访问被拒绝")
        )
    
    share = result["share"]
    
    # 根据资源类型获取资源详情
    # 这里应该调用 media 或 album 服务获取详细信息
    # 简化实现：只返回ID列表
    
    return {
        "share_code": share_code,
        "resource_type": share["resource_type"],
        "resource_ids": share["resource_ids"],
        "message": "访问成功"
    }
