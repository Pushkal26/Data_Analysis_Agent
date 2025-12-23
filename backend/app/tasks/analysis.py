"""
Analysis Tasks
==============
Background tasks for running data analysis.
"""

import asyncio
from typing import Dict, Any, List
import structlog

from app.core.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.analysis.run_analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_analysis_task(
    self,
    session_id: str,
    query: str,
    file_ids: List[int],
) -> Dict[str, Any]:
    """
    Background task to run data analysis.
    
    This is useful for long-running analyses that shouldn't
    block the API response.
    
    Args:
        session_id: Session identifier
        query: User's natural language query
        file_ids: List of file IDs to analyze
        
    Returns:
        Analysis result dictionary
    """
    logger.info(
        "Starting background analysis",
        session_id=session_id,
        query=query[:50],
        file_count=len(file_ids),
        task_id=self.request.id,
    )
    
    try:
        # Run the async analysis in a new event loop
        result = asyncio.run(_run_analysis_async(session_id, query, file_ids))
        
        logger.info(
            "Background analysis completed",
            session_id=session_id,
            task_id=self.request.id,
            success=result.get("success", False),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Background analysis failed",
            session_id=session_id,
            task_id=self.request.id,
            error=str(e),
        )
        
        # Retry on failure
        raise self.retry(exc=e)


async def _run_analysis_async(
    session_id: str,
    query: str,
    file_ids: List[int],
) -> Dict[str, Any]:
    """
    Async helper to run the LangGraph pipeline.
    """
    from app.models import async_session_maker
    from app.services.chat_service import ChatService
    
    async with async_session_maker() as db:
        chat_service = ChatService(db)
        result = await chat_service.process_message(session_id, query)
        return result


@celery_app.task(name="app.tasks.analysis.get_task_status")
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a background analysis task.
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() and result.successful() else None,
        "error": str(result.result) if result.ready() and not result.successful() else None,
    }

