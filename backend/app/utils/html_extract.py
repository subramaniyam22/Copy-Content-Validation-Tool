"""HTML content extraction utilities."""
import re
from typing import Optional


# Common noise selectors to remove before content extraction
NOISE_SELECTORS = [
    # Cookie banners
    '[class*="cookie"]', '[id*="cookie"]', '[class*="consent"]',
    '[class*="gdpr"]', '[id*="gdpr"]',
    # Navigation
    'nav', '.nav', '#nav', '[role="navigation"]',
    # Headers
    'header', '.header', '#header', '[role="banner"]',
    # Footers
    'footer', '.footer', '#footer', '[role="contentinfo"]',
    # Sidebars / asides
    'aside', '.sidebar', '#sidebar', '[role="complementary"]',
    # Sticky CTAs
    '[class*="sticky"]', '[class*="fixed-bottom"]', '[class*="floating"]',
    # Popups / modals
    '[class*="modal"]', '[class*="popup"]', '[class*="overlay"]',
    # Ad / promo
    '[class*="promo"]', '[class*="banner"]', '[class*="advertisement"]',
]

# Selectors for main content (priority order)
MAIN_CONTENT_SELECTORS = [
    'main',
    '[role="main"]',
    'article',
    '#content',
    '.content',
    '#main',
    '.main',
    '.main-content',
    '#main-content',
    'div[class*="content"]',
    'div[class*="main"]',
]

# Heading tags
HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']


def clean_text(text: str) -> str:
    """Clean extracted text: normalize whitespace, strip."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (words / 0.75)."""
    if not text:
        return 0
    words = len(text.split())
    return int(words / 0.75)


def build_heading_path(headings_stack: list[tuple[int, str]]) -> str:
    """Build a heading path string like 'H1: Title > H2: Subtitle > H3: Section'."""
    if not headings_stack:
        return ""
    return " > ".join(f"H{level}: {text}" for level, text in headings_stack)


def heading_level(tag: str) -> Optional[int]:
    """Extract heading level from tag name (h1=1, h2=2, etc)."""
    match = re.match(r'^h(\d)$', tag.lower())
    return int(match.group(1)) if match else None
