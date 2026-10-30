from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# ==============================================================================
# Document Tools Schemas
# ==============================================================================
class ListDocumentsInput(BaseModel):
    limit: int = Field(default=10, ge=1, le=50, description="Max documents to return")
    status: Optional[str] = Field(default=None, description="Filter by processing status")

class GetDocumentMetadataInput(BaseModel):
    document_id: str = Field(description="Unique ID of the document")

class GetExtractionInput(BaseModel):
    document_id: str = Field(description="Unique ID of the document whose extraction to load")

class UpdateReviewedExtractionInput(BaseModel):
    extraction_id: str = Field(description="Unique ID of the extraction record")
    updated_fields: Dict[str, Any] = Field(description="Dictionary of corrected field values")
    change_reason: Optional[str] = Field(default="Manual review correction", description="Reason for modification")

# ==============================================================================
# CRM Tools Schemas
# ==============================================================================
class SearchContactsInput(BaseModel):
    email: Optional[str] = Field(default=None, description="Exact or partial email match")
    phone: Optional[str] = Field(default=None, description="Normalized phone number")
    name: Optional[str] = Field(default=None, description="Name search keyword")

class SearchLeadsInput(BaseModel):
    email: Optional[str] = Field(default=None, description="Contact email to search for")
    phone: Optional[str] = Field(default=None, description="Contact phone to search for")
    status: Optional[str] = Field(default=None, description="Lead status filter")
    name: Optional[str] = Field(default=None, description="Lead contact name")

class GetLeadInput(BaseModel):
    lead_id: str = Field(description="Unique ID of the lead")

class CreateLeadInput(BaseModel):
    contact_name: str = Field(description="Full name of the contact")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    source: str = Field(default="Document Intake", description="Lead source")
    preferred_location: Optional[str] = Field(default=None, description="Target city or neighborhood")
    budget_range: Optional[str] = Field(default=None, description="Budget range text or formatted figure")
    min_budget: Optional[float] = Field(default=None, description="Minimum budget if known")
    max_budget: Optional[float] = Field(default=None, description="Maximum budget if known")
    bedrooms: Optional[int] = Field(default=None, description="Number of bedrooms requested")
    property_type: Optional[str] = Field(default=None, description="Type of property, e.g. Villa, Apartment")
    property_requirements: Optional[str] = Field(default=None, description="Specific features requested")
    priority: str = Field(default="medium", description="Priority: low, medium, high, urgent")
    contact_id: Optional[str] = Field(default=None, description="Existing contact ID if matched")

class UpdateLeadInput(BaseModel):
    lead_id: str = Field(description="Unique ID of the lead to update")
    status: Optional[str] = Field(default=None, description="New status")
    priority: Optional[str] = Field(default=None, description="New priority")
    preferred_location: Optional[str] = Field(default=None, description="Updated location")
    budget_range: Optional[str] = Field(default=None, description="Updated budget")
    property_requirements: Optional[str] = Field(default=None, description="Updated requirements")
    next_follow_up: Optional[str] = Field(default=None, description="Next follow up timestamp ISO format")

class AddLeadNoteInput(BaseModel):
    lead_id: str = Field(description="Unique ID of the lead")
    content: str = Field(description="Note text content")

# ==============================================================================
# Property Tools Schemas
# ==============================================================================
class SearchPropertiesInput(BaseModel):
    city: Optional[str] = Field(default=None, description="City location")
    property_type: Optional[str] = Field(default=None, description="Villa, Penthouse, etc.")
    max_price: Optional[float] = Field(default=None, description="Maximum price ceiling")
    min_bedrooms: Optional[int] = Field(default=None, description="Minimum bedrooms required")

class GetPropertyInput(BaseModel):
    property_id: str = Field(description="Unique ID of the property")

# ==============================================================================
# Task Tools Schemas
# ==============================================================================
class CreateTaskInput(BaseModel):
    lead_id: Optional[str] = Field(default=None, description="Associated lead ID")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Detailed task description")
    due_date: Optional[str] = Field(default=None, description="Due date ISO format")
    priority: str = Field(default="medium", description="Priority: low, medium, high, urgent")

class ListTasksInput(BaseModel):
    lead_id: Optional[str] = Field(default=None, description="Filter by lead ID")
    status: Optional[str] = Field(default=None, description="Filter by status: pending, completed")

class UpdateTaskStatusInput(BaseModel):
    task_id: str = Field(description="Unique ID of the task")
    status: str = Field(description="New status: pending, completed, cancelled")

# ==============================================================================
# Workflow & Approval Tools Schemas
# ==============================================================================
class RequestApprovalInput(BaseModel):
    workflow_id: str = Field(description="Current workflow execution ID")
    proposed_action: str = Field(description="Action proposed, e.g. create_lead, update_lead")
    target_resource_type: str = Field(description="Target resource type, e.g. lead, contact")
    target_resource_id: Optional[str] = Field(default=None, description="Target resource ID if updating")
    proposed_payload: Dict[str, Any] = Field(description="Exact data payload to execute upon approval")
    risk_category: str = Field(default="medium", description="Risk level: low, medium, high")
    reasoning: Optional[str] = Field(default=None, description="Model explanation for why this action is proposed")

class GetWorkflowStatusInput(BaseModel):
    workflow_id: str = Field(description="Workflow execution ID")

class GetWorkflowHistoryInput(BaseModel):
    workflow_id: str = Field(description="Workflow execution ID")

