"""Export service — generate CSV and XLSX exports of validation results."""
import csv
import io
from datetime import datetime
from typing import Optional

from app.utils.logging import logger

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


EXPORT_COLUMNS = [
    "page_url", "page_title", "category", "type", "severity",
    "evidence", "proposed_fix", "guideline_rule_id", "guideline_section",
    "confidence", "source",
]


class ExportService:
    """Export validation results to CSV and XLSX."""

    def export_csv(self, issues: list[dict]) -> bytes:
        """Generate CSV bytes from issue dicts."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for issue in issues:
            writer.writerow(self._normalize_row(issue))
        return output.getvalue().encode("utf-8")

    def export_xlsx(self, issues: list[dict]) -> Optional[bytes]:
        """Generate XLSX bytes from issue dicts."""
        if xlsxwriter is None:
            logger.error("xlsxwriter not installed — cannot export XLSX")
            return None

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Validation Results")

        # Header format
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#1a1a2e",
            "font_color": "#ffffff",
            "border": 1,
        })

        # Severity formats
        severity_fmts = {
            "high": workbook.add_format({"bg_color": "#FFE0E0", "border": 1}),
            "medium": workbook.add_format({"bg_color": "#FFF3E0", "border": 1}),
            "low": workbook.add_format({"bg_color": "#E8F5E9", "border": 1}),
        }
        default_fmt = workbook.add_format({"border": 1, "text_wrap": True})

        # Write headers
        for col, header in enumerate(EXPORT_COLUMNS):
            worksheet.write(0, col, header.replace("_", " ").title(), header_fmt)

        # Write data
        for row_idx, issue in enumerate(issues, start=1):
            row = self._normalize_row(issue)
            severity = str(row.get("severity", "")).lower()
            fmt = severity_fmts.get(severity, default_fmt)

            for col, key in enumerate(EXPORT_COLUMNS):
                worksheet.write(row_idx, col, str(row.get(key, "")), fmt)

        # Column widths
        widths = [35, 20, 15, 20, 8, 50, 50, 15, 15, 8, 12]
        for i, w in enumerate(widths):
            worksheet.set_column(i, i, w)

        workbook.close()
        return output.getvalue()

    def _normalize_row(self, issue: dict) -> dict:
        """Normalize an issue dict for export."""
        page = issue.get("scan_page", {})
        rule = issue.get("guideline_rule", {})

        return {
            "page_url": page.get("url", issue.get("page_url", "")),
            "page_title": page.get("title", issue.get("page_title", "")),
            "category": str(issue.get("category", "")),
            "type": str(issue.get("type", "")),
            "severity": str(issue.get("severity", "")),
            "evidence": str(issue.get("evidence", ""))[:500],
            "proposed_fix": str(issue.get("proposed_fix", ""))[:500],
            "guideline_rule_id": str(rule.get("rule_id", issue.get("guideline_rule_id", ""))),
            "guideline_section": str(rule.get("section_ref", issue.get("guideline_section", ""))),
            "confidence": str(issue.get("confidence", "")),
            "source": str(issue.get("source", "")),
        }
