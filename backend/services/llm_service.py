import logging
from livekit.plugins import openai
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
    Returns a FallbackAdapter containing Gemini 1.5 Flash clients.
    CRITICAL FIX: We use the `openai.LLM` client pointing to Google's OpenAI-compatible endpoint
    (`https://generativelanguage.googleapis.com/v1beta/openai/`).
    This completely bypasses the severely buggy `google-genai` SDK which was randomly
    failing streams with 10s deadline crashes.
    """
    logger.info("[LLM] Initializing Gemini 1.5 Flash via OpenAI Compatibility Endpoint")
    
    clients = [
        openai.LLM(
            model="gemini-1.5-flash",
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ) for key in _all_keys
    ]
    return FallbackAdapter(clients)
