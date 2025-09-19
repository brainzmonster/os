from datasets import Dataset
from typing import List, Dict, Optional, Any, Callable
import logging

from backend.utils.text_cleaner import full_clean  # optional cleaning if available

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

    Parameters
    ----------
    texts : List[str]
        Raw text samples to be tokenized.
    tokenizer :
        Any HuggingFace-compatible tokenizer with `__call__` signature.
    clean : bool
        If True, apply `full_clean` to each sample before tokenization.
    min_length : int
        Filter out samples with fewer than `min_length` word tokens (whitespace-split).
    max_length : Optional[int]
        If set, pass as tokenizer `max_length` (hard cap on sequence length).
    add_metadata : Optional[List[Dict[str, Any]]]
        Optional parallel metadata; keys of the first element are added as parallel columns.
    padding : str
        Tokenizer padding strategy: "max_length" or "longest".
    truncate : bool
        If True, enable tokenizer truncation.
    log_stats : bool
        If True, log basic stats about filtering and tokenization.

    Returns
    -------
    Dataset
        A HuggingFace Dataset with tokenized fields (e.g., input_ids, attention_mask).
    """

    # --- clean and filter texts (idempotent; keeps original signature intact) ---
    original_count = len(texts)
    if clean:
        texts = [full_clean(t) for t in texts]

    filtered = [t for t in texts if len(t.split()) >= min_length]
    if log_stats:
        logger.info(f"[Tokenizer] Loaded {original_count} examples → {len(filtered)} after filtering.")

    # --- compose dataset dictionary (supports parallel metadata columns) ---
    data = {"text": filtered}
    if add_metadata:
        # only add metadata keys that exist consistently across the list
        # this avoids KeyErrors if some rows omit fields
        stable_keys = set(add_metadata[0].keys())
        for row in add_metadata[1:]:
            stable_keys &= set(row.keys())
        for k in stable_keys:
            data[k] = [meta[k] for meta in add_metadata]

    # --- convert to HF dataset ---
    dataset = Dataset.from_dict(data)

    # --- tokenization wrapper (vectorized over a batch of rows) ---
    def tokenize_function(examples):
        kwargs = {
            "truncation": truncate,
            "padding": padding
        }
        if max_length:
            kwargs["max_length"] = max_length

        return tokenizer(examples["text"], **kwargs)

    # --- apply tokenization in batch ---
    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    if log_stats and len(tokenized_dataset) > 0:
        sample = tokenized_dataset[0]
        token_count = len(sample.get("input_ids", []))
        logger.info(f"[Tokenizer] First tokenized sample → {token_count} tokens")

    return tokenized_dataset


# -----------------------------------------------------------------------------
# NEW: supervised fine-tuning (sft) helper that builds a dataset from pairs
# -----------------------------------------------------------------------------
def build_sft_dataset(
    pairs: List[Dict[str, str]],
    tokenizer,
    prompt_key: str = "prompt",
    completion_key: str = "completion",
    clean: bool = False,
    min_length: int = 3,
    max_length: Optional[int] = None,
    padding: str = "max_length",
    truncate: bool = True,
    log_stats: bool = True,
    # template allows you to control how prompt/completion are serialized for LM training
    template: Optional[Callable[[str, str], str]] = None,
    include_special_tokens: bool = True,
):
    """
    Build a tokenized dataset for SFT (prompt → completion pairs), on top of `get_training_dataset`.

    This keeps your existing pipeline intact while adding a convenient path for
    pair-wise training data (chat-style, instruction tuning, etc.).

    Parameters
    ----------
    pairs : List[Dict[str, str]]
        List of records containing at least {prompt_key, completion_key}.
    tokenizer :
        HF tokenizer; used both for special tokens lookup and tokenization.
    prompt_key : str
        Key name inside each record that holds the user prompt.
    completion_key : str
        Key name inside each record that holds the target completion.
    clean : bool
        If True, apply `full_clean` to prompt and completion before formatting.
    min_length : int
        Minimum number of whitespace-separated tokens required (applied after formatting).
    max_length : Optional[int]
        If set, passed to tokenizer for truncation length.
    padding : str
        Tokenizer padding strategy: "max_length" or "longest".
    truncate : bool
        Pass `truncation=True/False` to tokenizer.
    log_stats : bool
        Log basic dataset construction stats.
    template : Optional[Callable[[str, str], str]]
        If provided, called as `template(prompt, completion)` → formatted string.
        If None, use a sensible default chat-style format.
    include_special_tokens : bool
        If True, prepend/append tokenizer BOS/EOS tokens (if available) for better LM conditioning.

    Returns
    -------
    Dataset
        Tokenized Dataset ready for Trainer.
    """

    if log_stats:
        logger.info(f"[SFT] Building dataset from {len(pairs)} prompt→completion pairs")

    # default template: chat-style serialization (LLM-friendly)
    # example:
    #   <bos><|user|>: ...\n<|assistant|>: ...<eos>
    def _default_template(p: str, c: str) -> str:
        bos = tokenizer.bos_token if include_special_tokens and hasattr(tokenizer, "bos_token") else ""
        eos = tokenizer.eos_token if include_special_tokens and hasattr(tokenizer, "eos_token") else ""
        return f"{bos}<|user|>: {p}\n<|assistant|>: {c}{eos}"

    fmt = template or _default_template

    # serialize pairs → flat text samples
    serialized_texts: List[str] = []
    metadata: List[Dict[str, Any]] = []

    for i, rec in enumerate(pairs):
        prompt = rec.get(prompt_key, "")
        completion = rec.get(completion_key, "")

        if clean:
            prompt = full_clean(prompt)
            completion = full_clean(completion)

        text = fmt(prompt, completion)
        serialized_texts.append(text)

        # carry over extra fields (tags, source, etc.) as metadata columns if present
        extra = {k: v for k, v in rec.items() if k not in (prompt_key, completion_key)}
        metadata.append(extra if extra else {"_row_id": i})

    # delegate tokenization to the canonical path (keeps behavior consistent)
    ds = get_training_dataset(
        texts=serialized_texts,
        tokenizer=tokenizer,
        clean=False,  # already cleaned above if requested
        min_length=min_length,
        max_length=max_length,
        add_metadata=metadata if any(metadata) else None,
        padding=padding,
        truncate=truncate,
        log_stats=log_stats,
    )

    if log_stats:
        logger.info(f"[SFT] final sft dataset size: {len(ds)} rows")

    return ds
