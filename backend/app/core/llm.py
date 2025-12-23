from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from app.core.config import settings

def get_llm_model(model_name: str = "gpt-4o"):
    """
    Factory to get the LLM model.
    Defaults to OpenAI GPT-4o, falls back to Anthropic if configured.
    """
    if "gpt" in model_name and settings.OPENAI_API_KEY:
        return ChatOpenAI(
            model=model_name,
            temperature=0, 
            openai_api_key=settings.OPENAI_API_KEY
        )
    elif "claude" in model_name and settings.ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model=model_name,
            temperature=0,
            anthropic_api_key=settings.ANTHROPIC_API_KEY
        )
    else:
        # Fallback or Error
        if settings.OPENAI_API_KEY:
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=settings.OPENAI_API_KEY)
        raise ValueError("No valid API Key found for OpenAI or Anthropic.")

