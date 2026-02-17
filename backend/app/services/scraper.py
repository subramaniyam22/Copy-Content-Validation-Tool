import asyncio
import re
import html2text
# from playwright.async_api import async_playwright
from typing import List, Dict

class ScraperService:
    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = True
        self.h2t.ignore_images = True
        self.h2t.ignore_emphasis = False
        self.h2t.body_width = 0
        self.h2t.skip_internal_links = True
        self.h2t.ignore_tables = True

    def extract_paragraphs(self, text, is_markdown=False):
        paragraphs = []
        current_content = []
        
        # print("Extracting paragraphs...")
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                if current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        paragraphs.append(content)
                    current_content = []
                continue
            
            if is_markdown and re.match(r'^(#{1,6})\s+(.+)$', line):
                if current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        paragraphs.append(content)
                    current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            content = ' '.join(current_content).strip()
            if content:
                paragraphs.append(content)
        
        return paragraphs

    def _scrape_sync(self, base_url: str, menu_options: List[str]) -> List[Dict]:
        results = []
        nav_pattern = re.compile(r'^(floor plans|photo gallery|amenities|pet friendly|neighborhood|map \s*\+ directions|contact us|schedule a tour|residents|$100 off|apply now)$', re.IGNORECASE)
        
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            for menu_option in menu_options:
                # Slugify the menu option
                slug = menu_option.strip().lower().replace(' ', '-')
                url = f"{base_url.rstrip('/')}/{slug}"
                
                print(f"Scraping: {url}")
                
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=60000)
                    if response and response.status == 404:
                        print(f"WARNING: 404 Not Found for {url}")
                        results.append({
                            "page_name": menu_option,
                            "url": url,
                            "paragraphs": [{"heading": "Error", "content": "404 Not Found"}]
                        })
                        continue
                    
                    selectors = [
                        'main h1, main h2, main h3, main h4, main h5, main h6, main p, main ul, main li',
                        'article h1, article h2, article h3, article h4, article h5, article h6, article p, article ul, article li',
                        '[role="main"] h1, [role="main"] h2, [role="main"] h3, [role="main"] h4, [role="main"] h5, [role="main"] h6',
                        '[role="main"] p, [role="main"] ul, [role="main"] li',
                        '.content h1, .content h2, .content p, .content ul, .content li',
                        '#content h1, #content h2, #content p, #content ul, #content li',
                        '.main h1, .main h2, .main p, .main ul, .main li',
                        'div[class*="content"] h1, div[class*="content"] p',
                        'div[class*="main"] h1, div[class*="main"] p'
                    ]
                    
                    combined_selector = ', '.join(selectors)
                    
                    elements = page.locator(combined_selector).filter(
                        has_not=page.locator('footer, .footer, #footer, [class*="footer"], [id*="footer"], '
                                            'header, .header, #header, [class*="header"], [id*="header"], nav, .nav, .menu')
                    ).all()
                    
                    # Fallback to body if semantic parsing failed
                    if not elements:
                        print(f"Semantic selectors failed for {url}, trying fallback...")
                        elements = page.locator('body h1, body h2, body p, body ul, body li').filter(
                             has_not=page.locator('footer, .footer, #footer, [class*="footer"], [id*="footer"], '
                                            'header, .header, #header, [class*="header"], [id*="header"], nav, .nav, .menu')
                        ).all()

                    print(f"Found {len(elements)} elements on {url}")
                    
                    current_heading = None
                    current_content = []
                    paragraphs = []
                    
                    for element in elements:
                        tag = element.evaluate('el => el.tagName.toLowerCase()')
                        text = element.inner_text()
                        text = text.strip()
                        print(f"DEBUG Element: {tag} - '{text[:30]}...'")
                        if not text:
                            print("  Skipping: Empty text")
                            continue
                        if nav_pattern.match(text):
                            print("  Skipping: Nav pattern match")
                            continue
                            
                        if tag in ['h1', 'h2']:
                            if 'cookie' in text.lower():
                                continue
                            
                            if current_heading and current_content:
                                content_text = '\n'.join(current_content)
                                paragraph_content = self.extract_paragraphs(content_text, is_markdown=True)
                                if paragraph_content:
                                    paragraphs.append({
                                        "heading": current_heading,
                                        "content": paragraph_content[0]
                                    })
                                current_content = []
                            current_heading = text
                        elif tag == 'ul':
                            current_content.append(f"\n{text}\n")
                        elif tag == 'li':
                            current_content.append(f"- {text}")
                        else:
                            current_content.append(text)
                    
                    # Process remaining
                    if current_heading and current_content:
                        content_text = '\n'.join(current_content)
                        paragraph_content = self.extract_paragraphs(content_text, is_markdown=True)
                        if paragraph_content:
                            paragraphs.append({
                                "heading": current_heading,
                                "content": paragraph_content[0]
                            })
                    elif current_content and not current_heading:
                        content_text = '\n'.join(current_content)
                        paragraph_content = self.extract_paragraphs(content_text, is_markdown=True)
                        if paragraph_content:
                            paragraphs.append({
                                "heading": None,
                                "content": paragraph_content[0]
                            })
                    
                    results.append({
                        "page_name": menu_option,
                        "url": url,
                        "paragraphs": paragraphs
                    })
                    
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
                    results.append({
                        "page_name": menu_option,
                        "url": url,
                        "paragraphs": []
                    })
            
            browser.close()
        return results

    async def scrape_urls(self, base_url: str, menu_options: List[str]) -> List[Dict]:
        return await asyncio.to_thread(self._scrape_sync, base_url, menu_options)
