# Import fine-tuning logic from the model trainer module
from backend.models.trainer import fine_tune_model

# Import DB connector (not used here but may be required for logging or tracking feedback)
from backend.db.connection import get_db

# SQLAlchemy session import (available for future use if DB feedback logging is added)
from sqlalchemy.orm import Session


# FeedbackLoopAgent is a simple module that accumulates user feedback
# and triggers model fine-tuning once a defined threshold is reached
class FeedbackLoopAgent:
    def __init__(self):
        # Internal buffer to store incoming feedback texts
        self.feedback_buffer = []

        # Number of feedback entries required to trigger training
        self.threshold = 5

    # Add a single feedback entry to the buffer
    def add_feedback(self, text: str):
        self.feedback_buffer.append(text)

        # If enough feedback is collected, initiate training
        if len(self.feedback_buffer) >= self.threshold:
            self._trigger_training()

    # Internal method that triggers fine-tuning and resets the buffer
    def _trigger_training(self):
        print("[brainzOS] Feedback threshold reached. Fine-tuning...")
        fine_tune_model(self.feedback_buffer)
        self.feedback_buffer.clear()


# Instantiate a global feedback agent to be reused across the system
feedback_agent = FeedbackLoopAgent()
