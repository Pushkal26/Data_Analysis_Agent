"""
LangGraph Nodes Package
=======================
All node implementations for the analysis pipeline.

Nodes:
- parse_files: Extract schemas, align columns
- ingest_query: Store query in state
- retrieve_context: Load file metadata
- analyze_intent: Determine user intent (aggregate, compare, etc.)
- plan_analysis: Create analysis plan
- align_timeseries: Align tables by time period
- generate_code: LLM generates pandas code
- validate_code: Check for dangerous patterns
- execute_code: Run code in sandbox
- trend_analysis: Detect patterns, anomalies, growth
- explain_result: Generate natural language explanation
- return_chat: Format final response
- handle_error: Handle failures gracefully
"""

from pipeline.nodes.ingest import ingest_query, retrieve_context
from pipeline.nodes.planning import analyze_intent, plan_analysis
from pipeline.nodes.code import generate_code, validate_code, execute_code
from pipeline.nodes.explain import explain_result, return_chat, handle_error
from pipeline.nodes.timeseries import parse_files, align_timeseries, trend_analysis

__all__ = [
    # Ingestion
    "parse_files",
    "ingest_query",
    "retrieve_context",
    # Planning
    "analyze_intent",
    "plan_analysis",
    "align_timeseries",
    # Code
    "generate_code",
    "validate_code",
    "execute_code",
    # Analysis
    "trend_analysis",
    "explain_result",
    # Output
    "return_chat",
    "handle_error",
]
