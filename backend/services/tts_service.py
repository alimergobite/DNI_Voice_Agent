from livekit.plugins import elevenlabs
from backend.config import settings

def get_tts_engine(api_key_override: str = None):
    """
    Returns the configured Text-to-Speech engine.
    Currently using ElevenLabs.
    """
    return elevenlabs.TTS(
        api_key=api_key_override or settings.ELEVENLABS_API_KEY, 
        model="eleven_turbo_v2_5",
        voice_id=settings.ELEVENLABS_VOICE_ID
    )
