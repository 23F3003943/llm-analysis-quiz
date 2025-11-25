# solver/math_solver.py

import re
import pandas as pd
import requests
from io import StringIO

def extract_numbers(text: str):
    """
    Pull all numbers from the question text.
    """
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    return [float(x) for x in nums]

def solve_math(text: str):
    """
    Solves simple math questions:
    - sum
    - mean/average
    - count
    - difference
    """
    text_lower = text.lower()
    nums = extract_numbers(text)

    if not nums:
        return {
            "question_type": "math_table",
            "error": "No numeric values detected"
        }

    # SUM
    if "sum" in text_lower or "total" in text_lower or "add" in text_lower:
        return {
            "question_type": "math_table",
            "operation": "sum",
            "numbers": nums,
            "answer": sum(nums)
        }

    # AVERAGE
    if "mean" in text_lower or "average" in text_lower:
        return {
            "question_type": "math_table",
            "operation": "average",
            "numbers": nums,
            "answer": sum(nums) / len(nums)
        }

    # COUNT
    if "how many" in text_lower or "count" in text_lower:
        return {
            "question_type": "math_table",
            "operation": "count",
            "numbers": nums,
            "answer": len(nums)
        }

    # FALLBACK
    return {
        "question_type": "math_table",
        "error": "Could not determine math operation",
        "numbers": nums
    }
