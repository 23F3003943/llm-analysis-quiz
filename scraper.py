import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def scrape_quiz_page(url: str):
    """
    Full Playwright scraper. Renders JS, returns question_text, file_links, submit_url.
    """

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle")

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Extract visible text
        question_text = soup.get_text("\n").strip()

        # Extract file links
        file_links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if any(ext in href for ext in ["csv", "pdf", "xlsx", "json"]):
                file_links.append(href)

        # Extract submit URL (search entire HTML)
        submit_url = None
        patterns = [
            r"https://tds-llm-analysis\.s-anand\.net/submit\S*",
            r"/submit"
        ]
        for p in patterns:
            match = re.search(p, html)
            if match:
                raw = match.group(0)
                submit_url = urljoin(url, raw.split("<")[0])
                break

        await browser.close()

        return {
            "question_text": question_text,
            "file_links": file_links,
            "submit_url": submit_url
        }
