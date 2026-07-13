import asyncio
import logging
from typing import AsyncIterable
from livekit.plugins import google
from livekit.agents.llm import LLM, ChatContext, ChatChunk, LLMStream
from livekit.agents._exceptions import APIStatusError
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
    Returns a RotatingGeminiLLM that transparently switches Gemini API keys
    when a 429 rate-limit error is hit mid-conversation, preventing crashes.
    """
    return RotatingGeminiLLM(model="gemini-2.5-flash", keys=_all_keys)

class RotatingGeminiLLM(LLM):
    """
    A wrapper around google.LLM that automatically rotates API keys when
    a 429 Too Many Requests error is encountered mid-conversation.
    On each turn, it tries the next key in round-robin order. If that key
    is also rate-limited, it tries the next one, until all keys are exhausted.
    """

    def __init__(self, model: str, keys: list[str]):
        super().__init__()
        self._model = model
        self._keys = keys
        self._index = 0

    def _get_llm(self) -> google.LLM:
        key = self._keys[self._index % len(self._keys)]
        self._index += 1
        logger.info(f"[LLM] Using Gemini key ending in ...{key[-8:]}")
        return google.LLM(model=self._model, api_key=key)

    def chat(self, *, chat_ctx: ChatContext, **kwargs) -> LLMStream:
        """
        Tries each key in rotation. If a key hits a 429 limit, it immediately
        retries with the next key — all transparently mid-conversation.
        """
        attempts = len(self._keys)
        last_error = None

        for attempt in range(attempts):
            try:
                llm = self._get_llm()
                return llm.chat(chat_ctx=chat_ctx, **kwargs)
            except APIStatusError as e:
                if e.status_code == 429:
                    logger.warning(
                        f"[LLM] Key rate-limited (429), rotating to next key... "
                        f"(attempt {attempt + 1}/{attempts})"
                    )
                    last_error = e
                    continue
                raise

        logger.error("[LLM] ALL Gemini API keys are rate-limited! Cannot proceed.")
        raise last_error
