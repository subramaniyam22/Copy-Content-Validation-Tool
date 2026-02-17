"""Issue fingerprinting for stable diff comparison."""
import hashlib
import re
from typing import Optional


def normalize_text(text: str) -> str:
    """Normalize text for fingerprinting: lowercase, collapse whitespace, strip."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_url(url: str) -> str:
    """Normalize URL for fingerprinting: strip fragments, trailing slash."""
    if not url:
        return ""
    url = url.split('#')[0]  # remove fragment
    url = url.rstrip('/')
    return url.lower()


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text content."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def compute_issue_fingerprint(
    page_url: str,
    category: str,
    issue_type: str,
    evidence: str,
    guideline_rule_id: Optional[str] = None,
) -> str:
    """
    Create a stable fingerprint hash for an issue.
    Used for diffing between scan runs.
    """
    parts = [
        normalize_url(page_url),
        category.lower() if category else "",
        issue_type.lower() if issue_type else "",
        normalize_text(evidence)[:200],  # cap evidence length
    ]
    if guideline_rule_id:
        parts.append(str(guideline_rule_id))

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
