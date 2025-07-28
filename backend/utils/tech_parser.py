import re
from collections import defaultdict
from backend.utils.tokenizer import count_tokens  # Optional, counts tokens if available

# Predefined technical categories with associated keywords
TECH_CATEGORIES = {
    "blockchain": [
        "solana", "ethereum", "blockchain", "wallet", "token", "smart contract", "hash", "ledger", "web3", "defi",
    ],
    "dev": [
        "node.js", "react", "api", "graphql", "rpc", "ganache", "docker",
    ],
    "ai": [
        "llm", "prompt", "embedding", "vector", "transformer", "agent"
    ],
    "wallets": [
        "metamask", "phantom", "keplr", "trust wallet"
    ]
}

# Flatten all terms into a single set for fast lookup
ALL_TECH_TERMS = set(term for terms in TECH_CATEGORIES.values() for term in terms)

# Match all known or custom-defined terms found in the input text
def extract_technologies(text: str, custom_terms: list[str] = None) -> list[str]:
    """
    Returns a list of all recognized tech terms found in the input.
    Custom terms can be passed to expand matching scope.
    """
    if custom_terms:
        combined = ALL_TECH_TERMS.union(set(custom_terms))
    else:
        combined = ALL_TECH_TERMS

    return [term for term in combined if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)]

# Analyze input text and return metadata about detected technologies
def extract_tech_metadata(text: str, custom_terms: list[str] = None) -> dict:
    """
    Returns a dict with category-wise matches, total score, and token count.
    """
    text_lower = text.lower()
    found = defaultdict(list)

    for category, keywords in TECH_CATEGORIES.items():
        for term in keywords:
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                found[category].append(term)

    flat_terms = [t for terms in found.values() for t in terms]
    score = len(flat_terms)

    return {
        "score": score,
        "matched_terms": flat_terms,
        "categories": dict(found),
        "token_count": count_tokens(text) if "count_tokens" in globals() else len(text.split())
    }

# Soft classification of input as technical or not
def is_technical(text: str, min_score: int = 1) -> bool:
    """
    Returns True if the text meets or exceeds the technical threshold.
    """
    return extract_tech_metadata(text)["score"] >= min_score

# NEW FUNCTION: Count how many keywords from each category appear
def extract_category_summary(text: str) -> dict:
    """
    Generate a summary count of each tech category based on terms found in the input.
    Useful for analytics, dashboards, or filtering logic.
    """
    text_lower = text.lower()
    summary = {}

    for category, keywords in TECH_CATEGORIES.items():
        matches = [
            term for term in keywords if re.search(rf"\b{re.escape(term)}\b", text_lower)
        ]
        summary[category] = len(matches)

    return summary
