from typing import Optional, List
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import decode_access_token
from app.db.models import User, Organization, OrganizationMember

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

class CurrentMemberContext:
    def __init__(self, user: User, organization: Organization, role: str):
        self.user = user
        self.organization = organization
        self.role = role

    @property
    def user_id(self) -> str:
        return self.user.id

    @property
    def organization_id(self) -> str:
        return self.organization.id

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload["sub"]
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive."
        )
    return user

async def get_current_member(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CurrentMemberContext:
    """
    Resolves organization membership and role for the authenticated user.
    Guarantees strict tenant isolation.
    """
    stmt = select(OrganizationMember, Organization).join(
        Organization, OrganizationMember.organization_id == Organization.id
    ).where(OrganizationMember.user_id == user.id)

    if x_organization_id:
        stmt = stmt.where(OrganizationMember.organization_id == x_organization_id)

    res = await db.execute(stmt)
    first_row = res.first()

    if not first_row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to the specified organization."
        )

    member, org = first_row
    return CurrentMemberContext(user=user, organization=org, role=member.role)

def require_role(allowed_roles: List[str]):
    def role_checker(member: CurrentMemberContext = Depends(get_current_member)):
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following roles: {allowed_roles}. Current role: {member.role}."
            )
        return member
    return role_checker

