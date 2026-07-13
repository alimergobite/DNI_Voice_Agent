import asyncio
import logging
from typing import AsyncIterable
from livekit.plugins import google
from livekit.agents.llm import LLM, ChatContext, ChatChunk, LLMStream, FallbackAdapter
from backend.config import settings

logger = logging.getLogger(__name__)

# Build the pool of available Gemini API keys (skip any that are empty)
_all_keys = [
    k for k in [
        settings.GEMINI_API_KEY,
        settings.GEMINI_API_KEY_2,
        settings.GEMINI_API_KEY_3,
    ] if k
]

_current_key_index = 0

def _get_next_key() -> str:
    """Rotates to the next available key in the pool."""
    global _current_key_index
    key = _all_keys[_current_key_index % len(_all_keys)]
    _current_key_index += 1
    return key

def get_llm_engine():
    """
    Returns a FallbackAdapter containing pre-created Gemini 2.5 Flash clients.
    If a key hits a 429 rate limit during stream iteration, the adapter natively
    falls back to the next client without crashing the agent.
    """
    clients = [
        google.LLM(
            model="gemini-2.5-flash",
            api_key=key,
            thinking_config={"thinking_budget": 0}
        ) for key in _all_keys
    ]
    return FallbackAdapter(clients)
