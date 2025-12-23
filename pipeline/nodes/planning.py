"""
Planning Nodes
==============
LLM-powered intent analysis and plan generation.
"""

import json
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from pipeline.state import GraphState
from pipeline.llm import get_llm


INTENT_ANALYSIS_PROMPT = """You are a data analysis assistant. Analyze the user's query and determine:

1. **Intent**: What type of analysis does the user want?
   - query: Simple data lookup
   - aggregate: Sum, average, count, etc.
   - compare: Compare values across groups/periods
   - trend: Analyze trends over time
   - forecast: Predict future values
   - anomaly: Detect outliers
   - correlation: Find relationships between variables

2. **Operation Type**: 
   - single_table: Analysis on one file only
   - cross_table: Analysis across multiple files
   - temporal: Time-based comparison (MoM, YoY, etc.)

3. **Files Needed**: Which files are relevant based on time periods mentioned?

Available files:
{available_files}

User Query: {user_query}

Chat History:
{chat_history}

Respond with a JSON object:
{{
    "intent": "ONE OF: query, aggregate, compare, trend, forecast, anomaly, correlation",
    "operation_type": "ONE OF: single_table, cross_table, temporal",
    "files_needed": ["filename1.csv", "filename2.csv"],
    "reasoning": "Brief explanation of your analysis"
}}

JSON Response:"""


PLAN_ANALYSIS_PROMPT = """You are a data analysis planner. Create a detailed analysis plan.

User Query: {user_query}
Intent: {intent}
Operation Type: {operation_type}

Available Files:
{available_files}

File Schemas:
{file_schemas}

Create a step-by-step plan for analyzing this data. Consider:
- Which columns to use
- Any grouping needed (group_by)
- Any filtering needed
- For cross-table: how to join/align data
- What calculations to perform

Respond with a JSON object:
{{
    "operations": [
        "Step 1: Load files...",
        "Step 2: Group by...",
        "Step 3: Calculate..."
    ],
    "group_by": ["column1", "column2"] or null,
    "filters": {{"column": "value"}} or null,
    "time_alignment_needed": true/false,
    "columns_to_use": ["col1", "col2"],
    "aggregations": ["mean", "sum"] or null,
    "reasoning": "Explanation of the plan"
}}

JSON Response:"""


def analyze_intent(state: GraphState) -> Dict[str, Any]:
    """
    Use LLM to analyze the user's intent.
    
    Determines:
    - What type of analysis is requested
    - Whether single-table or cross-table
    - Which files are needed
    """
    llm = get_llm(temperature=0.0)
    
    # Format available files info
    files_info = []
    for f in state.get("available_files", []):
        files_info.append(f"{f.get('filename')} - {f.get('time_period', 'Unknown period')}, "
                         f"{f.get('row_count', 0)} rows, "
                         f"columns: {', '.join(f.get('columns', [])[:5])}...")
    
    # Format chat history
    history = state.get("chat_history", [])
    history_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" 
                              for m in history[-5:]])  # Last 5 messages
    
    prompt = ChatPromptTemplate.from_template(INTENT_ANALYSIS_PROMPT)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "available_files": "\n".join(files_info),
            "user_query": state["user_query"],
            "chat_history": history_text or "No previous messages",
        })
        
        # Parse JSON from response
        content = response.content
        # Try to extract JSON from the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        
        return {
            "intent": result.get("intent", "query"),
            "operation_type": result.get("operation_type", "single_table"),
            "files_to_use": result.get("files_needed", []),
            "current_node": "analyze_intent",
            "node_history": ["analyze_intent"],
        }
        
    except Exception as e:
        # Default to simple query on first file
        first_file = state.get("available_files", [{}])[0].get("filename", "")
        return {
            "intent": "query",
            "operation_type": "single_table",
            "files_to_use": [first_file] if first_file else [],
            "errors": [f"Intent analysis error: {str(e)}"],
            "current_node": "analyze_intent",
            "node_history": ["analyze_intent"],
        }


def plan_analysis(state: GraphState) -> Dict[str, Any]:
    """
    Create a detailed analysis plan based on intent.
    """
    llm = get_llm(temperature=0.0)
    
    # Get file schemas
    file_schemas = {}
    for f in state.get("available_files", []):
        if f.get("filename") in state.get("files_to_use", []):
            file_schemas[f.get("filename")] = {
                "columns": f.get("columns", []),
                "numeric_columns": f.get("numeric_columns", []),
                "categorical_columns": f.get("categorical_columns", []),
                "time_period": f.get("time_period"),
            }
    
    # Format available files
    files_info = []
    for f in state.get("available_files", []):
        files_info.append(f"{f.get('filename')} - {f.get('time_period', 'Unknown period')}")
    
    prompt = ChatPromptTemplate.from_template(PLAN_ANALYSIS_PROMPT)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "user_query": state["user_query"],
            "intent": state.get("intent", "query"),
            "operation_type": state.get("operation_type", "single_table"),
            "available_files": "\n".join(files_info),
            "file_schemas": json.dumps(file_schemas, indent=2),
        })
        
        # Parse JSON from response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        plan = json.loads(content.strip())
        
        return {
            "plan": plan,
            "current_node": "plan_analysis",
            "node_history": ["plan_analysis"],
        }
        
    except Exception as e:
        # Simple default plan
        return {
            "plan": {
                "operations": ["Load data", "Perform basic analysis"],
                "group_by": None,
                "filters": None,
                "time_alignment_needed": state.get("operation_type") == "cross_table",
                "reasoning": f"Default plan (error: {str(e)})",
            },
            "current_node": "plan_analysis",
            "node_history": ["plan_analysis"],
        }
