import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.config import settings
from app.core.security import compute_payload_hash
from app.db.models import ApprovalRequest, WorkflowExecution, WorkflowStep
from app.services.crm import crm_service
from app.services.audit import audit_service

logger = logging.getLogger(__name__)

class ApprovalService:
    async def create_approval_request(
        self,
        organization_id: str,
        workflow_id: str,
        requesting_user_id: Optional[str],
        target_resource_type: str,
        proposed_action: str,
        proposed_payload: Dict[str, Any],
        target_resource_id: Optional[str] = None,
        risk_category: str = "medium",
        session: AsyncSession = None
    ) -> ApprovalRequest:
        payload_hash = compute_payload_hash(proposed_payload)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.APPROVAL_EXPIRY_HOURS)

        approval = ApprovalRequest(
            organization_id=organization_id,
            workflow_id=workflow_id,
            requesting_user_id=requesting_user_id,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            proposed_action=proposed_action,
            proposed_payload_json=proposed_payload,
            payload_hash=payload_hash,
            risk_category=risk_category,
            status="pending",
            expires_at=expires_at
        )
        session.add(approval)

        # Update workflow status to paused_for_approval
        w_stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        w_res = await session.execute(w_stmt)
        workflow = w_res.scalar_one_or_none()
        if workflow:
            workflow.status = "paused_for_approval"

        # Log audit event
        await audit_service.log_event(
            organization_id=organization_id,
            action_type="approval_requested",
            outcome="paused",
            actor_id=requesting_user_id,
            workflow_id=workflow_id,
            resource_type=target_resource_type,
            resource_id=target_resource_id,
            approval_id=approval.id,
            details={"action": proposed_action, "payload_hash": payload_hash, "risk": risk_category},
            session=session
        )

        await session.commit()
        await session.refresh(approval)
        return approval

    async def execute_approved_action(
        self,
        approval: ApprovalRequest,
        actor_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Executes the approved action. Validates hash before executing.
        """
        # Tamper verification
        current_hash = compute_payload_hash(approval.proposed_payload_json)
        if current_hash != approval.payload_hash:
            approval.status = "failed"
            approval.execution_result_json = {"error": "Tamper detected: Payload hash mismatch."}
            await session.commit()
            raise ValueError("Approval payload has been tampered with or modified. Execution aborted.")

        action = approval.proposed_action
        payload = approval.proposed_payload_json
        result = {}

        if action == "create_lead":
            created_lead = await crm_service.create_lead(
                organization_id=approval.organization_id,
                data=payload,
                actor_id=actor_id,
                session=session
            )
            result = {
                "status": "success",
                "action": "create_lead",
                "lead_id": created_lead.id,
                "contact_name": created_lead.contact_name,
                "preferred_location": created_lead.preferred_location,
                "budget_range": created_lead.budget_range
            }
        elif action == "update_lead":
            target_id = approval.target_resource_id or payload.get("lead_id")
            updated_lead = await crm_service.update_lead(
                organization_id=approval.organization_id,
                lead_id=target_id,
                data=payload,
                actor_id=actor_id,
                session=session
            )
            result = {
                "status": "success",
                "action": "update_lead",
                "lead_id": updated_lead.id,
                "contact_name": updated_lead.contact_name
            }
        else:
            raise ValueError(f"Unsupported approved action: {action}")

        # Also create a follow-up task if lead was created
        if action == "create_lead" and "lead_id" in result:
            task = await crm_service.create_task(
                organization_id=approval.organization_id,
                data={
                    "lead_id": result["lead_id"],
                    "title": f"Follow-up: Qualify inquiry from {result['contact_name']}",
                    "description": "Auto-scheduled by DocuFlow Property Intake Agent upon lead approval.",
                    "priority": "high"
                },
                session=session
            )
            result["follow_up_task_id"] = task.id

        approval.status = "completed"
        approval.execution_result_json = result

        # Resume and complete workflow
        w_stmt = select(WorkflowExecution).where(WorkflowExecution.id == approval.workflow_id)
        w_res = await session.execute(w_stmt)
        workflow = w_res.scalar_one_or_none()
        if workflow:
            workflow.status = "completed"
            workflow.final_summary = (
                f"Workflow completed successfully. Approved action '{action}' was executed.\n"
                f"Persisted Lead ID: {result.get('lead_id', 'N/A')}.\n"
                f"Follow-up Task Scheduled: {result.get('follow_up_task_id', 'N/A')}."
            )
            # Add step
            count_stmt = select(func.count(WorkflowStep.id)).where(WorkflowStep.workflow_id == workflow.id)
            step_count = (await session.execute(count_stmt)).scalar() or 0
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_number=step_count + 1,
                step_type="verification",
                status="completed",
                input_data_json={"approval_id": approval.id},
                output_data_json=result
            )
            session.add(step)

        await audit_service.log_event(
            organization_id=approval.organization_id,
            action_type="action_executed_after_approval",
            outcome="success",
            actor_id=actor_id,
            workflow_id=approval.workflow_id,
            resource_type=approval.target_resource_type,
            resource_id=result.get("lead_id"),
            approval_id=approval.id,
            details=result,
            session=session
        )

        await session.commit()
        return result

    async def decide_approval(
        self,
        approval_id: str,
        decision: str, # "approve" or "reject"
        approver_id: str,
        approver_role: str,
        notes: Optional[str],
        session: AsyncSession
    ) -> Dict[str, Any]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        res = await session.execute(stmt)
        approval = res.scalar_one_or_none()
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        if approval.status != "pending":
            raise ValueError(f"Cannot decide on approval in status '{approval.status}'.")

        # Expiry check
        now = datetime.now(timezone.utc)
        if approval.expires_at.replace(tzinfo=timezone.utc) < now:
            approval.status = "expired"
            await session.commit()
            raise ValueError("Approval request has expired.")

        # Permission check: must be owner, admin, or manager
        if approver_role not in ["owner", "admin", "manager"]:
            raise PermissionError("Insufficient permissions. Approvals require Manager, Admin, or Owner role.")

        approval.approver_user_id = approver_id
        approval.approver_notes = notes

        if decision == "reject":
            approval.status = "rejected"
            w_stmt = select(WorkflowExecution).where(WorkflowExecution.id == approval.workflow_id)
            w_res = await session.execute(w_stmt)
            workflow = w_res.scalar_one_or_none()
            if workflow:
                workflow.status = "failed"
                workflow.final_summary = f"Workflow halted: Proposed action was rejected by approver. Reason: {notes or 'No reason provided.'}"

            await audit_service.log_event(
                organization_id=approval.organization_id,
                action_type="approval_rejected",
                outcome="failure",
                actor_id=approver_id,
                workflow_id=approval.workflow_id,
                approval_id=approval.id,
                details={"notes": notes},
                session=session
            )
            await session.commit()
            return {"status": "rejected", "approval_id": approval.id}

        elif decision == "approve":
            approval.status = "approved"
            exec_result = await self.execute_approved_action(approval, approver_id, session)
            return {"status": "approved", "approval_id": approval.id, "execution_result": exec_result}
        else:
            raise ValueError(f"Invalid decision '{decision}'. Expected 'approve' or 'reject'.")

approval_service = ApprovalService()

