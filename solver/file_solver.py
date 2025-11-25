import requests
import pandas as pd
import pdfplumber
from io import BytesIO

def download_file(url: str):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.content


def solve_file_question(scraped: dict):
    """
    Detect CSV/PDF from scraped["file_links"], download it,
    extract content, return a simple computed answer.
    """

    file_links = scraped.get("file_links", [])
    if not file_links:
        return {"answer": "No file links found", "type": "file"}

    file_url = file_links[0]  # use first link
    raw = download_file(file_url)

    # --- CSV CASE ---
    if file_url.endswith(".csv"):
        df = pd.read_csv(BytesIO(raw))
        summary = df.describe().to_dict()
        return {
            "answer": "csv-summary",
            "summary": summary,
            "type": "file"
        }

    # --- PDF CASE ---
    if file_url.endswith(".pdf"):
        with pdfplumber.open(BytesIO(raw)) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text()

        return {
            "answer": text[:500],
            "type": "file"
        }

    return {"answer": "Unsupported file type", "type": "file"}
