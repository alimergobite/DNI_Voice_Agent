from livekit.plugins import google
from backend.config import settings

def get_llm_engine():
    """
    Returns the configured Large Language Model (LLM) engine.
    Currently using Gemini 2.5 Flash.
    """
    return google.LLM(
        model="gemini-2.5-flash", 
        api_key=settings.GEMINI_API_KEY
    )
