import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user, get_current_member, CurrentMemberContext
from app.db.models import User, Organization, OrganizationMember

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organization_name: Optional[str] = "My Real Estate Team"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    organizations: List[Dict[str, Any]]
    active_organization_id: str

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing user
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user = User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        is_active=True
    )
    db.add(user)
    await db.flush()

    # Create default organization
    slug = re.sub(r"[^a-z0-9]+", "-", req.organization_name.lower()).strip("-") or "org"
    slug = f"{slug}-{user.id[:6]}"
    org = Organization(name=req.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    # Make user owner
    member = OrganizationMember(user_id=user.id, organization_id=org.id, role="owner")
    db.add(member)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "organizations": [{"id": org.id, "name": org.name, "role": "owner"}],
        "active_organization_id": org.id
    }

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Fetch organizations
    m_stmt = select(OrganizationMember, Organization).join(
        Organization, OrganizationMember.organization_id == Organization.id
    ).where(OrganizationMember.user_id == user.id)
    m_res = await db.execute(m_stmt)
    org_list = []
    active_org_id = ""
    for member, org in m_res.all():
        org_list.append({"id": org.id, "name": org.name, "role": member.role})
        if not active_org_id:
            active_org_id = org.id

    token = create_access_token({"sub": user.id, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "organizations": org_list,
        "active_organization_id": active_org_id
    }

@router.get("/me")
async def get_me(
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    m_stmt = select(OrganizationMember, Organization).join(
        Organization, OrganizationMember.organization_id == Organization.id
    ).where(OrganizationMember.user_id == member.user.id)
    m_res = await db.execute(m_stmt)
    orgs = [{"id": o.id, "name": o.name, "role": m.role} for m, o in m_res.all()]

    return {
        "user": {
            "id": member.user.id,
            "email": member.user.email,
            "full_name": member.user.full_name
        },
        "current_organization": {
            "id": member.organization.id,
            "name": member.organization.name,
            "role": member.role
        },
        "organizations": orgs
    }

