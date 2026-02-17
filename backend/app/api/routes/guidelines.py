"""Guidelines API routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.repositories.db import get_db
from app.repositories import guideline_repo
from app.domain.schemas import GuidelineSetOut, GuidelineSetListOut, GuidelineVersionOut, GuidelineRuleOut
from app.services.guideline_service import GuidelineService
from app.services.rule_extraction_service import RuleExtractionService
from app.config import settings

router = APIRouter(prefix="/api/guidelines", tags=["guidelines"])


@router.post("", response_model=GuidelineSetOut)
async def create_guideline_set(
    name: str = Form(...),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new guideline set with files."""
    # Validate files
    file_dicts = []
    for f in files:
        ext = GuidelineService()._get_extension(f.filename)
        if ext not in GuidelineService.EXTRACTORS:
            raise HTTPException(400, f"Unsupported file type: {f.filename}")

        content = await f.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(400, f"File too large: {f.filename}")

        file_dicts.append({"filename": f.filename, "content_bytes": content})

    # Create set
    gs = await guideline_repo.create_guideline_set(db, name)

    # Extract text
    svc = GuidelineService()
    combined_text, text_hash, manifest = svc.extract_text_from_files(file_dicts)

    # Create version
    gv = await guideline_repo.create_guideline_version(
        db, gs.id, manifest, text_hash,
    )

    # Extract rules via LLM (if text available)
    if combined_text.strip():
        try:
            extractor = RuleExtractionService()
            rules, prompt_ver, model = extractor.extract_rules(combined_text)
            if rules:
                await guideline_repo.create_guideline_rules(db, gv.id, rules)
                # Update version with prompt/model info
                gv.prompt_version = prompt_ver
                gv.model_used = model
                await db.commit()
        except Exception as e:
            # Rule extraction is best-effort; don't fail the upload
            pass

    # Refresh and return
    gs = await guideline_repo.get_guideline_set(db, gs.id)
    return _format_set(gs)


@router.post("/{set_id}/versions", response_model=GuidelineVersionOut)
async def add_version(
    set_id: int,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload new files to create a new version of an existing guideline set."""
    gs = await guideline_repo.get_guideline_set(db, set_id)
    if not gs:
        raise HTTPException(404, "Guideline set not found")

    file_dicts = []
    for f in files:
        content = await f.read()
        file_dicts.append({"filename": f.filename, "content_bytes": content})

    svc = GuidelineService()
    combined_text, text_hash, manifest = svc.extract_text_from_files(file_dicts)

    gv = await guideline_repo.create_guideline_version(
        db, set_id, manifest, text_hash,
    )

    if combined_text.strip():
        try:
            extractor = RuleExtractionService()
            rules, prompt_ver, model = extractor.extract_rules(combined_text)
            if rules:
                await guideline_repo.create_guideline_rules(db, gv.id, rules)
                gv.prompt_version = prompt_ver
                gv.model_used = model
                await db.commit()
        except Exception:
            pass

    await db.refresh(gv)
    rules = await guideline_repo.get_rules_for_version(db, gv.id)
    return GuidelineVersionOut(
        id=gv.id,
        version_number=gv.version_number,
        created_at=gv.created_at,
        file_manifest=gv.file_manifest_json,
        rules_count=len(rules),
        prompt_version=gv.prompt_version,
        model_used=gv.model_used,
    )


@router.get("", response_model=GuidelineSetListOut)
async def list_guideline_sets(db: AsyncSession = Depends(get_db)):
    """List all guideline sets."""
    sets = await guideline_repo.list_guideline_sets(db)
    return GuidelineSetListOut(sets=[_format_set(gs) for gs in sets])


@router.get("/{set_id}", response_model=GuidelineSetOut)
async def get_guideline_set(set_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific guideline set with all versions."""
    gs = await guideline_repo.get_guideline_set(db, set_id)
    if not gs:
        raise HTTPException(404, "Guideline set not found")
    return _format_set(gs)


@router.get("/{set_id}/versions/{version_id}/rules", response_model=list[GuidelineRuleOut])
async def get_version_rules(
    set_id: int, version_id: int, db: AsyncSession = Depends(get_db)
):
    """Get all rules for a specific guideline version."""
    rules = await guideline_repo.get_rules_for_version(db, version_id)
    return [GuidelineRuleOut.model_validate(r) for r in rules]


def _format_set(gs) -> GuidelineSetOut:
    versions = []
    for v in gs.versions:
        versions.append(GuidelineVersionOut(
            id=v.id,
            version_number=v.version_number,
            created_at=v.created_at,
            file_manifest=v.file_manifest_json,
            rules_count=len(v.rules) if v.rules else 0,
            prompt_version=v.prompt_version,
            model_used=v.model_used,
        ))
    return GuidelineSetOut(
        id=gs.id,
        name=gs.name,
        created_at=gs.created_at,
        versions=versions,
    )
