"""
用户认证模块
提供 JWT Token 认证和权限管理
支持数据库持久化（优先）和内存字典（降级）
"""

import hashlib
import secrets
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

try:
    from jose import JWTError, jwt
except ImportError:
    JWTError = Exception
    jwt = None

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config_manager import config
from core.logger import logger

# JWT 配置 - 支持持久化到文件，生产环境必须设置
def _get_jwt_secret() -> str:
    """
    获取 JWT 密钥，按优先级：
    1. 环境变量 AI_NAS_JWT_SECRET
    2. data/.env 文件中的 AI_NAS_JWT_SECRET
    3. 自动生成并写入 data/.env（仅首次）
    """
    # 1. 优先从环境变量读取
    jwt_secret = os.getenv("AI_NAS_JWT_SECRET")
    if jwt_secret:
        return jwt_secret

    # 2. 从 data 目录的 .env 文件读取
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    env_file = os.path.join(data_dir, ".env")
    
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AI_NAS_JWT_SECRET="):
                        secret = line.split("=", 1)[1].strip()
                        if secret:
                            return secret
        except Exception as e:
            logger.debug(f"[Auth] Cannot read .env file: {e}")

    # 3. 首次启动：自动生成并写入 .env 文件
    new_secret = secrets.token_urlsafe(32)
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"# AI-NAS 自动生成的生产配置\n")
            f.write(f"# 请勿删除此文件，重启后 JWT Token 依赖此密钥\n")
            f.write(f"AI_NAS_JWT_SECRET={new_secret}\n")
        logger.info(f"[Auth] Generated JWT_SECRET and saved to {env_file}")
    except Exception as e:
        logger.warning(f"[Auth] Cannot write JWT_SECRET to {env_file}: {e}")
        warnings.warn(
            "[SECURITY] Cannot persist JWT_SECRET. Tokens will invalidate on restart. "
            "Set AI_NAS_JWT_SECRET environment variable for production.",
            RuntimeWarning
        )
        return new_secret

    return new_secret

SECRET_KEY = _get_jwt_secret()
logger.info("[Auth] JWT_SECRET loaded (persisted to data/.env)")

ALGORITHM = config.get_str('auth.algorithm', 'HS256')

# Token 过期时间：优先配置文件，其次环境变量，最后默认 24 小时
_token_expire_hours = config.get_int('auth.token_expire_hours', 0)
if _token_expire_hours <= 0:
    _token_expire_hours = int(os.getenv('AI_NAS_TOKEN_EXPIRE_HOURS', 24))
ACCESS_TOKEN_EXPIRE_MINUTES = _token_expire_hours * 60

# 角色定义
ROLES = {
    "admin": {"label": "管理员", "permissions": ["all"]},
    "editor": {"label": "编辑者", "permissions": ["media_read", "media_write", "album_manage", "task_manage", "ai_run"]},
    "viewer": {"label": "访客", "permissions": ["media_read", "album_read"]},
}

# 权限 -> 最低角色映射
PERMISSION_MIN_ROLE = {
    "all": "admin",
    "media_read": "viewer",
    "media_write": "editor",
    "album_read": "viewer",
    "album_manage": "editor",
    "task_manage": "editor",
    "ai_run": "editor",
    "device_manage": "admin",
    "user_manage": "admin",
}

# 安全头
security = HTTPBearer(auto_error=False)

# 角色层级: admin > editor > viewer
ROLE_LEVELS = {"admin": 3, "editor": 2, "viewer": 1}


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self._db = None  # 延迟加载，避免循环引用
        self._fallback_users: Dict[str, Dict[str, Any]] = {}
        self._fallback_loaded = False

    @property
    def _use_db(self) -> bool:
        """判断是否使用数据库"""
        try:
            return self._db is not None
        except Exception as e:
            logger.debug(f"[Auth] _use_db check failed: {e}")
            return False

    def set_db(self, db_instance):
        """设置数据库引用（在 app startup 时调用）"""
        self._db = db_instance

    def _load_fallback_users(self):
        """加载内存用户（降级方案）"""
        if self._fallback_loaded:
            return
        
        # 生成随机密码（首次启动）
        random_password = secrets.token_urlsafe(8)
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', random_password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        
        self._fallback_users["admin"] = {
            "username": "admin",
            "hashed_password": hashed,
            "salt": salt,
            "disabled": False,
            "role": "admin"
        }
        self._fallback_loaded = True
        
        # 打印到控制台（仅首次）
        logger.info("=" * 60)
        logger.info("[Auth] Initial admin account created (session only)")
        logger.info("  Username: admin")
        logger.info(f"  Password: {random_password}")
        logger.info("  [!] Please change password immediately after login!")
        logger.info("=" * 60)

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """哈希密码，返回 (hash, salt)"""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hashed, salt

    def verify_password(self, plain_password: str, hashed_password: str, salt: str) -> bool:
        """验证密码"""
        check_hash, _ = self._hash_password(plain_password, salt)
        return secrets.compare_digest(check_hash, hashed_password)

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """认证用户"""
        user = await self.get_user(username)
        if not user:
            return None
        if user.get("disabled"):
            return None
        if not self.verify_password(password, user["hashed_password"], user["salt"]):
            return None
        return user

    async def get_user(self, username: str) -> Optional[Dict]:
        """获取用户（优先数据库）"""
        if self._use_db:
            try:
                user = await self._db.get_user_by_username(username)
                return user
            except Exception as e:
                logger.debug(f"[Auth] DB get_user failed, fallback to memory: {e}")
        # 降级到内存
        self._load_fallback_users()
        return self._fallback_users.get(username)

    async def get_all_users_safe(self) -> List[Dict]:
        """获取所有用户（不含密码哈希）"""
        if self._use_db:
            try:
                return await self._db.get_all_users()
            except Exception as e:
                logger.debug(f"[Auth] DB get_all_users failed: {e}")
        self._load_fallback_users()
        return [{"username": u["username"], "role": u["role"], "disabled": u["disabled"]} for u in self._fallback_users.values()]

    async def create_user(self, username: str, password: str, role: str = "viewer") -> Dict:
        """创建用户"""
        hashed, salt = self._hash_password(password)
        if self._use_db:
            try:
                await self._db.create_user(username, hashed, salt, role)
                return {"username": username, "role": role, "disabled": False}
            except Exception as e:
                raise ValueError(f"创建用户失败: {e}")
        self._load_fallback_users()
        self._fallback_users[username] = {"username": username, "hashed_password": hashed, "salt": salt, "disabled": False, "role": role}
        return {"username": username, "role": role, "disabled": False}

    async def update_user_role(self, username: str, role: str):
        """更新用户角色"""
        if role not in ROLES:
            raise ValueError(f"无效角色: {role}")
        if self._use_db:
            await self._db.update_user_role(username, role)
        else:
            self._load_fallback_users()
            if username in self._fallback_users:
                self._fallback_users[username]["role"] = role

    async def update_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = await self.get_user(username)
        if not user:
            raise ValueError("用户不存在")
        if not self.verify_password(old_password, user["hashed_password"], user["salt"]):
            raise ValueError("旧密码错误")
        hashed, salt = self._hash_password(new_password)
        if self._use_db:
            await self._db.update_user_password(username, hashed, salt)
        else:
            self._fallback_users[username]["hashed_password"] = hashed
            self._fallback_users[username]["salt"] = salt
        return True

    async def toggle_user(self, username: str, disabled: bool):
        """启用/禁用用户"""
        if username == "admin":
            raise ValueError("不能禁用管理员账户")
        if self._use_db:
            await self._db.toggle_user_disabled(username, disabled)
        else:
            self._load_fallback_users()
            if username in self._fallback_users:
                self._fallback_users[username]["disabled"] = disabled

    async def delete_user(self, username: str):
        """删除用户"""
        if username == "admin":
            raise ValueError("不能删除管理员账户")
        if self._use_db:
            await self._db.delete_user(username)
        else:
            self._load_fallback_users()
            self._fallback_users.pop(username, None)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        if jwt is None:
            return "jwt-not-available"
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
        """获取当前用户（依赖注入）"""
        credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        if not credentials:
            raise credentials_exception
        if jwt is None:
            raise credentials_exception
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if not username:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        user = await self.get_user(username)
        if not user:
            raise credentials_exception
        if user.get("disabled"):
            raise HTTPException(status_code=400, detail="用户已被禁用")
        return user

    def check_permission(self, user: Dict, permission: str) -> bool:
        """检查用户权限"""
        role = user.get("role", "viewer")
        if role == "admin":
            return True
        role_info = ROLES.get(role, {})
        return permission in role_info.get("permissions", [])


# 全局认证管理器
auth_manager = AuthManager()


# 便捷依赖
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """获取当前用户"""
    return await auth_manager.get_current_user(credentials)

async def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """需要管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user

async def require_editor(current_user: Dict = Depends(get_current_user)) -> Dict:
    """需要编辑者或以上权限"""
    level = ROLE_LEVELS.get(current_user.get("role", "viewer"), 0)
    if level < ROLE_LEVELS["editor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要编辑者或管理员权限")
    return current_user
