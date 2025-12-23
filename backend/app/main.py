"""
FastAPI Backend Application
===========================
Main entry point for the Talk to Your Data API.

This file sets up:
- FastAPI app with CORS middleware
- Rate limiting middleware
- Request timing middleware
- Redis caching
- API route registration
- Startup/shutdown events for DB connections
- Health check endpoint
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api import upload, chat
from app.core.config import get_settings
from app.core.cache import cache_service
from app.core.middleware import RateLimitMiddleware, RequestTimingMiddleware

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
    - Initialize database connection pool
    - Connect to Redis
    - Load LLM models
    
    Shutdown:
    - Close database connections
    - Disconnect from Redis
    """
    # ----- STARTUP -----
    logger.info("Starting up Talk to Your Data API...")
    
    # Create upload directory
    from pathlib import Path
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    
    # Connect to Redis cache
    try:
        await cache_service.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning("Redis cache not available, caching disabled", error=str(e))
    
    logger.info("Startup complete!")
    
    yield  # Application runs here
    
    # ----- SHUTDOWN -----
    logger.info("Shutting down...")
    
    # Disconnect Redis
    await cache_service.disconnect()
    
    logger.info("Shutdown complete!")


# Create FastAPI application
app = FastAPI(
    title="Talk to Your Data API",
    description="LangGraph-powered conversational analytics platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ----- Middleware (order matters: first added = outermost) -----

# Request timing (outermost - measures total time)
app.add_middleware(RequestTimingMiddleware)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,  # 60 requests per minute
    requests_per_hour=1000,  # 1000 requests per hour
    exclude_paths=["/health", "/docs", "/openapi.json", "/redoc", "/"],
)

# CORS (allow Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit default port
        "http://127.0.0.1:8501",
        "http://localhost:3000",  # React (if used later)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Health Check -----
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    Returns status of all critical services.
    """
    # Check database connection
    db_status = "up"
    try:
        from sqlalchemy import text
        from app.models import async_session_maker
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Redis connection
    redis_status = "up" if cache_service.is_connected else "down"
    
    # Overall status
    all_up = db_status == "up"  # Redis is optional
    
    return {
        "status": "healthy" if all_up else "degraded",
        "services": {
            "api": "up",
            "database": db_status,
            "redis": redis_status,
        },
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Talk to Your Data API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


# ----- API Routes -----
app.include_router(upload.router, prefix="/api/v1", tags=["files"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
