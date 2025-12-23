"""
LLM Client Configuration
========================
Configures the LLM client based on settings (OpenAI, Anthropic, or Ollama).
"""

import os
from pathlib import Path
from typing import Optional
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Get the configured LLM client.
    
    Reads LLM_PROVIDER from environment and returns appropriate client.
    
    Args:
        temperature: Sampling temperature (0.0 = deterministic)
    
    Returns:
        LangChain chat model
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
    
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url,
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'openai', 'anthropic', or 'ollama'")


# Singleton instance (lazy loaded)
_llm_instance: Optional[BaseChatModel] = None


def get_llm_singleton() -> BaseChatModel:
    """Get or create the singleton LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance

