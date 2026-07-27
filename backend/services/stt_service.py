from livekit.plugins import azure, deepgram, sarvam
from backend.config import settings

def get_stt_engine(provider: str = "azure"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Defaults to Azure Speech Services (STT).
    """
    if provider == "sarvam" and settings.SARVAM_API_KEY:
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )
    elif provider == "deepgram":
        return deepgram.STT(
            model="nova-2-general",
            language="en-IN",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )
    else:
        # Default to Azure STT
        return azure.STT(
            speech_key=settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY,
            speech_endpoint=settings.AZURE_SPEECH_ENDPOINT,
            language="en-IN"
        )
