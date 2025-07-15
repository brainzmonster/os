# brainzOS-wide constants and default settings

# === Generation Defaults ===
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 100
DEFAULT_MODEL_NAME = "tiiuae/falcon-rw-1b"
DEFAULT_TOP_K = 5

# === Feedback & Training Thresholds ===
DEFAULT_FEEDBACK_THRESHOLD = 5           # Prompts needed for feedback-triggered fine-tuning
DEFAULT_AUTO_TRAIN_THRESHOLD = 10        # Usage count required for auto-training
DEFAULT_MEMORY_EXPIRY_SECONDS = 3600     # Time after which memory entries are considered stale

# === Inference / Agent Limits ===
MAX_BATCH_SIZE = 32                      # Max prompts per training batch
MAX_RETRIES = 3                          # Retry attempts for model calls or API failures
MAX_EMBEDDING_LENGTH = 512               # Embedding truncation limit

# === System Roles & Content Tags ===
SYSTEM_ROLES = ["user", "assistant", "system"]
SYSTEM_ROLE_ALIASES = {
    "u": "user",
    "a": "assistant",
    "s": "system"
}

CONTENT_TAGS = [
    "crypto", "tech", "code", "general", "feedback", "security", "ai", "web3", "data"
]

TAG_PRIORITIES = {
    "crypto": 10,
    "tech": 8,
    "code": 9,
    "feedback": 5,
    "general": 1
}

# === Prompt Evaluation ===
MIN_PROMPT_WORDS = 4                     # Filter threshold for noisy or low-effort prompts
MIN_PROMPT_SCORE = 0.3                   # Minimum semantic score for training eligibility

# === Vector Search Settings ===
VECTOR_DIMENSIONS = 768                  # Default embedding vector size
VECTOR_DISTANCE_METRIC = "cosine"        # Supported: cosine, euclidean, dot

# === System Messages ===
MSG_NO_PROMPTS = "[!] No valid prompts available."
MSG_TRAINING_STARTED = "[✓] Training process started..."
MSG_TRAINING_COMPLETE = "[✓] Training completed successfully."
MSG_MODEL_LOADING = "[~] Loading model: {}"
MSG_ERROR_GENERIC = "[✗] An error occurred. Please check logs."

# === Registry Keys ===
REGISTRY_MODEL = "llm_model"
REGISTRY_TOKENIZER = "llm_tokenizer"
REGISTRY_ENGINE = "inference_engine"
REGISTRY_MEMORY = "semantic_memory"
REGISTRY_VECTOR_DB = "vector_store"
