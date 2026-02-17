"""Enumerations used across the application."""
from enum import Enum


class PageSource(str, Enum):
    SITEMAP = "sitemap"
    NAV = "nav"
    CRAWL = "crawl"
    MANUAL = "manual"


class ScrapeStatus(str, Enum):
    PENDING = "pending"
    SCRAPING = "scraping"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    DISCOVERING = "discovering"
    SCRAPING = "scraping"
    PARSING_GUIDELINES = "parsing_guidelines"
    VALIDATING = "validating"
    RUNNING_TOOLS = "running_tools"
    FINALIZING = "finalizing"


class IssueSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueSource(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    AXE = "axe"
    LIGHTHOUSE = "lighthouse"


class IssueCategory(str, Enum):
    GRAMMAR = "grammar"
    SPELLING = "spelling"
    STYLE = "style"
    ACCESSIBILITY = "accessibility"
    SEO = "seo"
    PERFORMANCE = "performance"
    BRAND_COMPLIANCE = "brand_compliance"
    READABILITY = "readability"
    FORMATTING = "formatting"
    LINK_TEXT = "link_text"
    CONTENT = "content"


class ExclusionRuleType(str, Enum):
    URL_CONTAINS = "url_contains"
    URL_REGEX = "url_regex"
    NAV_LABEL_EXCLUDE = "nav_label_exclude"
    CSS_SELECTOR_EXCLUDE = "css_selector_exclude"
    DOMAIN_BLOCKLIST = "domain_blocklist"
    PATH_BLOCKLIST = "path_blocklist"


class DiffStatus(str, Enum):
    NEW = "new"
    RESOLVED = "resolved"
    UNCHANGED = "unchanged"
