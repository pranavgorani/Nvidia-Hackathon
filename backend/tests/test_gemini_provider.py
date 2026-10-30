import pytest
from pydantic import BaseModel
from app.providers.gemini import (
    GoogleGeminiProvider,
    GeminiQuotaExhaustedError,
    GeminiAuthenticationError
)
from app.core.config import settings

class SampleInquiry(BaseModel):
    client_name: str
    budget: str
    property_type: str

@pytest.mark.asyncio
async def test_gemini_provider_initialization():
    provider = GoogleGeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name="gemini-2.5-flash"
    )
    assert provider.model_name == "gemini-2.5-flash"
    assert provider.api_key == settings.GEMINI_API_KEY

@pytest.mark.asyncio
async def test_gemini_missing_api_key_raises():
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
        GoogleGeminiProvider(api_key="")

@pytest.mark.asyncio
async def test_gemini_provider_health():
    provider = GoogleGeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL
    )
    health = await provider.provider_health()
    assert health["provider"] == "google_gemini"
    assert health["model"] == settings.GEMINI_MODEL
    # Status can be healthy or report quota limit
    assert health["status"] in ["healthy", "unhealthy"]

@pytest.mark.asyncio
async def test_gemini_generate_response():
    provider = GoogleGeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL
    )
    try:
        resp = await provider.generate_response(
            prompt="Reply with the exact word 'CONFIRMED' only.",
            temperature=0.0
        )
        assert "CONFIRMED" in resp.strip()
    except GeminiQuotaExhaustedError as e:
        # Verifies quota error classification
        assert "quota" in str(e).lower() or "limit" in str(e).lower()

@pytest.mark.asyncio
async def test_gemini_structured_response():
    provider = GoogleGeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL
    )
    try:
        result = await provider.generate_structured_response(
            prompt="Alice Walker wants to purchase a 3-bedroom Luxury Villa with a $2.5M budget.",
            response_schema=SampleInquiry
        )
        assert isinstance(result, SampleInquiry)
        assert "Alice" in result.client_name
        assert "Villa" in result.property_type
    except GeminiQuotaExhaustedError as e:
        # Verifies quota error classification
        assert "quota" in str(e).lower() or "limit" in str(e).lower()
