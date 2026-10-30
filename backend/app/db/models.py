import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ==============================================================================
# Auth & Organization Models
# ==============================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="agent") # owner, admin, manager, agent, viewer
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="members")

    __table_args__ = (
        Index("idx_org_user", "organization_id", "user_id", unique=True),
    )

# ==============================================================================
# CRM Models
# ==============================================================================
class Contact(Base):
    __tablename__ = "crm_contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    company = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    leads = relationship("Lead", back_populates="contact")

class Lead(Base):
    __tablename__ = "crm_leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    source = Column(String(100), default="Direct Inquiry") # Document Intake, Web, Referral
    preferred_location = Column(String(255), nullable=True)
    budget_range = Column(String(100), nullable=True)
    min_budget = Column(Float, nullable=True)
    max_budget = Column(Float, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    property_type = Column(String(100), nullable=True) # Villa, Apartment, Commercial, Penthouse
    property_requirements = Column(Text, nullable=True)
    assigned_owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="new", index=True) # new, contacted, qualified, site_visit_scheduled, negotiation, won, lost
    priority = Column(String(50), default="medium") # low, medium, high, urgent
    last_contact_date = Column(DateTime, nullable=True)
    next_follow_up = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    contact = relationship("Contact", back_populates="leads")
    tasks = relationship("Task", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="lead", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="lead", cascade="all, delete-orphan")

class Property(Base):
    __tablename__ = "crm_properties"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Float, nullable=False)
    square_feet = Column(Integer, nullable=False)
    property_type = Column(String(100), nullable=False)
    status = Column(String(50), default="active", index=True) # active, pending, sold
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class Task(Base):
    __tablename__ = "crm_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending", index=True) # pending, completed, cancelled
    priority = Column(String(50), default="medium")
    assigned_to_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    lead = relationship("Lead", back_populates="tasks")

class Activity(Base):
    __tablename__ = "crm_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(String(50), nullable=False) # call, email, site_visit, note, status_change, document_intake
    summary = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="activities")

class Note(Base):
    __tablename__ = "crm_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    lead = relationship("Lead", back_populates="notes")

# ==============================================================================
# Document Intelligence Models
# ==============================================================================
class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False) # Opaque stored filename
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    processing_status = Column(String(50), default="uploaded", index=True) # uploaded, queued, processing, review_required, completed, failed
    raw_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    extractions = relationship("DocumentExtraction", back_populates="document", cascade="all, delete-orphan")

class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    inquiry_source = Column(String(100), nullable=True)
    preferred_location = Column(String(255), nullable=True)
    property_type = Column(String(100), nullable=True)
    budget = Column(String(100), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    preference = Column(String(50), nullable=True) # Buy, Rent
    requirements = Column(Text, nullable=True)
    inquiry_date = Column(String(50), nullable=True)
    # JSON containing evidence snippets, page numbers, confidence heuristics, validation warnings:
    field_metadata_json = Column(JSON, nullable=True)
    review_status = Column(String(50), default="pending", index=True) # pending, reviewed, approved, rejected
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    document = relationship("Document", back_populates="extractions")
    revisions = relationship("DocumentExtractionRevision", back_populates="extraction", cascade="all, delete-orphan")

class DocumentExtractionRevision(Base):
    __tablename__ = "document_extraction_revisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    extraction_id = Column(String(36), ForeignKey("document_extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    modified_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    previous_data_json = Column(JSON, nullable=False)
    new_data_json = Column(JSON, nullable=False)
    change_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    extraction = relationship("DocumentExtraction", back_populates="revisions")

# ==============================================================================
# Agent Orchestration, Approvals, Skills & Audit Models
# ==============================================================================
class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    skill_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String(50), default="1.0.0")
    input_schema_json = Column(JSON, nullable=True)
    output_schema_json = Column(JSON, nullable=True)
    allowed_tools_json = Column(JSON, nullable=False)
    approval_policy_json = Column(JSON, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    initiated_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    skill_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="pending", index=True) # pending, running, paused_for_approval, completed, failed, cancelled
    initial_instruction = Column(Text, nullable=False)
    context_data_json = Column(JSON, nullable=True)
    final_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    approvals = relationship("ApprovalRequest", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False) # plan, model_proposal, authorization, tool_call, tool_result, approval_request, verification
    status = Column(String(50), default="completed") # started, completed, failed
    input_data_json = Column(JSON, nullable=True)
    output_data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    workflow = relationship("WorkflowExecution", back_populates="steps")

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    requesting_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_resource_type = Column(String(100), nullable=False) # lead, contact, task
    target_resource_id = Column(String(36), nullable=True)
    proposed_action = Column(String(100), nullable=False) # create_lead, update_lead, delete_lead
    proposed_payload_json = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False) # SHA-256 hash of proposed_payload_json
    risk_category = Column(String(50), default="medium") # low, medium, high
    status = Column(String(50), default="pending", index=True) # pending, approved, rejected, expired, executing, completed, failed, cancelled
    approver_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approver_notes = Column(Text, nullable=True)
    execution_result_json = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    workflow = relationship("WorkflowExecution", back_populates="approvals")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String(36), nullable=True, index=True)
    step_id = Column(String(36), nullable=True)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    action_type = Column(String(100), nullable=False, index=True) # tool_executed, approval_granted, lead_created, etc.
    tool_name = Column(String(100), nullable=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)
    approval_id = Column(String(36), nullable=True)
    outcome = Column(String(50), nullable=False) # success, failure, paused
    error_category = Column(String(100), nullable=True)
    details_json = Column(JSON, nullable=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    organization_id = Column(String(36), nullable=False)
    tool_name = Column(String(100), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow)

