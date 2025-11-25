import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin


def extract_submit_url(html: str, base_url: str):
    """
    Detect submit URL patterns inside JS / JSON / script blocks.
    """
    patterns = [
        r'https://tds-llm-analysis\.s-anand\.net/submit\S*',
        r'"submit"\s*:\s*"([^"]+)"',
        r"'submit'\s*:\s*'([^']+)'",
        r'POST this JSON to\s+(\S+)'
    ]

    for p in patterns:
        match = re.search(p, html)
        if match:
            url = match.group(1) if match.groups() else match.group(0)
            return urljoin(base_url, url)

    return None


def scrape_quiz_page(url: str):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        body_text = soup.get_text("\n").strip()

        full_text = body_text
        file_links = []
        submit_url = None

        # --- Find iframes ---
        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src")
            if not src:
                continue

            iframe_url = urljoin(url, src)

            try:
                iframe_resp = requests.get(iframe_url, timeout=20)
                iframe_resp.raise_for_status()

                iframe_html = iframe_resp.text
                iframe_soup = BeautifulSoup(iframe_html, "html.parser")

                # Add iframe visible text
                iframe_text = iframe_soup.get_text("\n").strip()
                full_text += "\n" + iframe_text

                # ---- Detect submit URL inside iframe ----
                if not submit_url:
                    submit_url = extract_submit_url(iframe_html, iframe_url)

                # ---- Extract downloadable file links ----
                for a in iframe_soup.find_all("a", href=True):
                    href = urljoin(iframe_url, a["href"])
                    if any(ext in href for ext in ["csv", "pdf", "xlsx", "json"]):
                        file_links.append(href)

            except Exception:
                continue

        # As fallback, detect submit URL in main page HTML
        if not submit_url:
            submit_url = extract_submit_url(resp.text, url)

        # --- CLEAN SUBMIT URL (important!) ---
        if submit_url:
            submit_url = submit_url.split("<")[0].strip()
            submit_url = submit_url.split('"')[0].strip()
            submit_url = submit_url.split("'")[0].strip()
            submit_url = submit_url.replace("&lt;", "").replace("&gt;", "")

        return {
            "question_text": full_text[:8000],
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
