"""
Redis Cache Service
====================
Provides caching functionality for file metadata and analysis results.
"""

import json
import hashlib
from typing import Optional, Any, List
from datetime import timedelta
import redis.asyncio as redis
from functools import wraps
import structlog
import numpy as np

from app.core.config import get_settings


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types."""
    
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

logger = structlog.get_logger(__name__)
settings = get_settings()


class CacheService:
    """Redis-based caching service for the application."""
    
    _instance: Optional["CacheService"] = None
    _redis: Optional[redis.Redis] = None
    
    # Cache TTL settings
    DEFAULT_TTL = 3600  # 1 hour
    FILE_METADATA_TTL = 7200  # 2 hours
    ANALYSIS_RESULT_TTL = 1800  # 30 minutes
    SESSION_TTL = 86400  # 24 hours
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis cache connected", url=settings.redis_url)
            except Exception as e:
                logger.warning("Redis connection failed, caching disabled", error=str(e))
                self._redis = None
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache disconnected")
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None
    
    # ==================== Core Cache Operations ====================
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = DEFAULT_TTL
    ) -> bool:
        """Set a value in cache with TTL."""
        if not self._redis:
            return False
        
        try:
            # Use NumpyEncoder for numpy type support
            serialized = json.dumps(value, cls=NumpyEncoder, default=str)
            await self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._redis:
            return False
        
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self._redis:
            return 0
        
        try:
            keys = []
            async for key in self._redis.scan_iter(pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning("Cache delete pattern failed", pattern=pattern, error=str(e))
            return 0
    
    # ==================== File Metadata Caching ====================
    
    def _file_key(self, session_id: str, file_id: Optional[int] = None) -> str:
        """Generate cache key for file metadata."""
        if file_id:
            return f"file:{session_id}:{file_id}"
        return f"files:{session_id}"
    
    async def get_file_metadata(self, session_id: str, file_id: int) -> Optional[dict]:
        """Get cached file metadata."""
        key = self._file_key(session_id, file_id)
        return await self.get(key)
    
    async def set_file_metadata(self, session_id: str, file_id: int, metadata: dict) -> bool:
        """Cache file metadata."""
        key = self._file_key(session_id, file_id)
        return await self.set(key, metadata, self.FILE_METADATA_TTL)
    
    async def get_session_files(self, session_id: str) -> Optional[List[dict]]:
        """Get cached list of files for a session."""
        key = self._file_key(session_id)
        return await self.get(key)
    
    async def set_session_files(self, session_id: str, files: List[dict]) -> bool:
        """Cache list of files for a session."""
        key = self._file_key(session_id)
        return await self.set(key, files, self.FILE_METADATA_TTL)
    
    async def invalidate_session_files(self, session_id: str) -> int:
        """Invalidate all cached file data for a session."""
        pattern = f"file*:{session_id}*"
        return await self.delete_pattern(pattern)
    
    # ==================== Analysis Result Caching ====================
    
    def _analysis_key(self, session_id: str, query_hash: str) -> str:
        """Generate cache key for analysis results."""
        return f"analysis:{session_id}:{query_hash}"
    
    def _hash_query(self, query: str, file_ids: List[int]) -> str:
        """Generate a hash for a query + files combination."""
        content = f"{query}:{sorted(file_ids)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def get_analysis_result(
        self, 
        session_id: str, 
        query: str, 
        file_ids: List[int]
    ) -> Optional[dict]:
        """Get cached analysis result for a query."""
        query_hash = self._hash_query(query, file_ids)
        key = self._analysis_key(session_id, query_hash)
        
        result = await self.get(key)
        if result:
            logger.info("Analysis cache hit", session_id=session_id, query_hash=query_hash)
        return result
    
    async def set_analysis_result(
        self, 
        session_id: str, 
        query: str, 
        file_ids: List[int],
        result: dict
    ) -> bool:
        """Cache analysis result."""
        query_hash = self._hash_query(query, file_ids)
        key = self._analysis_key(session_id, query_hash)
        
        success = await self.set(key, result, self.ANALYSIS_RESULT_TTL)
        if success:
            logger.info("Analysis cached", session_id=session_id, query_hash=query_hash)
        return success
    
    # ==================== Rate Limiting ====================
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        limit: int = 10, 
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            tuple: (is_allowed, remaining_requests)
        """
        if not self._redis:
            return True, limit  # Allow if Redis not available
        
        key = f"ratelimit:{identifier}"
        
        try:
            current = await self._redis.incr(key)
            
            if current == 1:
                await self._redis.expire(key, window_seconds)
            
            remaining = max(0, limit - current)
            is_allowed = current <= limit
            
            return is_allowed, remaining
        except Exception as e:
            logger.warning("Rate limit check failed", identifier=identifier, error=str(e))
            return True, limit  # Allow on error
    
    async def get_rate_limit_info(self, identifier: str) -> dict:
        """Get current rate limit status for an identifier."""
        if not self._redis:
            return {"requests": 0, "ttl": 0}
        
        key = f"ratelimit:{identifier}"
        
        try:
            requests = await self._redis.get(key)
            ttl = await self._redis.ttl(key)
            
            return {
                "requests": int(requests) if requests else 0,
                "ttl": max(0, ttl),
            }
        except Exception as e:
            logger.warning("Rate limit info failed", identifier=identifier, error=str(e))
            return {"requests": 0, "ttl": 0}


# Singleton instance
cache_service = CacheService()


async def get_cache() -> CacheService:
    """Dependency to get cache service."""
    if not cache_service.is_connected:
        await cache_service.connect()
    return cache_service

