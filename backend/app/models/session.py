"""
Session Model
=============
Tracks user sessions for the application.

A session is created when a user starts interacting with the app.
All uploaded files and chat messages are linked to a session.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .file import UploadedFile
    from .message import ChatMessage
    from .analysis import AnalysisResult


class Session(Base):
    """
    User session model.
    
    Attributes:
        session_id: Unique identifier (UUID) for the session
        user_agent: Browser user agent (for debugging)
        ip_address: Client IP address (for analytics)
        metadata: Additional session metadata (JSON)
    """
    
    __tablename__ = "sessions"
    
    # Session identifier (UUID string)
    session_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )
    
    # Optional metadata
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    
    # Flexible metadata storage
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=True,
    )
    
    # ----- Relationships -----
    # One session has many uploaded files
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    
    # One session has many chat messages
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    
    # One session has many analysis results
    analysis_results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AnalysisResult.created_at.desc()",
    )
    
    def __repr__(self) -> str:
        return f"<Session(id={self.id}, session_id={self.session_id[:8]}...)>"

