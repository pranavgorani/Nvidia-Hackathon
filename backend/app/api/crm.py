from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import Lead, Contact, Property, Task, Note, Activity
from app.services.crm import crm_service

router = APIRouter(prefix="/api/crm", tags=["CRM"])

class LeadCreateSchema(BaseModel):
    contact_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: str = "Direct Inquiry"
    preferred_location: Optional[str] = None
    budget_range: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None
    property_requirements: Optional[str] = None
    priority: str = "medium"
    status: str = "new"

class LeadUpdateSchema(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    preferred_location: Optional[str] = None
    budget_range: Optional[str] = None
    property_requirements: Optional[str] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None

class NoteCreateSchema(BaseModel):
    content: str

class TaskCreateSchema(BaseModel):
    lead_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"

@router.get("/leads")
async def list_leads(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Lead).where(Lead.organization_id == member.organization_id)
    if status:
        stmt = stmt.where(Lead.status == status)
    if search:
        search_filter = or_(
            Lead.contact_name.ilike(f"%{search}%"),
            Lead.email.ilike(f"%{search}%"),
            Lead.preferred_location.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    stmt = stmt.order_by(Lead.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    leads = res.scalars().all()
    return leads

@router.post("/leads")
async def create_lead(
    req: LeadCreateSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    lead = await crm_service.create_lead(
        organization_id=member.organization_id,
        data=req.model_dump(),
        actor_id=member.user_id,
        session=db
    )
    return lead

@router.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Lead).where(and_(Lead.id == lead_id, Lead.organization_id == member.organization_id))
    res = await db.execute(stmt)
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    # Fetch tasks, notes, activities
    t_stmt = select(Task).where(Task.lead_id == lead_id).order_by(Task.created_at.desc())
    tasks = (await db.execute(t_stmt)).scalars().all()

    n_stmt = select(Note).where(Note.lead_id == lead_id).order_by(Note.created_at.desc())
    notes = (await db.execute(n_stmt)).scalars().all()

    a_stmt = select(Activity).where(Activity.lead_id == lead_id).order_by(Activity.created_at.desc())
    activities = (await db.execute(a_stmt)).scalars().all()

    return {
        "lead": lead,
        "tasks": tasks,
        "notes": notes,
        "activities": activities
    }

@router.put("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    req: LeadUpdateSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    lead = await crm_service.update_lead(
        organization_id=member.organization_id,
        lead_id=lead_id,
        data=req.model_dump(exclude_unset=True),
        actor_id=member.user_id,
        session=db
    )
    return lead

@router.post("/leads/{lead_id}/notes")
async def add_lead_note(
    lead_id: str,
    req: NoteCreateSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    note = Note(
        organization_id=member.organization_id,
        lead_id=lead_id,
        content=req.content,
        created_by_id=member.user_id
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

@router.get("/contacts")
async def list_contacts(
    search: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Contact).where(Contact.organization_id == member.organization_id)
    if search:
        stmt = stmt.where(or_(Contact.first_name.ilike(f"%{search}%"), Contact.last_name.ilike(f"%{search}%"), Contact.email.ilike(f"%{search}%")))
    res = await db.execute(stmt.order_by(Contact.created_at.desc()).limit(50))
    return res.scalars().all()

@router.get("/properties")
async def list_properties(
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Property).where(Property.organization_id == member.organization_id)
    if city:
        stmt = stmt.where(Property.city.ilike(f"%{city}%"))
    if property_type:
        stmt = stmt.where(Property.property_type.ilike(f"%{property_type}%"))
    res = await db.execute(stmt.limit(50))
    return res.scalars().all()

@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Task).where(Task.organization_id == member.organization_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if lead_id:
        stmt = stmt.where(Task.lead_id == lead_id)
    res = await db.execute(stmt.order_by(Task.created_at.desc()).limit(50))
    return res.scalars().all()

@router.post("/tasks")
async def create_task(
    req: TaskCreateSchema,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    task = await crm_service.create_task(
        organization_id=member.organization_id,
        data=req.model_dump(),
        session=db
    )
    return task

@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str = Query(..., pattern="^(pending|completed|cancelled)$"),
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Task).where(and_(Task.id == task_id, Task.organization_id == member.organization_id))
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    task.status = status
    await db.commit()
    await db.refresh(task)
    return task

