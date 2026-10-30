import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from google.genai import types

from app.tools.schemas import (
    ListDocumentsInput, GetDocumentMetadataInput, GetExtractionInput, UpdateReviewedExtractionInput,
    SearchContactsInput, SearchLeadsInput, GetLeadInput, CreateLeadInput, UpdateLeadInput, AddLeadNoteInput,
    SearchPropertiesInput, GetPropertyInput,
    CreateTaskInput, ListTasksInput, UpdateTaskStatusInput,
    RequestApprovalInput, GetWorkflowStatusInput, GetWorkflowHistoryInput
)
from app.db.models import Document, DocumentExtraction, Contact, Lead, Property, Task, Note, WorkflowExecution, WorkflowStep
from app.services.crm import crm_service
from app.services.document_intelligence import document_intelligence_service
from app.services.approval import approval_service
from app.services.audit import audit_service

logger = logging.getLogger(__name__)

class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        schema_cls: Any,
        handler: Callable,
        is_write_action: bool = False,
        requires_approval: bool = False
    ):
        self.name = name
        self.description = description
        self.schema_cls = schema_cls
        self.handler = handler
        self.is_write_action = is_write_action
        self.requires_approval = requires_approval

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool_def: ToolDefinition):
        self._tools[tool_def.name] = tool_def

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._tools

    def get_gemini_declarations(self, allowed_tool_names: Optional[List[str]] = None) -> List[Any]:
        """
        Converts registered tools into Gemini types.FunctionDeclaration objects.
        """
        declarations = []
        for name, tool in self._tools.items():
            if allowed_tool_names and name not in allowed_tool_names:
                continue

            # Convert Pydantic schema to parameters dict
            json_schema = tool.schema_cls.model_json_schema()
            # Clean up properties for Gemini function declaration
            params = {
                "type": "OBJECT",
                "properties": {},
                "required": json_schema.get("required", [])
            }
            for prop_name, prop_data in json_schema.get("properties", {}).items():
                p_type = prop_data.get("type", "string").upper()
                if p_type == "INTEGER":
                    p_type = "INTEGER"
                elif p_type == "NUMBER":
                    p_type = "NUMBER"
                elif p_type == "BOOLEAN":
                    p_type = "BOOLEAN"
                elif p_type == "ARRAY":
                    p_type = "ARRAY"
                elif p_type == "OBJECT":
                    p_type = "OBJECT"
                else:
                    p_type = "STRING"

                params["properties"][prop_name] = {
                    "type": p_type,
                    "description": prop_data.get("description", "")
                }

            decl = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=params
            )
            declarations.append(decl)

        if not declarations:
            return []
        return [types.Tool(function_declarations=declarations)]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        organization_id: str,
        actor_id: Optional[str],
        workflow_id: Optional[str],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Executes a proposed tool call with strict allowlist and parameter schema validation.
        """
        if not self.is_registered(tool_name):
            error_msg = f"Security Violation: Tool '{tool_name}' is not in the approved tool allowlist."
            await audit_service.log_event(
                organization_id=organization_id,
                action_type="unknown_tool_rejection",
                outcome="failure",
                actor_id=actor_id,
                workflow_id=workflow_id,
                tool_name=tool_name,
                error_category="allowlist_rejection",
                details={"arguments": arguments},
                session=session
            )
            raise ValueError(error_msg)

        tool_def = self._tools[tool_name]

        # Validate arguments against Pydantic schema
        try:
            validated_input = tool_def.schema_cls.model_validate(arguments)
        except ValidationError as ve:
            error_msg = f"Argument validation failed for tool '{tool_name}': {ve.errors()}"
            await audit_service.log_event(
                organization_id=organization_id,
                action_type="tool_validation_failure",
                outcome="failure",
                actor_id=actor_id,
                workflow_id=workflow_id,
                tool_name=tool_name,
                error_category="schema_validation_error",
                details={"errors": str(ve)},
                session=session
            )
            raise ValueError(error_msg)

        # Execute handler
        try:
            result = await tool_def.handler(
                validated_input=validated_input,
                organization_id=organization_id,
                actor_id=actor_id,
                workflow_id=workflow_id,
                session=session
            )

            await audit_service.log_event(
                organization_id=organization_id,
                action_type="tool_executed",
                outcome="success",
                actor_id=actor_id,
                workflow_id=workflow_id,
                tool_name=tool_name,
                resource_type=result.get("resource_type"),
                resource_id=result.get("resource_id"),
                details={"result_keys": list(result.keys()) if isinstance(result, dict) else "ok"},
                session=session
            )
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            await audit_service.log_event(
                organization_id=organization_id,
                action_type="tool_execution_error",
                outcome="failure",
                actor_id=actor_id,
                workflow_id=workflow_id,
                tool_name=tool_name,
                error_category="runtime_error",
                details={"error": str(e)},
                session=session
            )
            raise

    def _register_default_tools(self):
        # 1. Document tools
        self.register(ToolDefinition(
            name="list_documents",
            description="List processed and pending documents uploaded to the organization.",
            schema_cls=ListDocumentsInput,
            handler=self._handle_list_documents
        ))
        self.register(ToolDefinition(
            name="get_document_metadata",
            description="Retrieve metadata, original name, processing status, and raw text preview of a document.",
            schema_cls=GetDocumentMetadataInput,
            handler=self._handle_get_document_metadata
        ))
        self.register(ToolDefinition(
            name="get_extraction",
            description="Retrieve structured extracted property inquiry data, confidence scores, and source evidence snippets.",
            schema_cls=GetExtractionInput,
            handler=self._handle_get_extraction
        ))
        self.register(ToolDefinition(
            name="update_reviewed_extraction",
            description="Correct or update document extraction fields with human review and revision tracking.",
            schema_cls=UpdateReviewedExtractionInput,
            handler=self._handle_update_reviewed_extraction,
            is_write_action=True
        ))

        # 2. CRM tools
        self.register(ToolDefinition(
            name="search_contacts",
            description="Search contacts by exact email, normalized phone, or partial name to identify existing customers.",
            schema_cls=SearchContactsInput,
            handler=self._handle_search_contacts
        ))
        self.register(ToolDefinition(
            name="search_leads",
            description="Search leads by email, phone, name, or pipeline status.",
            schema_cls=SearchLeadsInput,
            handler=self._handle_search_leads
        ))
        self.register(ToolDefinition(
            name="get_lead",
            description="Retrieve detailed CRM lead record including property requirements, contact info, and activity history.",
            schema_cls=GetLeadInput,
            handler=self._handle_get_lead
        ))
        self.register(ToolDefinition(
            name="create_lead",
            description="Create a new CRM lead record with contact info, budget, location preferences, and requirement notes.",
            schema_cls=CreateLeadInput,
            handler=self._handle_create_lead,
            is_write_action=True,
            requires_approval=True
        ))
        self.register(ToolDefinition(
            name="update_lead",
            description="Update existing CRM lead status, requirements, budget, or next follow-up date.",
            schema_cls=UpdateLeadInput,
            handler=self._handle_update_lead,
            is_write_action=True,
            requires_approval=True
        ))
        self.register(ToolDefinition(
            name="add_lead_note",
            description="Add an internal CRM note or agent observation to a lead record.",
            schema_cls=AddLeadNoteInput,
            handler=self._handle_add_lead_note,
            is_write_action=True
        ))

        # 3. Property tools
        self.register(ToolDefinition(
            name="search_properties",
            description="Search inventory properties matching client requirements (city, property type, price ceiling, bedrooms).",
            schema_cls=SearchPropertiesInput,
            handler=self._handle_search_properties
        ))
        self.register(ToolDefinition(
            name="get_property",
            description="Get details of a specific property listing.",
            schema_cls=GetPropertyInput,
            handler=self._handle_get_property
        ))

        # 4. Task tools
        self.register(ToolDefinition(
            name="create_task",
            description="Create a follow-up or administrative task associated with a lead.",
            schema_cls=CreateTaskInput,
            handler=self._handle_create_task,
            is_write_action=True
        ))
        self.register(ToolDefinition(
            name="list_tasks",
            description="List CRM tasks filtered by lead ID or pending/completed status.",
            schema_cls=ListTasksInput,
            handler=self._handle_list_tasks
        ))
        self.register(ToolDefinition(
            name="update_task_status",
            description="Mark a task as completed or cancelled.",
            schema_cls=UpdateTaskStatusInput,
            handler=self._handle_update_task_status,
            is_write_action=True
        ))

        # 5. Workflow & Approval tools
        self.register(ToolDefinition(
            name="request_approval",
            description="Propose a write operation (e.g. create_lead or update_lead) and pause workflow for human approval.",
            schema_cls=RequestApprovalInput,
            handler=self._handle_request_approval,
            is_write_action=True
        ))
        self.register(ToolDefinition(
            name="get_workflow_status",
            description="Check the current status and execution step of a workflow.",
            schema_cls=GetWorkflowStatusInput,
            handler=self._handle_get_workflow_status
        ))
        self.register(ToolDefinition(
            name="get_workflow_history",
            description="Retrieve execution timeline steps and tool actions for a workflow.",
            schema_cls=GetWorkflowHistoryInput,
            handler=self._handle_get_workflow_history
        ))

    # ==========================================================================
    # Tool Handlers
    # ==========================================================================
    async def _handle_list_documents(self, validated_input: ListDocumentsInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Document).where(Document.organization_id == organization_id)
        if validated_input.status:
            stmt = stmt.where(Document.processing_status == validated_input.status)
        stmt = stmt.order_by(Document.created_at.desc()).limit(validated_input.limit)
        res = await session.execute(stmt)
        docs = res.scalars().all()
        return {
            "resource_type": "document",
            "count": len(docs),
            "documents": [
                {
                    "id": d.id,
                    "filename": d.original_name,
                    "status": d.processing_status,
                    "mime_type": d.mime_type,
                    "created_at": d.created_at.isoformat()
                }
                for d in docs
            ]
        }

    async def _handle_get_document_metadata(self, validated_input: GetDocumentMetadataInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Document).where(and_(Document.id == validated_input.document_id, Document.organization_id == organization_id))
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return {"error": f"Document {validated_input.document_id} not found."}
        return {
            "resource_type": "document",
            "resource_id": doc.id,
            "id": doc.id,
            "original_name": doc.original_name,
            "status": doc.processing_status,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "text_snippet": (doc.raw_text or "")[:500]
        }

    async def _handle_get_extraction(self, validated_input: GetExtractionInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(DocumentExtraction).where(
            and_(DocumentExtraction.document_id == validated_input.document_id, DocumentExtraction.organization_id == organization_id)
        ).order_by(DocumentExtraction.created_at.desc())
        res = await session.execute(stmt)
        extraction = res.scalar_one_or_none()
        if not extraction:
            return {"error": f"No extraction found for document {validated_input.document_id}."}
        return {
            "resource_type": "extraction",
            "resource_id": extraction.id,
            "id": extraction.id,
            "document_id": extraction.document_id,
            "customer_name": extraction.customer_name,
            "email": extraction.email,
            "phone": extraction.phone,
            "inquiry_source": extraction.inquiry_source,
            "preferred_location": extraction.preferred_location,
            "property_type": extraction.property_type,
            "budget": extraction.budget,
            "bedrooms": extraction.bedrooms,
            "preference": extraction.preference,
            "requirements": extraction.requirements,
            "inquiry_date": extraction.inquiry_date,
            "review_status": extraction.review_status,
            "field_metadata": extraction.field_metadata_json
        }

    async def _handle_update_reviewed_extraction(self, validated_input: UpdateReviewedExtractionInput, organization_id: str, actor_id: str, session: AsyncSession, **kwargs):
        extraction = await document_intelligence_service.update_reviewed_extraction(
            extraction_id=validated_input.extraction_id,
            updated_fields=validated_input.updated_fields,
            modified_by_id=actor_id,
            change_reason=validated_input.change_reason or "Tool update",
            session=session
        )
        return {
            "resource_type": "extraction",
            "resource_id": extraction.id,
            "status": "updated",
            "review_status": extraction.review_status
        }

    async def _handle_search_contacts(self, validated_input: SearchContactsInput, organization_id: str, session: AsyncSession, **kwargs):
        matches = await crm_service.match_existing_records(
            organization_id=organization_id,
            email=validated_input.email,
            phone=validated_input.phone,
            name=validated_input.name,
            session=session
        )
        return {"resource_type": "contact_matches", "matches": matches["contacts"]}

    async def _handle_search_leads(self, validated_input: SearchLeadsInput, organization_id: str, session: AsyncSession, **kwargs):
        matches = await crm_service.match_existing_records(
            organization_id=organization_id,
            email=validated_input.email,
            phone=validated_input.phone,
            name=validated_input.name,
            session=session
        )
        return {"resource_type": "lead_matches", "matches": matches["leads"]}

    async def _handle_get_lead(self, validated_input: GetLeadInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Lead).where(and_(Lead.id == validated_input.lead_id, Lead.organization_id == organization_id))
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            return {"error": f"Lead {validated_input.lead_id} not found."}
        return {
            "resource_type": "lead",
            "resource_id": lead.id,
            "id": lead.id,
            "contact_name": lead.contact_name,
            "email": lead.email,
            "phone": lead.phone,
            "status": lead.status,
            "preferred_location": lead.preferred_location,
            "budget_range": lead.budget_range,
            "bedrooms": lead.bedrooms,
            "property_type": lead.property_type,
            "property_requirements": lead.property_requirements
        }

    async def _handle_create_lead(self, validated_input: CreateLeadInput, organization_id: str, actor_id: str, session: AsyncSession, **kwargs):
        # Directly creating lead when executed (post-approval or allowed by policy)
        lead = await crm_service.create_lead(
            organization_id=organization_id,
            data=validated_input.model_dump(),
            actor_id=actor_id,
            session=session
        )
        return {
            "resource_type": "lead",
            "resource_id": lead.id,
            "status": "created",
            "lead_id": lead.id,
            "contact_name": lead.contact_name
        }

    async def _handle_update_lead(self, validated_input: UpdateLeadInput, organization_id: str, actor_id: str, session: AsyncSession, **kwargs):
        lead = await crm_service.update_lead(
            organization_id=organization_id,
            lead_id=validated_input.lead_id,
            data=validated_input.model_dump(exclude_unset=True),
            actor_id=actor_id,
            session=session
        )
        return {
            "resource_type": "lead",
            "resource_id": lead.id,
            "status": "updated",
            "lead_id": lead.id
        }

    async def _handle_add_lead_note(self, validated_input: AddLeadNoteInput, organization_id: str, actor_id: str, session: AsyncSession, **kwargs):
        note = Note(
            organization_id=organization_id,
            lead_id=validated_input.lead_id,
            content=validated_input.content,
            created_by_id=actor_id
        )
        session.add(note)
        await session.commit()
        return {"resource_type": "note", "resource_id": note.id, "status": "added"}

    async def _handle_search_properties(self, validated_input: SearchPropertiesInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Property).where(Property.organization_id == organization_id)
        if validated_input.city:
            stmt = stmt.where(Property.city.ilike(f"%{validated_input.city}%"))
        if validated_input.property_type:
            stmt = stmt.where(Property.property_type.ilike(f"%{validated_input.property_type}%"))
        if validated_input.max_price:
            stmt = stmt.where(Property.price <= validated_input.max_price)
        if validated_input.min_bedrooms:
            stmt = stmt.where(Property.bedrooms >= validated_input.min_bedrooms)
        res = await session.execute(stmt.limit(10))
        props = res.scalars().all()
        return {
            "resource_type": "properties",
            "count": len(props),
            "properties": [
                {
                    "id": p.id,
                    "title": p.title,
                    "city": p.city,
                    "price": p.price,
                    "bedrooms": p.bedrooms,
                    "property_type": p.property_type
                }
                for p in props
            ]
        }

    async def _handle_get_property(self, validated_input: GetPropertyInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Property).where(and_(Property.id == validated_input.property_id, Property.organization_id == organization_id))
        res = await session.execute(stmt)
        p = res.scalar_one_or_none()
        if not p:
            return {"error": f"Property {validated_input.property_id} not found."}
        return {
            "resource_type": "property",
            "resource_id": p.id,
            "title": p.title,
            "address": p.address,
            "price": p.price,
            "bedrooms": p.bedrooms,
            "property_type": p.property_type,
            "description": p.description
        }

    async def _handle_create_task(self, validated_input: CreateTaskInput, organization_id: str, session: AsyncSession, **kwargs):
        task = await crm_service.create_task(
            organization_id=organization_id,
            data=validated_input.model_dump(),
            session=session
        )
        return {"resource_type": "task", "resource_id": task.id, "status": "created", "task_id": task.id}

    async def _handle_list_tasks(self, validated_input: ListTasksInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Task).where(Task.organization_id == organization_id)
        if validated_input.lead_id:
            stmt = stmt.where(Task.lead_id == validated_input.lead_id)
        if validated_input.status:
            stmt = stmt.where(Task.status == validated_input.status)
        res = await session.execute(stmt.limit(20))
        tasks = res.scalars().all()
        return {
            "resource_type": "tasks",
            "count": len(tasks),
            "tasks": [{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority} for t in tasks]
        }

    async def _handle_update_task_status(self, validated_input: UpdateTaskStatusInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(Task).where(and_(Task.id == validated_input.task_id, Task.organization_id == organization_id))
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            return {"error": f"Task {validated_input.task_id} not found."}
        task.status = validated_input.status
        await session.commit()
        return {"resource_type": "task", "resource_id": task.id, "status": task.status}

    async def _handle_request_approval(self, validated_input: RequestApprovalInput, organization_id: str, actor_id: str, session: AsyncSession, **kwargs):
        approval = await approval_service.create_approval_request(
            organization_id=organization_id,
            workflow_id=validated_input.workflow_id,
            requesting_user_id=actor_id,
            target_resource_type=validated_input.target_resource_type,
            proposed_action=validated_input.proposed_action,
            proposed_payload=validated_input.proposed_payload,
            target_resource_id=validated_input.target_resource_id,
            risk_category=validated_input.risk_category,
            session=session
        )
        return {
            "resource_type": "approval_request",
            "resource_id": approval.id,
            "status": "pending_human_approval",
            "approval_id": approval.id,
            "payload_hash": approval.payload_hash,
            "action": approval.proposed_action
        }

    async def _handle_get_workflow_status(self, validated_input: GetWorkflowStatusInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(WorkflowExecution).where(
            and_(WorkflowExecution.id == validated_input.workflow_id, WorkflowExecution.organization_id == organization_id)
        )
        res = await session.execute(stmt)
        w = res.scalar_one_or_none()
        if not w:
            return {"error": f"Workflow {validated_input.workflow_id} not found."}
        return {
            "resource_type": "workflow",
            "resource_id": w.id,
            "id": w.id,
            "status": w.status,
            "skill_id": w.skill_id,
            "final_summary": w.final_summary
        }

    async def _handle_get_workflow_history(self, validated_input: GetWorkflowHistoryInput, organization_id: str, session: AsyncSession, **kwargs):
        stmt = select(WorkflowStep).where(WorkflowStep.workflow_id == validated_input.workflow_id).order_by(WorkflowStep.step_number.asc())
        res = await session.execute(stmt)
        steps = res.scalars().all()
        return {
            "resource_type": "workflow_history",
            "count": len(steps),
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "status": s.status,
                    "input": s.input_data_json,
                    "output": s.output_data_json
                }
                for s in steps
            ]
        }

tool_registry = ToolRegistry()

