"""Scraper service — extract structured content from web pages."""
from playwright.sync_api import sync_playwright
from app.config import settings
from app.utils.url_security import validate_url, SSRFError
from app.utils.html_extract import (
    NOISE_SELECTORS, MAIN_CONTENT_SELECTORS, HEADING_TAGS,
    clean_text, estimate_tokens, heading_level,
)
from app.domain.fingerprints import compute_content_hash
from app.utils.logging import logger


class ScraperService:
    """Scrape pages and extract structured content with heading hierarchy."""

    def __init__(self):
        self.timeout = settings.SCRAPE_TIMEOUT_MS

    def scrape_url(
        self,
        url: str,
        extra_exclude_selectors: list[str] = None,
    ) -> list[dict]:
        """
        Scrape a single URL and return structured content chunks.
        Each chunk: {heading_path, content_text, content_hash, token_estimate, title}
        """
        try:
            validate_url(url)
        except SSRFError as e:
            logger.error(f"SSRF blocked scrape of {url}: {e}")
            return []

        extra_selectors = extra_exclude_selectors or []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )

                resp = page.goto(url, wait_until="networkidle", timeout=self.timeout)
                if not resp or resp.status >= 400:
                    logger.warning(f"HTTP {resp.status if resp else 'no response'} for {url}")
                    browser.close()
                    return []

                page_title = page.title() or ""

                # Remove noise elements
                all_noise = NOISE_SELECTORS + extra_selectors
                for sel in all_noise:
                    try:
                        page.evaluate(f'''
                            document.querySelectorAll('{sel}').forEach(el => el.remove());
                        ''')
                    except Exception:
                        pass

                # Find main content container
                main_container = None
                for sel in MAIN_CONTENT_SELECTORS:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0:
                            main_container = sel
                            break
                    except Exception:
                        continue

                if not main_container:
                    main_container = "body"

                # Build heading tree and extract chunks
                chunks = self._extract_structured_content(page, main_container, page_title)

                browser.close()

                if not chunks:
                    # Fallback: get all text from main container
                    with sync_playwright() as p2:
                        b2 = p2.chromium.launch(headless=True)
                        pg2 = b2.new_page()
                        pg2.goto(url, wait_until="networkidle", timeout=self.timeout)
                        text = pg2.locator(main_container).first.inner_text()
                        text = clean_text(text)
                        b2.close()
                        if text:
                            chunks = [{
                                "heading_path": "",
                                "content_text": text[:5000],
                                "content_hash": compute_content_hash(text[:5000]),
                                "token_estimate": estimate_tokens(text[:5000]),
                                "title": page_title,
                            }]

                return chunks

        except Exception as e:
            logger.error(f"Scraper error for {url}: {e}")
            return []

    def _extract_structured_content(
        self, page, container_selector: str, page_title: str
    ) -> list[dict]:
        """Extract content organized by heading hierarchy."""
        chunks = []

        try:
            # Get all headings and text elements in order
            elements = page.evaluate(f'''() => {{
                const container = document.querySelector('{container_selector}');
                if (!container) return [];
                
                const results = [];
                const walker = document.createTreeWalker(
                    container,
                    NodeFilter.SHOW_ELEMENT,
                    {{
                        acceptNode: (node) => {{
                            const tag = node.tagName.toLowerCase();
                            if (['h1','h2','h3','h4','h5','h6','p','li','blockquote','td','th'].includes(tag)) {{
                                return NodeFilter.FILTER_ACCEPT;
                            }}
                            return NodeFilter.FILTER_SKIP;
                        }}
                    }}
                );
                
                let node;
                while (node = walker.nextNode()) {{
                    const tag = node.tagName.toLowerCase();
                    const text = node.innerText?.trim() || '';
                    if (text) {{
                        results.push({{ tag, text: text.substring(0, 2000) }});
                    }}
                }}
                return results;
            }}''')

            if not elements:
                return []

            # Build heading path and group content
            heading_stack = []
            current_heading_path = ""
            current_texts = []

            for el in elements:
                tag = el["tag"]
                text = el["text"]
                level = heading_level(tag)

                if level is not None:
                    # Save previous chunk
                    if current_texts:
                        combined = "\n".join(current_texts)
                        if combined.strip():
                            chunks.append({
                                "heading_path": current_heading_path,
                                "content_text": combined,
                                "content_hash": compute_content_hash(combined),
                                "token_estimate": estimate_tokens(combined),
                                "title": page_title,
                            })
                        current_texts = []

                    # Update heading stack
                    while heading_stack and heading_stack[-1][0] >= level:
                        heading_stack.pop()
                    heading_stack.append((level, text))
                    current_heading_path = " > ".join(
                        f"H{lv}: {t}" for lv, t in heading_stack
                    )
                else:
                    current_texts.append(text)

            # Save last chunk
            if current_texts:
                combined = "\n".join(current_texts)
                if combined.strip():
                    chunks.append({
                        "heading_path": current_heading_path,
                        "content_text": combined,
                        "content_hash": compute_content_hash(combined),
                        "token_estimate": estimate_tokens(combined),
                        "title": page_title,
                    })

        except Exception as e:
            logger.error(f"Content extraction error: {e}")

        return chunks

    def scrape_multiple(
        self, urls: list[str], extra_exclude_selectors: list[str] = None
    ) -> dict[str, list[dict]]:
        """Scrape multiple URLs. Returns {url: [chunks]}."""
        results = {}
        for url in urls:
            results[url] = self.scrape_url(url, extra_exclude_selectors)
        return results
