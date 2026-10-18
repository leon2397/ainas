"""
认证路由
提供登录、用户管理、角色管理等接口
"""

from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from core.auth import auth_manager, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, require_admin, ROLES

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ===== 请求/响应模型 =====

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    username: str
    role: str


class UserInfo(BaseModel):
    username: str
    role: str
    disabled: bool


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class UpdateRoleRequest(BaseModel):
    role: str


class ToggleUserRequest(BaseModel):
    disabled: bool


# ===== 认证接口 =====

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录，返回 JWT Token"""
    user = await auth_manager.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": user["username"],
        "role": user["role"]
    }


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"username": current_user["username"], "role": current_user["role"], "disabled": current_user["disabled"]}


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """修改密码"""
    try:
        await auth_manager.update_password(current_user["username"], request.old_password, request.new_password)
        return {"message": "密码修改成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出（JWT 无状态，客户端删除 Token 即可）"""
    return {"message": "已登出，请删除本地 Token"}


# ===== 用户管理接口（管理员） =====

@router.get("/users")
async def list_users(current_user: dict = Depends(require_admin)):
    """列出所有用户（管理员）"""
    return await auth_manager.get_all_users_safe()


@router.post("/users")
async def create_user(request: CreateUserRequest, current_user: dict = Depends(require_admin)):
    """创建新用户（管理员）"""
    if request.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色，可选: {list(ROLES.keys())}")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    try:
        user = await auth_manager.create_user(request.username, request.password, request.role)
        return {"message": f"用户 {request.username} 创建成功", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/users/{username}/role")
async def update_user_role(username: str, request: UpdateRoleRequest, current_user: dict = Depends(require_admin)):
    """修改用户角色（管理员）"""
    if username == current_user["username"]:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    try:
        await auth_manager.update_user_role(username, request.role)
        return {"message": f"用户 {username} 角色已更新为 {request.role}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/users/{username}/toggle")
async def toggle_user(username: str, request: ToggleUserRequest, current_user: dict = Depends(require_admin)):
    """启用/禁用用户（管理员）"""
    try:
        await auth_manager.toggle_user(username, request.disabled)
        return {"message": f"用户 {username} 已{'禁用' if request.disabled else '启用'}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(username: str, current_user: dict = Depends(require_admin)):
    """删除用户（管理员，不能删 admin）"""
    if username == current_user["username"]:
        raise HTTPException(status_code=400, detail="不能删除自己")
    try:
        await auth_manager.delete_user(username)
        return {"message": f"用户 {username} 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles")
async def list_roles(current_user: dict = Depends(get_current_user)):
    """获取所有角色定义"""
    return ROLES