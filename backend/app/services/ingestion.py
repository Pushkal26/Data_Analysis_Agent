import os
import shutil
import pandas as pd
from datetime import datetime
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.base import FileMetadata
from app.schemas.file import FileMetadataCreate
from app.services.date_utils import parse_date_from_filename

class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_upload(self, file: UploadFile) -> FileMetadata:
        # 1. Save file to disk
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # 2. Parse File content (extract columns)
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=5)
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path, nrows=5)
            else:
                os.remove(file_path)
                raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel.")
            
            columns = df.columns.tolist()
            # Map dtypes to string representation
            dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
            
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

        # 3. Infer Temporal Metadata
        start_date, end_date, period_label = parse_date_from_filename(file.filename)

        # 4. Save Metadata to DB
        file_meta = FileMetadata(
            filename=file.filename,
            filepath=file_path,
            upload_date=datetime.utcnow(),
            period_start=start_date,
            period_end=end_date,
            period_label=period_label,
            columns=columns,
            dtypes=dtypes
        )
        
        self.db.add(file_meta)
        await self.db.commit()
        await self.db.refresh(file_meta)
        
        return file_meta

