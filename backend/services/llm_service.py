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
    # GROQ LLM (Ultra-Low Latency)
    # ==========================================
    logger.info("[LLM] Initializing Groq LLM (llama-3.1-8b-instant)")
    return openai.LLM(
        model="llama-3.1-8b-instant",
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.0
    )

    # ==========================================
    # AZURE OPENAI (gpt-5-nano) - Temporarily disabled for latency testing
    # ==========================================
    # logger.info("[LLM] Initializing Azure OpenAI (gpt-5-nano)")
    # azure_client = AsyncAzureOpenAI(
    #     api_key=settings.AZURE_OPENAI_API_KEY,
    #     azure_endpoint="https://abhishekazureopenaitest.openai.azure.com",
    #     api_version="2024-02-01"
    # )
    # return openai.LLM(
    #     model="gpt-5-nano",
    #     client=azure_client,
    #     reasoning_effort="none",
    #     verbosity="low",
    #     temperature=0.0
    # )
