from livekit.plugins import sarvam
from backend.config import settings

def get_stt_engine():
    """
    Returns the configured Speech-to-Text (STT) engine.
    Utilizes Sarvam AI (saaras:v3) for high-accuracy Hindi, Hinglish, and telephonic speech recognition.
    """
    return sarvam.STT(
        model="saaras:v3",
        language="hi-IN",
        api_key=settings.SARVAM_API_KEY
    )
