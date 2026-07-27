from livekit.plugins import azure, elevenlabs, sarvam
from backend.config import settings

def get_tts_engine(provider: str = "azure"):
    """
    Returns the configured Text-to-Speech (TTS) engine.
    Defaults to Azure Speech Services (TTS) with voice 'en-IN-Diya:DragonHDLatestNeural'.
    """
    if provider == "sarvam":
        return sarvam.TTS(
            api_key=settings.SARVAM_API_KEY,
            speaker="ritu"
        )
    elif provider == "elevenlabs":
        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY, 
            model="eleven_flash_v2_5",
            voice_id=settings.ELEVENLABS_VOICE_ID,
            streaming_latency=2
        )
    else:
        # Default to Azure TTS (en-IN-Diya:DragonHDLatestNeural)
        return azure.TTS(
            speech_key=settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY,
            speech_endpoint=settings.AZURE_SPEECH_ENDPOINT,
            voice="en-IN-Diya:DragonHDLatestNeural"
        )
