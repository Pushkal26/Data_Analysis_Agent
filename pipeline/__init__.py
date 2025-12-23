"""
LangGraph Orchestration Package
===============================
Provides the analysis pipeline for "Talk to Your Data".

Usage:
    from langgraph import run_analysis_sync
    
    result = run_analysis_sync(
        session_id="...",
        user_query="What is the average revenue by region?",
        available_files=[...],
    )
"""

from pipeline.state import GraphState, create_initial_state
from pipeline.graph import build_graph, create_app, get_app, run_analysis, run_analysis_sync
from pipeline.llm import get_llm, get_llm_singleton

__all__ = [
    "GraphState",
    "create_initial_state",
    "build_graph",
    "create_app",
    "get_app",
    "run_analysis",
    "run_analysis_sync",
    "get_llm",
    "get_llm_singleton",
]
