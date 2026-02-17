"""Scan repository — DB operations for scan jobs, pages, chunks, and issues."""
from datetime import datetime
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import (
    ScanJob, ScanPage, PageContentChunk, Issue, Project,
    GuidelineRule, GuidelineVersion, GuidelineSet,
)
from app.domain.enums import JobStatus, JobStage, ScrapeStatus
from typing import Optional, Any


# ─── Projects ───

async def get_or_create_project(db: AsyncSession, base_url: str) -> Project:
    result = await db.execute(select(Project).where(Project.base_url == base_url))
    project = result.scalar_one_or_none()
    if not project:
        project = Project(base_url=base_url)
        db.add(project)
        await db.commit()
        await db.refresh(project)
    return project


# ─── Scan Jobs ───

async def create_scan_job(
    db: AsyncSession,
    project_id: int,
    guideline_version_id: Optional[int] = None,
    options: Optional[dict] = None,
) -> ScanJob:
    job = ScanJob(
        project_id=project_id,
        guideline_version_id=guideline_version_id,
        status=JobStatus.PENDING,
        options_json=options,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_scan_job(db: AsyncSession, job_id: int) -> Optional[ScanJob]:
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(ScanJob)
        .options(
            selectinload(ScanJob.pages)
            .selectinload(ScanPage.issues)
            .joinedload(Issue.guideline_rule)
            .joinedload(GuidelineRule.guideline_version)
            .joinedload(GuidelineVersion.guideline_set)
        )
        .where(ScanJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: int,
    status: Optional[JobStatus] = None,
    stage: Optional[JobStage] = None,
    progress: Optional[dict] = None,
    error: Optional[Any] = None,
):
    values = {}
    if status is not None:
        values["status"] = status
    if stage is not None:
        values["stage"] = stage
    if progress is not None:
        values["progress_json"] = progress
    if error is not None:
        values["error_json"] = error
    if status == JobStatus.RUNNING and "started_at" not in values:
        values["started_at"] = datetime.utcnow()
    if status in (JobStatus.COMPLETED, JobStatus.FAILED):
        values["finished_at"] = datetime.utcnow()

    if values:
        await db.execute(update(ScanJob).where(ScanJob.id == job_id).values(**values))
        await db.commit()


async def list_scans_by_url(db: AsyncSession, base_url: str) -> list[ScanJob]:
    result = await db.execute(
        select(ScanJob)
        .join(Project)
        .options(selectinload(ScanJob.pages).selectinload(ScanPage.issues))
        .where(Project.base_url == base_url)
        .order_by(ScanJob.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all_scans(db: AsyncSession, limit: int = 50) -> list[ScanJob]:
    result = await db.execute(
        select(ScanJob)
        .join(Project)
        .options(selectinload(ScanJob.pages).selectinload(ScanPage.issues))
        .order_by(ScanJob.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_previous_scan(db: AsyncSession, scan_id: int) -> Optional[ScanJob]:
    """Get the scan that was completed just before this one for the same project."""
    current = await db.execute(select(ScanJob).where(ScanJob.id == scan_id))
    current_job = current.scalar_one_or_none()
    if not current_job:
        return None

    result = await db.execute(
        select(ScanJob)
        .where(
            ScanJob.project_id == current_job.project_id,
            ScanJob.id != scan_id,
            ScanJob.status == JobStatus.COMPLETED,
            ScanJob.finished_at < (current_job.finished_at or current_job.created_at),
        )
        .order_by(ScanJob.finished_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ─── Scan Pages ───

async def create_scan_pages(db: AsyncSession, job_id: int, pages: list[dict]) -> list[ScanPage]:
    page_objs = []
    for p in pages:
        sp = ScanPage(
            scan_job_id=job_id,
            url=p["url"],
            title=p.get("title"),
            selected=p.get("selected", True),
            source=p.get("source"),
            scrape_status=ScrapeStatus.PENDING,
        )
        db.add(sp)
        page_objs.append(sp)
    await db.commit()
    for sp in page_objs:
        await db.refresh(sp)
    return page_objs


async def update_page_scrape_status(db: AsyncSession, page_id: int, status: ScrapeStatus, title: Optional[str] = None):
    values = {"scrape_status": status}
    if title:
        values["title"] = title
    await db.execute(update(ScanPage).where(ScanPage.id == page_id).values(**values))
    await db.commit()


# ─── Content Chunks ───

async def create_content_chunks(db: AsyncSession, page_id: int, chunks: list[dict]) -> list[PageContentChunk]:
    chunk_objs = []
    for c in chunks:
        pcc = PageContentChunk(
            scan_page_id=page_id,
            heading_path=c.get("heading_path", ""),
            content_text=c["content_text"],
            content_hash=c["content_hash"],
            token_estimate=c.get("token_estimate"),
        )
        db.add(pcc)
        chunk_objs.append(pcc)
    await db.commit()
    return chunk_objs


# ─── Issues ───

async def create_issues(db: AsyncSession, page_id: int, issues: list[dict]) -> list[Issue]:
    issue_objs = []
    for i in issues:
        issue = Issue(
            scan_page_id=page_id,
            category=i["category"],
            type=i["type"],
            severity=i["severity"],
            evidence=i.get("evidence"),
            explanation=i.get("explanation"),
            proposed_fix=i.get("proposed_fix"),
            guideline_rule_id=i.get("guideline_rule_id"),
            source=i["source"],
            confidence=i.get("confidence", 0.0),
            fingerprint=i["fingerprint"],
        )
        db.add(issue)
        issue_objs.append(issue)
    await db.commit()
    return issue_objs


async def get_issues_for_job(db: AsyncSession, job_id: int) -> list[Issue]:
    result = await db.execute(
        select(Issue)
        .join(ScanPage)
        .where(ScanPage.scan_job_id == job_id)
        .order_by(Issue.id)
    )
    return list(result.scalars().all())


async def get_issue_fingerprints_for_job(db: AsyncSession, job_id: int) -> dict[str, Issue]:
    issues = await get_issues_for_job(db, job_id)
    return {i.fingerprint: i for i in issues}
