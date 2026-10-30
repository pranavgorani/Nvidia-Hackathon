from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import Lead, Document, Property, WorkflowExecution, ApprovalRequest, AuditEvent
from app.providers.factory import get_ai_provider

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/metrics")
async def get_dashboard_metrics(
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    org_id = member.organization_id

    # 1. Total leads
    leads_res = await db.execute(
        select(func.count(Lead.id)).where(Lead.organization_id == org_id)
    )
    total_leads = leads_res.scalar() or 0

    # 2. New inquiries
    new_inq_res = await db.execute(
        select(func.count(Lead.id)).where(and_(Lead.organization_id == org_id, Lead.status == "new"))
    )
    new_inquiries = new_inq_res.scalar() or 0

    # 3. Active properties
    prop_res = await db.execute(
        select(func.count(Property.id)).where(and_(Property.organization_id == org_id, Property.status == "active"))
    )
    active_properties = prop_res.scalar() or 0

    # 4. Documents processed
    doc_res = await db.execute(
        select(func.count(Document.id)).where(
            and_(Document.organization_id == org_id, Document.processing_status.in_(["completed", "review_required"]))
        )
    )
    documents_processed = doc_res.scalar() or 0

    # 5. Workflows running
    wf_run_res = await db.execute(
        select(func.count(WorkflowExecution.id)).where(
            and_(WorkflowExecution.organization_id == org_id, WorkflowExecution.status == "running")
        )
    )
    workflows_running = wf_run_res.scalar() or 0

    # 6. Pending approvals
    appr_res = await db.execute(
        select(func.count(ApprovalRequest.id)).where(
            and_(ApprovalRequest.organization_id == org_id, ApprovalRequest.status == "pending")
        )
    )
    pending_approvals = appr_res.scalar() or 0

    # 7. Completed workflows
    wf_comp_res = await db.execute(
        select(func.count(WorkflowExecution.id)).where(
            and_(WorkflowExecution.organization_id == org_id, WorkflowExecution.status == "completed")
        )
    )
    completed_workflows = wf_comp_res.scalar() or 0

    # 8. Failed workflows
    wf_fail_res = await db.execute(
        select(func.count(WorkflowExecution.id)).where(
            and_(WorkflowExecution.organization_id == org_id, WorkflowExecution.status == "failed")
        )
    )
    failed_workflows = wf_fail_res.scalar() or 0

    # 9. Recent audit events
    audit_res = await db.execute(
        select(AuditEvent).where(AuditEvent.organization_id == org_id).order_by(AuditEvent.timestamp.desc()).limit(10)
    )
    recent_events = audit_res.scalars().all()

    # Provider health check
    ai_provider = get_ai_provider()
    provider_status = await ai_provider.provider_health()

    return {
        "metrics": {
            "total_leads": total_leads,
            "new_inquiries": new_inquiries,
            "active_properties": active_properties,
            "documents_processed": documents_processed,
            "workflows_running": workflows_running,
            "pending_approvals": pending_approvals,
            "completed_workflows": completed_workflows,
            "failed_workflows": failed_workflows,
        },
        "recent_activities": recent_events,
        "ai_provider": {
            "name": provider_status.get("provider", "google_gemini"),
            "model": provider_status.get("model", "gemini-2.5-flash"),
            "status": provider_status.get("status", "healthy"),
            "infrastructure": "Official Google GenAI SDK (Server-Side Only)"
        }
    }

