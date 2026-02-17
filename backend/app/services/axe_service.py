"""Axe-core accessibility service — run accessibility audits via Playwright."""
from playwright.sync_api import sync_playwright
from app.config import settings
from app.domain.enums import IssueSeverity, IssueSource
from app.utils.logging import logger


# axe-core CDN
AXE_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.4/axe.min.js"


class AxeService:
    """Run axe-core accessibility audits on web pages."""

    def __init__(self):
        self.timeout = settings.SCRAPE_TIMEOUT_MS

    def run_audit(self, url: str) -> list[dict]:
        """
        Run axe-core accessibility audit on a URL.
        Returns list of issue dicts.
        """
        issues = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Inject axe-core
                page.add_script_tag(url=AXE_CDN_URL)
                page.wait_for_function("typeof axe !== 'undefined'", timeout=10000)

                # Run audit
                results = page.evaluate('''async () => {
                    const results = await axe.run();
                    return {
                        violations: results.violations.map(v => ({
                            id: v.id,
                            impact: v.impact,
                            description: v.description,
                            help: v.help,
                            helpUrl: v.helpUrl,
                            nodes: v.nodes.slice(0, 5).map(n => ({
                                html: n.html?.substring(0, 200),
                                failureSummary: n.failureSummary,
                            })),
                        })),
                    };
                }''')

                for violation in results.get("violations", []):
                    severity = self._map_impact(violation.get("impact", "moderate"))
                    nodes_evidence = "; ".join([
                        n.get("html", "")[:100] for n in violation.get("nodes", [])
                    ])

                    issues.append({
                        "category": "accessibility",
                        "type": violation.get("id", "unknown"),
                        "severity": severity,
                        "evidence": nodes_evidence or violation.get("help", ""),
                        "explanation": violation.get("description", ""),
                        "proposed_fix": violation.get("help", "") + (
                            f" (see: {violation.get('helpUrl', '')})" if violation.get("helpUrl") else ""
                        ),
                        "source": IssueSource.AXE,
                        "confidence": 0.95,
                    })

                browser.close()

        except Exception as e:
            logger.error(f"Axe audit failed for {url}: {e}")

        return issues

    def _map_impact(self, impact: str) -> str:
        mapping = {
            "critical": IssueSeverity.HIGH,
            "serious": IssueSeverity.HIGH,
            "moderate": IssueSeverity.MEDIUM,
            "minor": IssueSeverity.LOW,
        }
        return mapping.get(impact, IssueSeverity.MEDIUM)
