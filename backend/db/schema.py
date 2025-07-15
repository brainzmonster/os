from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache
from typing import List, Tuple, Dict, Union, Optional

# Load the embedding model once
_model = SentenceTransformer("all-MiniLM-L6-v2")

# === Embedding Utilities ===

@lru_cache(maxsize=1024)
def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """
    Embed a single string using sentence-transformers, with optional L2 normalization.
    """
    vec = _model.encode(text, convert_to_numpy=True)
    if normalize:
        vec = vec / (np.linalg.norm(vec) + 1e-10)
    return vec

def embed_batch(texts: List[str], normalize: bool = True) -> np.ndarray:
    """
    Embed a list of strings in batch mode.
    """
    vecs = _model.encode(texts, convert_to_numpy=True)
    if normalize:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
        vecs = vecs / norms
    return vecs

# === Similarity Computation ===

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return float(dot / (norm1 * norm2 + 1e-10))

def dot_product(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return float(np.dot(vec1, vec2))

def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return float(np.linalg.norm(vec1 - vec2))

# === Similarity Search ===

def most_similar(
    query: str,
    corpus: Union[List[str], Dict[str, str]],
    top_k: int = 5,
    normalize: bool = True,
    min_score: float = 0.0,
    metric: str = "cosine"
) -> List[Tuple[str, float]]:
    """
    Return the top-k most similar entries from a corpus given a query string.

    Supports:
    - corpus as List[str] or Dict[id -> text]
    - cosine, dot, or euclidean distance
    - score filtering
    """
    query_vec = embed_text(query, normalize=normalize)

    if isinstance(corpus, dict):
        entries = corpus.items()
    else:
        entries = [(text, text) for text in corpus]

    def score_fn(a, b):
        if metric == "cosine":
            return cosine_similarity(a, b)
        elif metric == "dot":
            return dot_product(a, b)
        elif metric == "euclidean":
            return -euclidean_distance(a, b)  # invert for similarity sorting
        else:
            raise ValueError(f"Unknown metric: {metric}")

    scored = []
    for key, text in entries:
        vec = embed_text(text, normalize=normalize)
        score = score_fn(query_vec, vec)
        if score >= min_score:
            scored.append((key, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

# === Utility ===

def count_tokens(text: str) -> int:
    """
    Approximate token count using whitespace-based tokenization.
    """
    return len(text.split())
