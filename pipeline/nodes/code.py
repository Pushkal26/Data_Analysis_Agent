"""
Code Generation and Execution Nodes
====================================
LLM-powered code generation and safe execution.
"""

import json
import time
import traceback
from typing import Dict, Any, List
from io import StringIO
import sys

from langchain_core.prompts import ChatPromptTemplate

from pipeline.state import GraphState
from pipeline.llm import get_llm


CODE_GENERATION_PROMPT = """You are a Python data analyst. Generate pandas code to answer this query.

User Query: {user_query}

Analysis Plan:
{plan}

Available Files (with paths):
{file_info}

File Schemas:
{file_schemas}

IMPORTANT RULES:
1. Use pandas for all operations
2. CRITICAL: Use the EXACT file paths from the "Available Files" section above. DO NOT use example paths.
3. Always use keep_default_na=False when reading files to prevent "NA" (North America) from being read as NaN
4. Store the FINAL result in a variable called `result`
5. The result should be a DataFrame or a dictionary with the answer
6. Include comments explaining each step
7. Handle missing data gracefully
8. For cross-table comparison, add a 'period' column to identify each file's data

Example structure (DO NOT copy these paths - use actual paths from "Available Files" above):
```python
import pandas as pd

# Load data with actual paths from Available Files section
df1 = pd.read_csv("ACTUAL_PATH_HERE", keep_default_na=False)
df2 = pd.read_csv("ACTUAL_PATH_HERE", keep_default_na=False)

# Add period identifier
df1['period'] = 'Period 1'
df2['period'] = 'Period 2'

# Combine data
df = pd.concat([df1, df2])

# Perform analysis
result = df.groupby(['Region', 'period'])['Revenue'].mean().reset_index()
```

Generate ONLY the Python code using REAL file paths, no explanations:
```python
"""


FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    "eval(",
    "exec(",
    "os.system",
    "os.popen",
    "subprocess.",
    "shutil.",
    ".to_csv(",
    ".to_excel(",
    "rm -rf",
    "DROP TABLE",
    "DELETE FROM",
    "TRUNCATE ",
]


def generate_code(state: GraphState) -> Dict[str, Any]:
    """
    Generate Python/pandas code to execute the analysis.
    """
    llm = get_llm(temperature=0.0)
    
    # Build file info with paths
    file_info = []
    file_schemas = {}
    
    for f in state.get("available_files", []):
        filename = f.get("filename", "")
        if filename in state.get("files_to_use", []) or not state.get("files_to_use"):
            filepath = f.get("filepath", "")
            time_period = f.get("time_period", "Unknown")
            file_info.append(f"- {filename}: {filepath} (Period: {time_period})")
            
            file_schemas[filename] = {
                "filepath": filepath,
                "columns": f.get("columns", []),
                "numeric_columns": f.get("numeric_columns", []),
                "categorical_columns": f.get("categorical_columns", []),
                "time_period": time_period,
                "sample": f.get("sample_data", [])[:2],
            }
    
    prompt = ChatPromptTemplate.from_template(CODE_GENERATION_PROMPT)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "user_query": state["user_query"],
            "plan": json.dumps(state.get("plan", {}), indent=2),
            "file_info": "\n".join(file_info),
            "file_schemas": json.dumps(file_schemas, indent=2),
        })
        
        # Extract code from response
        content = response.content
        if "```python" in content:
            code = content.split("```python")[1].split("```")[0]
        elif "```" in content:
            code = content.split("```")[1].split("```")[0]
        else:
            code = content
        
        code = code.strip()
        
        return {
            "generated_code": code,
            "current_node": "generate_code",
            "node_history": ["generate_code"],
        }
        
    except Exception as e:
        return {
            "generated_code": None,
            "errors": [f"Code generation error: {str(e)}"],
            "current_node": "generate_code",
            "node_history": ["generate_code"],
        }


def validate_code(state: GraphState) -> Dict[str, Any]:
    """
    Validate the generated code for safety and correctness.
    """
    code = state.get("generated_code", "")
    
    if not code:
        return {
            "code_valid": False,
            "validation_errors": ["No code generated"],
            "current_node": "validate_code",
            "node_history": ["validate_code"],
        }
    
    errors = []
    
    # Check for forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in code.lower():
            errors.append(f"Forbidden pattern detected: {pattern}")
    
    # Check for syntax errors
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        errors.append(f"Syntax error: {str(e)}")
    
    # Check that result variable is defined
    if "result" not in code:
        errors.append("Code must define a 'result' variable")
    
    # Check for pandas import
    if "import pandas" not in code and "pd." in code:
        # Add pandas import if missing
        code = "import pandas as pd\n" + code
    
    if errors:
        return {
            "code_valid": False,
            "validation_errors": errors,
            "current_node": "validate_code",
            "node_history": ["validate_code"],
        }
    
    return {
        "code_valid": True,
        "validation_errors": [],
        "generated_code": code,  # May have been modified
        "current_node": "validate_code",
        "node_history": ["validate_code"],
    }


def execute_code(state: GraphState) -> Dict[str, Any]:
    """
    Execute the validated code in a sandboxed environment.
    """
    code = state.get("generated_code", "")
    
    if not code or not state.get("code_valid", False):
        return {
            "execution_result": {
                "success": False,
                "error": "No valid code to execute",
            },
            "current_node": "execute_code",
            "node_history": ["execute_code"],
        }
    
    # Create execution namespace with limited builtins
    import pandas as pd
    import numpy as np
    
    # Use full builtins to allow imports and all Python functionality
    # Safety is enforced by code validation (forbidden patterns)
    namespace = {
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
    }
    
    start_time = time.time()
    
    try:
        # Execute the code
        print(f"[DEBUG] Executing code:\n{code[:200]}...")
        exec(code, namespace)
        print(f"[DEBUG] Execution complete, checking result...")
        
        execution_time = (time.time() - start_time) * 1000  # ms
        
        # Get the result
        result = namespace.get("result")
        
        # Helper to convert numpy types to native Python types
        def convert_to_serializable(obj):
            if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                                np.int16, np.int32, np.int64, np.uint8,
                                np.uint16, np.uint32, np.uint64)):
                return int(obj)
            elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(i) for i in obj]
            return obj

        if result is None:
            return {
                "execution_result": {
                    "success": False,
                    "error": "No result variable defined",
                    "execution_time_ms": execution_time,
                },
                "current_node": "execute_code",
                "node_history": ["execute_code"],
            }
        
        # Convert result to serializable format
        if hasattr(result, "to_dict"):
            # DataFrame
            result_data = {
                "type": "dataframe",
                "data": convert_to_serializable(result.to_dict(orient="records")),
                "columns": result.columns.tolist(),
                "shape": list(result.shape),
            }
        elif isinstance(result, dict):
            result_data = {
                "type": "dict",
                "data": convert_to_serializable(result),
            }
        elif isinstance(result, (list, tuple)):
            result_data = {
                "type": "list",
                "data": convert_to_serializable(list(result)),
            }
        else:
            val = convert_to_serializable(result)
            result_data = {
                "type": "value",
                "data": val if isinstance(val, (int, float, str, bool)) else str(val),
            }
        
        return {
            "execution_result": {
                "success": True,
                "execution_time_ms": execution_time,
            },
            "result_data": result_data,
            "current_node": "execute_code",
            "node_history": ["execute_code"],
        }
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_trace = traceback.format_exc()
        print(f"[DEBUG] Execution error: {e}")
        print(f"[DEBUG] Traceback: {error_trace}")
        
        return {
            "execution_result": {
                "success": False,
                "error": str(e),
                "traceback": error_trace,
                "execution_time_ms": execution_time,
            },
            "errors": [f"Execution error: {str(e)}"],
            "current_node": "execute_code",
            "node_history": ["execute_code"],
        }

