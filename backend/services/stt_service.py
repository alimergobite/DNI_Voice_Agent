from livekit.plugins import deepgram, sarvam
from backend.config import settings

def get_stt_engine(provider: str = "azure"):
    """
    Returns the configured Speech-to-Text (STT) engine.
    Defaults to Azure Speech STT if available, or falls back to Deepgram/Sarvam STT.
    """
    if (provider == "azure" or not provider) and (settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY):
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
            print(f"[STT Warning] Failed to initialize Azure STT ({e}), falling back to Deepgram...")

    if provider == "sarvam" and settings.SARVAM_API_KEY:
        return sarvam.STT(
            model="saaras:v3",
            language="hi-IN",
            api_key=settings.SARVAM_API_KEY
        )
        
    # Deepgram STT (Fallback or explicit provider)
    if settings.DEEPGRAM_API_KEY:
        print("[STT] Using Deepgram STT (model=nova-2-general, lang=en-IN)")
        return deepgram.STT(
            model="nova-2-general",
            language="en-IN",
            api_key=settings.DEEPGRAM_API_KEY,
            smart_format=True
        )

    # Ultimate fallback to Azure STT
    from livekit.plugins import azure
    return azure.STT(
        speech_key=settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY,
        speech_host=settings.AZURE_SPEECH_ENDPOINT,
        language="en-IN"
    )


