import logging
from livekit.plugins import openai
from openai import AsyncOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns the configured LLM Engine for the agent.
    """
    # ==========================================
    # PREVIOUS CODE (gpt-5.4-mini)
    # ==========================================
    # from openai import AsyncAzureOpenAI
    # azure_client = AsyncAzureOpenAI(
    #     api_key=settings.AZURE_OPENAI_API_KEY,
    #     azure_endpoint="https://abhishekazureopenaitest.openai.azure.com",
    #     api_version="2024-02-01"
    # )
    # return openai.LLM(
    #     model="gpt-5.4-mini",
    #     client=azure_client,
    #     reasoning_effort="low",
    #     verbosity="low",
    #     temperature=0.0
    # )
    # ==========================================

    # ==========================================
    # PREVIOUS CODE (gpt-5-mini)
    # ==========================================
    # deployment_name = "gpt-5-mini"
    # endpoint = settings.AZURE_OPENAI_ENDPOINT or "https://microfoundryergo.services.ai.azure.com/openai/v1"
    # api_key = settings.AZURE_OPENAI_API_KEY
    # client = AsyncOpenAI(base_url=endpoint, api_key=api_key)
    # return openai.LLM(model=deployment_name, client=client, temperature=0.0)
    # ==========================================

    # ==========================================
    # Active Model: grok-4-20-reasoning
    # ==========================================
    deployment_name = "grok-4-20-reasoning"
    endpoint = settings.AZURE_OPENAI_ENDPOINT or "https://microfoundryergo.services.ai.azure.com/openai/v1"
    api_key = settings.AZURE_OPENAI_API_KEY

    logger.info(f"[LLM] Initializing LLM Model ({deployment_name})")

    client = AsyncOpenAI(
        base_url=endpoint,
        api_key=api_key
    )

    return openai.LLM(
        model=deployment_name,
        client=client,
        temperature=0.0
    )
