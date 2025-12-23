"""
LangGraph State Definition
==========================
Defines the state that flows through the LangGraph nodes.

The state contains all information needed for:
- Input query and context
- File metadata and data
- Analysis plan and operations
- Generated code and results
- Final explanation
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator


class OperationType(str, Enum):
    """Types of operations that can be performed on data."""
    SINGLE_TABLE = "single_table"      # Operations on one file
    CROSS_TABLE = "cross_table"        # Operations across multiple files
    TEMPORAL = "temporal"              # Time-based analysis


class AnalysisIntent(str, Enum):
    """Types of user intents for analysis."""
    QUERY = "query"                    # Simple data query
    AGGREGATE = "aggregate"            # Aggregation (sum, avg, etc.)
    COMPARE = "compare"                # Comparison between periods/groups
    TREND = "trend"                    # Trend analysis
    FORECAST = "forecast"              # Prediction/projection
    ANOMALY = "anomaly"                # Anomaly detection
    CORRELATION = "correlation"        # Correlation analysis


@dataclass
class FileInfo:
    """Information about an uploaded file."""
    id: int
    filename: str
    filepath: str
    time_period: Optional[str] = None
    time_period_type: Optional[str] = None
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    date_columns: List[str] = field(default_factory=list)
    schema: Dict[str, str] = field(default_factory=dict)


@dataclass
class AnalysisPlan:
    """Plan for analyzing data based on user query."""
    intent: str
    operation_type: str
    files_needed: List[str]
    operations: List[str]
    group_by: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    time_alignment_needed: bool = False
    reasoning: str = ""


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0


class GraphState(TypedDict):
    """
    The main state object that flows through LangGraph.
    
    This TypedDict defines all fields that can be accessed
    and modified by nodes in the graph.
    """
    
    # ----- Input -----
    session_id: str
    user_query: str
    chat_history: List[Dict[str, str]]
    
    # ----- File Context -----
    available_files: List[Dict[str, Any]]
    file_data: Dict[str, Any]  # filename -> DataFrame as dict
    
    # ----- File Parsing -----
    parsed_files: List[Dict[str, Any]]
    common_columns: List[str]
    all_numeric_columns: List[str]
    all_categorical_columns: List[str]
    
    # ----- Analysis Planning -----
    intent: Optional[str]
    operation_type: Optional[str]
    plan: Optional[Dict[str, Any]]
    files_to_use: List[str]
    
    # ----- Temporal Alignment -----
    alignment_info: Optional[Dict[str, Any]]
    
    # ----- Code Generation -----
    generated_code: Optional[str]
    code_valid: bool
    validation_errors: List[str]
    
    # ----- Execution -----
    execution_result: Optional[Dict[str, Any]]
    result_data: Optional[Any]
    
    # ----- Trend Analysis -----
    trend_insights: Optional[Dict[str, Any]]
    
    # ----- Output -----
    explanation: Optional[str]
    recommendations: List[str]
    final_response: Optional[str]
    
    # ----- Metadata -----
    current_node: str
    node_history: Annotated[List[str], operator.add]  # Append-only
    errors: Annotated[List[str], operator.add]  # Append-only
    retry_count: int


def create_initial_state(
    session_id: str,
    user_query: str,
    available_files: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> GraphState:
    """Create initial state for a new analysis."""
    return GraphState(
        session_id=session_id,
        user_query=user_query,
        chat_history=chat_history or [],
        available_files=available_files,
        file_data={},
        # File parsing
        parsed_files=[],
        common_columns=[],
        all_numeric_columns=[],
        all_categorical_columns=[],
        # Analysis planning
        intent=None,
        operation_type=None,
        plan=None,
        files_to_use=[],
        alignment_info=None,
        # Code generation
        generated_code=None,
        code_valid=False,
        validation_errors=[],
        # Execution
        execution_result=None,
        result_data=None,
        # Trend analysis
        trend_insights=None,
        # Output
        explanation=None,
        recommendations=[],
        final_response=None,
        # Metadata
        current_node="start",
        node_history=[],
        errors=[],
        retry_count=0,
    )
