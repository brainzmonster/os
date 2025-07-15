import re
import string
from typing import List, Optional

# === Core Cleaning Utilities ===

def clean_text(text: str) -> str:
    """
    Normalize whitespace and remove excessive line breaks.
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text

# === Extractors ===

def extract_code_snippets(text: str) -> List[str]:
    """
    Extract code blocks from Markdown (```code```), multiline-safe.
    """
    return re.findall(r"```[\s\S]*?```", text)

def extract_code_languages(text: str) -> List[str]:
    """
    Extract language tags from code blocks, e.g. ```python
    """
    return re.findall(r"```([a-zA-Z0-9]+)", text)

def extract_links(text: str) -> List[str]:
    """
    Return all HTTP/HTTPS URLs.
    """
    return re.findall(r"https?://\S+", text)

def extract_emails(text: str) -> List[str]:
    """
    Find all email addresses in the text.
    """
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)

def extract_html_tags(text: str) -> List[str]:
    """
    Return all HTML tag matches (e.g., <div>, </p>)
    """
    return re.findall(r"<[^>]+>", text)

# === Validators ===

def is_valid_prompt(text: str, min_length: int = 4, min_alpha: int = 1) -> bool:
    """
    Validate prompt length and presence of alphanumeric content.
    """
    text = text.strip()
    alnum_count = sum(c.isalnum() for c in text)
    return len(text) >= min_length and alnum_count >= min_alpha

def score_prompt_quality(text: str) -> float:
    """
    Heuristic quality score: based on length, alpha ratio, and structure.
    """
    text = text.strip()
    if not text:
        return 0.0
    alpha_ratio = sum(c.isalpha() for c in text) / len(text)
    length_score = min(len(text) / 300, 1.0)
    return round(0.6 * alpha_ratio + 0.4 * length_score, 3)

def detect_language_heuristic(text: str) -> Optional[str]:
    """
    Naive language heuristic based on character frequency.
    Returns: 'en', 'de', 'unknown'
    """
    text = text.lower()
    if any("ß" in text or "ä" in text or "ö" in text or "ü" in text for c in text):
        return "de"
    elif any(word in text for word in ("the", "and", "is", "this", "that")):
        return "en"
    return "unknown"
