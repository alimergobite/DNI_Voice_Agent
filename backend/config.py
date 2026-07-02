import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "DNI Voice Agent Production"
    
    # API Keys (Loaded from .env automatically)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
    
    # LiveKit Settings
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "DNI_LIVEKIT_KEY")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "DNI_LIVEKIT_SECRET_THAT_IS_LONG_ENOUGH_FOR_SECURITY")

settings = Settings()
