import argparse
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

LABELS = ["injury_news", "lineup_news", "general_commentary", "irrelevant"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--model-dir", default="models/tweet_classifier")
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)

    enc = tokenizer(args.text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        out = model(**enc)
        probs = out.logits.softmax(dim=-1).squeeze(0)
        conf, idx = torch.max(probs, dim=-1)
        label = LABELS[idx.item()]
        print(f"label={label}\tconfidence={conf.item():.3f}")


if __name__ == "__main__":
    main()


