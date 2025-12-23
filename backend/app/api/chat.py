"""
Chat API Endpoints
==================
Handles chat operations for the conversational interface.

Endpoints:
- POST /chat - Send a message and get analysis response
- GET /chat/history - Get chat history for a session
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db
from app.services.chat_service import ChatService
from app.schemas.message import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    MessageResponse,
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a chat message and get an analysis response.
    
    This endpoint:
    1. Validates the request
    2. Retrieves file context for the session
    3. Runs the LangGraph analysis pipeline
    4. Returns a natural language response with insights
    
    The response includes:
    - Natural language explanation
    - Analysis details (intent, files used, results)
    - Recommendations for next steps
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if not request.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    
    chat_service = ChatService(db)
    
    try:
        result = await chat_service.process_message(
            session_id=request.session_id,
            message=request.message,
        )
        
        return ChatResponse(
            status=result.get("status", "success"),
            response=result.get("response", ""),
            analysis=result.get("analysis"),
            processing_time_ms=result.get("processing_time_ms"),
            error=result.get("error"),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Query(..., description="Session identifier"),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get chat history for a session.
    
    Returns messages in chronological order (oldest first).
    """
    chat_service = ChatService(db)
    
    # Get session first
    session = await chat_service.get_session(session_id)
    if not session:
        return ChatHistoryResponse(
            session_id=session_id,
            messages=[],
            total_count=0,
        )
    
    # Get messages
    from sqlalchemy import select
    from app.models import ChatMessage
    
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    message_list = [
        MessageResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            analysis_id=m.analysis_id,
            created_at=m.created_at,
            metadata=m.metadata_json,
        )
        for m in messages
    ]
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=message_list,
        total_count=len(message_list),
    )


@router.get("/chat/analysis/{analysis_id}")
async def get_analysis_details(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed analysis result.
    
    Returns the full analysis including:
    - Generated code
    - Execution results
    - LangGraph node history
    """
    from sqlalchemy import select
    from app.models import AnalysisResult
    
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "id": analysis.id,
        "status": analysis.status.value,
        "user_query": analysis.user_query,
        "intent": analysis.intent,
        "operation_type": analysis.operation_type,
        "files_used": analysis.files_used,
        "plan": analysis.plan,
        "generated_code": analysis.generated_code,
        "code_valid": analysis.code_valid,
        "result_data": analysis.result_data,
        "explanation": analysis.explanation,
        "recommendations": analysis.recommendations,
        "execution_time_ms": analysis.execution_time_ms,
        "error_message": analysis.error_message,
        "node_history": analysis.node_history,
        "created_at": analysis.created_at.isoformat(),
    }

