# 🧠 Technical Deep Dive: Talk to Your Data

This document explains **how the entire project works** from end to end. After reading this, you'll understand every component and how they connect.

---

## 📚 Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [How a User Query Flows Through the System](#2-how-a-user-query-flows-through-the-system)
3. [Frontend (Streamlit)](#3-frontend-streamlit)
4. [Backend (FastAPI)](#4-backend-fastapi)
5. [Database (PostgreSQL)](#5-database-postgresql)
6. [The LangGraph Pipeline](#6-the-langgraph-pipeline)
7. [LLM Integration](#7-llm-integration)
8. [Caching (Redis)](#8-caching-redis)
9. [File Processing](#9-file-processing)
10. [Code Generation & Execution](#10-code-generation--execution)
11. [Key Design Decisions](#11-key-design-decisions)
12. [Common Patterns in the Code](#12-common-patterns-in-the-code)

---

## 1. The Big Picture

### What Does This Application Do?

This application lets users:
1. **Upload spreadsheets** (CSV/Excel files)
2. **Ask questions in plain English** ("What's the average revenue by region?")
3. **Get answers with charts and insights**

### How Does It Work (Simplified)?

```
User: "What is the average revenue by region?"
          ↓
    [Frontend receives question]
          ↓
    [Backend receives API request]
          ↓
    [LangGraph Pipeline starts]
          ↓
    [LLM understands the question]
          ↓
    [LLM writes Python/Pandas code]
          ↓
    [Code executes on the data]
          ↓
    [LLM explains the results]
          ↓
    [User sees answer + chart]
```

### The Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Streamlit | Web UI for upload, chat, analysis |
| Backend API | FastAPI | REST API, request handling |
| Orchestration | LangGraph | Controls the AI reasoning pipeline |
| LLM | OpenAI GPT-4 | Understands queries, writes code, explains results |
| Database | PostgreSQL | Stores sessions, files, messages, results |
| Cache | Redis | Caches results, rate limiting |
| Task Queue | Celery | Background processing (optional) |

---

## 2. How a User Query Flows Through the System

Let's trace what happens when a user asks: **"What is the average revenue by region?"**

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER ACTION                              │
│  User types "What is the average revenue by region?" in chat    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                          │
│  1. Captures the message                                         │
│  2. Sends POST request to /api/v1/chat                          │
│  3. Waits for response                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│  1. Receives request at chat.router                              │
│  2. Creates ChatService instance                                 │
│  3. Calls chat_service.process_message()                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CHAT SERVICE                                  │
│  1. Saves user message to database                               │
│  2. Fetches uploaded files for this session                      │
│  3. Checks cache for identical previous query                    │
│  4. If not cached, calls LangGraph pipeline                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH PIPELINE                            │
│                                                                  │
│  Node 1: INGEST_QUERY                                           │
│    → Stores query in state                                       │
│                                                                  │
│  Node 2: RETRIEVE_CONTEXT                                        │
│    → Loads file metadata (columns, types, sample data)           │
│                                                                  │
│  Node 3: ANALYZE_INTENT                                          │
│    → LLM determines: intent="aggregate", operation="single_table"│
│    → Selects relevant file: sales_dec_2024.csv                   │
│                                                                  │
│  Node 4: PLAN_ANALYSIS                                           │
│    → LLM creates step-by-step plan                               │
│                                                                  │
│  Node 5: GENERATE_CODE                                           │
│    → LLM writes pandas code:                                     │
│      df = pd.read_csv("sales_dec_2024.csv")                      │
│      result = df.groupby('Region')['Revenue'].mean()             │
│                                                                  │
│  Node 6: VALIDATE_CODE                                           │
│    → Checks for dangerous patterns (no os.system, etc.)          │
│                                                                  │
│  Node 7: EXECUTE_CODE                                            │
│    → Runs code in sandboxed environment                          │
│    → Gets result: {APAC: 1330.63, EU: 1326.03}                   │
│                                                                  │
│  Node 8: EXPLAIN_RESULT                                          │
│    → LLM writes natural language explanation                     │
│    → Generates recommendations                                   │
│                                                                  │
│  Node 9: RETURN_CHAT                                             │
│    → Formats final response                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACK TO CHAT SERVICE                          │
│  1. Saves analysis result to database                            │
│  2. Caches result in Redis                                       │
│  3. Saves assistant message to database                          │
│  4. Returns response to API                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                          │
│  1. Receives JSON response                                       │
│  2. Displays message in chat bubble                              │
│  3. Renders Plotly chart from result_data                        │
│  4. Shows recommendations                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Frontend (Streamlit)

### What is Streamlit?

Streamlit is a Python framework that turns Python scripts into web apps. You write Python, and it automatically creates the UI.

### File Structure

```
frontend/
├── app.py                    # Home page
├── pages/
│   ├── 1_📁_Upload.py       # File upload page
│   ├── 2_💬_Chat.py         # Chat interface
│   └── 3_📊_Analysis.py     # Analysis history
└── requirements.txt
```

### How Pages Work

Streamlit automatically creates a multi-page app from files in `pages/`. The number prefix (1_, 2_, 3_) controls the order.

### Key Concepts in the Code

**Session State** - Persists data across reruns:
```python
# Initialize once
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Use anywhere
session_id = st.session_state.session_id
```

**API Calls** - Using httpx to call backend:
```python
response = httpx.post(
    "http://localhost:8000/api/v1/chat",
    json={"session_id": session_id, "message": user_input},
    timeout=120.0
)
data = response.json()
```

**Charts** - Using Plotly for visualization:
```python
import plotly.express as px

df = pd.DataFrame(result_data["data"])
fig = px.bar(df, x="Region", y="Revenue")
st.plotly_chart(fig)
```

---

## 4. Backend (FastAPI)

### What is FastAPI?

FastAPI is a modern Python web framework for building APIs. It's fast, has automatic documentation, and uses Python type hints.

### File Structure

```
backend/app/
├── main.py              # Application entry point
├── api/                 # Route handlers
│   ├── upload.py        # POST /api/v1/upload
│   └── chat.py          # POST /api/v1/chat
├── core/                # Core utilities
│   ├── config.py        # Settings from .env
│   ├── cache.py         # Redis caching
│   └── middleware.py    # Rate limiting
├── models/              # Database models
├── schemas/             # Request/response schemas
└── services/            # Business logic
```

### How Requests Are Handled

**1. Request arrives at `main.py`:**
```python
app = FastAPI()
app.include_router(chat.router, prefix="/api/v1")
```

**2. Middleware processes it:**
```python
# Rate limiting checks
# Request timing starts
# CORS headers added
```

**3. Router handles it (`api/chat.py`):**
```python
@router.post("/chat")
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    service = ChatService(db)
    result = await service.process_message(
        request.session_id, 
        request.message
    )
    return ChatResponse(**result)
```

**4. Service does the work (`services/chat_service.py`):**
```python
class ChatService:
    async def process_message(self, session_id, message):
        # Save message
        # Get files
        # Run LangGraph
        # Save result
        # Return response
```

### Dependency Injection

FastAPI uses `Depends()` to inject dependencies:

```python
async def get_db():
    async with async_session_maker() as session:
        yield session

@router.post("/chat")
async def endpoint(db: AsyncSession = Depends(get_db)):
    # db is automatically provided
```

---

## 5. Database (PostgreSQL)

### Why PostgreSQL?

- Reliable and battle-tested
- Great for structured data
- Supports JSON columns (for flexible data)
- Async support with asyncpg

### Database Schema

```
┌─────────────────┐     ┌─────────────────┐
│    sessions     │     │ uploaded_files  │
├─────────────────┤     ├─────────────────┤
│ id              │◄────│ session_id (FK) │
│ session_id      │     │ filename        │
│ created_at      │     │ filepath        │
│ updated_at      │     │ columns (JSON)  │
└─────────────────┘     │ numeric_columns │
        │               │ time_period     │
        │               └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐
│ chat_messages   │     │analysis_results │
├─────────────────┤     ├─────────────────┤
│ session_id (FK) │     │ session_id (FK) │
│ role (user/ai)  │     │ user_query      │
│ content         │     │ intent          │
│ analysis_id(FK)─┼────►│ generated_code  │
└─────────────────┘     │ result_data     │
                        │ explanation     │
                        └─────────────────┘
```

### SQLAlchemy Models

Models define the database structure:

```python
# models/file.py
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    filename: Mapped[str] = mapped_column(String(255))
    columns: Mapped[List[str]] = mapped_column(ARRAY(String))
    numeric_columns: Mapped[List[str]] = mapped_column(ARRAY(String))
```

### Async Database Operations

We use async for non-blocking database access:

```python
async with async_session_maker() as session:
    result = await session.execute(
        select(UploadedFile).where(UploadedFile.session_id == session_id)
    )
    files = result.scalars().all()
```

---

## 6. The LangGraph Pipeline

### What is LangGraph?

LangGraph is a library for building stateful, multi-step AI applications. Think of it as a flowchart where each node is a step in your AI's reasoning process.

### Why Use LangGraph?

Without LangGraph, you'd have to manually manage:
- Which step to run next
- What data to pass between steps
- How to retry on failure
- Conditional branching

LangGraph handles all this with a graph-based approach.

### The State

All nodes share a common state dictionary:

```python
# pipeline/state.py
class GraphState(TypedDict):
    # Input
    session_id: str
    user_query: str
    available_files: List[Dict]
    
    # Processing
    intent: Optional[str]           # "aggregate", "compare", etc.
    operation_type: Optional[str]   # "single_table", "cross_table"
    files_to_use: List[str]         # Selected files
    plan: Optional[Dict]            # Step-by-step plan
    
    # Code generation
    generated_code: Optional[str]   # Python/pandas code
    code_valid: bool                # Passed validation?
    
    # Results
    execution_result: Optional[Dict]
    result_data: Optional[Dict]     # The actual data
    explanation: Optional[str]      # Natural language explanation
    recommendations: List[str]      # Actionable insights
    
    # Control
    current_node: str
    retry_count: int
    errors: List[str]
```

### The Nodes

Each node is a function that:
1. Receives the current state
2. Does some processing
3. Returns updates to the state

```python
# Example node
def analyze_intent(state: GraphState) -> Dict[str, Any]:
    query = state["user_query"]
    files = state["available_files"]
    
    # Call LLM to understand intent
    response = llm.invoke(prompt.format(query=query, files=files))
    
    # Return state updates
    return {
        "intent": response["intent"],
        "operation_type": response["operation_type"],
        "files_to_use": response["files"],
    }
```

### The Graph

The graph defines how nodes connect:

```python
# pipeline/graph.py
from langgraph.graph import StateGraph

# Create graph
graph = StateGraph(GraphState)

# Add nodes
graph.add_node("ingest_query", ingest_query)
graph.add_node("retrieve_context", retrieve_context)
graph.add_node("analyze_intent", analyze_intent)
graph.add_node("plan_analysis", plan_analysis)
graph.add_node("generate_code", generate_code)
graph.add_node("validate_code", validate_code)
graph.add_node("execute_code", execute_code)
graph.add_node("explain_result", explain_result)
graph.add_node("return_chat", return_chat)

# Add edges (connections)
graph.add_edge("ingest_query", "retrieve_context")
graph.add_edge("retrieve_context", "analyze_intent")
graph.add_edge("analyze_intent", "plan_analysis")
graph.add_edge("plan_analysis", "generate_code")
graph.add_edge("generate_code", "validate_code")

# Conditional edge (branching)
graph.add_conditional_edges(
    "validate_code",
    should_execute_or_retry,  # Function that decides
    {
        "execute": "execute_code",
        "retry": "generate_code",
        "error": "handle_error",
    }
)
```

### Visual Representation

```
START
  │
  ▼
┌─────────────────┐
│  ingest_query   │  ← Store query in state
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│retrieve_context │  ← Load file metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ analyze_intent  │  ← LLM: What does user want?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  plan_analysis  │  ← LLM: Create step-by-step plan
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  generate_code  │  ← LLM: Write pandas code
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  validate_code  │  ← Check for dangerous patterns
└────────┬────────┘
         │
    ┌────┴────┐
    │ Valid?  │
    └────┬────┘
     Yes │ No
         │  └──────────────┐
         ▼                 ▼
┌─────────────────┐  ┌──────────┐
│  execute_code   │  │  RETRY   │──→ back to generate_code
└────────┬────────┘  └──────────┘
         │
         ▼
┌─────────────────┐
│ explain_result  │  ← LLM: Explain in natural language
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  return_chat    │  ← Format final response
└────────┬────────┘
         │
         ▼
        END
```

---

## 7. LLM Integration

### How We Use the LLM

The LLM (GPT-4) is called at several points:

| Node | LLM Task |
|------|----------|
| `analyze_intent` | Understand what user wants |
| `plan_analysis` | Create analysis plan |
| `generate_code` | Write pandas code |
| `explain_result` | Explain results in English |

### LLM Configuration

```python
# pipeline/llm.py
from langchain_openai import ChatOpenAI

def get_llm(temperature: float = 0.0):
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,  # 0 = deterministic
        api_key=settings.openai_api_key,
    )
```

### Prompt Engineering

Each LLM call uses a carefully crafted prompt:

```python
# Intent analysis prompt
INTENT_PROMPT = """
You are a data analyst. Analyze this user query and determine:
1. Intent: aggregate, compare, query, trend, or visualize
2. Operation type: single_table, cross_table, or temporal
3. Which files to use

User Query: {query}

Available Files:
{files}

Respond in JSON format:
{{"intent": "...", "operation_type": "...", "files": [...]}}
"""
```

### Structured Output

We use JSON output parsing for reliability:

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()
chain = prompt | llm | parser

result = chain.invoke({"query": user_query, "files": file_info})
# result is already a Python dict
```

---

## 8. Caching (Redis)

### What is Redis?

Redis is an in-memory data store. It's extremely fast because data lives in RAM, not on disk.

### Why Cache?

LLM calls are expensive ($) and slow (~30 seconds). If the same query is asked twice, we return the cached result instantly.

### What We Cache

| Data | TTL | Purpose |
|------|-----|---------|
| Session files | 2 hours | Avoid DB queries |
| Analysis results | 30 min | Avoid LLM calls |
| Rate limit counters | 1 min/1 hr | Track request counts |

### How Caching Works

```python
# Before running LangGraph
cached = await cache.get_analysis_result(session_id, query, file_ids)
if cached:
    return cached  # Instant response!

# After running LangGraph
result = run_analysis(...)
await cache.set_analysis_result(session_id, query, file_ids, result)
```

### Cache Keys

```
file:session123:file456       → File metadata
files:session123              → List of files
analysis:session123:abc123    → Analysis result (query hash)
ratelimit:minute:192.168.1.1  → Request count
```

---

## 9. File Processing

### Upload Flow

```
User uploads file
       │
       ▼
┌─────────────────┐
│  Save to disk   │  → /uploads/{session_id}/{timestamp}_{filename}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parse file     │  → pd.read_csv() or pd.read_excel()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract schema  │  → Detect column types
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Detect time period│ → "Nov 2024" from "sales_nov_2024.csv"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Save to DB     │  → Store metadata in uploaded_files table
└─────────────────┘
```

### Schema Extraction

```python
def _extract_schema(self, df: pd.DataFrame) -> Dict:
    schema = {
        "columns": df.columns.tolist(),
        "numeric_columns": [],
        "categorical_columns": [],
        "date_columns": [],
    }
    
    for col in df.columns:
        dtype = df[col].dtype
        
        if pd.api.types.is_numeric_dtype(dtype):
            schema["numeric_columns"].append(col)
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            schema["date_columns"].append(col)
        else:
            # Try to parse as date
            try:
                pd.to_datetime(df[col])
                schema["date_columns"].append(col)
            except:
                schema["categorical_columns"].append(col)
    
    return schema
```

### Time Period Detection

```python
def _detect_time_period(self, filename: str) -> Tuple[str, str]:
    # "sales_nov_2024.csv" → ("Nov 2024", "monthly")
    # "report_q1_2025.xlsx" → ("Q1 2025", "quarterly")
    # "data_2024.csv" → ("2024", "yearly")
    
    patterns = {
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[_-]?(\d{4})': 'monthly',
        r'q([1-4])[_-]?(\d{4})': 'quarterly',
        r'(\d{4})': 'yearly',
    }
    # ... pattern matching logic
```

---

## 10. Code Generation & Execution

### How Code is Generated

The LLM writes pandas code based on:
1. User's query
2. Available columns and types
3. File paths

```python
CODE_GENERATION_PROMPT = """
Write Python code to answer this query: {query}

Available file: {filepath}
Columns: {columns}
Numeric columns: {numeric_columns}

Requirements:
- Use pandas
- Store final result in variable called 'result'
- Result should be a DataFrame or simple value

Code:
"""
```

### Example Generated Code

For query "Average revenue by region":

```python
import pandas as pd

df = pd.read_csv('/path/to/sales_dec_2024.csv')
result = df.groupby('Region')['Revenue'].mean().reset_index()
result.columns = ['Region', 'Avg_Revenue']
```

### Code Validation

Before execution, we check for dangerous patterns:

```python
FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "eval(",
    "exec(",
    "os.system",
    "__import__",
    ".to_csv(",      # Don't write files
    "DELETE ",       # No SQL injection
]

def validate_code(state: GraphState) -> Dict:
    code = state["generated_code"]
    
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code:
            return {"code_valid": False, "errors": [f"Forbidden: {pattern}"]}
    
    return {"code_valid": True}
```

### Sandboxed Execution

Code runs in a restricted environment:

```python
def execute_code(state: GraphState) -> Dict:
    code = state["generated_code"]
    
    # Limited namespace - only safe functions
    namespace = {
        "pd": pd,
        "np": np,
        "__builtins__": {
            "len": len, "range": range, "list": list,
            "dict": dict, "str": str, "int": int,
            "float": float, "sum": sum, "min": min,
            "max": max, "round": round, "sorted": sorted,
            # ... other safe built-ins
        },
    }
    
    exec(code, namespace)
    result = namespace.get("result")
    
    # Convert to serializable format
    if hasattr(result, "to_dict"):
        return {"result_data": result.to_dict(orient="records")}
```

---

## 11. Key Design Decisions

### Why Streamlit Instead of React?

| Streamlit | React |
|-----------|-------|
| Python only | JavaScript/TypeScript |
| Quick to build | More development time |
| Less customizable | Fully customizable |
| Built-in widgets | Need to build everything |

**Decision**: User requested Streamlit for simplicity and Python familiarity.

### Why LangGraph Instead of Simple Chains?

| Simple Chain | LangGraph |
|--------------|-----------|
| Linear flow only | Complex branching |
| Hard to retry | Built-in retry logic |
| No state management | Shared state across nodes |
| No conditional edges | Dynamic routing |

**Decision**: LangGraph provides structure for our multi-step analysis.

### Why Async Everywhere?

Async allows handling many requests without blocking:

```python
# Sync - blocks everything while waiting
result = db.execute(query)  # 100ms wait

# Async - can handle other requests while waiting
result = await db.execute(query)  # Other requests handled during wait
```

### Why Store Generated Code?

1. **Debugging**: See exactly what was run
2. **Reproducibility**: Re-run the same analysis
3. **Learning**: Users can learn pandas from examples
4. **Audit trail**: Know how results were computed

---

## 12. Common Patterns in the Code

### Pattern 1: Dependency Injection

```python
# Define how to create dependency
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

# Use it automatically
@router.post("/endpoint")
async def handler(db: AsyncSession = Depends(get_db)):
    # db is ready to use
```

### Pattern 2: Service Layer

Business logic lives in services, not routes:

```python
# BAD - logic in route
@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 100 lines of business logic here...

# GOOD - logic in service
@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    service = ChatService(db)
    return await service.process_message(request.session_id, request.message)
```

### Pattern 3: Pydantic for Validation

```python
# Request schema
class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=10000)

# Automatic validation - invalid requests rejected
@router.post("/chat")
async def chat(request: ChatRequest):  # Already validated!
    ...
```

### Pattern 4: Structured Logging

```python
import structlog

logger = structlog.get_logger(__name__)

# Logs are JSON, easily parseable
logger.info(
    "Analysis completed",
    session_id=session_id,
    query=query[:50],
    duration_ms=duration,
)

# Output: {"event": "Analysis completed", "session_id": "abc", ...}
```

### Pattern 5: Graceful Degradation

```python
# Try cache, fall back to DB
cached = await cache.get(key)
if cached:
    return cached

# Cache not available? Continue without it
result = await db.query(...)
try:
    await cache.set(key, result)
except:
    pass  # Cache failed, but we still have result
```

---

## 🎓 Summary

### The Flow in One Sentence

User uploads files → asks question → LangGraph orchestrates LLM calls → LLM writes and explains code → user sees results with charts.

### Key Components

1. **Frontend**: Streamlit renders UI, calls backend API
2. **Backend**: FastAPI handles requests, manages sessions
3. **Database**: PostgreSQL stores everything persistently
4. **LangGraph**: Orchestrates the multi-step AI pipeline
5. **LLM**: GPT-4 understands queries and generates code
6. **Redis**: Caches results for performance
7. **Pandas**: Executes the actual data analysis

### The Magic

The "magic" is in the LangGraph pipeline:
- It breaks a complex task (natural language → data insights) into manageable steps
- Each step can fail and retry
- The LLM handles the "understanding" and "creativity"
- Pandas handles the actual computation
- Everything is logged and stored for debugging

---

**Now you understand how Talk to Your Data works!** 🎉

