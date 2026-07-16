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
    # NEW CODE (Azure OpenAI - gpt-5.4-mini)
    # ==========================================
    logger.info("[LLM] Initializing Azure OpenAI (gpt-5-nano)")
    
    # Create the Azure specific client
    azure_client = AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint="https://abhishekazureopenaitest.openai.azure.com",
        api_version="2024-02-01"
    )
    
    # Inject it into LiveKit's OpenAI plugin with the CTO's exact speed parameters
    return openai.LLM(
        model="gpt-5.4-mini",
        client=azure_client,
        reasoning_effort="none",
        verbosity="low",
        temperature=0.0
    )
