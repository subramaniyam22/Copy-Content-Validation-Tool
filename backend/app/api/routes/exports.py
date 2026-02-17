"""Export API routes."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.db import get_db
from app.repositories import scan_repo
from app.services.export_service import ExportService
from app.domain.enums import JobStatus

router = APIRouter(prefix="/api/jobs", tags=["exports"])


@router.get("/{job_id}/export.csv")
async def export_csv(job_id: int, db: AsyncSession = Depends(get_db)):
    """Export job results as CSV."""
    job = await scan_repo.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    issues = _flatten_issues(job)
    svc = ExportService()
    csv_bytes = svc.export_csv(issues)

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="scan_{job_id}_results.csv"'},
    )


@router.get("/{job_id}/export.xlsx")
async def export_xlsx(job_id: int, db: AsyncSession = Depends(get_db)):
    """Export job results as XLSX."""
    job = await scan_repo.get_scan_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    issues = _flatten_issues(job)
    svc = ExportService()
    xlsx_bytes = svc.export_xlsx(issues)

    if xlsx_bytes is None:
        raise HTTPException(500, "XLSX export not available (xlsxwriter not installed)")

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="scan_{job_id}_results.xlsx"'},
    )


def _flatten_issues(job) -> list[dict]:
    """Flatten issues from a scan job into export-ready dicts."""
    issues = []
    for sp in (job.pages or []):
        for issue in (sp.issues or []):
            issues.append({
                "page_url": sp.url,
                "page_title": sp.title or "",
                "category": str(issue.category),
                "type": str(issue.type),
                "severity": str(issue.severity),
                "evidence": issue.evidence or "",
                "proposed_fix": issue.proposed_fix or "",
                "guideline_rule_id": str(issue.guideline_rule_id or ""),
                "guideline_section": "",
                "confidence": str(issue.confidence),
                "source": str(issue.source),
            })
    return issues
