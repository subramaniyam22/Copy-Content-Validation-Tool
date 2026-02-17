"""Scans and diff API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.db import get_db
from app.repositories import scan_repo
from app.domain.schemas import ScanSummaryOut, ScanCompareOut, IssueOut
from app.domain.enums import JobStatus
from app.services.diff_service import DiffService

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.get("", response_model=list[ScanSummaryOut])
async def list_scans(base_url: str = Query(...), db: AsyncSession = Depends(get_db)):
    """List all scans for a base URL."""
    scans = await scan_repo.list_scans_by_url(db, base_url)
    return [_format_scan_summary(s, base_url) for s in scans]


@router.get("/recent", response_model=list[ScanSummaryOut])
async def list_recent_scans(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List recent scans across all projects."""
    scans = await scan_repo.list_all_scans(db, limit)
    return [_format_scan_summary(s) for s in scans]


def _format_scan_summary(s, forced_url: str = None) -> ScanSummaryOut:
    total_issues = 0
    total_pages = 0
    if hasattr(s, 'pages') and s.pages:
        total_pages = len(s.pages)
        for p in s.pages:
            if hasattr(p, 'issues') and p.issues:
                total_issues += len(p.issues)
    
    url = forced_url or (s.project.base_url if hasattr(s, 'project') and s.project else "unknown")
    
    return ScanSummaryOut(
        id=s.id,
        base_url=url,
        status=s.status,
        total_pages=total_pages,
        total_issues=total_issues,
        created_at=s.created_at,
        finished_at=s.finished_at,
    )


@router.get("/{scan_id}/compare")
async def compare_scans(
    scan_id: int,
    to: int = Query(..., description="Scan ID to compare against"),
    db: AsyncSession = Depends(get_db),
):
    """Compare two scans by fingerprints."""
    fp_a = await scan_repo.get_issue_fingerprints_for_job(db, scan_id)
    fp_b = await scan_repo.get_issue_fingerprints_for_job(db, to)

    # Convert to dicts for the diff service
    fp_a_dict = {fp: _issue_to_dict(issue) for fp, issue in fp_a.items()}
    fp_b_dict = {fp: _issue_to_dict(issue) for fp, issue in fp_b.items()}

    svc = DiffService()
    result = svc.compare(fp_a_dict, fp_b_dict)

    return ScanCompareOut(
        scan_a_id=scan_id,
        scan_b_id=to,
        new_issues=[IssueOut(**i) for i in result["new_issues"]],
        resolved_issues=[IssueOut(**i) for i in result["resolved_issues"]],
        unchanged_count=result["unchanged_count"],
        summary=result["summary"],
    )


@router.get("/{scan_id}/compare-to-last")
async def compare_to_last(scan_id: int, db: AsyncSession = Depends(get_db)):
    """Compare a scan to the previous scan for the same project."""
    prev = await scan_repo.get_previous_scan(db, scan_id)
    if not prev:
        raise HTTPException(404, "No previous scan found for comparison")

    fp_a = await scan_repo.get_issue_fingerprints_for_job(db, prev.id)
    fp_b = await scan_repo.get_issue_fingerprints_for_job(db, scan_id)

    fp_a_dict = {fp: _issue_to_dict(issue) for fp, issue in fp_a.items()}
    fp_b_dict = {fp: _issue_to_dict(issue) for fp, issue in fp_b.items()}

    svc = DiffService()
    result = svc.compare(fp_a_dict, fp_b_dict)

    return ScanCompareOut(
        scan_a_id=prev.id,
        scan_b_id=scan_id,
        new_issues=[IssueOut(**i) for i in result["new_issues"]],
        resolved_issues=[IssueOut(**i) for i in result["resolved_issues"]],
        unchanged_count=result["unchanged_count"],
        summary=result["summary"],
    )


def _issue_to_dict(issue) -> dict:
    """Convert an Issue ORM model to a dict for the diff service."""
    sp = issue.scan_page if hasattr(issue, 'scan_page') and issue.scan_page else None
    return {
        "id": issue.id,
        "page_url": sp.url if sp else "",
        "page_title": sp.title if sp else "",
        "category": str(issue.category),
        "type": str(issue.type),
        "severity": issue.severity,
        "evidence": issue.evidence or "",
        "explanation": issue.explanation or "",
        "proposed_fix": issue.proposed_fix or "",
        "guideline_rule_id": issue.guideline_rule_id,
        "source": issue.source,
        "confidence": issue.confidence,
        "fingerprint": issue.fingerprint,
        "created_at": issue.created_at,
    }
