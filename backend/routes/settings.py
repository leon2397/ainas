"""
Settings API Routes
系统设置API - 支持配置文件的读写
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
import os
import yaml

from core.auth import get_current_user, require_admin
from core.logger import logger

router = APIRouter(prefix="/api/system", tags=["Settings"])


# ============ Config Manager ============

class SettingsManager:
    """设置管理器 - 读写配置文件"""
    
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
        self._cache = {}
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error loading {filename}: {e}")
            return {}
    
    def _save_yaml(self, filename: str, data: Dict[str, Any]) -> bool:
        """保存YAML配置文件"""
        filepath = os.path.join(self.config_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            logger.warning(f"Error saving {filename}: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        return {
            "global": self._load_yaml("global.yaml"),
            "web": self._load_yaml("web.yaml"),
            "storage": self._load_yaml("storage.yaml"),
            "devices": self._load_yaml("devices.yaml"),
            "ai_engine": self._load_yaml("ai_engine.yaml"),
            "cloud": self._load_yaml("cloud.yaml")
        }
    
    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """获取指定分类的设置"""
        filename_map = {
            "global": "global.yaml",
            "web": "web.yaml",
            "storage": "storage.yaml",
            "devices": "devices.yaml",
            "ai": "ai_engine.yaml",
            "cloud": "cloud.yaml"
        }
        
        filename = filename_map.get(category)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
        
        return self._load_yaml(filename)
    
    def update_settings(self, category: str, settings: Dict[str, Any]) -> bool:
        """更新指定分类的设置"""
        filename_map = {
            "global": "global.yaml",
            "web": "web.yaml",
            "storage": "storage.yaml",
            "devices": "devices.yaml",
            "ai": "ai_engine.yaml",
            "cloud": "cloud.yaml"
        }
        
        filename = filename_map.get(category)
        if not filename:
            raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
        
        # 合并现有设置
        current = self._load_yaml(filename)
        current.update(settings)
        
        return self._save_yaml(filename, current)


settings_manager = SettingsManager()


# ============ API Routes ============

class SettingsUpdateRequest(BaseModel):
    """设置更新请求"""
    category: str
    settings: Dict[str, Any]


@router.get("/settings")
async def get_settings(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    获取系统设置
    - 不传category: 返回所有设置
    - 传category: 返回指定分类的设置
    """
    if category:
        return settings_manager.get_settings_by_category(category)
    return settings_manager.get_all_settings()


@router.put("/settings")
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: dict = Depends(require_admin)
):
    """
    更新系统设置（需要管理员权限）
    """
    success = settings_manager.update_settings(request.category, request.settings)
    if success:
        return {"status": "success", "message": f"Settings updated for category: {request.category}"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


@router.get("/settings/options")
async def get_settings_options(current_user: dict = Depends(get_current_user)):
    """获取设置选项（用于前端表单）"""
    return {
        "language": [
            {"value": "zh-CN", "label": "简体中文"},
            {"value": "zh-TW", "label": "繁體中文"},
            {"value": "en-US", "label": "English"},
            {"value": "ja-JP", "label": "日本語"}
        ],
        "timezone": [
            {"value": "Asia/Shanghai", "label": "中国 (UTC+8)"},
            {"value": "Asia/Tokyo", "label": "日本 (UTC+9)"},
            {"value": "America/New_York", "label": "美国东部 (UTC-5)"},
            {"value": "Europe/London", "label": "英国 (UTC+0)"}
        ],
        "theme": [
            {"value": "light", "label": "浅色"},
            {"value": "dark", "label": "深色"},
            {"value": "auto", "label": "跟随系统"}
        ],
        "page_size": [
            {"value": "10", "label": "10"},
            {"value": "20", "label": "20"},
            {"value": "50", "label": "50"},
            {"value": "100", "label": "100"}
        ]
    }