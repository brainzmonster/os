import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# Define global config object
class Settings:
    # Project metadata
    PROJECT_NAME: str = "brainzOS"
    VERSION: str = "0.1.0"

    # Environment and mode
    ENV: str = os.getenv("ENV", "local")
    MODE: str = os.getenv("MODE", "dev")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Model configuration
    MODEL_NAME: str = os.getenv("MODEL_NAME", "tiiuae/falcon-rw-1b")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 100))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.7))

    # Database connection
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://brainz:synthpass@localhost/brainzdb")

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DEST: str = os.getenv("LOG_DEST", "stdout")

    # Feature flags
    ENABLE_AGENTS: bool = os.getenv("ENABLE_AGENTS", "true").lower() == "true"
    ENABLE_MEMORY: bool = os.getenv("ENABLE_MEMORY", "true").lower() == "true"

    # Optional external API keys
    OPENAI_KEY: str = os.getenv("OPENAI_KEY", "")
    HUGGINGFACE_KEY: str = os.getenv("HUGGINGFACE_KEY", "")

    # Runtime session identifiers
    SESSION_ID: str = str(uuid.uuid4())
    START_TIME: str = datetime.utcnow().isoformat()

    # Utility: export config to dict/json
    def to_dict(self) -> dict:
        return {
            "project": self.PROJECT_NAME,
            "version": self.VERSION,
            "env": self.ENV,
            "mode": self.MODE,
            "debug": self.DEBUG,
            "model_name": self.MODEL_NAME,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE,
            "database_url": self.DATABASE_URL,
            "log_level": self.LOG_LEVEL,
            "log_dest": self.LOG_DEST,
            "agents_enabled": self.ENABLE_AGENTS,
            "memory_enabled": self.ENABLE_MEMORY,
            "session_id": self.SESSION_ID,
            "start_time": self.START_TIME,
            "has_openai_key": bool(self.OPENAI_KEY),
            "has_huggingface_key": bool(self.HUGGINGFACE_KEY)
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Global singleton
settings = Settings()
