"""
Chat Message Model
==================
Stores conversation history for multi-turn chat.

Each message can be from the "user" or "assistant" and may
be linked to an analysis result.
"""

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base

if TYPE_CHECKING:
    from .session import Session
    from .analysis import AnalysisResult


class MessageRole(str, enum.Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """
    Chat message model.
    
    Attributes:
        role: Who sent the message (user/assistant/system)
        content: The message text
        analysis_id: Link to analysis result (if assistant message)
        metadata: Additional message metadata (e.g., tokens used)
    """
    
    __tablename__ = "chat_messages"
    
    # ----- Foreign Keys -----
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Optional link to analysis result
    analysis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # ----- Message Content -----
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # ----- Metadata -----
    # Store additional info like token count, model used, etc.
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=True,
    )
    
    # ----- Relationships -----
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="chat_messages",
    )
    
    analysis: Mapped[Optional["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="messages",
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<ChatMessage(id={self.id}, role={self.role.value}, content={content_preview})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "analysis_id": self.analysis_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_json,
        }

