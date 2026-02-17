"""Exclusion profile API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.db import get_db
from app.repositories import exclusion_repo
from app.domain.schemas import (
    ExclusionProfileCreate, ExclusionProfileOut,
    ExclusionRuleCreate, ExclusionRuleOut,
)

router = APIRouter(prefix="/api/exclusions", tags=["exclusions"])


@router.post("", response_model=ExclusionProfileOut)
async def create_exclusion_profile(
    req: ExclusionProfileCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new exclusion profile."""
    profile = await exclusion_repo.create_exclusion_profile(
        db, req.project_id, req.name, req.is_default,
    )
    return ExclusionProfileOut.model_validate(profile)


@router.get("", response_model=list[ExclusionProfileOut])
async def list_exclusion_profiles(
    project_id: int = None, db: AsyncSession = Depends(get_db)
):
    """List exclusion profiles, optionally filtered by project."""
    profiles = await exclusion_repo.list_exclusion_profiles(db, project_id)
    return [ExclusionProfileOut.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=ExclusionProfileOut)
async def get_exclusion_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific exclusion profile."""
    profile = await exclusion_repo.get_exclusion_profile(db, profile_id)
    if not profile:
        raise HTTPException(404, "Exclusion profile not found")
    return ExclusionProfileOut.model_validate(profile)


@router.post("/{profile_id}/rules", response_model=ExclusionRuleOut)
async def add_exclusion_rule(
    profile_id: int,
    req: ExclusionRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a rule to an exclusion profile."""
    rule = await exclusion_repo.add_exclusion_rule(
        db, profile_id, req.rule_type, req.rule_value, req.reason,
    )
    return ExclusionRuleOut.model_validate(rule)


@router.delete("/{profile_id}/rules/{rule_id}")
async def remove_exclusion_rule(
    profile_id: int, rule_id: int, db: AsyncSession = Depends(get_db),
):
    """Remove a rule from an exclusion profile."""
    success = await exclusion_repo.delete_exclusion_rule(db, rule_id)
    if not success:
        raise HTTPException(404, "Rule not found")
    return {"status": "deleted"}


@router.delete("/{profile_id}")
async def delete_exclusion_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an exclusion profile."""
    success = await exclusion_repo.delete_exclusion_profile(db, profile_id)
    if not success:
        raise HTTPException(404, "Profile not found")
    return {"status": "deleted"}
