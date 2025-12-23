"""
Celery Configuration
====================
Background task processing for heavy operations.
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "pushkal",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Fair distribution
    worker_concurrency=4,  # Number of concurrent tasks
    
    # Rate limiting
    task_annotations={
        "app.tasks.analysis.run_analysis": {
            "rate_limit": "10/m",  # 10 analyses per minute
        },
    },
    
    # Task routes
    task_routes={
        "app.tasks.analysis.*": {"queue": "analysis"},
        "app.tasks.cleanup.*": {"queue": "cleanup"},
    },
    
    # Beat scheduler (for periodic tasks)
    beat_schedule={
        "cleanup-old-files": {
            "task": "app.tasks.cleanup.cleanup_old_files",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-expired-cache": {
            "task": "app.tasks.cleanup.cleanup_expired_cache",
            "schedule": 1800.0,  # Every 30 minutes
        },
    },
)


# Import tasks to register them
# (will be created in app/tasks/)

