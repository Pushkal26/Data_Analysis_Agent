"""
File Schemas
============
Pydantic models for file upload API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """Metadata about an uploaded file."""
    
    id: int
    filename: str
    file_type: str
    time_period: Optional[str] = None
    time_period_type: Optional[str] = None
    row_count: int
    column_count: int = 0
    columns: List[str]
    numeric_columns: List[str]
    categorical_columns: List[str]
    date_columns: List[str] = []
    created_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    """Response body after file upload."""
    
    status: str = Field(
        ...,
        description="Upload status: success or error",
    )
    message: str = Field(
        ...,
        description="Status message",
    )
    file: Optional[FileMetadata] = Field(
        None,
        description="Uploaded file metadata",
    )
    
    # Schema information for the LLM
    schema_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary of file schema for LLM context",
    )


class FileListResponse(BaseModel):
    """Response body for listing uploaded files."""
    
    session_id: str
    files: List[FileMetadata]
    total_count: int


class FilePreviewResponse(BaseModel):
    """Response body for file data preview."""
    
    filename: str
    columns: List[str]
    row_count: int
    preview_rows: List[Dict[str, Any]] = Field(
        ...,
        description="First N rows of data",
    )
    statistics: Optional[Dict[str, Any]] = Field(
        None,
        description="Basic statistics for numeric columns",
    )
