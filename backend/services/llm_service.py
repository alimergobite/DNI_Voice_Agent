import os
import logging
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=True)

from livekit.plugins import openai
from openai import AsyncOpenAI, AsyncAzureOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns the configured LLM Engine for the agent.
    """
    model_choice = os.getenv("LLM_MODEL_NAME", "gpt-5.4-mini")

    if model_choice == "gpt-5.4-mini":
        logger.info("[LLM] Initializing Azure OpenAI (gpt-5.4-mini) for ultra-low latency voice streaming")
        azure_client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint="https://abhishekazureopenaitest.openai.azure.com",
            api_version="2024-02-01"
        )
        return openai.LLM(
            model="gpt-5.4-mini",
            client=azure_client,
            reasoning_effort="low",
            verbosity="low",
            temperature=0.0
        )
    else:
        # Custom endpoint model (e.g. grok-4-20-reasoning / grok-4-20-non-reasoning)
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or getattr(settings, "AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY") or getattr(settings, "AZURE_OPENAI_API_KEY", "")
        logger.info(f"[LLM] Initializing custom endpoint LLM ({model_choice}) with base_url: {endpoint}")
        client = AsyncOpenAI(
            base_url=endpoint,
            api_key=api_key
        )
        return openai.LLM(
            model=model_choice,
            client=client,
            temperature=0.0
        )
