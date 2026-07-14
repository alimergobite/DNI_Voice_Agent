import logging
from livekit.plugins import openai
from openai import AsyncAzureOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

def get_llm_engine():
    """
    Returns an Azure OpenAI LLM client configured exactly to the CTO's specifications.
    We use gpt-5.4-mini with reasoning_effort disabled for instantaneous voice response.
    """
    logger.info("[LLM] Initializing Azure OpenAI (gpt-5.4-mini)")
    
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
        verbosity="low"
    )
