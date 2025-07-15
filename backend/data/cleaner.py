import re
import string
import html
import unicodedata

# Define a basic stopword list (extendable)
DEFAULT_STOPWORDS = {"the", "a", "an", "is", "and", "of", "in", "to", "for"}

# === Cleaning Utilities ===

def clean_text(text: str) -> str:
    """
    Basic text cleaning:
    - Strip whitespace
    - Lowercase
    - Remove extra spaces
    - Remove punctuation
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text

def remove_code_blocks(text: str) -> str:
    """Remove Markdown-style code blocks (```...```)"""
    return re.sub(r"```[\s\S]*?```", "", text)

def remove_urls(text: str) -> str:
    """Remove HTTP/HTTPS URLs"""
    return re.sub(r"https?://\S+", "", text)

def remove_html_tags(text: str) -> str:
    """Strip HTML/XML tags and decode entities"""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)

def remove_emojis(text: str) -> str:
    """Remove emoji and symbol unicode ranges"""
    return re.sub(r"[\U00010000-\U0010FFFF]", "", text)

def remove_control_chars(text: str) -> str:
    """Remove control/non-printable unicode characters"""
    return "".join(c for c in text if unicodedata.category(c)[0] != "C")

def remove_stopwords(text: str, stopwords: set = DEFAULT_STOPWORDS) -> str:
    """Remove common stopwords from the text"""
    return " ".join(word for word in text.split() if word not in stopwords)

def normalize_language(text: str, lang: str = "en") -> str:
    """
    Placeholder for language-specific normalization (e.g. de -> umlaut handling)
    """
    if lang == "de":
        text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    return text

# === Combined Cleaning ===

def full_clean(
    text: str,
    remove_html: bool = True,
    remove_emoji: bool = True,
    remove_stop: bool = False,
    lang: str = "en"
) -> str:
    """
    Full cleaning pipeline (configurable).
    """
    text = remove_code_blocks(text)
    text = remove_urls(text)
    if remove_html:
        text = remove_html_tags(text)
    if remove_emoji:
        text = remove_emojis(text)
    text = remove_control_chars(text)
    text = normalize_language(text, lang=lang)
    text = clean_text(text)
    if remove_stop:
        text = remove_stopwords(text)
    return text

# === Utility ===

def count_tokens(text: str) -> int:
    """Count approximate token count (word-based)"""
    return len(text.split())
