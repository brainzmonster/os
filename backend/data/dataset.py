from datasets import Dataset
from typing import List, Dict, Optional, Any
import logging

from backend.utils.text_cleaner import full_clean  # Optional cleaning if available

logger = logging.getLogger("brainz")

def get_training_dataset(
    texts: List[str],
    tokenizer,
    clean: bool = False,
    min_length: int = 5,
    max_length: Optional[int] = None,
    add_metadata: Optional[List[Dict[str, Any]]] = None,
    padding: str = "max_length",  # or "longest"
    truncate: bool = True,
    log_stats: bool = True
):
    """
    Create a HuggingFace-compatible tokenized dataset from raw texts.
    """

    # Clean and filter texts
    original_count = len(texts)
    if clean:
        texts = [full_clean(t) for t in texts]

    filtered = [t for t in texts if len(t.split()) >= min_length]
    if log_stats:
        logger.info(f"[Tokenizer] Loaded {original_count} examples → {len(filtered)} after filtering.")

    # Compose dataset dictionary
    data = {"text": filtered}
    if add_metadata:
        for k in add_metadata[0].keys():
            data[k] = [meta[k] for meta in add_metadata]

    # Convert to HF dataset
    dataset = Dataset.from_dict(data)

    # Tokenization wrapper
    def tokenize_function(examples):
        kwargs = {
            "truncation": truncate,
            "padding": padding
        }
        if max_length:
            kwargs["max_length"] = max_length

        return tokenizer(examples["text"], **kwargs)

    # Apply tokenization in batch
    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    if log_stats:
        sample = tokenized_dataset[0]
        token_count = len(sample["input_ids"]) if "input_ids" in sample else 0
        logger.info(f"[Tokenizer] First tokenized sample → {token_count} tokens")

    return tokenized_dataset
