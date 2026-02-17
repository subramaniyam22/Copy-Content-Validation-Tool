"""Exclusion repository — DB operations for exclusion profiles and rules."""
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import ExclusionProfile, ExclusionRule
from app.domain.enums import ExclusionRuleType
from typing import Optional


async def create_exclusion_profile(
    db: AsyncSession,
    project_id: int,
    name: str,
    is_default: bool = False,
    rules: list[dict] = None,
) -> ExclusionProfile:
    ep = ExclusionProfile(project_id=project_id, name=name, is_default=is_default)
    db.add(ep)
    await db.flush()

    if rules:
        for r in rules:
            er = ExclusionRule(
                profile_id=ep.id,
                rule_type=r["rule_type"],
                rule_value=r["rule_value"],
            )
            db.add(er)

    await db.commit()
    await db.refresh(ep)
    return ep


async def get_exclusion_profile(db: AsyncSession, profile_id: int) -> Optional[ExclusionProfile]:
    result = await db.execute(
        select(ExclusionProfile)
        .options(selectinload(ExclusionProfile.rules))
        .where(ExclusionProfile.id == profile_id)
    )
    return result.scalar_one_or_none()


async def list_exclusion_profiles(
    db: AsyncSession, project_id: Optional[int] = None
) -> list[ExclusionProfile]:
    query = select(ExclusionProfile).options(selectinload(ExclusionProfile.rules))
    if project_id is not None:
        query = query.where(ExclusionProfile.project_id == project_id)
    query = query.order_by(ExclusionProfile.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_default_profile(db: AsyncSession, project_id: int) -> Optional[ExclusionProfile]:
    result = await db.execute(
        select(ExclusionProfile)
        .options(selectinload(ExclusionProfile.rules))
        .where(
            ExclusionProfile.project_id == project_id,
            ExclusionProfile.is_default == True,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def add_exclusion_rule(
    db: AsyncSession,
    profile_id: int,
    rule_type: ExclusionRuleType,
    rule_value: str,
    reason: Optional[str] = None,
) -> ExclusionRule:
    er = ExclusionRule(
        profile_id=profile_id,
        rule_type=rule_type,
        rule_value=rule_value,
        reason=reason,
    )
    db.add(er)
    await db.commit()
    await db.refresh(er)
    return er


async def delete_exclusion_rule(db: AsyncSession, rule_id: int) -> bool:
    result = await db.execute(
        select(ExclusionRule).where(ExclusionRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return False
    await db.delete(rule)
    await db.commit()
    return True


async def delete_exclusion_profile(db: AsyncSession, profile_id: int) -> bool:
    result = await db.execute(
        select(ExclusionProfile).where(ExclusionProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return False
    await db.delete(profile)
    await db.commit()
    return True
