from playwright.async_api import async_playwright
from urllib.parse import urljoin
import asyncio
import re


async def scrape_quiz_page(url: str):

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # --- CAPTURE CONSOLE OUTPUT (CRITICAL FOR demo-v2) ---
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text()))

        # Load page
        await page.goto(url, wait_until="networkidle")

        # Wait for JS logs (demo-v2 loads content late)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Extract visible text
        try:
            body_text = await page.inner_text("body")
        except:
            body_text = ""

        # Combine visible text + console logs
        full_text = body_text + "\n" + "\n".join(console_messages)

        submit_url = None
        file_links = []

        # ---------- IFRAME PROCESSING ----------
        for frame in page.frames:
            try:
                html = await frame.content()
                text = await frame.inner_text("body")
                full_text += "\n" + text

                # detect submit URL
                if not submit_url:
                    s = extract_submit_url(html, frame.url)
                    if s:
                        submit_url = s

                # detect downloadable files
                links = await frame.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.href)"
                )
                for l in links:
                    if any(ext in l for ext in ["csv", "pdf", "xlsx", "json"]):
                        file_links.append(l)

            except:
                continue

        # ---------- FALLBACK SUBMIT URL ----------
        if not submit_url:
            html = await page.content()
            submit_url = extract_submit_url(html, url)

        await browser.close()

        return {
            "question_text": full_text[:8000],
            "file_links": file_links,
            "submit_url": submit_url,
        }


def extract_submit_url(html: str, base_url: str):
    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(\/submit)',
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            url = m.group(1) if m.groups() else m.group(0)
            clean = url.split("<")[0].strip()
            return urljoin(base_url, clean)

    return None
