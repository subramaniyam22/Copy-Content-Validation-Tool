"""Discovery service — find pages from sitemap, nav, and crawl."""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from typing import Optional

import httpx
from playwright.sync_api import sync_playwright

from app.config import settings
from app.utils.url_security import (
    validate_url, normalize_url, is_same_domain,
    get_smart_exclude_suggestions, SSRFError,
)
from app.utils.logging import logger
from app.domain.enums import PageSource


class DiscoveryService:
    """Discovers pages from a base URL using sitemap, nav parsing, and BFS crawl."""

    def __init__(self):
        self.max_pages = settings.MAX_CRAWL_PAGES
        self.max_depth = settings.MAX_CRAWL_DEPTH
        self.timeout = settings.CRAWL_TIMEOUT_MS / 1000

    def discover(
        self,
        base_url: str,
        use_sitemap: bool = True,
        use_nav: bool = True,
        crawl_fallback: bool = True,
        max_pages: Optional[int] = None,
        max_depth: Optional[int] = None,
        exclusion_rules: list[dict] = None,
    ) -> dict:
        """
        Discover pages and return:
        - pages: list of {url, title, source, selected}
        - smart_exclude_suggestions: list of {url, reason, pattern}
        """
        max_pages = max_pages or self.max_pages
        max_depth = max_depth or self.max_depth
        exclusion_rules = exclusion_rules or []

        # Validate base URL
        try:
            validate_url(base_url)
        except SSRFError as e:
            logger.error(f"SSRF blocked: {e}")
            return {"pages": [], "smart_exclude_suggestions": [], "total_found": 0}

        seen_urls = set()
        pages = []

        # 1) Sitemap
        if use_sitemap:
            sitemap_pages = self._discover_sitemap(base_url, max_pages)
            for p in sitemap_pages:
                norm = normalize_url(p["url"])
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    pages.append(p)

        # 2) Nav links
        if use_nav and len(pages) < max_pages:
            nav_pages = self._discover_nav(base_url)
            for p in nav_pages:
                norm = normalize_url(p["url"])
                if norm not in seen_urls and is_same_domain(p["url"], base_url):
                    seen_urls.add(norm)
                    pages.append(p)
                    if len(pages) >= max_pages:
                        break

        # 3) Crawl fallback
        if crawl_fallback and len(pages) < max_pages:
            crawl_pages = self._crawl_bfs(base_url, seen_urls, max_pages - len(pages), max_depth)
            for p in crawl_pages:
                norm = normalize_url(p["url"])
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    pages.append(p)

        # Apply exclusion rules
        excluded = []
        active = []
        for p in pages:
            if self._should_exclude(p["url"], exclusion_rules):
                p["selected"] = False
                excluded.append(p)
            else:
                active.append(p)

        # Smart exclude suggestions for active pages
        active_urls = [p["url"] for p in active]
        suggestions = get_smart_exclude_suggestions(active_urls)

        return {
            "pages": active + excluded,
            "excluded": excluded,
            "smart_exclude_suggestions": suggestions,
            "total_found": len(pages),
        }

    def _discover_sitemap(self, base_url: str, max_pages: int) -> list[dict]:
        """Parse sitemap.xml (and sitemap index) for URLs."""
        pages = []
        sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(sitemap_url)
                if resp.status_code != 200:
                    return pages

                root = ET.fromstring(resp.text)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                urls = []
                # Check if sitemap index
                sitemap_refs = root.findall('.//sm:sitemap/sm:loc', ns)
                if sitemap_refs:
                    for ref in sitemap_refs[:5]:  # Limit sub-sitemaps
                        try:
                            sub_resp = client.get(ref.text.strip())
                            if sub_resp.status_code == 200:
                                sub_root = ET.fromstring(sub_resp.text)
                                for url_el in sub_root.findall('.//sm:url/sm:loc', ns):
                                    url = url_el.text.strip()
                                    if is_same_domain(url, base_url):
                                        urls.append(url)
                                        if len(urls) >= max_pages:
                                            break
                        except Exception:
                            continue
                        if len(urls) >= max_pages:
                            break
                else:
                    # Regular sitemap
                    for url_el in root.findall('.//sm:url/sm:loc', ns):
                        url = url_el.text.strip()
                        if is_same_domain(url, base_url):
                            urls.append(url)
                            if len(urls) >= max_pages:
                                break

                # Fetch titles in parallel for the discovered URLs
                from concurrent.futures import ThreadPoolExecutor
                def get_title(url):
                    try:
                        with httpx.Client(timeout=3.0, follow_redirects=True) as c:
                            r = c.get(url)
                            if r.status_code == 200:
                                match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE | re.DOTALL)
                                if match:
                                    import html
                                    return html.unescape(match.group(1).strip())
                    except Exception:
                        pass
                    return None

                with ThreadPoolExecutor(max_workers=10) as executor:
                    titles = list(executor.map(get_title, urls))

                for url, title in zip(urls, titles):
                    pages.append({
                        "url": url,
                        "title": title,
                        "source": PageSource.SITEMAP,
                        "selected": True,
                    })

        except Exception as e:
            logger.warning(f"Sitemap discovery failed for {base_url}: {e}")

        return pages

    def _discover_nav(self, base_url: str) -> list[dict]:
        """Load page in Playwright and extract nav/menu links."""
        pages = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(base_url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))

                # Collect links from nav areas
                nav_selectors = [
                    'nav a[href]',
                    'header a[href]',
                    '[role="navigation"] a[href]',
                    '.menu a[href]',
                    '.navbar a[href]',
                    '#nav a[href]',
                ]
                combined = ', '.join(nav_selectors)
                links = page.locator(combined).all()

                for link in links:
                    try:
                        href = link.get_attribute('href')
                        text = link.inner_text().strip()
                        if href and not href.startswith(('#', 'javascript:', 'tel:', 'mailto:')):
                            full_url = normalize_url(href, base_url)
                            if is_same_domain(full_url, base_url):
                                pages.append({
                                    "url": full_url,
                                    "title": text or None,
                                    "source": PageSource.NAV,
                                    "selected": True,
                                })
                    except Exception:
                        continue

                browser.close()
        except Exception as e:
            logger.warning(f"Nav discovery failed for {base_url}: {e}")

        return pages

    def _crawl_bfs(
        self, base_url: str, seen: set, max_pages: int, max_depth: int
    ) -> list[dict]:
        """BFS crawl same-domain links."""
        pages = []
        queue = [(base_url, 0)]
        visited = set(seen)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                while queue and len(pages) < max_pages:
                    url, depth = queue.pop(0)
                    if depth > max_depth:
                        continue
                    norm = normalize_url(url)
                    if norm in visited:
                        continue
                    visited.add(norm)

                    try:
                        resp = page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
                        if not resp or resp.status >= 400:
                            continue

                        pages.append({
                            "url": norm,
                            "title": page.title() or None,
                            "source": PageSource.CRAWL,
                            "selected": True,
                        })

                        # Collect links for next level
                        if depth < max_depth:
                            links = page.locator('a[href]').all()
                            for link in links[:100]:  # Limit per page
                                try:
                                    href = link.get_attribute('href')
                                    if href and not href.startswith(('#', 'javascript:', 'tel:', 'mailto:')):
                                        full = normalize_url(href, url)
                                        if is_same_domain(full, base_url) and full not in visited:
                                            queue.append((full, depth + 1))
                                except Exception:
                                    continue

                    except Exception as e:
                        logger.debug(f"Crawl skip {url}: {e}")
                        continue

                browser.close()
        except Exception as e:
            logger.warning(f"BFS crawl failed: {e}")

        return pages

    def _should_exclude(self, url: str, rules: list[dict]) -> bool:
        """Check if a URL should be excluded based on rules."""
        path = urlparse(url).path.lower()
        for rule in rules:
            rule_type = rule.get("rule_type", "")
            rule_value = rule.get("rule_value", "")
            if rule_type == "url_contains" and rule_value.lower() in path:
                return True
            elif rule_type == "url_regex":
                try:
                    if re.search(rule_value, url, re.IGNORECASE):
                        return True
                except re.error:
                    continue
            elif rule_type == "path_blocklist" and rule_value.lower() in path:
                return True
        return False
