from playwright.sync_api import sync_playwright
import os
from config import PLAYWRIGHT_BROWSERS_PATH
import json
import re


def clean_text(text):
    if isinstance(text, str):
        # Replace \n with space and remove multiple spaces
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_json(data):
    if isinstance(data, dict):
        return {k: clean_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json(item) for item in data]
    else:
        return clean_text(data)


def scrape_tds_data():
    # Configure browser path for Conda environment
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        # Navigate to main page
        page.goto(
            "https://tds.s-anand.net/#/2025-01/",
            wait_until="networkidle",
            timeout=60000
        )

        # Wait for sidebar to load
        page.wait_for_selector("aside.sidebar", state="attached", timeout=15000)

        # Extract sidebar links with hierarchy
        sidebar_links = page.evaluate('''() => {
            const links = [];
            document.querySelectorAll('aside.sidebar .sidebar-nav a').forEach(a => {
                const hierarchy = [];
                let current = a.closest('li');

                while(current) {
                    const folderTitle = current.querySelector('.folder-title');
                    if(folderTitle) {
                        hierarchy.unshift(folderTitle.textContent.trim());
                    }
                    current = current.parentElement.closest('li');
                }

                links.push({
                    href: a.getAttribute('href'),
                    title: a.textContent.trim(),
                    hierarchy: hierarchy
                });
            });
            return links;
        }''')

        print(f"Found {len(sidebar_links)} content pages to scrape")

        # Scrape each content page
        for idx, link in enumerate(sidebar_links):
            print(f"\nScraping ({idx + 1}/{len(sidebar_links)}): {link['title']}")

            # Navigate using hash directly
            page.evaluate(f"window.location.hash = '{link['href']}'")

            # Wait for content update
            try:
                page.wait_for_function('''() => {
                    const article = document.querySelector('article.markdown-section');
                    return article && article.innerHTML.length > 100;
                }''', timeout=15000)
            except:
                print(f"  Timed out waiting for content: {link['title']}")
                continue

            # Extract content
            content = page.query_selector('article.markdown-section').inner_text()
            links_in_content = page.eval_on_selector_all('article.markdown-section a', '''elements => 
                elements.map(a => ({
                    text: a.textContent.trim(),
                    url: a.href
                }))
            ''')

            # Store results
            results.append({
                "title": link['title'],
                "hierarchy": link['hierarchy'],
                "content": content.strip(),
                "links": links_in_content,
                "url": f"https://tds.s-anand.net/{link['href']}"
            })

        browser.close()

    results = clean_json(results)
    # Save results
    with open("course_content/cache/raw_data/tds_scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\nScraping completed. Data saved to tds_scraped_data.json")


if __name__ == "__main__":
    scrape_tds_data()
