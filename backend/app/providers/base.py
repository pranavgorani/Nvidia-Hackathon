from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ToolCallProposal(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None

class AgentTurnResult(BaseModel):
    text_response: Optional[str] = None
    tool_calls: List[ToolCallProposal] = []
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    candidates_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_name: str

class BaseAIProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        """Generate unstructured text response from the model."""
        pass

    @abstractmethod
    async def generate_structured_response(
        self,
        prompt: str,
        response_schema: Any,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> Any:
        """Generate typed structured response validated against a Pydantic schema or JSON schema."""
        pass

    @abstractmethod
    async def execute_agent_turn(
        self,
        contents: Any,
        tools: List[Any],
        system_instruction: Optional[str] = None
    ) -> AgentTurnResult:
        """
        Execute an agent turn with tool definitions using automatic function calling disabled.
        Returns proposed tool calls for backend authorization and execution.
        """
        pass

    @abstractmethod
    async def provider_health(self) -> Dict[str, Any]:
        """Perform a lightweight health check verifying connectivity and credentials."""
        pass

