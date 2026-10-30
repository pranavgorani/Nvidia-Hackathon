import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import Document, DocumentExtraction, WorkflowExecution, WorkflowStep
from app.services.document_intelligence import document_intelligence_service
from app.services.crm import crm_service
from app.services.approval import approval_service
from app.services.audit import audit_service
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class PropertyIntakeAgent:
    """
    Signature Skill: Property Intake Agent (v1.0.0)
    Executes the 11-step end-to-end workflow converting property inquiry documents
    into verified CRM records with human-in-the-loop approval.
    """

    async def execute(
        self,
        workflow: WorkflowExecution,
        document_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        org_id = workflow.organization_id
        actor_id = workflow.initiated_by_id
        current_step_num = 1

        async def record_step(step_type: str, input_data: Any, output_data: Any, status: str = "completed"):
            nonlocal current_step_num
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_number=current_step_num,
                step_type=step_type,
                status=status,
                input_data_json=input_data if isinstance(input_data, dict) else {"data": input_data},
                output_data_json=output_data if isinstance(output_data, dict) else {"data": output_data}
            )
            session.add(step)
            current_step_num += 1
            await session.commit()
            return step

        # STEP 1: Resolve the uploaded document & check permissions
        await record_step(
            step_type="plan",
            input_data={"instruction": workflow.initial_instruction, "document_id": document_id},
            output_data={"plan": "Step 1: Resolve document; Step 2: Extract text/intelligence; Step 3: Match CRM; Step 4: Propose action; Step 5: Enforce Approval."}
        )

        doc_stmt = select(Document).where(and_(Document.id == document_id, Document.organization_id == org_id))
        doc_res = await session.execute(doc_stmt)
        document = doc_res.scalar_one_or_none()
        if not document:
            error_msg = f"Document {document_id} not found or unauthorized for this organization."
            workflow.status = "failed"
            workflow.error_message = error_msg
            await session.commit()
            await record_step("verification", {"error": error_msg}, {"status": "failed"}, status="failed")
            return {"status": "failed", "error": error_msg}

        await record_step(
            step_type="tool_result",
            input_data={"action": "resolve_document", "document_id": document.id},
            output_data={"original_name": document.original_name, "mime_type": document.mime_type, "status": document.processing_status}
        )

        # STEP 2 & 3: Check processing status and retrieve validated extraction
        ext_stmt = select(DocumentExtraction).where(
            and_(DocumentExtraction.document_id == document.id, DocumentExtraction.organization_id == org_id)
        ).order_by(DocumentExtraction.created_at.desc())
        ext_res = await session.execute(ext_stmt)
        extraction = ext_res.scalar_one_or_none()

        if not extraction or document.processing_status in ["uploaded", "queued"]:
            # Run document intelligence pipeline with Google Gemini
            extraction = await document_intelligence_service.process_document(document.id, session)

        await record_step(
            step_type="tool_result",
            input_data={"action": "get_extraction", "document_id": document.id},
            output_data={
                "customer_name": extraction.customer_name,
                "email": extraction.email,
                "phone": extraction.phone,
                "preferred_location": extraction.preferred_location,
                "budget": extraction.budget,
                "property_type": extraction.property_type,
                "bedrooms": extraction.bedrooms,
                "review_status": extraction.review_status
            }
        )

        # STEP 4: Review extraction quality & missing fields
        missing_fields = []
        if not extraction.customer_name:
            missing_fields.append("customer_name")
        if not extraction.email and not extraction.phone:
            missing_fields.append("contact_information")

        extraction_quality = {
            "is_valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "review_status": extraction.review_status,
            "confidence_scores": {
                k: v.get("confidence") for k, v in (extraction.field_metadata_json or {}).items()
            }
        }
        await record_step(
            step_type="authorization",
            input_data={"check": "extraction_quality_check"},
            output_data=extraction_quality
        )

        # STEP 5: Match existing records (CRM deduplication)
        matches = await crm_service.match_existing_records(
            organization_id=org_id,
            email=extraction.email,
            phone=extraction.phone,
            name=extraction.customer_name,
            session=session
        )

        await record_step(
            step_type="tool_result",
            input_data={"action": "search_contacts_and_leads", "email": extraction.email, "phone": extraction.phone, "name": extraction.customer_name},
            output_data=matches
        )

        # STEP 6: Prepare proposed CRM action
        proposed_action = "create_lead"
        target_resource_id = None
        matched_lead = None

        if matches["leads"]:
            # Propose updating the first matched lead
            matched_lead = matches["leads"][0]
            proposed_action = "update_lead"
            target_resource_id = matched_lead["id"]
            proposed_payload = {
                "lead_id": matched_lead["id"],
                "preferred_location": extraction.preferred_location or matched_lead.get("preferred_location"),
                "budget_range": extraction.budget or matched_lead.get("budget_range"),
                "property_requirements": extraction.requirements or "Updated via document intake"
            }
        else:
            # Propose creating a new lead
            matched_contact_id = matches["contacts"][0]["id"] if matches["contacts"] else None
            proposed_payload = {
                "contact_name": extraction.customer_name or "Prospective Client (Document Intake)",
                "email": extraction.email,
                "phone": extraction.phone,
                "source": "Document Intake",
                "preferred_location": extraction.preferred_location,
                "budget_range": extraction.budget,
                "bedrooms": extraction.bedrooms,
                "property_type": extraction.property_type,
                "property_requirements": extraction.requirements,
                "priority": "high" if "urgent" in (extraction.requirements or "").lower() else "medium",
                "contact_id": matched_contact_id
            }

        # STEP 7 & 8: Apply policy & Request human approval
        # All writes to CRM require human-in-the-loop approval
        approval = await approval_service.create_approval_request(
            organization_id=org_id,
            workflow_id=workflow.id,
            requesting_user_id=actor_id,
            target_resource_type="lead",
            proposed_action=proposed_action,
            proposed_payload=proposed_payload,
            target_resource_id=target_resource_id,
            risk_category="medium",
            session=session
        )

        await record_step(
            step_type="approval_request",
            input_data={"action": proposed_action, "payload": proposed_payload},
            output_data={
                "approval_id": approval.id,
                "payload_hash": approval.payload_hash,
                "status": "pending",
                "message": f"Action '{proposed_action}' requires manager/admin approval before CRM execution."
            }
        )

        workflow.status = "paused_for_approval"
        workflow.final_summary = (
            f"Property Intake Agent completed extraction and record matching.\n"
            f"Proposed Action: {proposed_action.upper()} for '{proposed_payload.get('contact_name', 'Contact')}'.\n"
            f"Approval Request #{approval.id} is pending human sign-off."
        )
        await session.commit()

        return {
            "status": "paused_for_approval",
            "workflow_id": workflow.id,
            "approval_id": approval.id,
            "payload_hash": approval.payload_hash,
            "proposed_action": proposed_action,
            "proposed_payload": proposed_payload,
            "extraction_id": extraction.id
        }

property_intake_agent = PropertyIntakeAgent()

