import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db.models import Contact, Lead, Property, Task, Note, Activity

def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    return re.sub(r"\D", "", phone)

def parse_budget_number(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().upper().replace("$", "").replace(",", "")
        try:
            if v.endswith("M"):
                return float(v[:-1].strip()) * 1_000_000.0
            elif v.endswith("K"):
                return float(v[:-1].strip()) * 1_000.0
            return float(v)
        except (ValueError, TypeError):
            return None
    return None

def parse_int_number(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None

class CRMService:
    async def match_existing_records(
        self,
        organization_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Multi-criteria contact and lead matching with duplicate detection.
        Supports exact email match, normalized phone match, and candidate name matches.
        """
        matched_contacts = []
        matched_leads = []
        clean_phone = normalize_phone(phone)

        # 1. Contact search
        filters = []
        if email:
            filters.append(Contact.email.ilike(email.strip()))
        if clean_phone:
            filters.append(Contact.phone.contains(clean_phone[-10:]))
        if name:
            parts = name.strip().split()
            if len(parts) >= 2:
                filters.append(and_(Contact.first_name.ilike(f"%{parts[0]}%"), Contact.last_name.ilike(f"%{parts[-1]}%")))
            else:
                filters.append(or_(Contact.first_name.ilike(f"%{name}%"), Contact.last_name.ilike(f"%{name}%")))

        if filters:
            stmt = select(Contact).where(
                and_(Contact.organization_id == organization_id, or_(*filters))
            ).limit(10)
            res = await session.execute(stmt)
            for c in res.scalars():
                match_reasons = []
                if email and c.email and email.strip().lower() == c.email.strip().lower():
                    match_reasons.append("Exact Email Match")
                if clean_phone and c.phone and normalize_phone(c.phone) == clean_phone:
                    match_reasons.append("Normalized Phone Match")
                if name and f"{c.first_name} {c.last_name}".lower() == name.lower():
                    match_reasons.append("Full Name Match")

                matched_contacts.append({
                    "id": c.id,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "phone": c.phone,
                    "reasons": match_reasons or ["Fuzzy Match"]
                })

        # 2. Lead search
        lead_filters = []
        if email:
            lead_filters.append(Lead.email.ilike(email.strip()))
        if clean_phone:
            lead_filters.append(Lead.phone.contains(clean_phone[-10:]))
        if name:
            lead_filters.append(Lead.contact_name.ilike(f"%{name}%"))

        if lead_filters:
            l_stmt = select(Lead).where(
                and_(Lead.organization_id == organization_id, or_(*lead_filters))
            ).limit(10)
            l_res = await session.execute(l_stmt)
            for l in l_res.scalars():
                lead_reasons = []
                if email and l.email and email.strip().lower() == l.email.strip().lower():
                    lead_reasons.append("Exact Email Match")
                if clean_phone and l.phone and normalize_phone(l.phone) == clean_phone:
                    lead_reasons.append("Normalized Phone Match")
                if name and l.contact_name.lower() == name.lower():
                    lead_reasons.append("Contact Name Match")

                matched_leads.append({
                    "id": l.id,
                    "contact_name": l.contact_name,
                    "email": l.email,
                    "phone": l.phone,
                    "status": l.status,
                    "preferred_location": l.preferred_location,
                    "budget_range": l.budget_range,
                    "reasons": lead_reasons or ["Fuzzy Match"]
                })

        return {
            "contacts": matched_contacts,
            "leads": matched_leads,
            "has_match": bool(matched_contacts or matched_leads)
        }

    async def create_lead(
        self,
        organization_id: str,
        data: Dict[str, Any],
        actor_id: Optional[str],
        session: AsyncSession
    ) -> Lead:
        min_b = parse_budget_number(data.get("min_budget"))
        max_b = parse_budget_number(data.get("max_budget"))
        budget_range_val = data.get("budget_range")
        if not budget_range_val and (min_b or max_b):
            budget_range_val = f"${min_b:,.0f} - ${max_b:,.0f}" if (min_b and max_b) else f"${max_b or min_b:,.0f}"

        lead = Lead(
            organization_id=organization_id,
            contact_id=data.get("contact_id"),
            contact_name=str(data["contact_name"]),
            email=str(data["email"]) if data.get("email") else None,
            phone=str(data["phone"]) if data.get("phone") else None,
            source=data.get("source", "Document Intake"),
            preferred_location=data.get("preferred_location"),
            budget_range=str(budget_range_val) if budget_range_val else None,
            min_budget=min_b,
            max_budget=max_b,
            bedrooms=parse_int_number(data.get("bedrooms")),
            property_type=data.get("property_type"),
            property_requirements=data.get("property_requirements"),
            status=data.get("status", "new"),
            priority=data.get("priority", "medium")
        )
        session.add(lead)
        await session.flush()

        # Log Activity
        activity = Activity(
            organization_id=organization_id,
            lead_id=lead.id,
            contact_id=lead.contact_id,
            activity_type="document_intake",
            summary=f"Lead created via DocuFlow AI: {lead.contact_name}",
            details=f"Location: {lead.preferred_location or 'N/A'}, Budget: {lead.budget_range or 'N/A'}",
            created_by_id=actor_id
        )
        session.add(activity)
        await session.commit()
        await session.refresh(lead)
        return lead

    async def update_lead(
        self,
        organization_id: str,
        lead_id: str,
        data: Dict[str, Any],
        actor_id: Optional[str],
        session: AsyncSession
    ) -> Lead:
        stmt = select(Lead).where(and_(Lead.id == lead_id, Lead.organization_id == organization_id))
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            raise ValueError(f"Lead with ID {lead_id} not found in organization.")

        changes = []
        for key, value in data.items():
            if hasattr(lead, key) and value is not None:
                old_val = getattr(lead, key)
                if old_val != value:
                    setattr(lead, key, value)
                    changes.append(f"{key}: '{old_val}' -> '{value}'")

        if changes:
            activity = Activity(
                organization_id=organization_id,
                lead_id=lead.id,
                activity_type="status_change" if "status" in data else "note",
                summary="Lead updated by DocuFlow Agent",
                details="; ".join(changes),
                created_by_id=actor_id
            )
            session.add(activity)

        await session.commit()
        await session.refresh(lead)
        return lead

    async def create_task(
        self,
        organization_id: str,
        data: Dict[str, Any],
        session: AsyncSession
    ) -> Task:
        due_dt = None
        if data.get("due_date"):
            try:
                due_dt = datetime.fromisoformat(data["due_date"].replace("Z", "+00:00"))
            except Exception:
                due_dt = None

        task = Task(
            organization_id=organization_id,
            lead_id=data.get("lead_id"),
            title=data["title"],
            description=data.get("description"),
            due_date=due_dt,
            priority=data.get("priority", "medium"),
            status="pending"
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task

crm_service = CRMService()

