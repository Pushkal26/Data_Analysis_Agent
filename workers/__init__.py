"""
Celery Workers Package
======================
Background task workers for heavy processing.

Usage:
    # Start worker
    celery -A workers.celery_app worker --loglevel=info -Q analysis,cleanup
    
    # Start beat scheduler
    celery -A workers.celery_app beat --loglevel=info
    
    # Start flower monitoring
    celery -A workers.celery_app flower --port=5555
"""

from backend.app.core.celery_app import celery_app
from backend.app.tasks import (
    run_analysis_task,
    cleanup_old_files,
    cleanup_expired_cache,
)

__all__ = [
    "celery_app",
    "run_analysis_task",
    "cleanup_old_files",
    "cleanup_expired_cache",
]
