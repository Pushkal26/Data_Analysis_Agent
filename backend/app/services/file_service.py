"""
File Service
============
Handles file parsing, schema extraction, and time period detection.

This service:
1. Reads CSV/Excel files using pandas
2. Extracts column types (numeric, categorical, date)
3. Detects time periods from filenames
4. Saves metadata to the database
"""

import re
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Session, UploadedFile
from app.core.config import get_settings

settings = get_settings()


class TimePeriodParser:
    """
    Parses time period information from filenames.
    
    Supports patterns like:
    - sales_nov_2024.csv → ("Nov 2024", "monthly")
    - sales_q1_2025.csv → ("Q1 2025", "quarterly")
    - sales_2024.csv → ("2024", "yearly")
    - sales_december_2024.csv → ("Dec 2024", "monthly")
    """
    
    MONTH_PATTERNS = {
        'jan': 'Jan', 'january': 'Jan',
        'feb': 'Feb', 'february': 'Feb',
        'mar': 'Mar', 'march': 'Mar',
        'apr': 'Apr', 'april': 'Apr',
        'may': 'May',
        'jun': 'Jun', 'june': 'Jun',
        'jul': 'Jul', 'july': 'Jul',
        'aug': 'Aug', 'august': 'Aug',
        'sep': 'Sep', 'sept': 'Sept', 'september': 'Sep',
        'oct': 'Oct', 'october': 'Oct',
        'nov': 'Nov', 'november': 'Nov',
        'dec': 'Dec', 'december': 'Dec',
    }
    
    @classmethod
    def parse(cls, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse time period from filename.
        
        Args:
            filename: The filename to parse (e.g., "sales_nov_2024.csv")
        
        Returns:
            Tuple of (time_period, period_type):
            - ("Nov 2024", "monthly")
            - ("Q1 2025", "quarterly")
            - ("2024", "yearly")
            - (None, None) if no pattern found
        """
        # Remove extension and convert to lowercase
        name = Path(filename).stem.lower()
        
        # Try quarterly pattern: q1_2024, q1-2024, q1 2024
        quarter_match = re.search(r'q([1-4])[-_\s]?(\d{4})', name)
        if quarter_match:
            quarter = quarter_match.group(1)
            year = quarter_match.group(2)
            return f"Q{quarter} {year}", "quarterly"
        
        # Try monthly pattern: nov_2024, november_2024
        for pattern, month_name in cls.MONTH_PATTERNS.items():
            # Match pattern followed by year
            month_match = re.search(rf'{pattern}[-_\s]?(\d{{4}})', name)
            if month_match:
                year = month_match.group(1)
                return f"{month_name} {year}", "monthly"
        
        # Try yearly pattern: just a year like 2024
        year_match = re.search(r'(\d{4})', name)
        if year_match:
            year = year_match.group(1)
            # Check it's a reasonable year (2000-2099)
            if 2000 <= int(year) <= 2099:
                return year, "yearly"
        
        return None, None


class FileService:
    """
    Service for handling file operations.
    
    Responsibilities:
    - Parse CSV/Excel files
    - Extract schema information
    - Detect column types
    - Save file metadata to database
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = Session(session_id=session_id)
            self.db.add(session)
            await self.db.flush()
        
        return session
    
    def save_file(self, file_content: bytes, filename: str, session_id: str) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            session_id: Session identifier
        
        Returns:
            Path where file was saved
        """
        # Create session directory
        session_dir = self.upload_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
        unique_filename = f"{timestamp}_{safe_filename}"
        
        filepath = session_dir / unique_filename
        filepath.write_bytes(file_content)
        
        # Return absolute path for reliable access
        return str(filepath.resolve())
    
    def parse_file(self, filepath: str) -> pd.DataFrame:
        """
        Parse CSV or Excel file into DataFrame.
        
        Args:
            filepath: Path to the file
        
        Returns:
            Pandas DataFrame
        
        Raises:
            ValueError: If file format is not supported
        """
        path = Path(filepath)
        
        if path.suffix.lower() == '.csv':
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    return pd.read_csv(filepath, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"Could not decode CSV file: {filepath}")
        
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            return pd.read_excel(filepath)
        
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def extract_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract schema information from DataFrame.
        
        Args:
            df: Pandas DataFrame
        
        Returns:
            Dictionary with schema information:
            - columns: List of all column names
            - numeric_columns: List of numeric column names
            - categorical_columns: List of categorical column names
            - date_columns: List of date column names
            - schema: Dict mapping column name to dtype
            - sample_data: First 5 rows as list of dicts
        """
        # Get column types
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Categorize columns
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Try to detect date columns
        date_columns = []
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to parse as date
                try:
                    sample = df[col].dropna().head(10)
                    if len(sample) > 0:
                        pd.to_datetime(sample, format='mixed', dayfirst=True)
                        date_columns.append(col)
                except (ValueError, TypeError):
                    pass
        
        # Remove detected date columns from categorical
        categorical_columns = [c for c in categorical_columns if c not in date_columns]
        
        # Get sample data (first 5 rows)
        sample_data = df.head(5).to_dict(orient='records')
        
        # Convert any non-serializable values to strings
        for row in sample_data:
            for key, value in row.items():
                if pd.isna(value):
                    row[key] = None
                elif not isinstance(value, (str, int, float, bool, type(None))):
                    row[key] = str(value)
        
        return {
            'columns': df.columns.tolist(),
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns,
            'date_columns': date_columns,
            'schema': schema,
            'sample_data': sample_data,
            'row_count': len(df),
            'column_count': len(df.columns),
        }
    
    async def process_upload(
        self,
        file_content: bytes,
        filename: str,
        session_id: str,
    ) -> UploadedFile:
        """
        Process an uploaded file.
        
        This method:
        1. Gets or creates the session
        2. Saves the file to disk
        3. Parses the file with pandas
        4. Extracts schema information
        5. Detects time period from filename
        6. Saves metadata to database
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            session_id: Session identifier
        
        Returns:
            UploadedFile model instance
        """
        # Get or create session
        session = await self.get_or_create_session(session_id)
        
        # Check for existing file with same name in this session
        existing_file_result = await self.db.execute(
            select(UploadedFile)
            .where(UploadedFile.session_id == session.id)
            .where(UploadedFile.filename == filename)
        )
        existing_file = existing_file_result.scalar_one_or_none()
        
        # If exists, delete it first (overwrite behavior)
        if existing_file:
            await self.delete_file(existing_file.id)
        # Save file to disk
        filepath = self.save_file(file_content, filename, session_id)
        
        # Parse file
        df = self.parse_file(filepath)
        
        # Extract schema
        schema_info = self.extract_schema(df)
        
        # Detect time period
        time_period, period_type = TimePeriodParser.parse(filename)
        
        # Determine file type
        file_type = Path(filename).suffix.lower().lstrip('.')
        
        # Create database record
        uploaded_file = UploadedFile(
            session_id=session.id,
            filename=filename,
            filepath=filepath,
            file_type=file_type,
            file_size_bytes=len(file_content),
            time_period=time_period,
            time_period_type=period_type,
            row_count=schema_info['row_count'],
            column_count=schema_info['column_count'],
            columns=schema_info['columns'],
            numeric_columns=schema_info['numeric_columns'],
            categorical_columns=schema_info['categorical_columns'],
            date_columns=schema_info['date_columns'],
            schema=schema_info['schema'],
            sample_data=schema_info['sample_data'],
        )
        
        self.db.add(uploaded_file)
        await self.db.flush()
        
        return uploaded_file
    

    async def delete_file(self, file_id: int) -> bool:
        """Delete a file by ID (from disk and DB)."""
        file = await self.get_file_by_id(file_id)
        if not file:
            return False
            
        # Delete from disk
        try:
            if os.path.exists(file.filepath):
                os.remove(file.filepath)
        except OSError:
            pass # Continue to delete from DB even if file missing
            
        # Delete from DB
        await self.db.delete(file)
        await self.db.commit()
        return True




    async def get_files_for_session(self, session_id: str) -> List[UploadedFile]:
        """Get all uploaded files for a session."""
        # First get the session
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return []
        
        # Get files
        result = await self.db.execute(
            select(UploadedFile)
            .where(UploadedFile.session_id == session.id)
            .order_by(UploadedFile.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_file_by_id(self, file_id: int) -> Optional[UploadedFile]:
        """Get a file by its ID."""
        result = await self.db.execute(
            select(UploadedFile).where(UploadedFile.id == file_id)
        )
        return result.scalar_one_or_none()
    
    def load_file_data(self, uploaded_file: UploadedFile) -> pd.DataFrame:
        """Load the actual data from an uploaded file."""
        return self.parse_file(uploaded_file.filepath)

