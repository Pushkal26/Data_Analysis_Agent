"""
Application Configuration
=========================
Loads configuration from environment variables using pydantic-settings.
"""

from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Copy env.example to .env and fill in your values.
    """
    
    model_config = SettingsConfigDict(
        env_file="../.env",  # Load from project root
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # ----- LLM Configuration -----
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # ----- Database -----
    database_url: str = "postgresql://postgres:postgres@localhost:5432/pushkal_db"
    
    # ----- Redis -----
    redis_url: str = "redis://localhost:6379/0"
    
    # ----- Backend -----
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    secret_key: str = "change-this-in-production"
    
    # ----- Frontend -----
    frontend_port: int = 8501
    backend_api_url: str = "http://localhost:8000"
    
    # ----- File Upload -----
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    
    # ----- Logging -----
    log_level: str = "INFO"
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
