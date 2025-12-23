"""
Message Schemas
===============
Pydantic models for chat API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    
    session_id: str = Field(
        ...,
        description="Session identifier",
    )
    message: str = Field(
        ...,
        description="User's question or message",
        min_length=1,
        max_length=5000,
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context (e.g., selected files)",
    )


class MessageResponse(BaseModel):
    """A single chat message."""
    
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    analysis_id: Optional[int] = None
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    
    status: str = Field(
        ...,
        description="Response status: success or error",
    )
    response: str = Field(
        ...,
        description="Assistant's response text",
    )
    
    # Analysis details (if applicable)
    analysis: Optional[Dict[str, Any]] = Field(
        None,
        description="Analysis details including intent, plan, results",
    )
    
    # Visualization data (if applicable)
    visualization: Optional[Dict[str, Any]] = Field(
        None,
        description="Chart/table data for frontend rendering",
    )
    
    # Recommended follow-up questions
    follow_ups: Optional[List[str]] = Field(
        None,
        description="Suggested follow-up questions",
    )
    
    # Processing metadata
    processing_time_ms: Optional[float] = Field(
        None,
        description="Time taken to process the request",
    )
    
    # Error details
    error: Optional[str] = Field(
        None,
        description="Error message if status is error",
    )


class ChatHistoryResponse(BaseModel):
    """Response body for chat history endpoint."""
    
    session_id: str
    messages: List[MessageResponse]
    total_count: int

