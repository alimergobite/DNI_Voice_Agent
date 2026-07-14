import logging
from livekit.plugins import google
from livekit.agents.llm import FallbackAdapter
from backend.config import settings

logger = logging.getLogger(__name__)

# Build the pool of available Gemini API keys
_all_keys = [
    k for k in [
        settings.GEMINI_API_KEY,
        settings.GEMINI_API_KEY_2,
        settings.GEMINI_API_KEY_3,
    ] if k
]

def get_llm_engine():
    """
    Returns a FallbackAdapter containing Gemini 2.5 Flash Lite clients.
    Because we downgraded `livekit-plugins-google` to v1.5.18, it uses the highly stable
    `google-generativeai` SDK which natively accepts the user's `AQ.` OAuth keys
    AND does not suffer from the 10s deadline streaming crash.
    """
    logger.info("[LLM] Initializing Groq LLM (llama-3.1-8b-instant)")
    
    # We must use Groq because all 3 of the user's Gemini keys are attached to a 
    # Google Cloud Project that has completely exhausted its daily free tier limits,
    # resulting in silent 429 errors from Google.
    from livekit.plugins import openai
    return openai.LLM(
        model="llama-3.1-8b-instant",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
