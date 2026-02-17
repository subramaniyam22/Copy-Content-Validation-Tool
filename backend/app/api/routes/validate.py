"""Validation and Jobs API routes."""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
from app.utils.logging import logger

from app.repositories.db import get_db
from app.repositories import scan_repo
from app.domain.schemas import (
    ValidateRequest, JobOut, JobProgressOut, JobResultsOut,
    IssueOut, IssueSummary, PageResultOut,
)
from app.domain.enums import JobStatus, JobStage, IssueSeverity, IssueSource
from app.models.models import ScanJob, ScanPage, Issue
from app.workers.queue import job_queue, get_redis
from app.workers.tasks import run_validation_job

router = APIRouter(prefix="/api", tags=["validation"])


@router.post("/validate", response_model=JobOut)
async def start_validation(req: ValidateRequest, db: AsyncSession = Depends(get_db)):
    """Create and enqueue a validation job."""
    # Get or create project
    project = await scan_repo.get_or_create_project(db, req.base_url)

    # Resolve guideline version
    gv_id = None
    if req.guideline_set_id:
        from app.models.models import GuidelineVersion
        if req.guideline_version:
            result = await db.execute(
                select(GuidelineVersion).where(
                    GuidelineVersion.guideline_set_id == req.guideline_set_id,
                    GuidelineVersion.version_number == req.guideline_version,
                )
            )
            gv = result.scalar_one_or_none()
            if gv:
                gv_id = gv.id
        else:
            # Pick latest version
            result = await db.execute(
                select(GuidelineVersion)
                .where(GuidelineVersion.guideline_set_id == req.guideline_set_id)
                .order_by(GuidelineVersion.version_number.desc())
                .limit(1)
            )
            gv = result.scalar_one_or_none()
            if gv:
                gv_id = gv.id

    # Create scan job
    options = {
        "run_axe": req.run_axe,
        "run_lighthouse": req.run_lighthouse,
        "run_deterministic": req.run_deterministic,
        "run_llm": req.run_llm,
    }
    job = await scan_repo.create_scan_job(
        db, project.id, guideline_version_id=gv_id, options=options,
    )

    # Create scan pages
    pages_data = [{"url": url, "selected": True} for url in req.page_urls]
    await scan_repo.create_scan_pages(db, job.id, pages_data)

    # Run job: use threading on Windows (RQ workers require os.fork which is Linux-only)
    import os
    import threading
    if os.name == 'nt':
        # Windows: run directly in background thread
        logger.info(f"Starting job {job.id} in background thread (Windows mode)")
        t = threading.Thread(
            target=run_validation_job,
            args=(job.id, req.page_urls, options),
            daemon=True,
        )
        t.start()
    else:
        # Linux/Docker: use RQ worker queue
        try:
            job_queue.enqueue(
                run_validation_job,
                job.id,
                req.page_urls,
                options,
                job_timeout=1800,
            )
        except Exception as e:
            logger.error(f"Failed to enqueue job {job.id}: {e}")
            await scan_repo.update_job_status(
                db, job.id,
                status=JobStatus.FAILED,
                error={"error": f"Failed to enqueue: {str(e)}"},
            )

    return JobOut(
        id=job.id,
        status=job.status,
        stage=job.stage,
        progress=None,
        error=None,
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get current job status and progress."""
    job = await scan_repo.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Get live progress from Redis
    progress = None
    try:
        r = get_redis()
        progress_raw = r.get(f"job:{job_id}:progress")
        if progress_raw:
            progress_data = json.loads(progress_raw)
            progress = JobProgressOut(
                stage=progress_data.get("stage", job.stage or "discovering"),
                total_pages=progress_data.get("total_pages", 0),
                scraped=progress_data.get("scraped", 0),
                validated=progress_data.get("validated", 0),
                current_page=progress_data.get("current_page"),
                message=progress_data.get("message"),
            )
    except Exception:
        pass

    if not progress and job.progress_json:
        progress = JobProgressOut(**job.progress_json)

    return JobOut(
        id=job.id,
        status=job.status,
        stage=job.stage,
        progress=progress,
        error=job.error_json,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/jobs/{job_id}/events")
async def job_events_sse(job_id: int, db: AsyncSession = Depends(get_db)):
    """SSE endpoint for live job progress updates."""
    job = await scan_repo.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        r = get_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(f"job:{job_id}:events")

        try:
            # Send current state first
            current = r.get(f"job:{job_id}:progress")
            if current:
                yield {"event": "progress", "data": current.decode()}

            # Then stream updates
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield {"event": "progress", "data": data}

                    # Check if job is done
                    parsed = json.loads(data)
                    if parsed.get("stage") in ("finalizing", "failed"):
                        yield {"event": "done", "data": data}
                        break

                await asyncio.sleep(0.5)
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return EventSourceResponse(event_generator())


@router.get("/jobs/{job_id}/results", response_model=JobResultsOut)
async def get_job_results(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get complete job results with issues organized by page."""
    job = await scan_repo.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Build page results
    page_results = []
    all_issues = []

    for sp in (job.pages or []):
        page_issues = []
        for issue in (sp.issues or []):
            issue_out = IssueOut(
                id=issue.id,
                page_url=sp.url,
                page_title=sp.title,
                category=issue.category,
                type=issue.type,
                severity=issue.severity,
                evidence=issue.evidence,
                explanation=issue.explanation,
                proposed_fix=issue.proposed_fix,
                guideline_rule_id=issue.guideline_rule_id,
                guideline_set_name=issue.guideline_rule.guideline_version.guideline_set.name if issue.guideline_rule else None,
                guideline_section=issue.guideline_rule.section_ref if issue.guideline_rule else None,
                guideline_source_file=issue.guideline_rule.source_file if issue.guideline_rule else None,
                source=issue.source,
                confidence=issue.confidence,
                fingerprint=issue.fingerprint,
                created_at=issue.created_at,
            )
            page_issues.append(issue_out)
            all_issues.append(issue_out)

        page_results.append(PageResultOut(
            url=sp.url,
            title=sp.title,
            issue_count=len(page_issues),
            issues=page_issues,
        ))

    # Build summary
    summary = IssueSummary(
        total=len(all_issues),
        high=sum(1 for i in all_issues if i.severity == IssueSeverity.HIGH),
        medium=sum(1 for i in all_issues if i.severity == IssueSeverity.MEDIUM),
        low=sum(1 for i in all_issues if i.severity == IssueSeverity.LOW),
        by_category={},
        by_source={},
    )
    for i in all_issues:
        summary.by_category[i.category] = summary.by_category.get(i.category, 0) + 1
        summary.by_source[str(i.source)] = summary.by_source.get(str(i.source), 0) + 1

    # Build fix packs
    fix_packs = {
        "quick_wins": [i for i in all_issues if i.severity == IssueSeverity.LOW and i.confidence >= 0.8],
        "medium_effort": [i for i in all_issues if i.severity == IssueSeverity.MEDIUM],
        "structural_fixes": [i for i in all_issues if i.severity == IssueSeverity.HIGH],
    }

    return JobResultsOut(
        job_id=job_id,
        status=job.status,
        summary=summary,
        pages=page_results,
        fix_packs=fix_packs,
    )
