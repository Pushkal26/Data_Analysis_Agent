"""
Upload API Endpoints
====================
Handles file upload and file listing operations.

Endpoints:
- POST /upload - Upload a new file
- GET /files - List files for a session
- GET /files/{file_id} - Get file details
- GET /files/{file_id}/preview - Get file data preview
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db
from app.services.file_service import FileService
from app.schemas.file import (
    FileUploadResponse,
    FileMetadata,
    FileListResponse,
    FilePreviewResponse,
)
from app.core.config import get_settings

settings = get_settings()

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="CSV or Excel file to upload"),
    session_id: str = Form(..., description="Session identifier"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV or Excel file.
    
    The file will be:
    1. Saved to disk
    2. Parsed to extract schema information
    3. Time period detected from filename
    4. Metadata stored in database
    
    Returns file metadata including detected columns and time period.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    content = await file.read()
    max_size = settings.max_file_size_bytes
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )
    
    try:
        # Process the upload
        file_service = FileService(db)
        uploaded_file = await file_service.process_upload(
            file_content=content,
            filename=file.filename,
            session_id=session_id,
        )
        
        # Invalidate cache for this session (since files changed)
        from app.core.cache import cache_service
        await cache_service.invalidate_session_files(session_id)
        
        # Build response
        file_metadata = FileMetadata(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            file_type=uploaded_file.file_type,
            time_period=uploaded_file.time_period,
            time_period_type=uploaded_file.time_period_type,
            row_count=uploaded_file.row_count,
            column_count=uploaded_file.column_count,
            columns=uploaded_file.columns,
            numeric_columns=uploaded_file.numeric_columns,
            categorical_columns=uploaded_file.categorical_columns,
            date_columns=uploaded_file.date_columns,
            created_at=uploaded_file.created_at,
        )
        
        # Create schema summary for LLM context
        schema_summary = {
            "filename": uploaded_file.filename,
            "time_period": uploaded_file.time_period,
            "row_count": uploaded_file.row_count,
            "numeric_columns": uploaded_file.numeric_columns,
            "categorical_columns": uploaded_file.categorical_columns,
            "sample_values": {
                col: uploaded_file.sample_data[0].get(col) if uploaded_file.sample_data else None
                for col in uploaded_file.columns[:5]  # First 5 columns
            }
        }
        
        return FileUploadResponse(
            status="success",
            message=f"File '{file.filename}' uploaded successfully",
            file=file_metadata,
            schema_summary=schema_summary,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/files", response_model=FileListResponse)
async def list_files(
    session_id: str = Query(..., description="Session identifier"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all uploaded files for a session.
    """
    file_service = FileService(db)
    files = await file_service.get_files_for_session(session_id)
    
    file_list = [
        FileMetadata(
            id=f.id,
            filename=f.filename,
            file_type=f.file_type,
            time_period=f.time_period,
            time_period_type=f.time_period_type,
            row_count=f.row_count,
            column_count=f.column_count,
            columns=f.columns,
            numeric_columns=f.numeric_columns,
            categorical_columns=f.categorical_columns,
            date_columns=f.date_columns,
            created_at=f.created_at,
        )
        for f in files
    ]
    
    return FileListResponse(
        session_id=session_id,
        files=file_list,
        total_count=len(file_list),
    )


@router.get("/files/{file_id}", response_model=FileMetadata)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific file.
    """
    file_service = FileService(db)
    uploaded_file = await file_service.get_file_by_id(file_id)
    
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileMetadata(
        id=uploaded_file.id,
        filename=uploaded_file.filename,
        file_type=uploaded_file.file_type,
        time_period=uploaded_file.time_period,
        time_period_type=uploaded_file.time_period_type,
        row_count=uploaded_file.row_count,
        column_count=uploaded_file.column_count,
        columns=uploaded_file.columns,
        numeric_columns=uploaded_file.numeric_columns,
        categorical_columns=uploaded_file.categorical_columns,
        date_columns=uploaded_file.date_columns,
        created_at=uploaded_file.created_at,
    )


@router.get("/files/{file_id}/preview", response_model=FilePreviewResponse)
async def preview_file(
    file_id: int,
    rows: int = Query(10, ge=1, le=100, description="Number of rows to preview"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a preview of file data.
    """
    file_service = FileService(db)
    uploaded_file = await file_service.get_file_by_id(file_id)
    
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Load actual data
        df = file_service.load_file_data(uploaded_file)
        preview_data = df.head(rows).to_dict(orient='records')
        
        # Convert non-serializable values
        for row in preview_data:
            for key, value in row.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    row[key] = str(value) if value is not None else None
        
        # Basic statistics for numeric columns
        statistics = {}
        for col in uploaded_file.numeric_columns:
            if col in df.columns:
                statistics[col] = {
                    "min": float(df[col].min()) if not df[col].isna().all() else None,
                    "max": float(df[col].max()) if not df[col].isna().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                    "sum": float(df[col].sum()) if not df[col].isna().all() else None,
                }
        
        return FilePreviewResponse(
            filename=uploaded_file.filename,
            columns=uploaded_file.columns,
            row_count=uploaded_file.row_count,
            preview_rows=preview_data,
            statistics=statistics,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    session_id: str = Query(..., description="Session identifier for cache invalidation"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an uploaded file.
    
    This will:
    1. Remove the file from disk
    2. Delete the database record
    3. Invalidate the cache for the session
    """
    from app.core.cache import cache_service
    
    file_service = FileService(db)
    
    # Get file details before deletion for verification
    uploaded_file = await file_service.get_file_by_id(file_id)
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete the file
    success = await file_service.delete_file(file_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete file")
    
    # Invalidate cache for this session
    await cache_service.invalidate_session_files(session_id)
    
    # Commit the deletion
    await db.commit()
    
    return {
        "status": "success",
        "message": f"File '{uploaded_file.filename}' deleted successfully",
        "file_id": file_id,
    }

