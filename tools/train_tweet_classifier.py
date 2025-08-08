import json
import os
from pathlib import Path
from typing import List, Dict

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments


LABELS = ["injury_news", "lineup_news", "general_commentary", "irrelevant"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}


class TweetsDataset(Dataset):
    def __init__(self, samples: List[Dict], tokenizer, max_length: int = 160):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        ex = self.samples[idx]
        text = ex["text"]
        label = LABEL2ID[ex["label"]]
        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item["labels"] = torch.tensor(label, dtype=torch.long)
        return item


def load_jsonl(path: Path) -> List[Dict]:
    samples: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("label") in LABELS and obj.get("text"):
                samples.append(obj)
    return samples


def main():
    data_path = Path("data/tweets/labeled_tweets.jsonl")
    out_dir = Path("models/tweet_classifier")
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_jsonl(data_path)
    if not samples:
        print("No labeled samples found. Add data to data/tweets/labeled_tweets.jsonl")
        return

    model_name = "roberta-base"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # Simple split
    split = max(1, int(0.8 * len(samples)))
    train_ds = TweetsDataset(samples[:split], tokenizer)
    eval_ds = TweetsDataset(samples[split:], tokenizer)

    args = TrainingArguments(
        output_dir=str(out_dir / "runs"),
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=2,
        learning_rate=5e-5,
        logging_steps=50,
    )

    trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
    trainer.train()

    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"✅ Model saved to {out_dir}")


if __name__ == "__main__":
    main()


