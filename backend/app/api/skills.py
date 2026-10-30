from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_member, CurrentMemberContext
from app.db.models import Skill

router = APIRouter(prefix="/api/skills", tags=["Skills"])

@router.get("")
async def list_skills(
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Skill).order_by(Skill.name.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    member: CurrentMemberContext = Depends(get_current_member),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Skill).where(Skill.skill_id == skill_id)
    res = await db.execute(stmt)
    skill = res.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")
    return skill

