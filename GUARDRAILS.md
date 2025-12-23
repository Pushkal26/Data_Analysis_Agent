# 🛡️ Security Guardrails & Safety Measures

This document describes the security measures implemented to ensure safe operation of the Talk to Your Data platform.

---

## Table of Contents

1. [Code Execution Safety](#1-code-execution-safety)
2. [Input Validation](#2-input-validation)
3. [Rate Limiting](#3-rate-limiting)
4. [Data Protection](#4-data-protection)
5. [LLM Safety](#5-llm-safety)
6. [Infrastructure Security](#6-infrastructure-security)
7. [Assumptions](#7-assumptions)

---

## 1. Code Execution Safety

### The Risk

LLM-generated code is executed on the server. This creates potential for:
- Remote code execution (RCE)
- File system access
- Network requests
- Data exfiltration

### Mitigations

#### 1.1 Forbidden Pattern Detection

Before execution, code is scanned for dangerous patterns:

```python
FORBIDDEN_PATTERNS = [
    # System access
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    
    # Code injection
    "eval(",
    "exec(",
    "compile(",
    
    # System commands
    "os.system",
    "os.popen",
    "subprocess.",
    "shutil.",
    
    # File operations (beyond read)
    ".to_csv(",
    ".to_excel(",
    ".to_json(",
    
    # Destructive operations
    "rm ",
    "del ",
    ".drop(",
    "DELETE ",
    "DROP ",
]
```

#### 1.2 Sandboxed Execution

Code runs in a restricted namespace:

```python
namespace = {
    "pd": pd,
    "np": np,
    "__builtins__": {
        # Only safe built-ins
        "len": len,
        "range": range,
        "list": list,
        "dict": dict,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "zip": zip,
        "enumerate": enumerate,
        "print": print,
        "isinstance": isinstance,
        "type": type,
    },
}
```

**What's blocked:**
- `open()` for arbitrary files (except pandas read)
- `__import__()` for dynamic imports
- `eval()`, `exec()`, `compile()`
- Network access (`socket`, `requests`, `urllib`)
- Environment variables access

#### 1.3 Execution Timeout

Code execution has a timeout to prevent infinite loops:

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout
```

#### 1.4 Resource Limits

- Memory: Limited by container/process limits
- CPU: Execution timeout prevents CPU exhaustion
- Disk: Files stored in designated upload directory only

---

## 2. Input Validation

### 2.1 File Upload Validation

```python
# Allowed file types
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Maximum file size
MAX_FILE_SIZE_MB = 50

# Validation checks
- File extension must be in ALLOWED_EXTENSIONS
- File size must not exceed MAX_FILE_SIZE_MB
- Content-type header verification
- File content sniffing (magic bytes)
```

### 2.2 Query Validation

```python
class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=10000)
    
    @validator('session_id')
    def validate_session_id(cls, v):
        # Only allow alphanumeric and hyphens
        if not re.match(r'^[a-zA-Z0-9\-]+$', v):
            raise ValueError('Invalid session ID')
        return v
```

### 2.3 Path Traversal Prevention

```python
def safe_path(filename: str, base_dir: Path) -> Path:
    """Prevent directory traversal attacks."""
    # Remove any path components
    safe_name = Path(filename).name
    
    # Sanitize filename
    safe_name = re.sub(r'[^\w\-_.]', '_', safe_name)
    
    # Resolve and verify within base
    full_path = (base_dir / safe_name).resolve()
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal detected")
    
    return full_path
```

---

## 3. Rate Limiting

### 3.1 Per-IP Limits

```python
# Configured in middleware
requests_per_minute = 60
requests_per_hour = 1000

# Tracked in Redis
key = f"ratelimit:minute:{ip_address}"
```

### 3.2 Per-Endpoint Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/chat` | 10 | 1 minute |
| `/api/v1/upload` | 20 | 1 minute |
| `/api/v1/files` | 100 | 1 minute |

### 3.3 LLM Rate Limiting

```python
# Celery task annotation
@celery_app.task(
    rate_limit="10/m",  # 10 analyses per minute
)
def run_analysis_task(...):
    ...
```

---

## 4. Data Protection

### 4.1 Session Isolation

- Each session has a unique UUID
- Files stored in session-specific directories
- Database queries filtered by session_id
- No cross-session data access

```
/uploads/
├── session-a1b2c3/
│   └── sales_2024.csv
├── session-d4e5f6/
│   └── report.xlsx
```

### 4.2 Data Retention

```python
# Automatic cleanup (Celery beat)
@celery_app.task
def cleanup_old_files(max_age_days=7):
    """Delete files older than 7 days."""
    ...
    
@celery_app.task  
def cleanup_old_analyses(max_age_days=30):
    """Archive analyses older than 30 days."""
    ...
```

### 4.3 Sensitive Data Handling

- **API keys**: Stored in environment variables, never in code
- **Database credentials**: Environment variables only
- **File content**: Not logged, only metadata
- **LLM requests**: Query logged, full data not logged

---

## 5. LLM Safety

### 5.1 Prompt Injection Prevention

```python
# System prompts clearly separate user content
prompt = f"""
[SYSTEM]
You are a data analyst. Only analyze the provided data.
Do not execute commands or access external resources.

[USER QUERY]
{user_query}

[DATA CONTEXT]
{file_metadata}
"""
```

### 5.2 Output Validation

```python
# Validate LLM JSON output
def validate_llm_response(response: dict) -> bool:
    required_fields = ["intent", "operation_type"]
    allowed_intents = ["query", "aggregate", "compare", "trend"]
    
    if response.get("intent") not in allowed_intents:
        return False
    return True
```

### 5.3 Code Review Before Execution

1. LLM generates code
2. Forbidden pattern check
3. Syntax validation
4. Sandboxed execution

---

## 6. Infrastructure Security

### 6.1 Network Security

```yaml
# docker-compose.yml - internal network
services:
  postgres:
    networks:
      - internal
    # Not exposed externally
    
  redis:
    networks:
      - internal
    # Not exposed externally
```

### 6.2 Database Security

```python
# Parameterized queries (SQLAlchemy)
result = await session.execute(
    select(UploadedFile).where(UploadedFile.session_id == session_id)
)
# Never raw SQL with string interpolation
```

### 6.3 CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Explicit origins only
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Limited methods
    allow_headers=["*"],
)
```

### 6.4 Headers

```python
# Security headers (add via middleware or reverse proxy)
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

---

## 7. Assumptions

### 7.1 Trust Boundaries

| Component | Trust Level | Justification |
|-----------|-------------|---------------|
| User uploads | Untrusted | Could contain malicious data |
| User queries | Untrusted | Could attempt prompt injection |
| LLM output | Semi-trusted | Validated before execution |
| Database | Trusted | Internal, authenticated |
| Redis | Trusted | Internal network only |

### 7.2 Deployment Assumptions

1. **Private network**: Backend services not exposed to internet
2. **Reverse proxy**: nginx/traefik handles TLS termination
3. **Container isolation**: Docker/K8s provides process isolation
4. **Secret management**: Secrets injected via environment, not files

### 7.3 Data Assumptions

1. **Data sensitivity**: Uploaded data may contain PII/confidential info
2. **Data volume**: Files limited to 50MB, reasonable for spreadsheets
3. **Data format**: Only structured tabular data (CSV/Excel)
4. **Data retention**: 7-30 days, then purged

### 7.4 User Assumptions

1. **Single-tenant**: Each session is independent
2. **No authentication**: Session-based only (add auth for production)
3. **Trusted frontend**: Streamlit app is trusted source

---

## Security Checklist

### Before Production

- [ ] Enable HTTPS/TLS
- [ ] Add user authentication
- [ ] Configure WAF (Web Application Firewall)
- [ ] Enable database encryption at rest
- [ ] Set up log aggregation and monitoring
- [ ] Configure backup and recovery
- [ ] Perform penetration testing
- [ ] Review and update dependencies
- [ ] Enable audit logging
- [ ] Configure network segmentation

### Ongoing

- [ ] Monitor rate limit hits
- [ ] Review LLM-generated code patterns
- [ ] Rotate API keys regularly
- [ ] Update dependencies monthly
- [ ] Review access logs weekly
- [ ] Test backup recovery quarterly

---

## Incident Response

### If Code Execution Compromised

1. **Isolate**: Stop affected containers
2. **Assess**: Check execution logs for malicious activity
3. **Contain**: Revoke session, delete uploaded files
4. **Remediate**: Patch forbidden patterns, update validation
5. **Report**: Document and notify if data breach

### If LLM Prompt Injected

1. **Log**: Capture the malicious prompt
2. **Block**: Add pattern to input validation
3. **Review**: Check if any harmful code was generated
4. **Update**: Strengthen system prompt boundaries

---

**Last Updated**: December 2024
**Review Frequency**: Quarterly

