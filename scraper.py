from playwright.async_api import async_playwright
from urllib.parse import urljoin
import asyncio
import re

# ======================================================
# FINAL MAX-COMPAT SCRAPER (NETWORK + IFRAME + JS)
# ======================================================

async def scrape_quiz_page(url: str):
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await browser.new_page()

        # STORE HTML from all network responses
        network_html = []

        page.on("response", lambda resp: asyncio.create_task(capture_response(resp, network_html)))

        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)

        full_text = ""

        # DOM TEXT ---------------------------------------
        try:
            t1 = await page.inner_text("body")
            if t1:
                full_text += t1.strip() + "\n"
        except:
            pass

        try:
            t2 = await page.evaluate("() => document.body.innerText")
            if t2:
                full_text += t2.strip() + "\n"
        except:
            pass

        # SHADOW DOM TEXT ---------------------------------------
        try:
            shadow_txt = await page.evaluate("""
                () => {
                    function getAllText(node) {
                        let out = "";
                        function walk(n) {
                            if (!n) return;
                            if (n.nodeType === Node.TEXT_NODE) out += n.textContent + "\\n";
                            if (n.shadowRoot) walk(n.shadowRoot);
                            for (const c of n.childNodes) walk(c);
                        }
                        walk(node);
                        return out;
                    }
                    return getAllText(document.body);
                }
            """)
            if shadow_txt:
                full_text += shadow_txt.strip() + "\n"
        except:
            pass

        # IFRAMES ---------------------------------------
        for frame in page.frames:
            try:
                ftxt = await frame.evaluate("() => document.body.innerText")
                if ftxt:
                    full_text += ftxt.strip() + "\n"
            except:
                pass

        # NETWORK HTML ---------------------------------------
        for html in network_html:
            text_only = clean_html(html)
            if text_only.strip():
                full_text += text_only.strip() + "\n"

        # SUBMIT URL ---------------------------------------
        submit_url = extract_submit_url_from_all(full_text, network_html, url)

        await browser.close()

        return {
            "question_text": full_text[:8000].strip(),
            "file_links": extract_file_links(network_html),
            "submit_url": submit_url
        }


# ======================================================
# CAPTURE NETWORK RESPONSES
# ======================================================

async def capture_response(resp, bucket):
    try:
        ct = resp.headers.get("content-type", "")
        if "text/html" in ct:
            body = await resp.text()
            if body:
                bucket.append(body)
    except:
        pass


# ======================================================
# CLEAN HTML → TEXT
# ======================================================

def clean_html(html: str):
    if not html:
        return ""
    text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


# ======================================================
# EXTRACT SUBMIT URL
# ======================================================

def extract_submit_url_from_all(full_text: str, html_list, base_url: str):
    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(https?://[^\s]+)',
        r'POST this JSON to\s+(\/submit\S*)'
    ]

    # search in combined text
    text_sources = [full_text] + html_list

    for src in text_sources:
        if not src:
            continue
        for p in patterns:
            m = re.search(p, src)
            if m:
                candidate = m.group(1) if m.groups() else m.group(0)
                return urljoin(base_url, candidate.strip())

    return None


# ======================================================
# EXTRACT FILE LINKS
# ======================================================

def extract_file_links(html_list):
    links = []
    for html in html_list:
        found = re.findall(r'href="([^"]+)"', html)
        for l in found:
            if any(ext in l for ext in ["csv", "pdf", "xlsx", "json"]):
                links.append(l)
    return links
