import os
import torch
from datetime import datetime
from transformers import (
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    EarlyStoppingCallback,
)
from backend.models.loader import load_model
from backend.data.dataset import get_training_dataset
from backend.core.config import settings
from backend.data.cleaner import full_clean


def fine_tune_model(
    train_texts: list[str],
    epochs: int = 1,
    batch_size: int = 2,
    save_total_limit: int = 2,
    use_early_stopping: bool = True,
    patience: int = 3
):
    print("[brainzOS] Starting fine-tuning...")

    # Load model and tokenizer
    llm = load_model()
    model = llm["model"]
    tokenizer = llm["tokenizer"]

    # Clean text
    train_texts = [full_clean(t) for t in train_texts if t and len(t.strip()) > 3]
    if not train_texts:
        raise ValueError("[brainzOS] No valid training texts provided.")

    print(f"[brainzOS] Loaded {len(train_texts)} training samples.")

    # Get tokenized dataset
    train_dataset = get_training_dataset(train_texts, tokenizer)
    print(f"[brainzOS] First sample token length: {len(train_dataset[0]['input_ids'])}")

    # Device check
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[brainzOS] Using device: {device}")

    # Timestamped output path
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/fine_tuned_{timestamp}"
    os.makedirs(output_path, exist_ok=True)

    # Training config
    args = TrainingArguments(
        output_dir=output_path,
        overwrite_output_dir=True,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        save_steps=10,
        save_total_limit=save_total_limit,
        logging_dir=os.path.join(output_path, "logs"),
        logging_steps=5,
        evaluation_strategy="no",
        report_to="none",  # disable W&B etc.
        fp16=torch.cuda.is_available(),
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )

    callbacks = []
    if use_early_stopping:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=patience))

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=callbacks
    )

    # Begin training
    train_output = trainer.train()
    train_loss = train_output.training_loss

    print(f"[brainzOS] Fine-tuning complete. Final loss: {train_loss:.4f}")
    print(f"[brainzOS] Model saved to: {output_path}")

    return {
        "model": model,
        "loss": train_loss,
        "output_path": output_path,
    }
