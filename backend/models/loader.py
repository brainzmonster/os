from transformers import AutoModelForCausalLM, AutoTokenizer
from backend.models.adapter import apply_adapter
from backend.core.config import settings
import torch
import logging
import sys

logger = logging.getLogger("brainz.model")

MODEL_NAME = settings.MODEL_NAME

def _log_model_info(model):
    total_params = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"[brainzaOS] Model architecture: {type(model).__name__}")
    logger.info(f"[brainzaOS] Total parameters: {total_params:,}")
    logger.info(f"[brainzaOS] Trainable parameters: {trainable:,}")

def load_model():
    """
    Load a causal language model and tokenizer, apply adapters, 
    and place on the best available device.
    """
    logger.info("[brainzaOS] Loading language model...")

    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        
        # Handle FP16 or bfloat16 if CUDA is available
        torch_dtype = None
        if torch.cuda.is_available():
            if getattr(settings, "LOAD_FP16", True):
                torch_dtype = torch.float16
            elif getattr(settings, "LOAD_BFLOAT16", False):
                torch_dtype = torch.bfloat16

        # Load model
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch_dtype,
            device_map="auto" if torch.cuda.is_available() else None,
        )

        # Apply adapters (LoRA, quantization, etc.)
        model = apply_adapter(model)
        model.eval()

        # Move to device explicitly if not using auto device_map
        if not hasattr(model, "device") or model.device.type == "cpu":
            if torch.cuda.is_available():
                model = model.to("cuda")
                logger.info("[brainzaOS] Model moved to CUDA manually")
            else:
                logger.info("[brainzaOS] Model will run on CPU")

        # Report model info
        _log_model_info(model)

        # GPU info
        if torch.cuda.is_available():
            mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info(f"[brainzaOS] GPU memory available: {mem:.2f} GB")

        return {"model": model, "tokenizer": tokenizer}

    except Exception as e:
        logger.error(f"[brainzaOS] Failed to load model: {e}")
        sys.exit(1)
