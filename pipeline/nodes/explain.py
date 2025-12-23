"""
Explanation and Output Nodes
============================
LLM-powered result explanation and response formatting.
"""

import json
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate

from pipeline.state import GraphState
from pipeline.llm import get_llm


EXPLANATION_PROMPT = """You are a data analyst explaining results to a business user.

User Query: {user_query}

Analysis Result:
{result_data}

Files Used: {files_used}
Analysis Type: {analysis_type}

Generate a clear, actionable explanation:
1. Start with a direct answer to the query
2. Highlight key insights (biggest movers, notable trends, etc.)
3. Provide 1-2 actionable recommendations
4. Use specific numbers from the data
5. CRITICAL: Ensure strict spacing between all words and numbers.
   - WRONG: "$100to$200"
   - RIGHT: "$100 to $200"
   - WRONG: "growthof5%in"
   - RIGHT: "growth of 5% in"

Keep the explanation concise (3-5 sentences for the main insight, 1-2 bullet points for recommendations).

Format your response as:
**Key Finding:** [Main insight with specific numbers]

**Details:**
[2-3 supporting observations]

**Recommendations:**
- [Action 1]
- [Action 2]

Your response:"""


def explain_result(state: GraphState) -> Dict[str, Any]:
    """
    Generate a natural language explanation of the results.
    """
    result_data = state.get("result_data", {})
    execution_result = state.get("execution_result", {})
    
    # Handle execution errors
    if not execution_result.get("success", False):
        error = execution_result.get("error", "Unknown error")
        return {
            "explanation": f"I encountered an error while analyzing your data: {error}",
            "recommendations": ["Please try rephrasing your question", 
                              "Make sure the data contains the columns you're asking about"],
            "current_node": "explain_result",
            "node_history": ["explain_result"],
        }
    
    if not result_data:
        return {
            "explanation": "No results were generated from the analysis.",
            "recommendations": ["Please try a different query"],
            "current_node": "explain_result",
            "node_history": ["explain_result"],
        }
    
    llm = get_llm(temperature=0.3)  # Slightly higher temp for more natural language
    
    # Get files used
    files_used = state.get("files_to_use", [])
    analysis_type = f"{state.get('intent', 'query')} ({state.get('operation_type', 'single_table')})"
    
    prompt = ChatPromptTemplate.from_template(EXPLANATION_PROMPT)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "user_query": state["user_query"],
            "result_data": json.dumps(result_data, indent=2, default=str)[:3000],  # Limit size
            "files_used": ", ".join(files_used),
            "analysis_type": analysis_type,
        })
        
        explanation = response.content
        
        # Extract recommendations if present
        recommendations = []
        if "**Recommendations:**" in explanation:
            parts = explanation.split("**Recommendations:**")
            explanation_body = parts[0].strip()  # Keep only the part before Recommendations
            
            rec_section = parts[1]
            for line in rec_section.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    recommendations.append(line[2:])
                elif line.startswith("* "):
                    recommendations.append(line[2:])
            
            # Update explanation to exclude the raw recommendations text
            explanation = explanation_body
        
        return {
            "explanation": explanation,
            "recommendations": recommendations or ["Consider exploring related metrics"],
            "current_node": "explain_result",
            "node_history": ["explain_result"],
        }
        
    except Exception as e:
        # Fallback explanation
        return {
            "explanation": f"Analysis complete. Here are the results based on your query.",
            "recommendations": ["Review the data table for detailed insights"],
            "errors": [f"Explanation generation error: {str(e)}"],
            "current_node": "explain_result",
            "node_history": ["explain_result"],
        }


def return_chat(state: GraphState) -> Dict[str, Any]:
    """
    Format the final response for the chat interface.
    """
    explanation = state.get("explanation", "")
    result_data = state.get("result_data", {})
    recommendations = state.get("recommendations", [])
    errors = state.get("errors", [])
    
    # Build final response
    if errors and not explanation:
        final_response = "I encountered some issues while processing your request:\n"
        final_response += "\n".join(f"- {e}" for e in errors)
    else:
        final_response = explanation
    
    # Add data summary if available
    if result_data and result_data.get("type") == "dataframe":
        data = result_data.get("data", [])
        if data:
            final_response += f"\n\n📊 *Result: {len(data)} rows returned*"
    
    return {
        "final_response": final_response,
        "current_node": "return_chat",
        "node_history": ["return_chat"],
    }


def handle_error(state: GraphState) -> Dict[str, Any]:
    """
    Handle errors and prepare error response.
    """
    errors = state.get("errors", [])
    validation_errors = state.get("validation_errors", [])
    
    all_errors = errors + validation_errors
    
    if not all_errors:
        all_errors = ["An unknown error occurred during analysis"]
    
    error_message = "I wasn't able to complete your analysis:\n\n"
    error_message += "\n".join(f"• {e}" for e in all_errors[:3])  # Show first 3 errors
    error_message += "\n\nPlease try rephrasing your question or check if the data contains the requested columns."
    
    return {
        "explanation": error_message,
        "final_response": error_message,
        "recommendations": [
            "Try a simpler query first",
            "Check available column names in your files"
        ],
        "current_node": "handle_error",
        "node_history": ["handle_error"],
    }

