"""Tests for diff service — fingerprint comparison and regression tracking."""
import pytest
from app.services.diff_service import DiffService
from app.domain.fingerprints import (
    compute_issue_fingerprint,
    normalize_text,
    normalize_url,
    compute_content_hash,
)


@pytest.fixture
def diff_service():
    return DiffService()


# ────────────────────── Fingerprint Utils ──────────────────────

class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("Hello World") == "hello world"

    def test_collapses_whitespace(self):
        assert normalize_text("hello   world") == "hello world"

    def test_strips(self):
        assert normalize_text("  hello  ") == "hello"

    def test_empty(self):
        assert normalize_text("") == ""

    def test_none(self):
        assert normalize_text(None) == ""

    def test_tabs_and_newlines(self):
        assert normalize_text("hello\t\tworld\n\nnew") == "hello world new"


class TestNormalizeUrl:
    def test_removes_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_removes_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_lowercases(self):
        assert normalize_url("https://Example.COM/Page") == "https://example.com/page"

    def test_empty(self):
        assert normalize_url("") == ""

    def test_none(self):
        assert normalize_url(None) == ""


class TestContentHash:
    def test_deterministic(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_different_text(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("goodbye world")
        assert h1 != h2

    def test_normalization(self):
        # Same normalized text = same hash
        h1 = compute_content_hash("Hello   World")
        h2 = compute_content_hash("hello world")
        assert h1 == h2


class TestIssueFingerprint:
    def test_deterministic(self):
        fp1 = compute_issue_fingerprint(
            "https://example.com/page", "formatting", "banned_phrase", "click here"
        )
        fp2 = compute_issue_fingerprint(
            "https://example.com/page", "formatting", "banned_phrase", "click here"
        )
        assert fp1 == fp2

    def test_different_url(self):
        fp1 = compute_issue_fingerprint(
            "https://example.com/page1", "formatting", "banned_phrase", "click here"
        )
        fp2 = compute_issue_fingerprint(
            "https://example.com/page2", "formatting", "banned_phrase", "click here"
        )
        assert fp1 != fp2

    def test_different_category(self):
        fp1 = compute_issue_fingerprint(
            "https://example.com/page", "formatting", "banned_phrase", "click here"
        )
        fp2 = compute_issue_fingerprint(
            "https://example.com/page", "accessibility", "banned_phrase", "click here"
        )
        assert fp1 != fp2

    def test_url_normalization(self):
        # Trailing slash and fragment shouldn't affect fingerprint
        fp1 = compute_issue_fingerprint(
            "https://example.com/page/", "formatting", "banned_phrase", "click here"
        )
        fp2 = compute_issue_fingerprint(
            "https://example.com/page#top", "formatting", "banned_phrase", "click here"
        )
        assert fp1 == fp2

    def test_with_guideline_rule_id(self):
        fp1 = compute_issue_fingerprint(
            "https://example.com/page", "voice", "guideline", "issue text", "RULE-001"
        )
        fp2 = compute_issue_fingerprint(
            "https://example.com/page", "voice", "guideline", "issue text", "RULE-002"
        )
        assert fp1 != fp2

    def test_returns_sha256_hex(self):
        fp = compute_issue_fingerprint(
            "https://example.com/page", "cat", "type", "evidence"
        )
        assert len(fp) == 64  # SHA-256 hex digest


# ────────────────────── Diff Service ──────────────────────

class TestDiffService:
    def _make_issue(self, category: str, evidence: str, severity: str = "medium") -> dict:
        return {
            "category": category,
            "type": "test",
            "severity": severity,
            "evidence": evidence,
            "source": "deterministic",
        }

    def test_identical_scans(self, diff_service):
        fp_a = {
            "fp1": self._make_issue("formatting", "issue 1"),
            "fp2": self._make_issue("readability", "issue 2"),
        }
        fp_b = dict(fp_a)  # same fingerprints

        result = diff_service.compare(fp_a, fp_b)
        assert result["unchanged_count"] == 2
        assert len(result["new_issues"]) == 0
        assert len(result["resolved_issues"]) == 0

    def test_all_new_issues(self, diff_service):
        fp_a = {}
        fp_b = {
            "fp1": self._make_issue("formatting", "new issue 1"),
            "fp2": self._make_issue("readability", "new issue 2"),
        }

        result = diff_service.compare(fp_a, fp_b)
        assert len(result["new_issues"]) == 2
        assert result["unchanged_count"] == 0
        assert len(result["resolved_issues"]) == 0

    def test_all_resolved(self, diff_service):
        fp_a = {
            "fp1": self._make_issue("formatting", "old issue 1"),
            "fp2": self._make_issue("readability", "old issue 2"),
        }
        fp_b = {}

        result = diff_service.compare(fp_a, fp_b)
        assert len(result["resolved_issues"]) == 2
        assert result["unchanged_count"] == 0
        assert len(result["new_issues"]) == 0

    def test_mixed_changes(self, diff_service):
        fp_a = {
            "fp1": self._make_issue("formatting", "stays"),
            "fp2": self._make_issue("readability", "gets resolved"),
        }
        fp_b = {
            "fp1": self._make_issue("formatting", "stays"),
            "fp3": self._make_issue("accessibility", "new regression"),
        }

        result = diff_service.compare(fp_a, fp_b)
        assert result["unchanged_count"] == 1
        assert len(result["new_issues"]) == 1
        assert len(result["resolved_issues"]) == 1

    def test_summary_structure(self, diff_service):
        fp_a = {"fp1": self._make_issue("formatting", "old", "high")}
        fp_b = {
            "fp1": self._make_issue("formatting", "old", "high"),
            "fp2": self._make_issue("readability", "new", "medium"),
        }

        result = diff_service.compare(fp_a, fp_b)
        summary = result["summary"]
        assert "new_count" in summary
        assert "resolved_count" in summary
        assert "unchanged_count" in summary
        assert "new_by_severity" in summary
        assert summary["new_count"] == 1
        assert summary["resolved_count"] == 0
        assert summary["unchanged_count"] == 1

    def test_empty_both(self, diff_service):
        result = diff_service.compare({}, {})
        assert result["unchanged_count"] == 0
        assert len(result["new_issues"]) == 0
        assert len(result["resolved_issues"]) == 0
