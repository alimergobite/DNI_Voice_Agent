from livekit.plugins import elevenlabs, sarvam
from backend.config import settings

def get_tts_engine(provider: str = "elevenlabs"):
    """
    Returns the configured Text-to-Speech engine dynamically.
    Utilizes ElevenLabs (eleven_flash_v2_5) by default.
    """
    if provider == "sarvam":
        return sarvam.TTS(
            api_key=settings.SARVAM_API_KEY,
            speaker="ritu"
        )
    else:
        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY, 
            model="eleven_flash_v2_5",
            voice_id=settings.ELEVENLABS_VOICE_ID,
            streaming_latency=2
        )
