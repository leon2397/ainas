"""
Plugin API Routes
V6.0 Phase 3: Plugin System API
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import tempfile

from core.auth import get_current_user

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# ============ Models ============

class PluginConfig(BaseModel):
    config: dict


class PluginListResponse(BaseModel):
    plugins: List[dict]
    total: int


class PluginDetailResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    tags: List[str]
    state: str
    enabled: bool
    config: dict = {}


# ============ Routes ============

@router.get("/", response_model=PluginListResponse)
async def list_plugins(
    plugin_type: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user)
):
    """List all plugins"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from plugins.registry import get_registry
    registry = get_registry()
    plugins = registry.list_all()
    
    return PluginListResponse(
        plugins=plugins,
        total=len(plugins)
    )


@router.get("/{plugin_id}", response_model=PluginDetailResponse)
async def get_plugin(
    plugin_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get plugin details"""
    from plugins.registry import get_registry
    registry = get_registry()
    manifest = registry.get_manifest(plugin_id)
    instance = registry.get(plugin_id)
    
    if not manifest:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return PluginDetailResponse(
        id=manifest.id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        author=manifest.author,
        plugin_type=manifest.plugin_type.value,
        tags=manifest.tags,
        state=instance.state.value if instance else "installed",
        enabled=instance is not None,
        config=instance.config if instance else {}
    )


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Enable plugin"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from plugins.registry import get_registry
    registry = get_registry()
    
    if registry.enable(plugin_id):
        return {"message": "Plugin enabled", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail="Enable failed")


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Disable plugin"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from plugins.registry import get_registry
    registry = get_registry()
    
    if registry.disable(plugin_id):
        return {"message": "Plugin disabled", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail="Disable failed")


@router.post("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    config_data: PluginConfig,
    current_user: Dict = Depends(get_current_user)
):
    """Update plugin config"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from plugins.registry import get_registry
    registry = get_registry()
    instance = registry.get(plugin_id)
    
    if not instance:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    
    if instance.update_config(config_data.config):
        return {"message": "Config updated", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail="Config validation failed")


@router.post("/install")
async def install_plugin(
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
):
    """Install plugin from ZIP"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        from plugins.registry import get_registry
        registry = get_registry()
        plugin_id = registry.install_from_zip(tmp_path)
        
        if plugin_id:
            return {"message": "Plugin installed", "plugin_id": plugin_id}
        raise HTTPException(status_code=400, detail="Install failed")
    finally:
        os.unlink(tmp_path)


@router.delete("/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Uninstall plugin"""
    if current_user.get("role") not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin required")
    
    from plugins.registry import get_registry
    registry = get_registry()
    
    if registry.uninstall(plugin_id):
        return {"message": "Plugin uninstalled", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail="Uninstall failed")


# ============ Built-in Plugin Management ============

@router.get("/storage/drivers")
async def list_storage_drivers(current_user: Dict = Depends(get_current_user)):
    """List available storage drivers"""
    from plugins.registry import get_registry
    from plugins.base import PluginType
    registry = get_registry()
    return {"drivers": registry.list_by_type(PluginType.STORAGE)}


@router.get("/ai/engines")
async def list_ai_engines(current_user: Dict = Depends(get_current_user)):
    """List available AI engines"""
    from plugins.registry import get_registry
    from plugins.base import PluginType
    registry = get_registry()
    return {"engines": registry.list_by_type(PluginType.AI)}


# ============ Plugin Market ============

@router.get("/market/featured")
async def get_featured_plugins(current_user: Dict = Depends(get_current_user)):
    """Get featured plugins"""
    return {
        "featured": [
            {
                "id": "onedrive-sync",
                "name": "OneDrive Sync",
                "description": "Sync with Microsoft OneDrive",
                "author": "AI-NAS Team",
                "type": "storage",
                "rating": 4.8,
                "downloads": 1234
            },
            {
                "id": "google-photos",
                "name": "Google Photos Import",
                "description": "Import from Google Photos",
                "author": "AI-NAS Team",
                "type": "integration",
                "rating": 4.6,
                "downloads": 856
            }
        ]
    }
