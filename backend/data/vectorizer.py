from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple, Union, Dict, Optional
from functools import lru_cache

# Load pre-trained sentence transformer (MiniLM for fast inference)
_model = SentenceTransformer("all-MiniLM-L6-v2")

# === Text Embedding ===

@lru_cache(maxsize=512)
def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """Generate a semantic embedding from a single text input."""
    vec = _model.encode(text, convert_to_numpy=True)
    return vec / np.linalg.norm(vec) if normalize else vec

def embed_batch(texts: List[str], normalize: bool = True) -> np.ndarray:
    """Generate embeddings for a batch of texts."""
    vecs = _model.encode(texts, convert_to_numpy=True)
    if normalize:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-10
        vecs = vecs / norms
    return vecs

# === Cosine Similarity ===

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return float(np.clip(dot / (norm1 * norm2 + 1e-10), -1.0, 1.0))

# === Similarity Matching ===

def most_similar(
    query: str,
    corpus: Union[List[str], Dict[str, str]],
    top_k: int = 5,
    min_score: float = 0.0,
    normalize: bool = True
) -> List[Tuple[str, float]]:
    """
    Return top-k most similar texts (or IDs) from a corpus given a query.

    corpus can be:
    - List[str] of raw texts
    - Dict[str, str] where keys are metadata IDs and values are texts
    """
    query_vec = embed_text(query, normalize=normalize)

    if isinstance(corpus, dict):
        items = corpus.items()
    else:
        items = [(text, text) for text in corpus]

    results = []
    for key, text in items:
        score = cosine_similarity(query_vec, embed_text(text, normalize=normalize))
        if score >= min_score:
            results.append((key, score))

    return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
