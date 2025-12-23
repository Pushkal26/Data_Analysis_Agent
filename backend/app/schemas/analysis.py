"""
Analysis Schemas
================
Pydantic models for analysis-related API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AnalysisPlanResponse(BaseModel):
    """LLM-generated analysis plan."""
    
    intent: Literal["query", "aggregate", "compare", "trend", "forecast", "anomaly", "correlation"]
    operation_type: Literal["single_table", "cross_table", "temporal"]
    files_needed: List[str]
    operations: List[str]
    reasoning: str
    
    # For cross-table operations
    time_alignment_needed: bool = False
    group_by: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    """Response body for analysis results."""
    
    id: int
    status: Literal["pending", "running", "completed", "failed"]
    user_query: str
    
    # Analysis details
    intent: Optional[str] = None
    operation_type: Optional[str] = None
    files_used: List[str]
    
    # Results
    result_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Analysis results (DataFrame as dict, aggregated values, etc.)",
    )
    
    # Explanation
    explanation: Optional[str] = Field(
        None,
        description="Natural language explanation of results",
    )
    
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations",
    )
    
    # Execution info
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    """Response body for listing analyses."""
    
    session_id: str
    analyses: List[AnalysisResponse]
    total_count: int


class AnalysisDebugResponse(BaseModel):
    """Debug information for an analysis (development only)."""
    
    id: int
    user_query: str
    
    # LangGraph execution trace
    node_history: List[str]
    langgraph_trace: Optional[Dict[str, Any]] = None
    
    # Generated code
    generated_code: Optional[str] = None
    code_valid: bool = False
    
    # Full plan
    plan: Optional[Dict[str, Any]] = None

