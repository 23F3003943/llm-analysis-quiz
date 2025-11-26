import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import re


async def extract_submit_url(html: str, base_url: str):
    """
    Extract /submit endpoint from JS-rendered HTML.
    Handles broken tags, base64, JSON inline, multi-line text, etc.
    """
    patterns = [
        r"https://tds-llm-analysis\.s-anand\.net/submit",
        r"/submit",
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r"POST this JSON to\s+(/submit)"
    ]

    for p in patterns:
        match = re.search(p, html, flags=re.IGNORECASE)
        if match:
            url = match.group(1) if match.groups() else match.group(0)
            return urljoin(base_url, url)

    return None


async def render_iframe_content(page, iframe_url):
    """Render an iframe URL separately using Playwright."""
    iframe_page = await page.context.new_page()
    await iframe_page.goto(iframe_url, wait_until="networkidle")

    html = await iframe_page.content()
    text = await iframe_page.inner_text("body")

    await iframe_page.close()
    return html, text


async def scrape_quiz_page(url: str):
    """
    FULL Playwright JS-rendered scraper.
    Loads the page, renders all JavaScript, extracts:
    - Question text
    - Iframe text + files
    - Submit URL
    """

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Load the page
            await page.goto(url, wait_until="networkidle")
            html = await page.content()
            text = await page.inner_text("body")

            file_links = []
            submit_url = None

            # Extract iframes
            frames = page.frames
            for frame in frames:
                if frame.url == url:
                    continue  # skip main frame

                iframe_url = frame.url
                iframe_html = await frame.content()
                iframe_text = await frame.inner_text("body")

                # append iframe text to main text
                text += "\n" + iframe_text

                # detect submit URL
                if not submit_url:
                    submit_url = await extract_submit_url(iframe_html, iframe_url)

                # extract downloadable file links from iframe
                for link in await frame.eval_on_selector_all("a", "elements => elements.map(e => e.href)"):
                    if any(ext in link for ext in ["csv", "pdf", "xlsx", "json"]):
                        file_links.append(link)

            # Fallback: detect submit URL in main HTML
            if not submit_url:
                submit_url = await extract_submit_url(html, url)

            # Clean submit URL
            if submit_url:
                submit_url = submit_url.split("<")[0].strip().split('"')[0].split("'")[0]

            await browser.close()

        return {
            "question_text": text[:8000],
            "file_links": file_links,
            "submit_url": submit_url
        }

    except Exception as e:
        return {
            "error": str(e),
            "question_text": None,
            "file_links": [],
            "submit_url": None
        }
