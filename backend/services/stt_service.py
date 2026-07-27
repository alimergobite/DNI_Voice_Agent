from livekit.plugins import sarvam, deepgram
from backend.config import settings

def get_stt_engine(provider: str = "sarvam"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Defaults to Sarvam STT (saaras:v3, hi-IN) for excellent Hindi/Hinglish/English accuracy.
    """
    if settings.SARVAM_API_KEY:
        print("[STT] Using Sarvam AI STT (model=saaras:v3, lang=hi-IN)")
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )

    # Fallback to Deepgram STT
    if settings.DEEPGRAM_API_KEY:
        print("[STT] Using Deepgram STT (model=nova-2-general, lang=en-IN)")
        return deepgram.STT(
            model="nova-2-general",
            language="en-IN",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )

    # Fallback to Azure STT
    try:
        from livekit.plugins import azure
        speech_key = settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY
        speech_host = settings.AZURE_SPEECH_ENDPOINT
        print(f"[STT] Using Azure STT (host={speech_host}, lang=en-IN)")
        return azure.STT(
            speech_key=speech_key,
            speech_host=speech_host,
            language="en-IN"
        )
    except Exception as e:
        raise RuntimeError(f"No valid STT provider available: {e}")



