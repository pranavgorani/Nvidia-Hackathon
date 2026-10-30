import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import engine, Base
from app.core.security import get_password_hash
from app.db.models import User, Organization, OrganizationMember, Skill, Property

INITIAL_SKILLS = [
    {
        "skill_id": "property_intake_agent",
        "name": "Property Intake Agent",
        "description": "Processes property inquiry documents (PDF/images), extracts lead requirements, matches existing CRM records, prepares validated CRM updates, requests human approval, and executes actions.",
        "version": "1.0.0",
        "allowed_tools": [
            "get_document_metadata", "get_extraction", "search_contacts", "search_leads",
            "create_lead", "update_lead", "create_task", "add_lead_note", "request_approval"
        ],
        "approval_policy": {
            "require_approval_for_create": True,
            "require_approval_for_update": True,
            "auto_approve_reads": True
        }
    },
    {
        "skill_id": "lead_qualification",
        "name": "Lead Qualification",
        "description": "Evaluates lead intent, budget feasibility, urgency, and assigns priority scoring.",
        "version": "1.0.0",
        "allowed_tools": ["get_lead", "update_lead", "search_properties", "create_task"],
        "approval_policy": {"require_approval": False}
    },
    {
        "skill_id": "document_analyst",
        "name": "Document Analyst",
        "description": "Extracts detailed terms, clauses, and key data points from real estate contracts and lease agreements.",
        "version": "1.0.0",
        "allowed_tools": ["get_document_metadata", "get_extraction", "update_reviewed_extraction"],
        "approval_policy": {"require_approval": False}
    },
    {
        "skill_id": "follow_up_preparation",
        "name": "Follow-up Preparation",
        "description": "Identifies leads needing follow-up, summarizes past interactions, drafts tailored follow-up messages and reminder tasks.",
        "version": "1.0.0",
        "allowed_tools": ["search_leads", "get_lead", "create_task", "add_lead_note"],
        "approval_policy": {"require_approval": True}
    },
    {
        "skill_id": "crm_record_matching",
        "name": "CRM Record Matching",
        "description": "Performs multi-criteria deduplication and entity resolution across contacts and leads.",
        "version": "1.0.0",
        "allowed_tools": ["search_contacts", "search_leads"],
        "approval_policy": {"require_approval": False}
    },
    {
        "skill_id": "task_planner",
        "name": "Task Planner",
        "description": "Generates milestone plans and scheduled actions for property showings, client negotiations, and transaction closing.",
        "version": "1.0.0",
        "allowed_tools": ["list_tasks", "create_task", "update_task_status"],
        "approval_policy": {"require_approval": False}
    }
]

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def seed_data(session: AsyncSession):
    # Check if admin user exists
    user_stmt = select(User).where(User.email == "admin@docuflow.ai")
    res = await session.execute(user_stmt)
    existing_user = res.scalar_one_or_none()

    if not existing_user:
        admin_user = User(
            email="admin@docuflow.ai",
            full_name="DocuFlow Admin",
            hashed_password=get_password_hash("DocuFlow2026!"),
            is_active=True
        )
        session.add(admin_user)
        await session.flush()

        org = Organization(
            name="Acme Real Estate Holdings",
            slug="acme-holdings"
        )
        session.add(org)
        await session.flush()

        member = OrganizationMember(
            user_id=admin_user.id,
            organization_id=org.id,
            role="owner"
        )
        session.add(member)

        # Seed sample properties
        properties = [
            Property(
                organization_id=org.id,
                title="The Grand Penthouse at Downtown Marina",
                address="100 Marina Boulevard, Suite 45",
                city="San Francisco",
                state="CA",
                price=2450000.0,
                bedrooms=3,
                bathrooms=3.5,
                square_feet=3200,
                property_type="Penthouse",
                status="active",
                description="Ultra-luxury skyline penthouse with floor-to-ceiling panoramic bay views."
            ),
            Property(
                organization_id=org.id,
                title="Modern Hillside Villa",
                address="742 Evergreen Terrace",
                city="Palo Alto",
                state="CA",
                price=3850000.0,
                bedrooms=4,
                bathrooms=4.0,
                square_feet=4500,
                property_type="Villa",
                status="active",
                description="Contemporary architectural masterpiece with smart home tech and landscaped pool."
            ),
            Property(
                organization_id=org.id,
                title="Sunnyvale Garden Townhome",
                address="512 West Olive Avenue",
                city="Sunnyvale",
                state="CA",
                price=1350000.0,
                bedrooms=2,
                bathrooms=2.5,
                square_feet=1650,
                property_type="Townhome",
                status="active",
                description="Peaceful residential community near tech hubs with private patio."
            )
        ]
        session.add_all(properties)

    # Seed skills
    for s in INITIAL_SKILLS:
        skill_stmt = select(Skill).where(Skill.skill_id == s["skill_id"])
        s_res = await session.execute(skill_stmt)
        if not s_res.scalar_one_or_none():
            skill_obj = Skill(
                skill_id=s["skill_id"],
                name=s["name"],
                description=s["description"],
                version=s["version"],
                allowed_tools_json=s["allowed_tools"],
                approval_policy_json=s["approval_policy"],
                is_enabled=True
            )
            session.add(skill_obj)

    await session.commit()

