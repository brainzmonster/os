from transformers import AutoTokenizer
from backend.core.config import settings
import logging

logger = logging.getLogger("brainz")

# Internal singleton tokenizer instance
_tokenizer_instance = None
_tokenizer_meta = {}

def get_tokenizer():
    """
    Lazy-loads the tokenizer and caches it for reuse.
    Logs metadata upon first load.
    """
    global _tokenizer_instance, _tokenizer_meta
    if _tokenizer_instance is None:
        logger.info(f"[brainzOS] Loading tokenizer: {settings.MODEL_NAME}")
        _tokenizer_instance = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
        _tokenizer_meta = {
            "name": settings.MODEL_NAME,
            "vocab_size": _tokenizer_instance.vocab_size,
            "type": type(_tokenizer_instance).__name__
        }
        logger.info(f"[brainzOS] Tokenizer loaded ({_tokenizer_meta['type']}) — Vocab size: {_tokenizer_meta['vocab_size']}")
    return _tokenizer_instance

def get_tokenizer_metadata() -> dict:
    """
    Returns static metadata from the tokenizer instance (if loaded).
    """
    return _tokenizer_meta

def tokenize_text(text: str, padding: bool = False, truncation: bool = True, max_length: int = None) -> dict:
    """
    Tokenize a single string input into a PyTorch tensor-compatible dict.
    """
    tokenizer = get_tokenizer()
    kwargs = {
        "return_tensors": "pt",
        "truncation": truncation,
        "padding": "max_length" if padding else False
    }
    if max_length:
        kwargs["max_length"] = max_length
    return tokenizer(text, **kwargs)

def tokenize_batch(texts: list[str], padding: bool = True, truncation: bool = True, max_length: int = None) -> dict:
    """
    Tokenize a list of input strings in batch mode.
    """
    tokenizer = get_tokenizer()
    kwargs = {
        "return_tensors": "pt",
        "truncation": truncation,
        "padding": "max_length" if padding else "longest"
    }
    if max_length:
        kwargs["max_length"] = max_length
    return tokenizer(texts, **kwargs)

def count_tokens(text: str) -> int:
    """
    Returns number of tokens in a given input string.
    """
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))

def decode_tokens(token_ids: list[int]) -> str:
    """
    Decode a list of token IDs back to string.
    """
    tokenizer = get_tokenizer()
    return tokenizer.decode(token_ids, skip_special_tokens=True)
