# 💬 Talk to Your Data

A production-grade conversational analytics platform that lets you upload spreadsheets and ask questions in natural language. Powered by LangGraph, GPT-4, and pandas.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Redis](https://img.shields.io/badge/Redis-7-red.svg)

---

## ✨ Features

### Core Functionality
- **📁 Multi-file Upload** - Upload CSV and Excel files with automatic schema detection
- **💬 Natural Language Queries** - Ask questions like "What's the average revenue by region?"
- **🔄 Cross-table Analysis** - Compare data across multiple files and time periods
- **📊 Interactive Charts** - Visualize results with Plotly charts
- **🧠 AI-Powered Insights** - Get key findings, recommendations, and actionable insights

### Technical Features
- **🔗 LangGraph Pipeline** - Structured reasoning flow with retry logic
- **⚡ Redis Caching** - Cache analysis results for instant repeated queries
- **🚦 Rate Limiting** - Protect against abuse (60 req/min, 1000 req/hr)
- **📦 Background Tasks** - Celery workers for heavy processing
- **🔌 Connection Pooling** - Optimized database connections
- **📝 Structured Logging** - JSON logs for observability

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit     │────▶│    FastAPI      │────▶│   PostgreSQL    │
│   Frontend      │     │    Backend      │     │   Database      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   LangGraph     │
                        │   Pipeline      │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │   OpenAI    │    │    Redis    │    │   Celery    │
     │   GPT-4     │    │    Cache    │    │   Workers   │
     └─────────────┘    └─────────────┘    └─────────────┘
```

### LangGraph Pipeline Flow

```
User Query → Ingest → Plan → Generate Code → Validate → Execute → Explain → Response
                ↓                                          ↑
            [Retry on failure with error context] ─────────┘
```

---

## 📋 Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for PostgreSQL and Redis)
- **OpenAI API Key** (or Anthropic/Ollama)

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd pushkal

# Create environment file
cp env.example .env
```

### 2. Configure Environment

Edit `.env` with your settings:

```bash
# Required: LLM API Key
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini

# Database (default works with Docker)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/pushkal_db

# Redis (default works with Docker)
REDIS_URL=redis://redis:6379/0
```

### 3. Start Infrastructure & Applications

```bash
# Start PostgreSQL and Redis
docker-compose up --build


### 4. Access the Application

- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Everything is running inside Docker — no need to manually set up virtual environments.
---

## 📖 Usage Guide

### Step 1: Upload Data Files

1. Navigate to **📁 Upload** page
2. Drag and drop your CSV or Excel files
3. The system automatically detects:
   - Column types (numeric, categorical, date)
   - Time periods from filenames (e.g., `sales_nov_2024.csv` → "Nov 2024")

### Step 2: Ask Questions

Navigate to **💬 Chat** and ask questions like:

| Query Type | Example |
|------------|---------|
| **Aggregation** | "What is the average revenue by region?" |
| **Comparison** | "Compare sales between November and December 2024" |
| **Ranking** | "Show top 5 products by units sold" |
| **Filtering** | "Total revenue for APAC region only" |
| **Trends** | "How did revenue change over time?" |

### Step 3: View Results

- **📊 Charts** - Interactive Plotly visualizations
- **📋 Tables** - Detailed data tables
- **💡 Insights** - AI-generated key findings and recommendations

### Step 4: Review History

Navigate to **📊 Analysis** to:
- View past analyses
- Download generated Python code
- Export results as CSV

---

## 🔧 Configuration Options

### LLM Providers

The application supports multiple LLM providers. Configure in `.env`:

#### OpenAI (Recommended)
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o, gpt-4-turbo
```

#### Anthropic Claude
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

#### Ollama (Local)
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Rate Limiting

Configure in `backend/app/main.py`:
```python
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
)
```

### Cache TTL

Configure in `backend/app/core/cache.py`:
```python
FILE_METADATA_TTL = 7200      # 2 hours
ANALYSIS_RESULT_TTL = 1800    # 30 minutes
SESSION_TTL = 86400           # 24 hours
```

---

## 📁 Project Structure

```
pushkal/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API Routes
│   │   │   ├── upload.py      # File upload endpoints
│   │   │   └── chat.py        # Chat endpoints
│   │   ├── core/              # Core utilities
│   │   │   ├── config.py      # Settings management
│   │   │   ├── cache.py       # Redis caching
│   │   │   ├── middleware.py  # Rate limiting
│   │   │   └── celery_app.py  # Task queue
│   │   ├── models/            # SQLAlchemy Models
│   │   │   ├── session.py     # Session model
│   │   │   ├── file.py        # UploadedFile model
│   │   │   ├── message.py     # ChatMessage model
│   │   │   └── analysis.py    # AnalysisResult model
│   │   ├── schemas/           # Pydantic Schemas
│   │   ├── services/          # Business Logic
│   │   │   ├── file_service.py
│   │   │   └── chat_service.py
│   │   ├── tasks/             # Celery Tasks
│   │   │   ├── analysis.py    # Background analysis
│   │   │   └── cleanup.py     # Maintenance tasks
│   │   └── main.py            # Application entry
│   ├── alembic/               # Database migrations
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/                   # Streamlit Frontend
│   ├── app.py                 # Main application
│   ├── pages/
│   │   ├── 1_📁_Upload.py     # Upload page
│   │   ├── 2_💬_Chat.py       # Chat page
│   │   └── 3_📊_Analysis.py   # History page
│   └── requirements.txt
│
├── pipeline/                   # LangGraph Pipeline
│   ├── graph.py               # State graph definition
│   ├── state.py               # GraphState TypedDict
│   ├── llm.py                 # LLM configuration
│   └── nodes/                 # Pipeline nodes
│       ├── ingest.py          # Query ingestion
│       ├── planning.py        # Intent analysis
│       ├── code.py            # Code generation
│       └── explain.py         # Result explanation
│
├── data/                       # Sample data files
│   ├── sales_nov_2024.csv
│   ├── sales_dec_2024.csv
│   └── sales_q1_2025.csv
│
├── docker-compose.yml          # Infrastructure
├── .env                        # Environment config
└── README.md
```

---

## 🔌 API Reference

### Health Check
```bash
GET /health
```
Returns status of all services (API, Database, Redis).

### Upload File
```bash
POST /api/v1/upload
Content-Type: multipart/form-data

file: <file>
session_id: <string>
```

### List Files
```bash
GET /api/v1/files?session_id=<session_id>
```

### Send Chat Message
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "session_id": "your-session-id",
  "message": "What is the average revenue?"
}
```

### Get Chat History
```bash
GET /api/v1/chat/history?session_id=<session_id>&limit=20
```

### Get Analysis Details
```bash
GET /api/v1/chat/analysis/{analysis_id}
```

---

## 🧪 Testing

### Test File Upload
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@data/sales_nov_2024.csv" \
  -F "session_id=test-session"
```

### Test Chat
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session", "message": "What is the total revenue?"}'
```

### Run Unit Tests
```bash
cd backend
pytest tests/ -v
```

---

## 🚀 Production Deployment

### Using Docker Compose (Full Stack)

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f
```

### Using Gunicorn (Backend)

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Start Celery Workers

```bash
# Start worker
celery -A app.core.celery_app worker --loglevel=info -Q analysis,cleanup

# Start beat scheduler (for periodic tasks)
celery -A app.core.celery_app beat --loglevel=info
```

### Environment Variables for Production

```bash
# Security
SECRET_KEY=your-production-secret-key

# Database
DATABASE_URL=postgresql://user:pass@db-host:5432/pushkal_db

# Redis
REDIS_URL=redis://redis-host:6379/0

# Logging
LOG_LEVEL=INFO
```

---

## 🛠️ Development

### Adding New LangGraph Nodes

1. Create node function in `pipeline/nodes/`
2. Update state in `pipeline/state.py` if needed
3. Register node in `pipeline/graph.py`

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding New API Endpoints

1. Create router in `backend/app/api/`
2. Add schemas in `backend/app/schemas/`
3. Register router in `backend/app/main.py`

---

## 🐛 Troubleshooting

### Common Issues

**"Cannot connect to PostgreSQL"**
```bash
# Check if Docker is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres
```

**"OPENAI_API_KEY not found"**
```bash
# Ensure .env file exists and has the key
cat .env | grep OPENAI
```

**"Redis connection failed"**
```bash
# Check Redis status
docker-compose logs redis

# The app works without Redis (caching disabled)
```

**"Module not found: pipeline"**
```bash
# Ensure you're in the project root
cd /path/to/pushkal
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## 📝 Sample Data

The `data/` folder contains sample CSV files for testing:

| File | Description | Rows | Period |
|------|-------------|------|--------|
| `sales_nov_2024.csv` | November sales | 10 | Nov 2024 |
| `sales_dec_2024.csv` | December sales | 12 | Dec 2024 |
| `sales_q1_2025.csv` | Q1 summary | 9 | Q1 2025 |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - Pipeline orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Streamlit](https://streamlit.io/) - Frontend framework
- [OpenAI](https://openai.com/) - LLM provider

---

**Built with ❤️ for conversational data analytics**
