"""
Database Models Package
=======================
Exports all SQLAlchemy models and database utilities.

Usage:
    from app.models import Session, UploadedFile, ChatMessage, AnalysisResult
    from app.models import get_db, Base
"""

# Base and database utilities
from .base import Base, engine, async_session_maker, get_db

# Models
from .session import Session
from .file import UploadedFile
from .message import ChatMessage, MessageRole
from .analysis import (
    AnalysisResult,
    AnalysisIntent,
    OperationType,
    AnalysisStatus,
)

__all__ = [
    # Base
    "Base",
    "engine",
    "async_session_maker",
    "get_db",
    # Models
    "Session",
    "UploadedFile",
    "ChatMessage",
    "MessageRole",
    "AnalysisResult",
    "AnalysisIntent",
    "OperationType",
    "AnalysisStatus",
]
