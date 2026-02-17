"""Guideline repository — DB operations for guideline sets, versions, and rules."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import GuidelineSet, GuidelineVersion, GuidelineRule, GuidelineRuleEmbedding
from typing import Optional


async def create_guideline_set(db: AsyncSession, name: str) -> GuidelineSet:
    gs = GuidelineSet(name=name)
    db.add(gs)
    await db.commit()
    await db.refresh(gs)
    return gs


async def get_guideline_set(db: AsyncSession, set_id: int) -> Optional[GuidelineSet]:
    result = await db.execute(
        select(GuidelineSet)
        .options(selectinload(GuidelineSet.versions).selectinload(GuidelineVersion.rules))
        .where(GuidelineSet.id == set_id)
    )
    return result.scalar_one_or_none()


async def list_guideline_sets(db: AsyncSession) -> list[GuidelineSet]:
    result = await db.execute(
        select(GuidelineSet)
        .options(selectinload(GuidelineSet.versions).selectinload(GuidelineVersion.rules))
        .order_by(GuidelineSet.created_at.desc())
    )
    return list(result.scalars().all())


async def create_guideline_version(
    db: AsyncSession,
    set_id: int,
    file_manifest: dict,
    text_hash: str,
    prompt_version: Optional[str] = None,
    model_used: Optional[str] = None,
) -> GuidelineVersion:
    # Get next version number
    result = await db.execute(
        select(func.coalesce(func.max(GuidelineVersion.version_number), 0))
        .where(GuidelineVersion.guideline_set_id == set_id)
    )
    next_version = result.scalar() + 1

    gv = GuidelineVersion(
        guideline_set_id=set_id,
        version_number=next_version,
        file_manifest_json=file_manifest,
        extracted_text_hash=text_hash,
        prompt_version=prompt_version,
        model_used=model_used,
    )
    db.add(gv)
    await db.commit()
    await db.refresh(gv)
    return gv


async def create_guideline_rules(
    db: AsyncSession, version_id: int, rules: list[dict]
) -> list[GuidelineRule]:
    rule_objs = []
    for r in rules:
        gr = GuidelineRule(
            guideline_version_id=version_id,
            rule_id=r.get("rule_id", ""),
            category=r.get("category", "general"),
            type=r.get("type", "guideline"),
            severity_default=r.get("severity_default", "medium"),
            rule_text=r.get("rule_text", ""),
            fix_template=r.get("fix_template"),
            examples_good=r.get("examples_good"),
            examples_bad=r.get("examples_bad"),
            source_file=r.get("source_file"),
            section_ref=r.get("section_ref"),
        )
        db.add(gr)
        rule_objs.append(gr)
    await db.commit()
    for r in rule_objs:
        await db.refresh(r)
    return rule_objs


async def get_rules_for_version(db: AsyncSession, version_id: int) -> list[GuidelineRule]:
    result = await db.execute(
        select(GuidelineRule)
        .where(GuidelineRule.guideline_version_id == version_id)
        .order_by(GuidelineRule.id)
    )
    return list(result.scalars().all())


async def store_rule_embedding(db: AsyncSession, rule_id: int, embedding: list[float]):
    emb = GuidelineRuleEmbedding(guideline_rule_id=rule_id, embedding=embedding)
    db.add(emb)
    await db.commit()
