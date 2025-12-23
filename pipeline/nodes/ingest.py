"""
Ingest and Context Nodes
========================
Handles query parsing and file context retrieval.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any

from pipeline.state import GraphState


def ingest_query(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate the incoming user query.
    
    This node:
    1. Validates the query is not empty
    2. Cleans up the query text
    3. Logs the query for tracing
    """
    query = state["user_query"].strip()
    
    if not query:
        return {
            "errors": ["Empty query provided"],
            "current_node": "ingest_query",
            "node_history": ["ingest_query"],
        }
    
    return {
        "user_query": query,
        "current_node": "ingest_query",
        "node_history": ["ingest_query"],
    }


def retrieve_context(state: GraphState) -> Dict[str, Any]:
    """
    Load file data into memory for analysis.
    
    This node:
    1. Reads file metadata from state
    2. Loads actual file data using pandas
    3. Stores data in state for later use
    """
    available_files = state.get("available_files", [])
    file_data = {}
    
    for file_info in available_files:
        filepath = file_info.get("filepath")
        filename = file_info.get("filename")
        
        if not filepath or not Path(filepath).exists():
            continue
        
        try:
            # Load the file
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
            elif filepath.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                continue
            
            # Store as dict for JSON serialization
            file_data[filename] = {
                "columns": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "row_count": len(df),
                "sample": df.head(3).to_dict(orient='records'),
            }
            
        except Exception as e:
            # Log error but continue with other files
            pass
    
    return {
        "file_data": file_data,
        "current_node": "retrieve_context",
        "node_history": ["retrieve_context"],
    }

