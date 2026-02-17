"""Worker tasks — orchestrate the discover→scrape→validate pipeline."""
import json
import traceback
from datetime import datetime

from app.config import settings
from app.repositories.db import SyncSessionLocal
from app.repositories import scan_repo, guideline_repo
from app.domain.enums import JobStatus, JobStage, ScrapeStatus, IssueSource
from app.domain.fingerprints import compute_issue_fingerprint
from app.utils.logging import logger
from app.workers.queue import get_redis


def _update_progress(job_id: int, progress: dict):
    """Push progress update to Redis for SSE consumption."""
    r = get_redis()
    r.set(f"job:{job_id}:progress", json.dumps(progress), ex=3600)
    r.publish(f"job:{job_id}:events", json.dumps(progress))


def run_validation_job(job_id: int, page_urls: list[str], options: dict):
    """
    Main worker task. Runs synchronously inside RQ worker.
    Stages: scraping → validating → running_tools → finalizing
    """
    # Import services here to avoid circular imports
    from app.services.scraper_service import ScraperService
    from app.services.deterministic_validators import DeterministicValidator
    from app.services.llm_validator import LLMValidator
    from app.services.axe_service import AxeService

    db = SyncSessionLocal()
    try:
        # Mark job as running
        from sqlalchemy import update as sa_update
        from app.models.models import ScanJob, ScanPage, PageContentChunk, Issue

        db.execute(
            sa_update(ScanJob).where(ScanJob.id == job_id).values(
                status=JobStatus.RUNNING,
                stage=JobStage.SCRAPING,
                started_at=datetime.utcnow(),
            )
        )
        db.commit()

        # Get all selected pages for this job
        pages = db.query(ScanPage).filter(
            ScanPage.scan_job_id == job_id,
            ScanPage.selected == True,
        ).all()

        total_pages = len(pages)
        scraped = 0
        validated = 0

        # ─── Stage: SCRAPING ───
        _update_progress(job_id, {
            "stage": "scraping",
            "total_pages": total_pages,
            "scraped": 0,
            "validated": 0,
            "message": "Starting scraping...",
        })

        scraper = ScraperService()

        for page in pages:
            try:
                _update_progress(job_id, {
                    "stage": "scraping",
                    "total_pages": total_pages,
                    "scraped": scraped,
                    "validated": validated,
                    "current_page": page.url,
                    "message": f"Scraping {page.url}",
                })

                chunks = scraper.scrape_url(page.url)

                # Save chunks to DB
                for chunk in chunks:
                    pcc = PageContentChunk(
                        scan_page_id=page.id,
                        heading_path=chunk.get("heading_path", ""),
                        content_text=chunk["content_text"],
                        content_hash=chunk["content_hash"],
                        token_estimate=chunk.get("token_estimate", 0),
                    )
                    db.add(pcc)

                page.scrape_status = ScrapeStatus.DONE
                if chunks and chunks[0].get("title"):
                    page.title = chunks[0]["title"]

                scraped += 1
            except Exception as e:
                logger.error(f"Scrape failed for {page.url}: {e}")
                page.scrape_status = ScrapeStatus.FAILED
                scraped += 1

            db.commit()

        # ─── Stage: VALIDATING ───
        db.execute(
            sa_update(ScanJob).where(ScanJob.id == job_id).values(
                stage=JobStage.VALIDATING,
            )
        )
        db.commit()

        _update_progress(job_id, {
            "stage": "validating",
            "total_pages": total_pages,
            "scraped": scraped,
            "validated": 0,
            "message": "Starting validation...",
        })

        # Prepare validators
        deterministic = DeterministicValidator()

        # Get guideline rules if available
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        guideline_rules = []
        if job.guideline_version_id:
            from app.models.models import GuidelineRule
            guideline_rules = db.query(GuidelineRule).filter(
                GuidelineRule.guideline_version_id == job.guideline_version_id
            ).all()

        run_llm = options.get("run_llm", True)
        run_axe = options.get("run_axe", True)

        llm_validator = None
        if run_llm:
            try:
                llm_validator = LLMValidator(guideline_rules=guideline_rules)
            except Exception as e:
                logger.error(f"LLM validator init failed: {e}")

        axe_service = None
        if run_axe:
            try:
                axe_service = AxeService()
            except Exception as e:
                logger.error(f"Axe service init failed: {e}")

        for page in pages:
            if page.scrape_status != ScrapeStatus.DONE:
                validated += 1
                continue

            try:
                _update_progress(job_id, {
                    "stage": "validating",
                    "total_pages": total_pages,
                    "scraped": scraped,
                    "validated": validated,
                    "current_page": page.url,
                    "message": f"Validating {page.url}",
                })

                # Get chunks for this page
                chunks_db = db.query(PageContentChunk).filter(
                    PageContentChunk.scan_page_id == page.id
                ).all()

                all_issues = []

                # 1) Deterministic validation
                if options.get("run_deterministic", True):
                    for chunk in chunks_db:
                        det_issues = deterministic.validate(
                            text=chunk.content_text,
                            heading_path=chunk.heading_path,
                            page_url=page.url,
                        )
                        all_issues.extend(det_issues)

                # 2) LLM validation
                if llm_validator and chunks_db:
                    chunk_texts = [
                        {"heading_path": c.heading_path, "content": c.content_text}
                        for c in chunks_db
                    ]
                    try:
                        llm_issues = llm_validator.validate_chunks(
                            page_url=page.url,
                            chunks=chunk_texts,
                        )
                        all_issues.extend(llm_issues)
                    except Exception as e:
                        logger.error(f"LLM validation failed for {page.url}: {e}")

                # 3) Axe accessibility
                if axe_service:
                    try:
                        axe_issues = axe_service.run_audit(page.url)
                        all_issues.extend(axe_issues)
                    except Exception as e:
                        logger.error(f"Axe audit failed for {page.url}: {e}")

                # Save issues
                # Create a lookup map for rule string IDs to integer primary keys
                rule_id_map = {r.rule_id: r.id for r in guideline_rules}

                for issue_data in all_issues:
                    raw_rule_id = issue_data.get("guideline_rule_id")
                    integer_rule_id = None
                    if raw_rule_id:
                        # Normalize rule_id (strip brackets if LLM included them)
                        clean_id = str(raw_rule_id).strip("[] \t\n")
                        integer_rule_id = rule_id_map.get(clean_id) or rule_id_map.get(raw_rule_id)

                    fingerprint = compute_issue_fingerprint(
                        page_url=page.url,
                        category=issue_data["category"],
                        issue_type=issue_data["type"],
                        evidence=issue_data.get("evidence", ""),
                        guideline_rule_id=integer_rule_id,
                    )
                    issue = Issue(
                        scan_page_id=page.id,
                        category=issue_data["category"],
                        type=issue_data["type"],
                        severity=issue_data["severity"],
                        evidence=issue_data.get("evidence"),
                        explanation=issue_data.get("explanation"),
                        proposed_fix=issue_data.get("proposed_fix"),
                        guideline_rule_id=integer_rule_id,
                        source=issue_data["source"],
                        confidence=issue_data.get("confidence", 0.0),
                        fingerprint=fingerprint,
                    )
                    db.add(issue)

                validated += 1
                db.commit()

            except Exception as e:
                logger.error(f"Validation failed for {page.url}: {e}")
                validated += 1
                db.commit()

        # ─── Stage: FINALIZING ───
        db.execute(
            sa_update(ScanJob).where(ScanJob.id == job_id).values(
                status=JobStatus.COMPLETED,
                stage=JobStage.FINALIZING,
                finished_at=datetime.utcnow(),
                progress_json={
                    "stage": "finalizing",
                    "total_pages": total_pages,
                    "scraped": scraped,
                    "validated": validated,
                    "message": "Completed",
                },
            )
        )
        db.commit()

        _update_progress(job_id, {
            "stage": "finalizing",
            "total_pages": total_pages,
            "scraped": scraped,
            "validated": validated,
            "message": "Completed",
        })

        logger.info(f"Job {job_id} completed: {scraped} scraped, {validated} validated")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}\n{traceback.format_exc()}")
        try:
            from sqlalchemy import update as sa_update
            from app.models.models import ScanJob
            db.execute(
                sa_update(ScanJob).where(ScanJob.id == job_id).values(
                    status=JobStatus.FAILED,
                    finished_at=datetime.utcnow(),
                    error_json={
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    },
                )
            )
            db.commit()
        except Exception:
            pass

        _update_progress(job_id, {
            "stage": "failed",
            "message": str(e),
        })
    finally:
        db.close()
