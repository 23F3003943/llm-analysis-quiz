import asyncio
from playwright.async_api import async_playwright

async def scrape_quiz_page(url: str):

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
    headless=False,
    args=["--no-sandbox", "--disable-setuid-sandbox"]
)
        page = await browser.new_page()

        print(f"🔎 Opening quiz page: {url}")

        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # -------------------------------------------
            # 1. Try reading NORMAL body content
            # -------------------------------------------
            try:
                body_text = await page.inner_text("body")
            except:
                body_text = ""

            # -------------------------------------------
            # 2. Check for IFRAMES (demo uses iframe!)
            # -------------------------------------------
            frames = page.frames
            frame_text = ""
            file_links = []
            submit_url = None

            for f in frames:
                try:
                    html = await f.content()

                    # Extract visible text
                    try:
                        text = await f.inner_text("body")
                    except:
                        text = html

                    frame_text += text + "\n"

                    # Extract all links in this frame
                    anchors = await f.query_selector_all("a")
                    for a in anchors:
                        href = await a.get_attribute("href")
                        if href and ("pdf" in href or "csv" in href or "json" in href):
                            file_links.append(href)

                    # Extract submit URL
                    if "submit" in html:
                        import re
                        urls = re.findall(r'https?://\S+', html)
                        for u in urls:
                            if "submit" in u:
                                submit_url = u
                                break

                except:
                    continue

            full_text = (body_text + "\n" + frame_text).strip()

        except Exception as e:
            await browser.close()
            return {
                "error": str(e),
                "question_text": None,
                "file_links": [],
                "submit_url": None
            }

        await browser.close()

        return {
            "question_text": full_text[:8000],  # limit size
            "file_links": file_links,
            "submit_url": submit_url
        }
