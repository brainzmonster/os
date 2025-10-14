from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache
from typing import List, Tuple, Dict, Union, Optional

# Load the embedding model once (process-wide singleton)
_model = SentenceTransformer("all-MiniLM-L6-v2")

# =====================================================================
#                           Embedding Utilities
# =====================================================================

@lru_cache(maxsize=1024)
def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """
    Embed a single string using sentence-transformers, with optional L2 normalization.

    Args:
        text: Input text to embed.
        normalize: If True, return a unit-length vector (recommended for cosine).

    Returns:
        np.ndarray: 1D embedding vector.
    """
    vec = _model.encode(text, convert_to_numpy=True)
    if normalize:
        vec = vec / (np.linalg.norm(vec) + 1e-10)
    return vec


def embed_batch(texts: List[str], normalize: bool = True) -> np.ndarray:
    """
    Embed a list of strings in batch mode.

    Args:
        texts: List of input texts.
        normalize: If True, return unit-length vectors row-wise.

    Returns:
        np.ndarray: 2D array with shape (len(texts), dim).
    """
    vecs = _model.encode(texts, convert_to_numpy=True)
    if normalize:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
        vecs = vecs / norms
    return vecs

# =====================================================================
#                       Similarity / Distance Metrics
# =====================================================================

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Returns:
        float in [-1, 1], higher means more similar.
    """
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return float(dot / (norm1 * norm2 + 1e-10))


def dot_product(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute raw dot product (useful if vectors already normalized).
    """
    return float(np.dot(vec1, vec2))


def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute L2 distance.
    """
    return float(np.linalg.norm(vec1 - vec2))

# =====================================================================
#                           Similarity Search
# =====================================================================

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
      - corpus as List[str] (keys == values) or Dict[id -> text]
      - 'cosine', 'dot', or 'euclidean' (euclidean is inverted to act as similarity)
      - score filtering via 'min_score'
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
            return -euclidean_distance(a, b)  # invert so "higher is better"
        else:
            raise ValueError(f"Unknown metric: {metric}")

    scored = []
    for key, text in entries:
        vec = embed_text(text, normalize=normalize)
        score = score_fn(query_vec, vec)
        if score >= min_score:
            scored.append((key, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

# =====================================================================
#                                Utility
# =====================================================================

def count_tokens(text: str) -> int:
    """
    Approximate token count using whitespace-based tokenization.
    NOTE: This is only a rough heuristic for UI/analytics; not model-accurate.
    """
    return len(text.split())

# =====================================================================
#                      NEW: Semantic De-duplication
# =====================================================================

def semantic_deduplicate(
    texts: List[str],
    threshold: float = 0.92,
    normalize: bool = True,
) -> List[str]:
    """
    Remove near-duplicate texts based on semantic similarity.

    This keeps the first occurrence of a message and drops later entries that are
    semantically "too close" (similarity >= threshold) to any previously kept item.
    Useful for:
      - Cleaning prompt logs before training
      - Avoiding redundant memory inserts
      - Curating datasets on-the-fly

    Args:
        texts: Ordered list of candidate strings.
        threshold: Cosine similarity cutoff for considering two items duplicates.
        normalize: Whether to L2-normalize embeddings (recommended for cosine).

    Returns:
        List[str]: Filtered texts in original order with near-duplicates removed.
    """
    if not texts:
        return []

    kept_texts: List[str] = []
    kept_vecs: Optional[np.ndarray] = None  # Will store embeddings of kept items

    # Pre-compute embeddings in one go for efficiency
    all_vecs = embed_batch(texts, normalize=normalize)

    for idx, (t, vec) in enumerate(zip(texts, all_vecs)):
        if kept_vecs is None or kept_vecs.size == 0:
            # First item is always kept
            kept_texts.append(t)
            kept_vecs = vec.reshape(1, -1)
            continue

        # Compute cosine similarity against all previously kept vectors
        # (Assumes unit vectors if normalize=True; falls back to normalized dot)
        sims = kept_vecs @ vec if normalize else (kept_vecs @ vec) / (
            np.linalg.norm(kept_vecs, axis=1) * (np.linalg.norm(vec) + 1e-10) + 1e-10
        )

        # If any kept item is too similar, skip this one
        if np.max(sims) >= threshold:
            continue

        # Otherwise keep it and append its vector
        kept_texts.append(t)
        kept_vecs = np.vstack([kept_vecs, vec])

    return kept_texts
