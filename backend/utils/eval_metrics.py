import numpy as np
import evaluate

# Load HuggingFace evaluation metrics
bleu = evaluate.load("bleu")
rouge = evaluate.load("rouge")
f1_metric = evaluate.load("f1")
meteor = evaluate.load("meteor")
accuracy = evaluate.load("accuracy")  # For exact string match (optional use case)

# Optional: Perplexity (if using precomputed log-likelihoods)
# perplexity = evaluate.load("perplexity")

# === Core Metric Computation ===

def compute_bleu(preds: list[str], refs: list[str]) -> float:
    return bleu.compute(predictions=preds, references=[[r] for r in refs])['bleu']

def compute_rouge(preds: list[str], refs: list[str]) -> dict:
    return rouge.compute(predictions=preds, references=refs)

def compute_f1(preds: list[str], refs: list[str]) -> float:
    return f1_metric.compute(predictions=preds, references=refs)['f1']

def compute_meteor(preds: list[str], refs: list[str]) -> float:
    return meteor.compute(predictions=preds, references=refs)['meteor']

def compute_accuracy(preds: list[str], refs: list[str]) -> float:
    return accuracy.compute(predictions=preds, references=refs)['accuracy']

# === Token-level stats ===

def token_overlap(pred: str, ref: str) -> float:
    p_tokens = set(pred.lower().split())
    r_tokens = set(ref.lower().split())
    if not p_tokens or not r_tokens:
        return 0.0
    return len(p_tokens & r_tokens) / len(p_tokens | r_tokens)

def compute_token_overlap(preds: list[str], refs: list[str]) -> float:
    scores = [token_overlap(p, r) for p, r in zip(preds, refs)]
    return np.mean(scores)

# === Model Evaluation ===

def evaluate_model(preds: list[str], refs: list[str], verbose: bool = False) -> dict:
    if verbose:
        print(f"[Eval] Evaluating {len(preds)} predictions...")

    results = {
        "bleu": round(compute_bleu(preds, refs), 4),
        "f1": round(compute_f1(preds, refs), 4),
        "meteor": round(compute_meteor(preds, refs), 4),
        "accuracy": round(compute_accuracy(preds, refs), 4),
        "token_overlap": round(compute_token_overlap(preds, refs), 4),
    }

    rouge_scores = compute_rouge(preds, refs)
    for k, v in rouge_scores.items():
        results[k] = round(v, 4)

    if verbose:
        avg_pred_len = np.mean([len(p.split()) for p in preds])
        avg_ref_len = np.mean([len(r.split()) for r in refs])
        print(f"[Eval] Avg prediction length: {avg_pred_len:.1f}")
        print(f"[Eval] Avg reference length: {avg_ref_len:.1f}")

    return results
