import logging
from livekit.plugins import openai
from openai import AsyncAzureOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns the configured LLM Engine for the agent.
    """
    # ==========================================
    # OLD CODE (Google Gemini / Flash Lite & Groq)
    # ==========================================
    # from livekit.plugins import google
    # from livekit.agents.llm import FallbackAdapter
    #
    # logger.info("[LLM] Initializing Groq LLM (llama-3.1-8b-instant)")
    # return openai.LLM(
    #     model="llama-3.1-8b-instant",
    #     api_key=settings.GROQ_API_KEY,
    #     base_url="https://api.groq.com/openai/v1"
    # )
    # ==========================================

    # ==========================================
    # GROQ LLM (Ultra-Low Latency + Smart Model)
    # ==========================================
    logger.info("[LLM] Initializing Groq LLM (llama-3.3-70b-versatile)")
    return openai.LLM(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0
    )
