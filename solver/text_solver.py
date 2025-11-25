def solve_text_question(scraped: dict):
    text = scraped.get("question_text", "").lower()

    # Example simple patterns
    if "capital of france" in text:
        return {"answer": "Paris", "type": "text"}

    if "2+2" in text or "two plus two" in text:
        return {"answer": 4, "type": "text"}

    # Default fallback
    return {
        "answer": "Unable to determine text answer",
        "type": "text"
    }
