from livekit.plugins import azure, deepgram, sarvam
from backend.config import settings

def get_stt_engine(provider: str = "deepgram"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Uses Deepgram STT if available, or falls back to Azure/Sarvam STT.
    """
    if settings.DEEPGRAM_API_KEY:
        return deepgram.STT(
            model="nova-2-general",
            language="en-IN",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )
    elif provider == "sarvam" and settings.SARVAM_API_KEY:
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )
    else:
        return azure.STT(
            speech_key=settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY,
            speech_endpoint=settings.AZURE_SPEECH_ENDPOINT,
            language="en-IN"
        )
