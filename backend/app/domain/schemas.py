"""Pydantic schemas for API request/response models."""
from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Any
from datetime import datetime
from .enums import (
    PageSource, ScrapeStatus, JobStatus, JobStage,
    IssueSeverity, IssueSource, IssueCategory,
    ExclusionRuleType, DiffStatus,
)


# ──────────────────────────── Discovery ────────────────────────────

class DiscoverRequest(BaseModel):
    base_url: str
    use_sitemap: bool = True
    use_nav: bool = True
    crawl_fallback: bool = True
    max_pages: int = 50
    max_depth: int = 3
    exclusion_profile_id: Optional[int] = None


class DiscoveredPage(BaseModel):
    id: Optional[int] = None
    url: str
    title: Optional[str] = None
    source: PageSource
    selected: bool = True
    smart_exclude_reason: Optional[str] = None


class SmartExcludeSuggestion(BaseModel):
    url: str
    reason: str
    pattern: str


class DiscoverResponse(BaseModel):
    pages: list[DiscoveredPage]
    excluded: list[DiscoveredPage] = []
    smart_exclude_suggestions: list[SmartExcludeSuggestion] = []
    total_found: int = 0


# ──────────────────────────── Guidelines ────────────────────────────

class GuidelineSetCreate(BaseModel):
    name: str


class GuidelineRuleOut(BaseModel):
    id: int
    rule_id: str
    category: str
    type: str
    severity_default: IssueSeverity = IssueSeverity.MEDIUM
    rule_text: str
    fix_template: Optional[str] = None
    examples_good: Optional[str] = None
    examples_bad: Optional[str] = None
    source_file: Optional[str] = None
    section_ref: Optional[str] = None

    class Config:
        from_attributes = True


class GuidelineVersionOut(BaseModel):
    id: int
    version_number: int
    created_at: datetime
    file_manifest: Optional[Any] = None
    rules_count: int = 0
    prompt_version: Optional[str] = None
    model_used: Optional[str] = None

    class Config:
        from_attributes = True


class GuidelineSetOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    versions: list[GuidelineVersionOut] = []

    class Config:
        from_attributes = True


class GuidelineSetListOut(BaseModel):
    sets: list[GuidelineSetOut]


# ──────────────────────────── Exclusions ────────────────────────────

class ExclusionRuleIn(BaseModel):
    rule_type: ExclusionRuleType
    rule_value: str


class ExclusionProfileIn(BaseModel):
    name: str
    is_default: bool = False
    rules: list[ExclusionRuleIn] = []


class ExclusionProfileCreate(BaseModel):
    project_id: int
    name: str
    is_default: bool = False


class ExclusionRuleCreate(BaseModel):
    rule_type: ExclusionRuleType
    rule_value: str
    reason: Optional[str] = None


class ExclusionRuleOut(BaseModel):
    id: int
    rule_type: ExclusionRuleType
    rule_value: str
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class ExclusionProfileOut(BaseModel):
    id: int
    name: str
    is_default: bool
    created_at: datetime
    rules: list[ExclusionRuleOut] = []

    class Config:
        from_attributes = True


# ──────────────────────────── Validation / Jobs ────────────────────────────

class ValidateRequest(BaseModel):
    base_url: str
    page_urls: list[str]
    guideline_set_id: Optional[int] = None
    guideline_version: Optional[int] = None
    exclusion_profile_id: Optional[int] = None
    run_axe: bool = True
    run_lighthouse: bool = False
    run_deterministic: bool = True
    run_llm: bool = True


class JobProgressOut(BaseModel):
    stage: str  # Accept string from Redis progress updates
    discovered: int = 0
    selected: int = 0
    scraped: int = 0
    validated: int = 0
    total_pages: int = 0
    current_page: Optional[str] = None
    message: Optional[str] = None


class JobOut(BaseModel):
    id: int
    status: JobStatus
    stage: Optional[JobStage] = None
    progress: Optional[JobProgressOut] = None
    error: Optional[Any] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────── Issues ────────────────────────────

class IssueOut(BaseModel):
    id: int
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    category: str
    type: str
    severity: IssueSeverity
    evidence: Optional[str] = None
    explanation: Optional[str] = None
    proposed_fix: Optional[str] = None
    guideline_rule_id: Optional[int] = None
    guideline_set_name: Optional[str] = None
    guideline_section: Optional[str] = None
    guideline_source_file: Optional[str] = None
    source: IssueSource
    confidence: float = 0.0
    fingerprint: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IssueSummary(BaseModel):
    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}


class PageResultOut(BaseModel):
    url: str
    title: Optional[str] = None
    issue_count: int = 0
    issues: list[IssueOut] = []


class JobResultsOut(BaseModel):
    job_id: int
    status: JobStatus
    summary: IssueSummary
    pages: list[PageResultOut] = []
    fix_packs: Optional[dict[str, list[IssueOut]]] = None


# ──────────────────────────── Scans / Diffs ────────────────────────────

class ScanSummaryOut(BaseModel):
    id: int
    base_url: str
    status: JobStatus
    total_pages: int = 0
    total_issues: int = 0
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DiffIssue(BaseModel):
    issue: IssueOut
    status: DiffStatus


class ScanCompareOut(BaseModel):
    scan_a_id: int
    scan_b_id: int
    new_issues: list[IssueOut] = []
    resolved_issues: list[IssueOut] = []
    unchanged_count: int = 0
    summary: dict[str, Any] = {}


# ──────────────────────────── Projects ────────────────────────────

class ProjectOut(BaseModel):
    id: int
    base_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    base_url: str
