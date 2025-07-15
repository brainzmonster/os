import uuid
import logging
from datetime import datetime
from backend.models.trainer import fine_tune_model
from backend.db.connection import get_db
from backend.services.analytics_service import get_most_common_prompts

class AutoTrainer:
    def __init__(
        self,
        threshold: int = 10,
        batch_size: int = 50,
        dry_run: bool = False,
        include_completions: bool = False
    ):
        self.threshold = threshold
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.include_completions = include_completions

        self.logger = logging.getLogger("AutoTrainer")
        logging.basicConfig(level=logging.INFO)

    def analyze_and_train(self) -> dict:
        session_id = str(uuid.uuid4())
        self.logger.info(f"[{session_id}] Starting auto-training analysis...")

        try:
            # Fetch prompt usage data
            prompts = get_most_common_prompts(limit=self.batch_size)

            # Filter prompts based on usage threshold
            qualified = [
                p for p in prompts if p.get("count", 0) >= self.threshold
            ]

            if not qualified:
                self.logger.info(f"[{session_id}] No prompts met training threshold.")
                return {
                    "session": session_id,
                    "status": "skipped",
                    "qualified": 0,
                    "trained": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }

            if self.include_completions:
                training_data = [
                    {"prompt": p["prompt"], "completion": p.get("completion", "")}
                    for p in qualified
                ]
            else:
                training_data = [p["prompt"] for p in qualified]

            self.logger.info(f"[{session_id}] Qualified prompts: {len(training_data)}")

            # Run training
            if not self.dry_run:
                fine_tune_model(training_data)
                self.logger.info(f"[{session_id}] Fine-tuning complete.")
            else:
                self.logger.info(f"[{session_id}] Dry-run mode enabled. Training skipped.")

            return {
                "session": session_id,
                "status": "trained" if not self.dry_run else "dry-run",
                "qualified": len(training_data),
                "trained": len(training_data) if not self.dry_run else 0,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"[{session_id}] Error during auto-training: {str(e)}")
            return {
                "session": session_id,
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def set_threshold(self, new_threshold: int):
        self.threshold = new_threshold
        self.logger.info(f"[AutoTrainer] Threshold updated to {new_threshold}")

    def set_dry_run(self, dry_run: bool):
        self.dry_run = dry_run
        self.logger.info(f"[AutoTrainer] Dry-run mode set to {dry_run}")


# Initialize the auto-training engine
auto_trainer = AutoTrainer()
