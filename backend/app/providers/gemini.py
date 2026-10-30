import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from app.core.config import settings
from app.providers.base import BaseAIProvider, AgentTurnResult, ToolCallProposal

logger = logging.getLogger(__name__)

class GeminiProviderError(RuntimeError):
    """Base error for Gemini API failures."""
    pass

class GeminiQuotaExhaustedError(GeminiProviderError):
    """Raised when the Gemini API returns a 429 RESOURCE_EXHAUSTED error."""
    pass

class GeminiAuthenticationError(GeminiProviderError):
    """Raised when the Gemini API credentials are invalid or unauthorized."""
    pass

def map_gemini_api_error(e: APIError) -> Exception:
    msg = getattr(e, "message", str(e))
    code = getattr(e, "code", None)
    if code == 429 or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return GeminiQuotaExhaustedError(f"Gemini API rate limit or quota exceeded: {msg}")
    elif code in [401, 403] or "API_KEY_INVALID" in msg:
        return GeminiAuthenticationError(f"Gemini API authentication failed: {msg}")
    return GeminiProviderError(f"Google Gemini API error: {msg}")

class GoogleGeminiProvider(BaseAIProvider):
    """
    Official Google Gemini API implementation using the google-genai SDK.
    Follows zero-trust tool execution: model generates tool proposals;
    the backend authorizes and executes tools.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ):
        if api_key is None:
            self.api_key = settings.GEMINI_API_KEY
        else:
            self.api_key = api_key

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. Configure GEMINI_API_KEY in your environment or .env."
            )

        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.timeout_seconds = timeout_seconds or settings.TOOL_EXECUTION_TIMEOUT_SECONDS
        self.client = genai.Client(api_key=self.api_key)

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction
        )
        try:
            # Run in thread pool to avoid blocking asyncio event loop
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return response.text or ""
        except APIError as e:
            logger.error(f"Gemini API error during generate_response: {e.message}")
            raise map_gemini_api_error(e) from e
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {str(e)}")
            raise

    async def generate_structured_response(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> Any:
        """
        Generates structured JSON output conforming to the provided Pydantic model or JSON schema.
        """
        # Determine schema representation
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            schema_arg = response_schema.model_json_schema()
        else:
            schema_arg = response_schema

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=schema_arg
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            raw_text = response.text or "{}"
            parsed = json.loads(raw_text)

            # If a Pydantic model was provided, validate and return instance
            if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
                return response_schema.model_validate(parsed)
            return parsed
        except APIError as e:
            logger.error(f"Gemini API error during structured response: {e.message}")
            raise map_gemini_api_error(e) from e
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON returned from Gemini: {e}")
            raise ValueError(f"Failed to parse structured JSON response: {e}") from e

    async def execute_agent_turn(
        self,
        contents: Any,
        tools: List[Any],
        system_instruction: Optional[str] = None
    ) -> AgentTurnResult:
        """
        Executes a turn with function calling tool definitions.
        Automatic function calling is explicitly disabled so model proposals
        must be intercepted, validated, authorized, and executed by backend services.
        """
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            tools=tools if tools else None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ) if tools else None
        )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents,
                config=config
            )

            # Extract token usage safely
            prompt_tokens = None
            candidates_tokens = None
            total_tokens = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                candidates_tokens = getattr(response.usage_metadata, "candidates_token_count", None)
                total_tokens = getattr(response.usage_metadata, "total_token_count", None)

            # Extract tool calls (proposals)
            proposals: List[ToolCallProposal] = []
            if hasattr(response, "function_calls") and response.function_calls:
                for idx, fc in enumerate(response.function_calls):
                    args_dict = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                    proposals.append(
                        ToolCallProposal(
                            tool_name=fc.name,
                            arguments=args_dict,
                            call_id=f"call_{idx}_{fc.name}"
                        )
                    )

            text_resp = None
            try:
                text_resp = response.text
            except Exception:
                # When only function calls are present, accessing .text might raise or be empty
                pass

            return AgentTurnResult(
                text_response=text_resp,
                tool_calls=proposals,
                finish_reason="tool_call" if proposals else "stop",
                prompt_tokens=prompt_tokens,
                candidates_tokens=candidates_tokens,
                total_tokens=total_tokens,
                model_name=self.model_name
            )
        except APIError as e:
            logger.error(f"Gemini API error during agent turn: {e.message}")
            raise map_gemini_api_error(e) from e

    async def provider_health(self) -> Dict[str, Any]:
        """
        Verifies API key validity and model responsiveness with a 1-token test prompt.
        """
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=5
            )
            resp = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents="ping",
                config=config
            )
            return {
                "status": "healthy",
                "provider": "google_gemini",
                "model": self.model_name,
                "verified": bool(resp and resp.text)
            }
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "google_gemini",
                "model": self.model_name,
                "error": str(e)
            }

