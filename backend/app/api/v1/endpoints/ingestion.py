from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.services.ingestion import IngestionService
from app.schemas.file import FileUploadResponse, FileMetadataResponse
from app.models.base import FileMetadata
from sqlalchemy import select

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Upload a CSV/Excel file.
    Automatically extracts schema and infers date range from filename.
    """
    service = IngestionService(db)
    metadata = await service.process_upload(file)
    
    return FileUploadResponse(
        message="File uploaded and processed successfully",
        file_id=metadata.id,
        metadata=metadata
    )

@router.get("/files", response_model=List[FileMetadataResponse])
async def list_files(db: AsyncSession = Depends(deps.get_db)):
    """
    List all uploaded files and their metadata.
    """
    result = await db.execute(select(FileMetadata).order_by(FileMetadata.upload_date.desc()))
    files = result.scalars().all()
    return files

