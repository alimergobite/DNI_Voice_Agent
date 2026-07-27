from livekit.plugins import elevenlabs, sarvam, azure
from backend.config import settings

def get_tts_engine(provider: str = "azure"):
    """
    Returns the configured Text-to-Speech engine dynamically.
    Providers: "azure", "elevenlabs", "sarvam"
    """
    if provider == "elevenlabs":
        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY, 
            model="eleven_flash_v2_5",
            voice_id=settings.ELEVENLABS_VOICE_ID,
            streaming_latency=2
        )
    elif provider == "sarvam":
        return sarvam.TTS(
            api_key=settings.SARVAM_API_KEY,
            speaker="ritu"
        )
    else:
        # Default to Azure TTS (en-IN-Diya:DragonHDLatestNeural)
        endpoint = settings.AZURE_OPENAI_ENDPOINT or "https://microfoundryergo.cognitiveservices.azure.com/"
        if "cognitiveservices" not in endpoint:
            endpoint = "https://microfoundryergo.cognitiveservices.azure.com/"

        return azure.TTS(
            voice="en-IN-Diya:DragonHDLatestNeural",
            speech_key=settings.AZURE_OPENAI_API_KEY,
            speech_endpoint=endpoint
        )
