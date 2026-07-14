import logging
from livekit.plugins import openai
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns an OpenAI-compatible LLM client configured to use Groq's LPU inference engine.
    We must use Groq because all 3 of the user's Gemini keys are attached to a 
    Google Cloud Project that has completely exhausted its daily free tier limits,
    resulting in silent 429 errors from Google.
    """
    logger.info("[LLM] Initializing Groq LLM (llama-3.1-8b-instant)")
    
    return openai.LLM(
        model="llama-3.1-8b-instant",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
