from livekit.plugins import deepgram
from backend.config import settings

def get_stt_engine():
    """
    Returns the configured Speech-to-Text (STT) engine.
    Utilizes Deepgram Nova-3 with language detection & Hinglish support for ultra-low latency & multilingual accuracy.
    """
    return deepgram.STT(
        model="nova-3",
        api_key=settings.DEEPGRAM_API_KEY,
        language="hi-Latn",
        detect_language=True,
        endpointing_ms=250
    )
