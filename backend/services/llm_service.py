import logging
from livekit.plugins import openai
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns an OpenAI-compatible LLM client configured to use Groq's LPU inference engine.
    This eliminates the 1-2 second "thinking" delay of Gemini 2.5 Flash, bringing the 
    Time-To-First-Token down to < 300ms.
    """
    logger.info("[LLM] Initializing Groq LLM (llama-3.3-70b-versatile)")
    
    return openai.LLM(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
