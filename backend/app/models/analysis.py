"""
Analysis Result Model
=====================
Stores the results of LangGraph analysis operations.

This captures the full analysis pipeline:
- User query
- Detected intent
- Analysis plan
- Generated code
- Execution results
- Natural language explanation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base

if TYPE_CHECKING:
    from .session import Session
    from .message import ChatMessage


class AnalysisIntent(str, enum.Enum):
    """Types of user intents detected by LLM."""
    QUERY = "query"                    # Simple data query
    AGGREGATE = "aggregate"            # Aggregation (sum, avg, etc.)
    COMPARE = "compare"                # Comparison between periods/groups
    TREND = "trend"                    # Trend analysis
    FORECAST = "forecast"              # Prediction/projection
    ANOMALY = "anomaly"                # Anomaly detection
    CORRELATION = "correlation"        # Correlation analysis


class OperationType(str, enum.Enum):
    """Types of operations performed."""
    SINGLE_TABLE = "single_table"
    CROSS_TABLE = "cross_table"
    TEMPORAL = "temporal"


class AnalysisStatus(str, enum.Enum):
    """Status of the analysis."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResult(Base):
    """
    Analysis result model.
    
    Captures the entire LangGraph pipeline execution:
    
    1. Input: user query
    2. Planning: intent, operation type, files needed
    3. Execution: generated code, results
    4. Output: explanation, recommendations
    """
    
    __tablename__ = "analysis_results"
    
    # ----- Foreign Keys -----
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # ----- Status -----
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, values_callable=lambda x: [e.value for e in x]),
        default=AnalysisStatus.PENDING,
        nullable=False,
    )
    
    # ----- Input -----
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    
    # ----- Analysis Planning (from LLM) -----
    intent: Mapped[Optional[AnalysisIntent]] = mapped_column(
        Enum(AnalysisIntent, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    
    operation_type: Mapped[Optional[OperationType]] = mapped_column(
        Enum(OperationType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    
    # Files used in analysis
    files_used: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    # Full analysis plan from LLM (JSON)
    plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # ----- Code Generation -----
    generated_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_valid: Mapped[bool] = mapped_column(default=False)
    
    # ----- Execution Results -----
    # The actual result data (DataFrame as JSON, or aggregated values)
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Error message if execution failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Execution time in milliseconds
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # ----- Output -----
    # Natural language explanation
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Actionable recommendations
    recommendations: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    # ----- LangGraph Tracing -----
    # Track which nodes were executed
    node_history: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    
    # Full LangGraph state for debugging
    langgraph_trace: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # ----- Relationships -----
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="analysis_results",
    )
    
    # Messages that reference this analysis
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="analysis",
    )
    
    def __repr__(self) -> str:
        query_preview = self.user_query[:30] + "..." if len(self.user_query) > 30 else self.user_query
        return f"<AnalysisResult(id={self.id}, status={self.status.value}, query={query_preview})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "status": self.status.value,
            "user_query": self.user_query,
            "intent": self.intent.value if self.intent else None,
            "operation_type": self.operation_type.value if self.operation_type else None,
            "files_used": self.files_used,
            "result_data": self.result_data,
            "explanation": self.explanation,
            "recommendations": self.recommendations,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

