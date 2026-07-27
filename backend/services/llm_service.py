import logging
from livekit.plugins import openai
from openai import AsyncOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns the configured LLM Engine for the agent.
    Configured for Kimi-K2.6 via Azure OpenAI endpoint.
    """
    deployment_name = "Kimi-K2.6"
    endpoint = settings.AZURE_OPENAI_ENDPOINT or "https://microfoundryergo.services.ai.azure.com/openai/v1"
    api_key = settings.AZURE_OPENAI_API_KEY

    logger.info(f"[LLM] Initializing Azure OpenAI Model ({deployment_name})")

    client = AsyncOpenAI(
        base_url=endpoint,
        api_key=api_key
    )

    return openai.LLM(
        model=deployment_name,
        client=client,
        temperature=0.0
    )
