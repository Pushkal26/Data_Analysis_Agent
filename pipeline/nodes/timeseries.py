"""
Timeseries Nodes
================
Nodes for temporal alignment and trend analysis.
"""

from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from pipeline.state import GraphState
from pipeline.llm import get_llm_singleton


# ============================================================
# ALIGN TIMESERIES NODE
# ============================================================

ALIGN_PROMPT = ChatPromptTemplate.from_template("""
You are a data analyst preparing data for cross-table temporal analysis.

The user wants to compare data across these time periods:
{time_periods}

Available files:
{files_info}

Your task:
1. Identify common columns that can be used for alignment (e.g., Region, Product)
2. Identify the time granularity (monthly, quarterly, yearly)
3. Suggest how to align the tables for comparison
4. Identify which numeric columns to compare

Respond in JSON:
{{
    "alignment_keys": ["Region", "Product"],  // Columns to join on
    "time_column_name": "period",  // Name for the time dimension
    "time_granularity": "monthly",  // monthly, quarterly, yearly
    "numeric_columns_to_compare": ["Revenue", "Units"],
    "alignment_strategy": "left_join",  // left_join, outer_join, union
    "notes": "Brief explanation of alignment approach"
}}
""")


def align_timeseries(state: GraphState) -> Dict[str, Any]:
    """
    Align multiple tables by time period for cross-table analysis.
    
    This node:
    1. Identifies common columns across tables
    2. Determines time granularity
    3. Creates alignment strategy
    """
    files = state.get("available_files", [])
    files_to_use = state.get("files_to_use", [])
    operation_type = state.get("operation_type", "")
    
    # Only align if cross-table or temporal operation
    if operation_type not in ["cross_table", "temporal"]:
        return {
            "alignment_info": None,
            "current_node": "align_timeseries",
            "node_history": ["align_timeseries"],
        }
    
    # Get selected files info
    selected_files = [f for f in files if f.get("filename") in files_to_use]
    
    if len(selected_files) < 2:
        return {
            "alignment_info": None,
            "current_node": "align_timeseries",
            "node_history": ["align_timeseries"],
        }
    
    # Extract time periods
    time_periods = [f.get("time_period", "Unknown") for f in selected_files]
    
    # Build files info for LLM
    files_info = []
    for f in selected_files:
        files_info.append({
            "filename": f.get("filename"),
            "time_period": f.get("time_period"),
            "columns": f.get("columns", []),
            "numeric_columns": f.get("numeric_columns", []),
            "categorical_columns": f.get("categorical_columns", []),
        })
    
    try:
        llm = get_llm_singleton()
        parser = JsonOutputParser()
        chain = ALIGN_PROMPT | llm | parser
        
        alignment_info = chain.invoke({
            "time_periods": time_periods,
            "files_info": files_info,
        })
        
        return {
            "alignment_info": alignment_info,
            "current_node": "align_timeseries",
            "node_history": ["align_timeseries"],
        }
        
    except Exception as e:
        return {
            "alignment_info": {
                "error": str(e),
                "alignment_keys": [],
                "time_granularity": "unknown",
            },
            "errors": [f"Alignment error: {str(e)}"],
            "current_node": "align_timeseries",
            "node_history": ["align_timeseries"],
        }


# ============================================================
# TREND ANALYSIS NODE
# ============================================================

TREND_PROMPT = ChatPromptTemplate.from_template("""
You are a data analyst performing trend and anomaly analysis.

Query: {query}
Time periods: {time_periods}
Data summary:
{data_summary}

Execution result:
{result_data}

Analyze the data for:
1. **Trends**: Is there growth, decline, or stability?
2. **Patterns**: Seasonality, cyclical behavior?
3. **Anomalies**: Unusual spikes, drops, or outliers?
4. **Correlations**: Do any metrics move together?

Calculate where possible:
- MoM (Month-over-Month) growth %
- QoQ (Quarter-over-Quarter) growth %
- YoY (Year-over-Year) growth % if applicable

Respond in JSON:
{{
    "trends": [
        {{"metric": "Revenue", "direction": "increasing", "rate": "15% MoM", "confidence": "high"}}
    ],
    "patterns": [
        {{"type": "seasonality", "description": "Higher sales in December"}}
    ],
    "anomalies": [
        {{"metric": "Units", "period": "Dec 2024", "type": "spike", "magnitude": "2x average", "possible_cause": "holiday season"}}
    ],
    "correlations": [
        {{"metrics": ["Discount", "Revenue"], "relationship": "negative", "strength": "moderate"}}
    ],
    "growth_metrics": {{
        "mom_growth": {{"Revenue": 15.2, "Units": 8.5}},
        "qoq_growth": null,
        "yoy_growth": null
    }},
    "key_insight": "One sentence summary of the most important finding",
    "recommended_actions": [
        "Action 1 based on findings",
        "Action 2 based on findings"
    ]
}}
""")


def trend_analysis(state: GraphState) -> Dict[str, Any]:
    """
    Analyze trends, patterns, and anomalies in the data.
    
    This node:
    1. Detects growth trends (MoM, QoQ, YoY)
    2. Identifies patterns (seasonality, cycles)
    3. Flags anomalies
    4. Finds correlations
    """
    query = state.get("user_query", "")
    result_data = state.get("result_data", {})
    files = state.get("available_files", [])
    files_to_use = state.get("files_to_use", [])
    intent = state.get("intent", "")
    
    # Only run for trend/compare intents or if explicitly requested
    trend_keywords = ["trend", "growth", "change", "compare", "anomal", "pattern", "season"]
    should_analyze = (
        intent in ["trend", "compare"] or
        any(kw in query.lower() for kw in trend_keywords)
    )
    
    if not should_analyze or not result_data:
        return {
            "trend_insights": None,
            "current_node": "trend_analysis",
            "node_history": ["trend_analysis"],
        }
    
    # Get time periods
    selected_files = [f for f in files if f.get("filename") in files_to_use]
    time_periods = [f.get("time_period", "Unknown") for f in selected_files]
    
    # Build data summary
    data_summary = []
    for f in selected_files:
        data_summary.append({
            "file": f.get("filename"),
            "period": f.get("time_period"),
            "rows": f.get("row_count"),
            "numeric_cols": f.get("numeric_columns", []),
        })
    
    try:
        llm = get_llm_singleton()
        parser = JsonOutputParser()
        chain = TREND_PROMPT | llm | parser
        
        trend_insights = chain.invoke({
            "query": query,
            "time_periods": time_periods,
            "data_summary": data_summary,
            "result_data": result_data,
        })
        
        # Merge recommendations
        existing_recs = state.get("recommendations", [])
        new_recs = trend_insights.get("recommended_actions", [])
        combined_recs = existing_recs + new_recs
        
        return {
            "trend_insights": trend_insights,
            "recommendations": combined_recs[:5],  # Keep top 5
            "current_node": "trend_analysis",
            "node_history": ["trend_analysis"],
        }
        
    except Exception as e:
        return {
            "trend_insights": {"error": str(e)},
            "current_node": "trend_analysis",
            "node_history": ["trend_analysis"],
        }


# ============================================================
# PARSE FILES NODE
# ============================================================

def parse_files(state: GraphState) -> Dict[str, Any]:
    """
    Parse and validate input files, extract schemas, align columns.
    
    This is the first node in the pipeline that:
    1. Validates file availability
    2. Extracts and normalizes schemas
    3. Identifies common columns across files
    4. Prepares file metadata for downstream nodes
    """
    files = state.get("available_files", [])
    
    if not files:
        return {
            "parsed_files": [],
            "common_columns": [],
            "all_numeric_columns": [],
            "all_categorical_columns": [],
            "errors": ["No files available for analysis"],
            "current_node": "parse_files",
            "node_history": ["parse_files"],
        }
    
    # Extract schemas
    parsed_files = []
    all_columns = []
    all_numeric = []
    all_categorical = []
    
    for f in files:
        parsed = {
            "filename": f.get("filename"),
            "filepath": f.get("filepath"),
            "time_period": f.get("time_period"),
            "time_period_type": f.get("time_period_type"),
            "row_count": f.get("row_count"),
            "columns": f.get("columns", []),
            "numeric_columns": f.get("numeric_columns", []),
            "categorical_columns": f.get("categorical_columns", []),
            "date_columns": f.get("date_columns", []),
        }
        parsed_files.append(parsed)
        
        all_columns.append(set(f.get("columns", [])))
        all_numeric.extend(f.get("numeric_columns", []))
        all_categorical.extend(f.get("categorical_columns", []))
    
    # Find common columns across all files
    if all_columns:
        common_columns = list(set.intersection(*all_columns)) if len(all_columns) > 1 else list(all_columns[0])
    else:
        common_columns = []
    
    # Unique columns
    all_numeric = list(set(all_numeric))
    all_categorical = list(set(all_categorical))
    
    return {
        "parsed_files": parsed_files,
        "common_columns": common_columns,
        "all_numeric_columns": all_numeric,
        "all_categorical_columns": all_categorical,
        "current_node": "parse_files",
        "node_history": ["parse_files"],
    }

