"""
Custom Middleware
=================
Rate limiting and request tracking middleware.
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import time

from app.core.cache import cache_service

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    
    Limits requests per IP address or session.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: list = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get client identifier (IP address or session ID)
        client_ip = request.client.host if request.client else "unknown"
        session_id = request.headers.get("X-Session-ID", client_ip)
        identifier = f"{client_ip}:{session_id}"
        
        # Check rate limits
        if cache_service.is_connected:
            # Per-minute check
            allowed_minute, remaining_minute = await cache_service.check_rate_limit(
                f"minute:{identifier}",
                limit=self.requests_per_minute,
                window_seconds=60,
            )
            
            # Per-hour check
            allowed_hour, remaining_hour = await cache_service.check_rate_limit(
                f"hour:{identifier}",
                limit=self.requests_per_hour,
                window_seconds=3600,
            )
            
            if not allowed_minute or not allowed_hour:
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "detail": "Too many requests. Please slow down.",
                        "retry_after": 60 if not allowed_minute else 3600,
                    },
                    headers={
                        "X-RateLimit-Remaining-Minute": str(remaining_minute),
                        "X-RateLimit-Remaining-Hour": str(remaining_hour),
                        "Retry-After": str(60 if not allowed_minute else 3600),
                    },
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if cache_service.is_connected:
            response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request timing.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Add timing header
        response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
        
        # Log slow requests
        if duration_ms > 5000:  # > 5 seconds
            logger.warning(
                "Slow request detected",
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
            )
        
        return response

