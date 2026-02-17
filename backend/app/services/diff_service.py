"""Diff service — compare scans for regression tracking."""
from app.domain.enums import DiffStatus
from app.utils.logging import logger


class DiffService:
    """Compare two scan jobs by issue fingerprints."""

    def compare(
        self,
        scan_a_fingerprints: dict[str, dict],
        scan_b_fingerprints: dict[str, dict],
    ) -> dict:
        """
        Compare two sets of issue fingerprints.
        scan_a = baseline (older), scan_b = new scan.
        
        Returns:
        - new_issues: in B but not A (regressions)
        - resolved_issues: in A but not B (fixes)
        - unchanged_count: in both
        - summary: counts by severity/category
        """
        a_keys = set(scan_a_fingerprints.keys())
        b_keys = set(scan_b_fingerprints.keys())

        new_keys = b_keys - a_keys
        resolved_keys = a_keys - b_keys
        unchanged_keys = a_keys & b_keys

        new_issues = [scan_b_fingerprints[k] for k in new_keys]
        resolved_issues = [scan_a_fingerprints[k] for k in resolved_keys]

        # Build summary
        summary = {
            "new_count": len(new_keys),
            "resolved_count": len(resolved_keys),
            "unchanged_count": len(unchanged_keys),
            "new_by_severity": self._count_by_attr(new_issues, "severity"),
            "resolved_by_severity": self._count_by_attr(resolved_issues, "severity"),
            "new_by_category": self._count_by_attr(new_issues, "category"),
            "resolved_by_category": self._count_by_attr(resolved_issues, "category"),
        }

        return {
            "new_issues": new_issues,
            "resolved_issues": resolved_issues,
            "unchanged_count": len(unchanged_keys),
            "summary": summary,
        }

    def _count_by_attr(self, issues: list[dict], attr: str) -> dict[str, int]:
        counts = {}
        for issue in issues:
            val = str(getattr(issue, attr, None) or issue.get(attr, "unknown"))
            counts[val] = counts.get(val, 0) + 1
        return counts
