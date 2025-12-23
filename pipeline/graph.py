"""
LangGraph Graph Definition
==========================
Defines the StateGraph that orchestrates the analysis flow.

Flow:
    ingest_query 
        → retrieve_context 
        → analyze_intent 
        → plan_analysis 
        → [align_timeseries if needed]
        → generate_code 
        → validate_code 
        → execute_code 
        → explain_result 
        → return_chat
"""

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from pipeline.state import GraphState
from pipeline.nodes import (
    ingest_query,
    retrieve_context,
    analyze_intent,
    plan_analysis,
    generate_code,
    validate_code,
    execute_code,
    explain_result,
    return_chat,
    handle_error,
)
from pipeline.nodes.timeseries import (
    parse_files,
    align_timeseries,
    trend_analysis,
)


# ----- Conditional Edge Functions -----

def should_align_timeseries(state: GraphState) -> Literal["align_timeseries", "generate_code"]:
    """Decide if time series alignment is needed."""
    plan = state.get("plan", {})
    operation_type = state.get("operation_type", "single_table")
    
    if operation_type in ["cross_table", "temporal"]:
        if plan.get("time_alignment_needed", False):
            return "align_timeseries"
    
    return "generate_code"


def check_code_validity(state: GraphState) -> Literal["execute_code", "generate_code", "handle_error"]:
    """Check if code is valid or needs regeneration."""
    if state.get("code_valid", False):
        return "execute_code"
    
    retry_count = state.get("retry_count", 0)
    if retry_count < 2:  # Allow 2 retries
        return "generate_code"
    
    return "handle_error"


def check_execution_success(state: GraphState) -> Literal["explain_result", "handle_error"]:
    """Check if execution was successful."""
    execution_result = state.get("execution_result", {})
    
    if execution_result.get("success", False):
        return "explain_result"
    
    return "handle_error"


def increment_retry(state: GraphState) -> Dict[str, Any]:
    """Increment retry counter (used before regenerating code)."""
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "node_history": ["increment_retry"],
    }


# ----- Build the Graph -----

def build_graph() -> StateGraph:
    """
    Build and return the LangGraph StateGraph.
    
    The graph follows this flow:
    
    START → ingest_query → retrieve_context → analyze_intent → plan_analysis
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    │
                    ▼
            [should_align_timeseries?]
                    │
            ┌───────┴───────┐
            ▼               ▼
    align_timeseries    generate_code
            │               │
            └───────┬───────┘
                    ▼
            validate_code
                    │
            [check_code_validity?]
                    │
            ┌───────┼───────┐
            ▼       ▼       ▼
      execute   regenerate  error
            │               
            │               
            ▼               
    [check_execution_success?]
            │
    ┌───────┴───────┐
    ▼               ▼
    explain      error
            │       │
            └───┬───┘
                ▼
            return_chat → END
    """
    
    # Create the graph with our state schema
    graph = StateGraph(GraphState)
    
    # ----- Add Nodes -----
    # Ingestion
    graph.add_node("ingest_query", ingest_query)
    graph.add_node("parse_files", parse_files)
    graph.add_node("retrieve_context", retrieve_context)
    
    # Planning
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("align_timeseries", align_timeseries)
    
    # Code generation
    graph.add_node("generate_code", generate_code)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("validate_code", validate_code)
    graph.add_node("execute_code", execute_code)
    
    # Analysis
    graph.add_node("trend_analysis", trend_analysis)
    graph.add_node("explain_result", explain_result)
    
    # Output
    graph.add_node("return_chat", return_chat)
    graph.add_node("handle_error", handle_error)
    
    # ----- Add Edges -----
    
    # Set entry point
    graph.set_entry_point("ingest_query")
    
    # Linear flow: ingest → parse_files → retrieve → analyze → plan
    graph.add_edge("ingest_query", "parse_files")
    graph.add_edge("parse_files", "retrieve_context")
    graph.add_edge("retrieve_context", "analyze_intent")
    graph.add_edge("analyze_intent", "plan_analysis")
    
    # Conditional: plan → align OR generate
    graph.add_conditional_edges(
        "plan_analysis",
        should_align_timeseries,
        {
            "align_timeseries": "align_timeseries",
            "generate_code": "generate_code",
        }
    )
    
    # align → generate
    graph.add_edge("align_timeseries", "generate_code")
    
    # generate → validate
    graph.add_edge("generate_code", "validate_code")
    
    # Conditional: validate → execute OR retry OR error
    graph.add_conditional_edges(
        "validate_code",
        check_code_validity,
        {
            "execute_code": "execute_code",
            "generate_code": "increment_retry",
            "handle_error": "handle_error",
        }
    )
    
    # increment_retry → generate_code
    graph.add_edge("increment_retry", "generate_code")
    
    # Conditional: execute → trend_analysis OR error
    graph.add_conditional_edges(
        "execute_code",
        check_execution_success,
        {
            "explain_result": "trend_analysis",  # Go to trend analysis first
            "handle_error": "handle_error",
        }
    )
    
    # trend_analysis → explain
    graph.add_edge("trend_analysis", "explain_result")
    
    # explain → return
    graph.add_edge("explain_result", "return_chat")
    
    # return → END
    graph.add_edge("return_chat", END)
    
    # error → return (with error message)
    graph.add_edge("handle_error", "return_chat")
    
    return graph


def create_app():
    """
    Create the compiled LangGraph application with memory.
    
    Returns:
        Compiled graph ready for invocation
    """
    graph = build_graph()
    
    # Add memory for conversation persistence
    memory = MemorySaver()
    
    # Compile the graph
    app = graph.compile(checkpointer=memory)
    
    return app


# Singleton instance
_app_instance = None


def get_app():
    """Get or create the singleton app instance."""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance


async def run_analysis(
    session_id: str,
    user_query: str,
    available_files: list,
    chat_history: list = None,
) -> Dict[str, Any]:
    """
    Run the analysis pipeline.
    
    Args:
        session_id: User session identifier
        user_query: The user's question
        available_files: List of file metadata dicts
        chat_history: Previous chat messages
    
    Returns:
        Final state with results
    """
    from pipeline.state import create_initial_state
    
    app = get_app()
    
    initial_state = create_initial_state(
        session_id=session_id,
        user_query=user_query,
        available_files=available_files,
        chat_history=chat_history,
    )
    
    # Run the graph
    config = {"configurable": {"thread_id": session_id}}
    
    final_state = None
    async for state in app.astream(initial_state, config):
        final_state = state
    
    # Get the last node's output
    if final_state:
        # The state is a dict with node name as key
        for node_name, node_state in final_state.items():
            if isinstance(node_state, dict):
                return node_state
    
    return initial_state


def run_analysis_sync(
    session_id: str,
    user_query: str,
    available_files: list,
    chat_history: list = None,
) -> Dict[str, Any]:
    """
    Synchronous version of run_analysis.
    """
    from pipeline.state import create_initial_state
    
    app = get_app()
    
    initial_state = create_initial_state(
        session_id=session_id,
        user_query=user_query,
        available_files=available_files,
        chat_history=chat_history,
    )
    
    # Run the graph synchronously
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        final_state = app.invoke(initial_state, config)
        
        # Ensure we return a valid dict
        if final_state is None:
            return {
                **initial_state,
                "errors": ["Analysis returned no result"],
                "final_response": "Unable to complete analysis",
            }
        
        return final_state
        
    except Exception as e:
        return {
            **initial_state,
            "errors": [str(e)],
            "final_response": f"Analysis error: {str(e)}",
        }
