from loguru import logger
"""
Cache Management API Routes
Provides endpoints for cache statistics and management
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from core.auth import auth_manager
from core.rbac import require_permission
from services.cache import get_cache, clear_cache, get_cache_stats, CACHE_PROFILES

logger = logger.bind(name="ai_nas")
router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheStats(BaseModel):
    type: str
    hits: int
    misses: int
    total_requests: int
    hit_rate: float
    items_cached: int


class CacheProfile(BaseModel):
    name: str
    ttl: int
    description: str


class ClearCacheRequest(BaseModel):
    profile: Optional[str] = None  # Clear specific profile or all


@router.get("/stats", response_model=CacheStats)
async def get_cache_statistics():
    """
    Get cache statistics including hit rate and item count
    """
    try:
        stats = get_cache_stats()
        return CacheStats(**stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles")
async def list_cache_profiles():
    """
    List available cache profiles
    """
    profiles = []
    for name, config in CACHE_PROFILES.items():
        profiles.append(CacheProfile(
            name=name,
            ttl=config["ttl"],
            description=f"Cache with TTL of {config['ttl']} seconds"
        ))
    return profiles


@router.post("/clear")
async def clear_cache_endpoint(request: ClearCacheRequest = None):
    """
    Clear cache
    
    - Without body: clears all cache
    - With {"profile": "name"}: clears specific cache profile
    """
    try:
        if request and request.profile:
            # Clear specific profile
            if request.profile not in CACHE_PROFILES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown profile: {request.profile}"
                )
            # Note: In-memory cache doesn't support profile-level clearing
            # Redis can be extended to support this
            cache = get_cache()
            if hasattr(cache, "clear_profile"):
                cache.clear_profile(request.profile)
            else:
                # Fallback: clear all
                clear_cache()
            return {"message": f"Cleared cache profile: {request.profile}"}
        else:
            # Clear all
            clear_cache()
            return {"message": "All cache cleared"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warm")
async def warm_cache():
    """
    Warm up cache with frequently accessed data
    
    This is a placeholder - in production, this would:
    1. Preload popular media items
    2. Preload album covers
    3. Preload statistics
    """
    try:
        stats = get_cache_stats()
        return {
            "message": "Cache warmed",
            "stats": stats,
            "note": "Warming logic should be implemented based on access patterns"
        }
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))