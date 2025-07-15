from transformers import pipeline
from functools import lru_cache
import logging
import uuid
from typing import List, Dict, Optional, Union


class PromptOptimizer:
    def __init__(
        self,
        model_name: str = "facebook/bart-large-mnli",
        enable_logging: bool = True,
        confidence_threshold: float = 0.2
    ):
        # Load the zero-shot classifier
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_name
        )
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold

        # Configure logging
        self.logger = logging.getLogger("PromptOptimizer")
        if enable_logging:
            logging.basicConfig(level=logging.INFO)

    @lru_cache(maxsize=128)
    def _cached_score(self, prompt: str, label_tuple: tuple) -> Dict[str, float]:
        labels = list(label_tuple)
        result = self.classifier(prompt, candidate_labels=labels)
        return {
            label: score
            for label, score in zip(result["labels"], result["scores"])
        }

    def score_prompt(
        self,
        prompt: str,
        labels: Optional[List[str]] = None,
        return_filtered: bool = False,
        session_id: Optional[str] = None
    ) -> Dict[str, float]:
        if labels is None:
            labels = ["relevant", "irrelevant", "technical", "off-topic"]

        if session_id is None:
            session_id = str(uuid.uuid4())

        label_tuple = tuple(labels)
        raw_scores = self._cached_score(prompt, label_tuple)

        if self.logger:
            self.logger.info(f"[{session_id}] Scored prompt: \"{prompt}\" → {raw_scores}")

        # Optionally filter results based on confidence threshold
        if return_filtered:
            filtered = {
                label: score for label, score in raw_scores.items()
                if score >= self.confidence_threshold
            }
            return dict(sorted(filtered.items(), key=lambda x: x[1], reverse=True))

        return dict(sorted(raw_scores.items(), key=lambda x: x[1], reverse=True))

    def batch_score(
        self,
        prompts: List[str],
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, float]]:
        return [self.score_prompt(prompt, labels) for prompt in prompts]

    def switch_model(self, new_model: str):
        """Dynamically switch the underlying model at runtime"""
        self.classifier = pipeline("zero-shot-classification", model=new_model)
        self.model_name = new_model
        self.logger.info(f"Switched PromptOptimizer model to: {new_model}")


# Global instance for use across the system
optimizer = PromptOptimizer()
