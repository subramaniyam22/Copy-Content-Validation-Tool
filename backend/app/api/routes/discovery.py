"""Discovery API routes."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.db import get_db
from app.repositories import scan_repo
from app.domain.schemas import DiscoverRequest, DiscoverResponse, DiscoveredPage, SmartExcludeSuggestion
from app.services.discovery_service import DiscoveryService
from app.repositories import exclusion_repo

router = APIRouter(prefix="/api", tags=["discovery"])


@router.post("/discover", response_model=DiscoverResponse)
async def discover_pages(req: DiscoverRequest, db: AsyncSession = Depends(get_db)):
    """Discover pages from a base URL using sitemap, nav, and crawl."""
    # Load exclusion rules if profile provided
    exclusion_rules = []
    if req.exclusion_profile_id:
        profile = await exclusion_repo.get_exclusion_profile(db, req.exclusion_profile_id)
        if profile:
            exclusion_rules = [
                {"rule_type": r.rule_type.value, "rule_value": r.rule_value}
                for r in profile.rules
            ]

    service = DiscoveryService()

    # Run discovery in thread pool (Playwright is sync)
    result = await asyncio.to_thread(
        service.discover,
        base_url=req.base_url,
        use_sitemap=req.use_sitemap,
        use_nav=req.use_nav,
        crawl_fallback=req.crawl_fallback,
        max_pages=req.max_pages,
        max_depth=req.max_depth,
        exclusion_rules=exclusion_rules,
    )

    pages = [DiscoveredPage(**p) for p in result["pages"]]
    excluded = [DiscoveredPage(**p) for p in result.get("excluded", [])]
    suggestions = [SmartExcludeSuggestion(**s) for s in result.get("smart_exclude_suggestions", [])]

    return DiscoverResponse(
        pages=pages,
        excluded=excluded,
        smart_exclude_suggestions=suggestions,
        total_found=result.get("total_found", len(pages)),
    )
