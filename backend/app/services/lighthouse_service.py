"""Lighthouse service — stub with interface and storage model.

This service implements the full interface for Lighthouse audits but returns
a "not available" status since running Lighthouse requires a Node.js environment.
The interface and storage model are ready for future implementation.
"""
from app.domain.enums import IssueSeverity, IssueSource
from app.utils.logging import logger


class LighthouseService:
    """Lighthouse audit service (stubbed — interface ready for implementation)."""

    def __init__(self):
        self.available = False

    def is_available(self) -> bool:
        """Check if Lighthouse is available in the current environment."""
        return self.available

    def run_audit(self, url: str) -> list[dict]:
        """
        Run Lighthouse audit on a URL.
        
        Returns list of issue dicts. Currently returns empty list with
        a warning since Lighthouse requires a separate Node.js process.
        
        TODO: Implement by spawning a Node.js process with lighthouse CLI
              or using a dockerized lighthouse service.
        """
        if not self.available:
            logger.info(f"Lighthouse not available — skipping audit for {url}")
            return []

        # Future implementation would:
        # 1. Run: npx lighthouse <url> --output json --chrome-flags="--headless"
        # 2. Parse the JSON report
        # 3. Extract performance, SEO, and accessibility findings
        # 4. Map to issue dicts with source=IssueSource.LIGHTHOUSE

        return []

    def parse_lighthouse_report(self, report_json: dict) -> list[dict]:
        """
        Parse a Lighthouse JSON report into issue dicts.
        Ready for use when run_audit is fully implemented.
        """
        issues = []
        categories = report_json.get("categories", {})

        for cat_id, cat_data in categories.items():
            score = cat_data.get("score", 1.0)
            if score is not None and score < 0.9:
                # Get failing audits
                audit_refs = cat_data.get("auditRefs", [])
                for ref in audit_refs:
                    audit_id = ref.get("id", "")
                    audit = report_json.get("audits", {}).get(audit_id, {})
                    audit_score = audit.get("score", 1.0)

                    if audit_score is not None and audit_score < 1.0:
                        severity = IssueSeverity.LOW
                        if audit_score < 0.5:
                            severity = IssueSeverity.HIGH
                        elif audit_score < 0.9:
                            severity = IssueSeverity.MEDIUM

                        issues.append({
                            "category": self._map_category(cat_id),
                            "type": audit_id,
                            "severity": severity,
                            "evidence": audit.get("displayValue", ""),
                            "explanation": audit.get("description", ""),
                            "proposed_fix": audit.get("title", ""),
                            "source": IssueSource.LIGHTHOUSE,
                            "confidence": 0.92,
                        })

        return issues

    def _map_category(self, lighthouse_cat: str) -> str:
        mapping = {
            "performance": "performance",
            "accessibility": "accessibility",
            "seo": "seo",
            "best-practices": "content",
        }
        return mapping.get(lighthouse_cat, "content")
