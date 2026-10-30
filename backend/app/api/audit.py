from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["Audit & Activity"])

@router.get("/logs")
async def list_audit_logs(
    action_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditEvent).where(AuditEvent.organization_id == member.organization_id)
    if action_type:
        stmt = stmt.where(AuditEvent.action_type == action_type)
    res = await db.execute(stmt.order_by(AuditEvent.timestamp.desc()).limit(limit))
    return res.scalars().all()

