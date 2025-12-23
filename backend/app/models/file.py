"""
Uploaded File Model
===================
Stores metadata about uploaded CSV/Excel files.

The actual file data is stored on disk (or S3), while metadata
like column names, row counts, and detected time periods are stored here.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .session import Session


class UploadedFile(Base):
    """
    Uploaded file metadata model.
    
    Attributes:
        filename: Original filename (e.g., "sales_nov_2024.csv")
        filepath: Storage path (local or S3)
        file_type: "csv" or "xlsx"
        time_period: Detected time period (e.g., "Nov 2024", "Q1-2025")
        row_count: Number of data rows
        columns: List of column names
        numeric_columns: List of numeric column names
        categorical_columns: List of categorical column names
        schema: Column name -> data type mapping
    """
    
    __tablename__ = "uploaded_files"
    
    # ----- Foreign Keys -----
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ----- File Information -----
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # csv, xlsx
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    
    # ----- Detected Time Period -----
    # Extracted from filename or data (e.g., "Nov 2024", "Q1-2025")
    time_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    time_period_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )  # "monthly", "quarterly", "yearly"
    
    # ----- Data Statistics -----
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # ----- Schema Information (JSON) -----
    columns: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    numeric_columns: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    categorical_columns: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    date_columns: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    # Column name -> dtype (e.g., {"Revenue": "float64", "Region": "object"})
    schema: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    
    # Sample data (first 5 rows as JSON for quick preview)
    sample_data: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # ----- Relationships -----
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="uploaded_files",
    )
    
    def __repr__(self) -> str:
        return f"<UploadedFile(id={self.id}, filename={self.filename})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "time_period": self.time_period,
            "row_count": self.row_count,
            "columns": self.columns,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

