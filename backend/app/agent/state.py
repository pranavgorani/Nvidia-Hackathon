from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED_FOR_APPROVAL = "paused_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepType(str, Enum):
    PLAN = "plan"
    MODEL_PROPOSAL = "model_proposal"
    AUTHORIZATION = "authorization"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUEST = "approval_request"
    VERIFICATION = "verification"

class AgentWorkflowContext(BaseModel):
    workflow_id: str
    organization_id: str
    actor_id: Optional[str] = None
    skill_id: str
    instruction: str
    document_id: Optional[str] = None
    turn_count: int = 0
    max_turns: int = 15
    variables: Dict[str, Any] = Field(default_factory=dict)
    steps_log: List[Dict[str, Any]] = Field(default_factory=list)

