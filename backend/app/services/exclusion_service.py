"""Exclusion service — apply exclusion rules to filter URLs."""
import re
from urllib.parse import urlparse
from app.utils.logging import logger


# Default exclusion patterns for new projects
DEFAULT_EXCLUSION_PATTERNS = [
    {"rule_type": "url_contains", "rule_value": "privacy"},
    {"rule_type": "url_contains", "rule_value": "terms"},
    {"rule_type": "url_contains", "rule_value": "cookie"},
    {"rule_type": "url_contains", "rule_value": "login"},
    {"rule_type": "url_contains", "rule_value": "account"},
    {"rule_type": "url_contains", "rule_value": "portal"},
]


class ExclusionService:
    """Apply exclusion rules to filter URLs during discovery and scraping."""

    def apply_exclusions(self, urls: list[str], rules: list[dict]) -> tuple[list[str], list[str]]:
        """
        Apply exclusion rules to a list of URLs.
        Returns: (included_urls, excluded_urls)
        """
        included = []
        excluded = []

        for url in urls:
            if self._is_excluded(url, rules):
                excluded.append(url)
            else:
                included.append(url)

        return included, excluded

    def _is_excluded(self, url: str, rules: list[dict]) -> bool:
        """Check if a URL matches any exclusion rule."""
        path = urlparse(url).path.lower()

        for rule in rules:
            rule_type = rule.get("rule_type", "")
            rule_value = rule.get("rule_value", "")

            if rule_type == "url_contains":
                if rule_value.lower() in url.lower():
                    return True

            elif rule_type == "url_regex":
                try:
                    if re.search(rule_value, url, re.IGNORECASE):
                        return True
                except re.error:
                    logger.warning(f"Invalid regex exclusion: {rule_value}")

            elif rule_type == "path_blocklist":
                if rule_value.lower() in path:
                    return True

            elif rule_type == "domain_blocklist":
                domain = urlparse(url).hostname or ""
                if rule_value.lower() in domain.lower():
                    return True

            elif rule_type == "nav_label_exclude":
                # This is handled during discovery, not URL filtering
                pass

        return False

    def preview_exclusions(self, urls: list[str], rules: list[dict]) -> dict:
        """Preview how many URLs would be excluded."""
        included, excluded = self.apply_exclusions(urls, rules)
        return {
            "total": len(urls),
            "included": len(included),
            "excluded": len(excluded),
            "excluded_urls": excluded,
        }

    def get_default_rules(self) -> list[dict]:
        """Get default exclusion rules for a new project."""
        return list(DEFAULT_EXCLUSION_PATTERNS)
