import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def scrape_quiz_page(url: str):
    try:
        print(f"🔎 Fetching quiz page: {url}")

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # -------------------------------
        # Extract main page text
        # -------------------------------
        body_text = soup.get_text(separator="\n").strip()

        # -------------------------------
        # Detect iframes containing quiz
        # -------------------------------
        full_text = body_text
        file_links = []
        submit_url = None

        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src")
            if not src:
                continue

            iframe_url = urljoin(url, src)

            try:
                iframe_resp = requests.get(iframe_url, timeout=20)
                iframe_resp.raise_for_status()

                iframe_soup = BeautifulSoup(iframe_resp.text, "html.parser")

                # Append iframe text
                iframe_text = iframe_soup.get_text(separator="\n").strip()
                full_text += "\n" + iframe_text

                # Extract file links
                for a in iframe_soup.find_all("a", href=True):
                    href = a["href"]
                    full_href = urljoin(iframe_url, href)

                    if any(ext in href for ext in ["pdf", "csv", "json", "xlsx"]):
                        file_links.append(full_href)

                # Extract submit URL
                for f in iframe_soup.find_all("form"):
                    action = f.get("action")
                    if action and "submit" in action:
                        submit_url = urljoin(iframe_url, action)

            except Exception as e:
                print("⚠️ iframe error:", e)
                continue

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
