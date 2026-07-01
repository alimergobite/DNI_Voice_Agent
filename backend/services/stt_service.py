from livekit.plugins import deepgram
from backend.config import settings

def get_stt_engine():
    """
    Returns the configured Speech-to-Text (STT) engine.
    Currently utilizes Deepgram Nova-2 for ultra-low latency.
    """
    return deepgram.STT(
        model="nova-2-general",
        api_key=settings.DEEPGRAM_API_KEY
    )
