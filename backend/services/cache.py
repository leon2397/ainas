"""
Cache Service - Redis + Memory Fallback
Provides caching for frequently accessed data
"""

import time
import json
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
from loguru import logger

# Try to import Redis, fallback to in-memory cache
try:
    import redis
    REDIS_AVAILABLE = True
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class InMemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_parts = [prefix, *[str(a) for a in args]]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = ":".join(key_parts)
        # Hash if key is too long
        if len(key_str) > 200:
            return hashlib.md5(key_str.encode()).hexdigest()
        return key_str
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry > time.time():
                self.hits += 1
                return value
            else:
                del self._cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "type": "in_memory",
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 2),
            "items_cached": len(self._cache)
        }


class RedisCache:
    """Redis cache with fallback to memory cache"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = 300
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix, *[str(a) for a in args]]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str = ":".join(key_parts)
        if len(key_str) > 200:
            return f"ainas:{hashlib.md5(key_str.encode()).hexdigest()}"
        return f"ainas:{key_str}"
    
    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(key)
            if value:
                self.hits += 1
                return json.loads(value)
            self.misses += 1
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        try:
            ttl = ttl or self.default_ttl
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self) -> None:
        try:
            for key in self.client.scan_iter("ainas:*"):
                self.client.delete(key)
            self.hits = 0
            self.misses = 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    def get_stats(self) -> Dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        try:
            keys = self.client.dbsize()
        except redis.RedisError:  # Redis 连接错误时返回 0
            keys = 0
        return {
            "type": "redis",
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate": round(hit_rate, 2),
            "items_cached": keys
        }


# Global cache instance
_cache: Optional[Any] = None


def get_cache() -> Any:
    """Get or create cache instance"""
    global _cache
    if _cache is None:
        if REDIS_AVAILABLE:
            try:
                _cache = RedisCache()
                _cache.client.ping()
                logger.info("Using Redis cache")
            except redis.RedisError:  # Redis 连接失败时降级到内存缓存
                logger.info("Redis not available, using in-memory cache")
                _cache = InMemoryCache()
        else:
            _cache = InMemoryCache()
            logger.info("Using in-memory cache")
    return _cache


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key"""
    return get_cache()._make_key(prefix, *args, **kwargs)


def cached(ttl: int = 300, key_prefix: str = "default"):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl=60, key_prefix="media_list")
        async def get_media_list(page: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            # Generate cache key
            cache_key_str = cache._make_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                cache.set(cache_key_str, result, ttl)
            
            return result
        return wrapper
    return decorator


def clear_cache() -> None:
    """Clear all cache"""
    get_cache().clear()


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return get_cache().get_stats()


# Cache profiles for different data types
CACHE_PROFILES = {
    "media_list": {"ttl": 60, "prefix": "media"},
    "album_list": {"ttl": 300, "prefix": "album"},
    "device_list": {"ttl": 60, "prefix": "device"},
    "stats": {"ttl": 30, "prefix": "stats"},
    "user_info": {"ttl": 600, "prefix": "user"},
}