import logging
from livekit.plugins import google
from livekit.agents.llm import LLM, ChatContext, ChatChunk, LLMStream, FallbackAdapter
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
    Returns a FallbackAdapter containing pre-created Gemini 2.5 Flash clients.
    Includes the http_options timeout=15.0 to bypass Google's new 10s minimum deadline requirement.
    """
    logger.info("[LLM] Initializing Gemini 2.5 Flash Pool with FallbackAdapter")
    
    clients = [
        google.LLM(
            model="gemini-1.5-flash",
            api_key=key,
            http_options={'timeout': 15.0}
        ) for key in _all_keys
    ]
    return FallbackAdapter(clients)
