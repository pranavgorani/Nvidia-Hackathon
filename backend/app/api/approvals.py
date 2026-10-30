from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import ApprovalRequest
from app.services.approval import approval_service

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

class ApprovalDecisionSchema(BaseModel):
    decision: str # "approve" or "reject"
    notes: Optional[str] = None

@router.get("")
async def list_approvals(
    status: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApprovalRequest).where(ApprovalRequest.organization_id == member.organization_id)
    if status:
        stmt = stmt.where(ApprovalRequest.status == status)
    res = await db.execute(stmt.order_by(ApprovalRequest.created_at.desc()).limit(50))
    return res.scalars().all()

@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApprovalRequest).where(
        and_(ApprovalRequest.id == approval_id, ApprovalRequest.organization_id == member.organization_id)
    )
    res = await db.execute(stmt)
    approval = res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return approval

@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    req: ApprovalDecisionSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await approval_service.decide_approval(
            approval_id=approval_id,
            decision=req.decision,
            approver_id=member.user_id,
            approver_role=member.role,
            notes=req.notes,
            session=db
        )
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

