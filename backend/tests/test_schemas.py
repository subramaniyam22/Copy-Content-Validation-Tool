"""Tests for Pydantic domain schemas — validate models accept and reject inputs correctly."""
import pytest
from datetime import datetime
from app.domain.schemas import (
    DiscoverRequest, DiscoveredPage, DiscoverResponse,
    ValidateRequest, JobOut, IssueOut, IssueSummary,
    GuidelineRuleOut,
    ExclusionRuleIn, ExclusionProfileIn,
    ScanSummaryOut, ScanCompareOut,
    PageResultOut, JobResultsOut,
)
from app.domain.enums import (
    PageSource, IssueSeverity, IssueSource, JobStatus,
    ExclusionRuleType, IssueCategory,
)


class TestDiscoverSchemas:
    def test_discover_request_defaults(self):
        req = DiscoverRequest(base_url="https://example.com")
        assert req.use_sitemap is True
        assert req.use_nav is True
        assert req.crawl_fallback is True
        assert req.max_pages == 50
        assert req.max_depth == 3
        assert req.exclusion_profile_id is None

    def test_discover_request_custom(self):
        req = DiscoverRequest(
            base_url="https://example.com",
            use_sitemap=False,
            max_pages=10,
            max_depth=1,
        )
        assert req.use_sitemap is False
        assert req.max_pages == 10

    def test_discovered_page(self):
        page = DiscoveredPage(
            url="https://example.com/about",
            source=PageSource.SITEMAP,
        )
        assert page.selected is True
        assert page.title is None

    def test_discover_response_empty(self):
        resp = DiscoverResponse(pages=[], total_found=0)
        assert len(resp.pages) == 0
        assert resp.total_found == 0


class TestValidationSchemas:
    def test_validate_request_defaults(self):
        req = ValidateRequest(
            base_url="https://example.com",
            page_urls=["https://example.com/p1"],
        )
        assert req.run_axe is True
        assert req.run_lighthouse is False
        assert req.run_deterministic is True
        assert req.run_llm is True
        assert req.guideline_set_id is None

    def test_validate_request_with_guidelines(self):
        req = ValidateRequest(
            base_url="https://example.com",
            page_urls=["https://example.com/p1"],
            guideline_set_id=1,
            guideline_version=2,
        )
        assert req.guideline_set_id == 1
        assert req.guideline_version == 2

    def test_issue_out(self):
        issue = IssueOut(
            id=1,
            category="formatting",
            type="banned_phrase",
            severity=IssueSeverity.MEDIUM,
            source=IssueSource.DETERMINISTIC,
            confidence=0.9,
        )
        assert issue.severity == IssueSeverity.MEDIUM
        assert issue.confidence == 0.9
        assert issue.fingerprint is None

    def test_issue_summary(self):
        s = IssueSummary(total=10, high=2, medium=5, low=3)
        assert s.total == 10
        assert s.by_category == {}


class TestJobSchemas:
    def test_job_out_minimal(self):
        job = JobOut(
            id=1,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
        )
        assert job.stage is None
        assert job.progress is None
        assert job.error is None

    def test_job_results_out(self):
        r = JobResultsOut(
            job_id=1,
            status=JobStatus.COMPLETED,
            summary=IssueSummary(total=5, high=1, medium=2, low=2),
            pages=[],
        )
        assert r.summary.total == 5
        assert r.fix_packs is None


class TestGuidelineSchemas:
    def test_guideline_rule_out(self):
        rule = GuidelineRuleOut(
            id=1,
            rule_id="VOICE-001",
            category="voice",
            type="guideline",
            rule_text="Use active voice",
        )
        assert rule.severity_default == IssueSeverity.MEDIUM
        assert rule.fix_template is None


class TestExclusionSchemas:
    def test_exclusion_rule_in(self):
        rule = ExclusionRuleIn(
            rule_type=ExclusionRuleType.URL_CONTAINS,
            rule_value="/admin",
        )
        assert rule.rule_type == ExclusionRuleType.URL_CONTAINS

    def test_exclusion_profile_in(self):
        profile = ExclusionProfileIn(
            name="Default Profile",
            rules=[
                ExclusionRuleIn(rule_type=ExclusionRuleType.URL_CONTAINS, rule_value="/login"),
            ],
        )
        assert len(profile.rules) == 1
        assert profile.is_default is False


class TestScanSchemas:
    def test_scan_summary_out(self):
        s = ScanSummaryOut(
            id=1,
            base_url="https://example.com",
            status=JobStatus.COMPLETED,
            total_pages=10,
            total_issues=25,
            created_at=datetime.now(),
        )
        assert s.total_pages == 10

    def test_scan_compare_out(self):
        c = ScanCompareOut(
            scan_a_id=1,
            scan_b_id=2,
            new_issues=[],
            resolved_issues=[],
            unchanged_count=5,
            summary={"new_count": 0},
        )
        assert c.unchanged_count == 5
