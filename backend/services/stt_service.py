from livekit.plugins import deepgram, sarvam
from backend.config import settings

def get_stt_engine(provider: str = "deepgram"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Uses Deepgram Nova-2 for ultra-fast (~100ms), 100% clean English text & number formatting.
    """
    if provider == "sarvam":
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )
    else:
        # Default to Deepgram Nova-2
        return deepgram.STT(
            model="nova-2-general",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )
