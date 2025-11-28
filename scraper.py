from playwright.async_api import async_playwright
from urllib.parse import urljoin
import asyncio
import re

# ======================================================
# FINAL SCRAPER — FULLY COMPATIBLE WITH ALL QUIZ TYPES
# ======================================================

async def scrape_quiz_page(url: str):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text()))

        # Load the page
        await page.goto(url, wait_until="domcontentloaded")

        # Wait for JS to finish rendering
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # ------- Extract main page text -------
        try:
            body_text = await page.inner_text("body")
        except:
            body_text = ""

        full_text = body_text.strip()

        submit_url = None
        file_links = []

        # ============= IFRAME HANDLING =============
        # Wait for iframes to load
        for _ in range(10):
            if len(page.frames) > 1:
                break
            await asyncio.sleep(0.3)

        # Go through all frames
        for frame in page.frames:
            try:
                # Wait for frame content
                try:
                    await frame.wait_for_load_state("domcontentloaded", timeout=1500)
                except:
                    pass

                # Attempt to extract text
                try:
                    frame_text = await frame.inner_text("body")
                except:
                    frame_text = ""

                if frame_text.strip():
                    full_text += "\n" + frame_text.strip()

                # Extract HTML of frame to detect submit URL
                try:
                    frame_html = await frame.content()
                except:
                    frame_html = ""

                # Detect submit URL
                if not submit_url:
                    s = extract_submit_url(frame_html, frame.url)
                    if s:
                        submit_url = s

                # Extract file links
                try:
                    links = await frame.eval_on_selector_all(
                        "a[href]", "els => els.map(e => e.href)"
                    )
                    for l in links:
                        if any(ext in l for ext in ["csv", "pdf", "xlsx", "json"]):
                            file_links.append(l)
                except:
                    pass

            except:
                continue

        # ============= FALLBACK SUBMIT URL (MAIN PAGE) =============
        if not submit_url:
            try:
                main_html = await page.content()
                submit_url = extract_submit_url(main_html, url)
            except:
                pass

        # ============= CONSOLE LOG TEXT =============
        if console_messages:
            full_text += "\n" + "\n".join(console_messages)

        await browser.close()

        return {
            "question_text": full_text[:8000],   # limit size
            "file_links": file_links,
            "submit_url": submit_url
        }


# ======================================================
# SUBMIT URL DETECTION
# ======================================================
def extract_submit_url(html: str, base_url: str):
    if not html:
        return None

    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(https?://[^\s]+)',
        r'POST this JSON to\s+(\/submit\S*)'
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            candidate = m.group(1) if m.groups() else m.group(0)
            clean = candidate.split("<")[0].strip()
            return urljoin(base_url, clean)

    return None
