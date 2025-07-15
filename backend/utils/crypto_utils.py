import re
from collections import defaultdict

# === Address detection ===

def detect_wallet_addresses(text: str) -> list[str]:
    """
    Detect Ethereum and Solana-style wallet addresses in a text.
    """
    return re.findall(r"\b(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})\b", text)


def classify_wallet_address(addr: str) -> str:
    """
    Classify the wallet type based on structure.
    """
    if addr.startswith("0x") and len(addr) == 42:
        return "ethereum"
    elif re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", addr):
        return "solana"
    return "unknown"


# === Token detection ===

TOKEN_CATEGORIES = {
    "stablecoins": ["usdc", "usdt", "dai"],
    "layer1": ["eth", "sol", "btc", "avax"],
    "narratives": ["nft", "dao", "dex", "bridge", "zk", "liquid staking"]
}

def extract_tokens(text: str) -> list[str]:
    """
    Extract known crypto token or term mentions.
    """
    all_keywords = [kw for group in TOKEN_CATEGORIES.values() for kw in group]
    return [kw for kw in all_keywords if re.search(rf"\b{kw}\b", text, re.IGNORECASE)]


def classify_tokens(text: str) -> dict:
    """
    Return matched token keywords grouped by category.
    """
    matches = defaultdict(list)
    lower_text = text.lower()
    for category, terms in TOKEN_CATEGORIES.items():
        for token in terms:
            if re.search(rf"\b{re.escape(token)}\b", lower_text):
                matches[category].append(token)
    return dict(matches)


# === Composite detection ===

def has_crypto_context(text: str) -> bool:
    """
    Returns True if the text has either a wallet address or token reference.
    """
    return bool(detect_wallet_addresses(text)) or bool(extract_tokens(text))


def analyze_crypto_entities(text: str) -> dict:
    """
    Full context analysis with address type, tokens, and score.
    """
    addresses = detect_wallet_addresses(text)
    address_types = list({classify_wallet_address(addr) for addr in addresses})

    token_matches = extract_tokens(text)
    token_classification = classify_tokens(text)

    score = len(addresses) * 2 + len(token_matches)

    return {
        "wallets": addresses,
        "wallet_types": address_types,
        "tokens": token_matches,
        "token_categories": token_classification,
        "has_crypto": bool(addresses or token_matches),
        "score": score,
    }
