import re
from collections import defaultdict
from backend.utils.tokenizer import count_tokens  # Optional

# Define categorized technical terms
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

# Flatten the terms for simple lookup
ALL_TECH_TERMS = set(term for terms in TECH_CATEGORIES.values() for term in terms)

# Extract all matching technologies from the input
def extract_technologies(text: str, custom_terms: list[str] = None) -> list[str]:
    if custom_terms:
        combined = ALL_TECH_TERMS.union(set(custom_terms))
    else:
        combined = ALL_TECH_TERMS

    return [term for term in combined if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)]

# Categorized tech extraction with scores and grouping
def extract_tech_metadata(text: str, custom_terms: list[str] = None) -> dict:
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

# Determine if the input is technical with a soft threshold
def is_technical(text: str, min_score: int = 1) -> bool:
    return extract_tech_metadata(text)["score"] >= min_score
