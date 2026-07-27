import logging
from livekit.plugins import openai
from openai import AsyncOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns the configured LLM Engine for the agent.
    Configured for grok-4-20-reasoning via Azure OpenAI.
    """
    deployment_name = "grok-4-20-reasoning"
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
