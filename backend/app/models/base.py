"""
Database Base Configuration
===========================
Sets up SQLAlchemy async engine and session management.
"""

from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.config import get_settings

settings = get_settings()

# Naming convention for constraints (helps with migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Provides:
    - Automatic table naming
    - Common timestamp columns
    - Naming conventions for constraints
    """
    
    metadata = MetaData(naming_convention=convention)
    
    # Common columns for all tables
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ----- Database Engine Setup -----

def get_database_url() -> str:
    """
    Convert sync database URL to async URL.
    PostgreSQL: postgresql:// -> postgresql+asyncpg://
    """
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Create async engine with production-optimized settings
engine = create_async_engine(
    get_database_url(),
    echo=settings.log_level == "DEBUG",  # Log SQL in debug mode
    
    # Connection pool settings
    pool_pre_ping=True,     # Check connection health before use
    pool_size=10,           # Base connection pool size
    max_overflow=20,        # Allow up to 20 extra connections under load
    pool_timeout=30,        # Wait up to 30s for a connection
    pool_recycle=1800,      # Recycle connections after 30 minutes
    
    # Connection settings
    connect_args={
        "server_settings": {
            "application_name": "pushkal_api",  # Identify in pg_stat_activity
        }
    },
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
