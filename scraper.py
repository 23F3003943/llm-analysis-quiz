from playwright.async_api import async_playwright
from urllib.parse import urljoin
import re

async def scrape_quiz_page(url: str):
    """
    Fully-rendered scraper with JS execution + iframe extraction.
    """

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture JS console logs (debug)
        page.on("console", lambda msg: print("PAGE LOG:", msg.text()))

        # Go to page & wait for JS
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1500)  # let JS finish

        # Extract full text of main page
        try:
            full_text = await page.inner_text("body")
        except:
            full_text = ""

        html_main = await page.content()

        submit_url = extract_submit_url(html_main, url)
        file_links = extract_file_links(page)

        # Extract from iframes too
        for frame in page.frames:
            try:
                frame_text = await frame.inner_text("body")
                full_text += "\n" + frame_text

                frame_html = await frame.content()
                if not submit_url:
                    submit_url = extract_submit_url(frame_html, frame.url)

                links = await frame.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.href)"
                )

                for link in links:
                    if any(ext in link for ext in ["csv", "pdf", "xlsx", "json"]):
                        file_links.append(link)

            except:
                continue

        await browser.close()

        return {
            "question_text": full_text.strip()[:8000],
            "file_links": list(set(file_links)),
            "submit_url": submit_url
        }


def extract_file_links(page):
    """Extract all CSV / PDF / XLSX links from main page."""
    async def _extract():
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)"
        )
        return [l for l in links if any(ext in l for ext in ["csv", "pdf", "xlsx", "json"])]
    try:
        return page.context.loop.run_until_complete(_extract())
    except:
        return []


def extract_submit_url(html: str, base_url: str):
    """Find quiz submit url."""
    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(https?://[^\s"<]+)',
        r'action="([^"]*submit[^"]*)"'
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            url = m.group(1) if m.groups() else m.group(0)
            clean = url.split("<")[0].strip()
            return urljoin(base_url, clean)

    return None
