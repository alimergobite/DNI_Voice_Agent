from livekit.plugins import deepgram, sarvam
from backend.config import settings

def get_stt_engine(provider: str = "sarvam"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Utilizes Sarvam AI (saaras:v3) by default for native Hindi, Hinglish, and telephonic speech recognition.
    """
    if provider == "deepgram":
        return deepgram.STT(
            model="nova-2-general",
            language="en-IN",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )
    else:
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )
