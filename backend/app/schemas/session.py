"""
Session Schemas
===============
Pydantic models for session-related API endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for creating a new session."""
    
    session_id: str = Field(
        ...,
        description="Unique session identifier (UUID)",
        min_length=36,
        max_length=36,
    )
    user_agent: Optional[str] = Field(
        None,
        description="Browser user agent string",
    )
    ip_address: Optional[str] = Field(
        None,
        description="Client IP address",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional session metadata",
    )


class SessionResponse(BaseModel):
    """Response body for session endpoints."""
    
    id: int
    session_id: str
    created_at: datetime
    updated_at: datetime
    file_count: int = Field(
        0,
        description="Number of uploaded files in this session",
    )
    message_count: int = Field(
        0,
        description="Number of chat messages in this session",
    )
    
    model_config = {"from_attributes": True}


class SessionHistoryResponse(BaseModel):
    """Response body for session history endpoint."""
    
    session_id: str
    files: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    analyses: List[Dict[str, Any]]

