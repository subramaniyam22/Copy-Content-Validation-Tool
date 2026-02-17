import sys
import os

# Ensure backend directory is in path
sys.path.append(os.getcwd())

from app.services.scraper import ScraperService

def test_scraper():
    print("Testing scraper...")
    scraper = ScraperService()
    # Test the specific URL the user was transforming: https://www.sunridgehotels.com/contact
    # Note: Scraper appends menu option to base url.
    # Base: https://www.sunridgehotels.com/
    # Option: contact
    
    results = scraper._scrape_sync("https://www.sunridgehotels.com/", ["contact"])
    
    for page in results:
        print(f"Page: {page['page_name']}")
        print(f"URL: {page['url']}")
        print(f"Paragraphs found: {len(page['paragraphs'])}")
        if page['paragraphs']:
            print("First paragraph excerpt:", page['paragraphs'][0]['content'][:100])
        else:
            print("No content found.")

if __name__ == "__main__":
    test_scraper()
