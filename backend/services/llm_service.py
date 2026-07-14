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
    logger.info("[LLM] Initializing Gemini 2.5 Flash Lite Pool")
    
    clients = [
        google.LLM(
            model="gemini-2.5-flash-lite",
            api_key=key
        ) for key in _all_keys
    ]
    return FallbackAdapter(clients)
