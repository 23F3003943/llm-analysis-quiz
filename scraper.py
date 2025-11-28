from playwright.async_api import async_playwright
from urllib.parse import urljoin
import asyncio
import re


async def scrape_quiz_page(url: str):
    """
    Fully working Playwright scraper that:
    - waits for JS
    - waits for dynamic quiz text to load
    - extracts text from body + iframes
    - finds submit URL
    - finds downloadable files
    """

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load the page
        await page.goto(url, wait_until="domcontentloaded")

        # 🔥 WAIT for dynamic JavaScript content to appear (up to 5 sec)
        try:
            await page.wait_for_selector("#result, pre, body", timeout=5000)
        except:
            pass  # even if it fails, we still extract

        # Give JS extra time for rendering
        await asyncio.sleep(1.5)

        # Extract visible text
        try:
            body_text = await page.inner_text("body")
        except:
            body_text = ""

        submit_url = None
        file_links = []
        full_text = body_text or ""

        # ---------------------------------------
        # 🔥 Extract iframe content if present
        # ---------------------------------------
        for frame in page.frames:
            try:
                html = await frame.content()

                try:
                    text = await frame.inner_text("body")
                except:
                    text = ""
                full_text += "\n" + text

                # Try extracting submit URL
                if not submit_url:
                    s = extract_submit_url(html, frame.url)
                    if s:
                        submit_url = s

                # Scan links inside iframe
                links = await frame.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.href)"
                )
                for l in links:
                    if any(ext in l for ext in ["csv", "pdf", "xlsx", "json"]):
                        file_links.append(l)

            except:
                continue

        # ---------------------------------------
        # Fallback: scan main page HTML
        # ---------------------------------------
        if not submit_url:
            html = await page.content()
            submit_url = extract_submit_url(html, url)

        await browser.close()

        return {
            "question_text": full_text.strip()[:8000],
            "file_links": file_links,
            "submit_url": submit_url
        }


def extract_submit_url(html: str, base_url: str):
    """
    Extract submit URLs from main or iframe HTML.
    """
    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(\/submit)'
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            url = m.group(1) if m.groups() else m.group(0)
            clean = url.split("<")[0].strip()
            return urljoin(base_url, clean)

    return None
