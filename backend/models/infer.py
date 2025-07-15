import torch
import time
from backend.core.engine import engine
from backend.data.cleaner import full_clean  # NEU

def generate_response(
    prompt: str,
    max_tokens: int = 100,
    temperature: float = 0.7,
    top_k: int = 50,
    top_p: float = 0.95,
    repetition_penalty: float = 1.1,
    num_beams: int = 1,
    return_metadata: bool = False,
    return_cleaned: bool = False,
):
    """
    Generate a response from the loaded LLM with optional generation config.

    Args:
        prompt (str): Input prompt
        max_tokens (int): Max tokens to generate
        temperature (float): Sampling temperature
        top_k (int): Top-k sampling cutoff
        top_p (float): Nucleus sampling probability
        repetition_penalty (float): Penalty for repeated tokens
        num_beams (int): Beam search (set to 1 for greedy)
        return_metadata (bool): If True, return additional stats
        return_cleaned (bool): If True, apply post-cleaning to output

    Returns:
        str or dict: Response or response + metadata
    """

    llm = engine.get_model()
    model = llm["model"]
    tokenizer = llm["tokenizer"]

    cleaned_prompt = full_clean(prompt)

    device = model.device if torch.cuda.is_available() else torch.device("cpu")

    inputs = tokenizer(cleaned_prompt, return_tensors="pt").to(device)

    if inputs["input_ids"].shape[1] > 1024:
        print(f"[brainzOS] Warning: prompt length ({inputs['input_ids'].shape[1]}) may exceed context window.")

    start = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            num_beams=num_beams,
            do_sample=True if num_beams == 1 else False
        )
    end = time.time()

    raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    final_output = full_clean(raw_output) if return_cleaned else raw_output

    if return_metadata:
        return {
            "response": final_output,
            "tokens_generated": len(outputs[0]),
            "latency": round(end - start, 3),
            "prompt_length": inputs["input_ids"].shape[1],
            "device": str(device),
        }

    return final_output
