from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import WorkflowExecution, WorkflowStep
from app.agent.orchestrator import agent_orchestrator

router = APIRouter(prefix="/api/agent", tags=["Agent Orchestration"])

class AgentRunRequest(BaseModel):
    instruction: str
    skill_id: Optional[str] = "property_intake_agent"
    document_id: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

@router.post("/run")
async def run_agent(
    req: AgentRunRequest,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    result = await agent_orchestrator.run_workflow(
        organization_id=member.organization_id,
        actor_id=member.user_id,
        instruction=req.instruction,
        skill_id=req.skill_id,
        document_id=req.document_id,
        context_data=req.context_data,
        session=db
    )
    return result

@router.get("/workflows")
async def list_workflows(
    status: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkflowExecution).where(WorkflowExecution.organization_id == member.organization_id)
    if status:
        stmt = stmt.where(WorkflowExecution.status == status)
    res = await db.execute(stmt.order_by(WorkflowExecution.created_at.desc()).limit(30))
    return res.scalars().all()

@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkflowExecution).where(
        and_(WorkflowExecution.id == workflow_id, WorkflowExecution.organization_id == member.organization_id)
    )
    res = await db.execute(stmt)
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    # Fetch steps ordered by step_number
    s_stmt = select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.step_number.asc())
    s_res = await db.execute(s_stmt)
    steps = s_res.scalars().all()

    return {
        "workflow": workflow,
        "steps": steps
    }

