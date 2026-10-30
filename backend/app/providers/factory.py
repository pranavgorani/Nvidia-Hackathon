import logging
from typing import Optional
from app.core.config import settings
from app.providers.base import BaseAIProvider
from app.providers.gemini import GoogleGeminiProvider

logger = logging.getLogger(__name__)

_provider_instance: Optional[BaseAIProvider] = None

def get_ai_provider() -> BaseAIProvider:
    """
    Factory resolving the active AI inference provider.
    Centralizes inference configuration and guarantees backend-only API key access.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if settings.AI_PROVIDER == "google_gemini":
        logger.info(f"Initializing GoogleGeminiProvider with model {settings.GEMINI_MODEL}")
        _provider_instance = GoogleGeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
        return _provider_instance
    else:
        raise ValueError(
            f"Unsupported AI Provider '{settings.AI_PROVIDER}'. "
            "DocuFlow AI Agent OS requires AI_PROVIDER=google_gemini with valid GEMINI_API_KEY."
        )

def set_ai_provider(provider: Optional[BaseAIProvider]) -> None:
    """Sets or overrides the provider instance (used for testing and mocking)."""
    global _provider_instance
    _provider_instance = provider

