from livekit.plugins import sarvam
from backend.config import settings

def get_stt_engine():
    """
    Returns the configured Speech-to-Text (STT) engine.
    Utilizes Sarvam AI (saaras:v3) for high-accuracy Hindi, Hinglish, and telephonic speech recognition.
    """
    return sarvam.STT(
        model="saaras:v3",
        language="en-IN",
        prompt="Dubai National Insurance customer verification. Spoken dates and numbers: 3rd, 3, teen, Feb, February, 1990, unnis sau nabbe, Emirates ID digits.",
        api_key=settings.SARVAM_API_KEY
    )
