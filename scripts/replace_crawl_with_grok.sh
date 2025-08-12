#!/usr/bin/env bash
set -euo pipefail

echo "Installing xai-sdk…"
pip install --quiet xai-sdk

echo "Running Grok tweet fetcher…"
python tools/grok_tweet_fetcher.py --out data/tweets/grok_scraped.jsonl

echo "Done. Output at data/tweets/grok_scraped.jsonl"



