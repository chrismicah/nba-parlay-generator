import argparse
from pathlib import Path
from typing import Dict

import pandas as pd


DEFAULT_CRED: Dict[str, float] = {
    # High-cred insiders/reporters
    "wojespn": 0.99,
    "ShamsCharania": 0.99,
    "Underdog__NBA": 0.95,
    # Solid reporters/analysts
    "ChrisBHaynes": 0.92,
    "Marc_DAmico": 0.85,
    "SteveJonesJr": 0.85,
    # Fantasy/betting oriented
    "Rotoworld_BK": 0.80,
    "danbesbris": 0.78,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Append author credibility scores to tweets dataset")
    p.add_argument(
        "--in-csv",
        type=str,
        default=str(Path("data/tweets/nba_tweets_expanded_dataset.csv")),
        help="Input CSV path",
    )
    p.add_argument(
        "--out-csv",
        type=str,
        default=str(Path("data/tweets/nba_tweets_expanded_dataset_with_cred.csv")),
        help="Output CSV path",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_path = Path(args.in_csv)
    out_path = Path(args.out_csv)

    if not in_path.exists():
        print(f"❌ Input not found: {in_path}")
        return

    df = pd.read_csv(in_path)
    if "author" not in df.columns:
        print("❌ Missing 'author' column in input CSV")
        return

    def score_for(author: str) -> float:
        if not isinstance(author, str):
            return 0.5
        return DEFAULT_CRED.get(author, 0.6)

    df["author_credibility"] = df["author"].apply(score_for)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ Wrote: {out_path} (rows={len(df)})")


if __name__ == "__main__":
    main()



