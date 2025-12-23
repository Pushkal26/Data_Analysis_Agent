"""
Cleanup Tasks
=============
Periodic tasks for cleaning up old data.
"""

import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import structlog

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@celery_app.task(name="app.tasks.cleanup.cleanup_old_files")
def cleanup_old_files(max_age_days: int = 7) -> dict:
    """
    Clean up uploaded files older than max_age_days.
    
    Args:
        max_age_days: Maximum age of files to keep (default 7 days)
        
    Returns:
        Statistics about cleaned up files
    """
    logger.info("Starting file cleanup", max_age_days=max_age_days)
    
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return {"deleted_files": 0, "deleted_sessions": 0, "freed_bytes": 0}
    
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    
    deleted_files = 0
    deleted_sessions = 0
    freed_bytes = 0
    
    # Iterate through session directories
    for session_dir in upload_dir.iterdir():
        if not session_dir.is_dir():
            continue
        
        session_modified = datetime.fromtimestamp(session_dir.stat().st_mtime)
        
        if session_modified < cutoff_time:
            # Delete all files in this session
            for file_path in session_dir.iterdir():
                if file_path.is_file():
                    freed_bytes += file_path.stat().st_size
                    file_path.unlink()
                    deleted_files += 1
            
            # Remove empty session directory
            try:
                session_dir.rmdir()
                deleted_sessions += 1
            except OSError:
                pass  # Directory not empty
    
    logger.info(
        "File cleanup completed",
        deleted_files=deleted_files,
        deleted_sessions=deleted_sessions,
        freed_mb=round(freed_bytes / (1024 * 1024), 2),
    )
    
    return {
        "deleted_files": deleted_files,
        "deleted_sessions": deleted_sessions,
        "freed_bytes": freed_bytes,
    }


@celery_app.task(name="app.tasks.cleanup.cleanup_expired_cache")
def cleanup_expired_cache() -> dict:
    """
    Clean up expired cache entries from Redis.
    
    Note: Redis automatically removes expired keys,
    but this task can clean up orphaned or forgotten keys.
    
    Returns:
        Statistics about cache cleanup
    """
    logger.info("Starting cache cleanup")
    
    # Run async cleanup
    result = asyncio.run(_cleanup_cache_async())
    
    logger.info("Cache cleanup completed", **result)
    
    return result


async def _cleanup_cache_async() -> dict:
    """Async helper for cache cleanup."""
    from app.core.cache import cache_service
    
    if not cache_service.is_connected:
        await cache_service.connect()
    
    if not cache_service.is_connected:
        return {"status": "skipped", "reason": "redis not connected"}
    
    # Clean up stale rate limit keys (shouldn't happen often)
    deleted = await cache_service.delete_pattern("ratelimit:*")
    
    return {
        "status": "completed",
        "cleaned_ratelimit_keys": deleted,
    }


@celery_app.task(name="app.tasks.cleanup.cleanup_old_analyses")
def cleanup_old_analyses(max_age_days: int = 30) -> dict:
    """
    Archive or delete old analysis results from the database.
    
    Args:
        max_age_days: Maximum age of analysis results to keep
        
    Returns:
        Statistics about archived analyses
    """
    logger.info("Starting analysis cleanup", max_age_days=max_age_days)
    
    result = asyncio.run(_cleanup_analyses_async(max_age_days))
    
    logger.info("Analysis cleanup completed", **result)
    
    return result


async def _cleanup_analyses_async(max_age_days: int) -> dict:
    """Async helper for analysis cleanup."""
    from datetime import datetime, timedelta
    from sqlalchemy import delete
    from app.models import async_session_maker, AnalysisResult
    
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    
    async with async_session_maker() as session:
        # Delete old analysis results
        result = await session.execute(
            delete(AnalysisResult).where(AnalysisResult.created_at < cutoff)
        )
        await session.commit()
        
        deleted_count = result.rowcount
    
    return {
        "deleted_analyses": deleted_count,
        "cutoff_date": cutoff.isoformat(),
    }

