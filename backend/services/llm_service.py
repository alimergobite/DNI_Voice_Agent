import logging
from livekit.plugins import openai
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns an OpenAI-compatible LLM client configured to use Groq's LPU inference engine.
    Since the user's Gemini API keys are completely exhausted/blocked at the Google Cloud Project level,
    we must use Groq. Mixtral 8x7B provides the intelligence to follow complex KYC scripts
    while maintaining ultra-fast <2s response times.
    """
    logger.info("[LLM] Initializing Groq LLM (meta-llama/llama-4-scout-17b-16e-instruct)")
    
    return openai.LLM(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
