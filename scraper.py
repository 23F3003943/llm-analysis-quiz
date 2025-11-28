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

        # Capture console logs (important for multistep-demo-v2)
        console_messages = []
        page.on("console", lambda msg: console_messages.append(str(msg)))

        # Load the page
        await page.goto(url, wait_until="domcontentloaded")

        # Allow JS to fully render
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1.5)

        # -------- Extract main visible text --------
        try:
            body_text = await page.inner_text("body")
        except:
            body_text = ""

        full_text = body_text.strip()

        submit_url = None
        file_links = []

        # ======================================================
        # HANDLE IFRAMES
        # ======================================================

        # Wait for iframes to load
        for _ in range(10):
            if len(page.frames) > 1:
                break
            await asyncio.sleep(0.2)

        for frame in page.frames:
            try:
                # Try reading text from iframe via normal Playwright call
                try:
                    frame_text = await frame.inner_text("body")
                except:
                    frame_text = ""

                # If empty → try JS extraction (works for blocked/cross-origin)
                if not (frame_text or "").strip():
                    try:
                        frame_text = await frame.evaluate(
                            "() => document.body && document.body.innerText"
                        )
                    except:
                        pass

                # If still empty → fallback to HTML → strip tags
                if not (frame_text or "").strip():
                    try:
                        html_dump = await frame.evaluate(
                            "() => document.body && document.body.innerHTML"
                        )
                        if html_dump:
                            frame_text = re.sub(r"<[^>]+>", "", html_dump)
                        else:
                            frame_text = ""
                    except:
                        frame_text = ""

                # Append clean iframe text
                text_clean = (frame_text or "").strip()
                if text_clean:
                    full_text += "\n" + text_clean

                # ---------- Detect submit URL in iframe ----------
                try:
                    frame_html = await frame.content()
                except:
                    frame_html = ""

                if not submit_url:
                    s = extract_submit_url(frame_html, frame.url)
                    if s:
                        submit_url = s

                # ---------- Detect file download links ----------
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

        # ======================================================
        # FALLBACK: CHECK MAIN PAGE HTML FOR SUBMIT URL
        # ======================================================
        if not submit_url:
            try:
                html = await page.content()
                submit_url = extract_submit_url(html, url)
            except:
                pass

        # ======================================================
        # Include console log messages (VERY IMPORTANT)
        # ======================================================
        if console_messages:
            full_text += "\n" + "\n".join(console_messages)

        await browser.close()

        return {
            "question_text": full_text[:8000],  # safe limit
            "file_links": file_links,
            "submit_url": submit_url
        }


# ======================================================
# SUBMIT URL EXTRACTION
# ======================================================
def extract_submit_url(html: str, base_url: str):
    if not html:
        return None

    # Several patterns used by TDS pages
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
            # Get the URL
            candidate = m.group(1) if m.groups() else m.group(0)

            # Clean HTML noise
            clean = candidate.split("<")[0].strip()

            # Join relative paths if needed
            return urljoin(base_url, clean)

    return None
