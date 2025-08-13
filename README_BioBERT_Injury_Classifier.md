# BioBERT Injury Severity Classification Model

## Overview

This project implements a BioBERT-based injury severity classification model specifically designed for NBA sports injury data. The model classifies injury-related tweets into four severity categories with confidence thresholding to ensure reliable predictions for downstream betting and fantasy applications.

## Model Architecture

- **Base Model**: BioBERT (`dmis-lab/biobert-base-cased-v1.1`)
- **Task**: Multi-class sequence classification
- **Classes**: 4 injury severity levels
- **Confidence Threshold**: 0.8 (configurable)

## Injury Severity Categories

1. **`out_for_season`** - Long-term injuries (surgeries, season-ending injuries)
2. **`day_to_day`** - Short-term injuries (questionable, probable status)
3. **`minor`** - Minor injuries with minimal impact
4. **`unconfirmed`** - Unverified or non-injury related content

## Dataset

- **Source**: NBA reporter tweets with manual injury severity labels
- **Size**: 360 labeled tweets
- **Distribution**:
  - `out_for_season`: 195 samples (54.2%)
  - `day_to_day`: 87 samples (24.2%)
  - `minor`: 40 samples (11.1%)
  - `unconfirmed`: 38 samples (10.6%)

## Key Features

### 1. Confidence Thresholding
- Predictions below 0.8 confidence are flagged for manual review
- Ensures high-quality predictions for automated decision making
- Provides transparency in model uncertainty

### 2. BioBERT Advantage
- Pre-trained on biomedical text for better understanding of medical terminology
- Superior performance on injury-related language compared to general BERT models
- Better generalization on sparse sports injury data

### 3. Comprehensive Output
- Predicted injury severity
- Confidence score (0-1)
- All class probabilities
- Manual review flag
- Actionable insights for betting/fantasy applications

## Files Structure

```
tools/
├── train_biobert_injury_classifier.py  # Main training script
├── classify_injury_severity.py         # CLI inference tool
└── integrate_injury_classifier.py     # Integration utilities

models/
└── biobert_injury_classifier/          # Trained model artifacts
    ├── pytorch_model.bin
    ├── config.json
    ├── tokenizer.json
    └── label_mappings.json

data/tweets/
└── nba_reporters_expanded_injury_severity_filtered.csv  # Training data
```

## Usage

### 1. Training the Model

```bash
python3 tools/train_biobert_injury_classifier.py
```

This will:
- Load and preprocess the labeled dataset
- Fine-tune BioBERT on injury severity classification
- Save the trained model to `models/biobert_injury_classifier/`
- Evaluate performance on test set

### 2. Single Text Classification

```bash
# Text format output
python3 tools/classify_injury_severity.py --text "LeBron James is out with a torn ACL"

# JSON format output
python3 tools/classify_injury_severity.py --text "Player is questionable tonight" --output-format json
```

### 3. Batch Classification

```bash
# From file (one text per line)
python3 tools/classify_injury_severity.py --file tweets.txt

# Custom confidence threshold
python3 tools/classify_injury_severity.py --text "Minor ankle sprain" --confidence-threshold 0.9
```

### 4. Integration with NBA Parlay Project

```python
from tools.integrate_injury_classifier import classify_injury_tweets

# Classify all tweets in a CSV file
df_with_predictions = classify_injury_tweets(
    "data/tweets/nba_reporters_expanded.csv",
    output_path="data/tweets/classified_injuries.csv",
    confidence_threshold=0.8
)

# Filter for actionable high-confidence predictions
actionable = df_with_predictions[
    (df_with_predictions['injury_confidence'] >= 0.8) &
    (df_with_predictions['predicted_injury_severity'].isin(['out_for_season', 'day_to_day']))
]
```

## Model Performance

### Training Results
- **Training Loss**: Decreased from 1.43 to 0.27 over 5 epochs
- **Validation Accuracy**: 74.1% at best checkpoint
- **Early Stopping**: Implemented to prevent overfitting

### Confidence Analysis
- **Coverage**: ~40-60% of predictions meet 0.8 confidence threshold
- **High-Confidence Accuracy**: Significantly higher than overall accuracy
- **Manual Review Rate**: 40-60% of predictions flagged for review

### Sample Predictions

| Text | Predicted | Confidence | Review Needed |
|------|-----------|------------|---------------|
| "LeBron James is out with a torn ACL and will miss the rest of the season" | `out_for_season` | 0.767 | ⚠️ Yes |
| "Steph Curry is questionable for tonight's game with a minor ankle sprain" | `day_to_day` | 0.830 | ✅ No |
| "Kawhi Leonard underwent surgery and is expected to be out 6-8 months" | `out_for_season` | 0.848 | ✅ No |

## Integration Benefits

### For Betting Applications
1. **Automated Injury Detection**: Identify injury news in real-time
2. **Severity Assessment**: Understand impact on player availability
3. **Confidence Filtering**: Only act on high-confidence predictions
4. **Risk Management**: Flag uncertain predictions for manual review

### For Fantasy Sports
1. **Lineup Decisions**: Quick assessment of player status
2. **Waiver Wire**: Identify players likely to miss extended time
3. **Trade Analysis**: Evaluate injury risk in player trades
4. **Season Planning**: Long-term roster construction

## Technical Implementation

### Model Architecture
```python
class BioBERTInjuryClassifier:
    def __init__(self, confidence_threshold=0.8):
        self.model_name = "dmis-lab/biobert-base-cased-v1.1"
        self.confidence_threshold = confidence_threshold
    
    def predict_with_confidence(self, texts):
        # Returns predictions with confidence scores
        # Flags low-confidence predictions for review
```

### Confidence Thresholding Logic
```python
# Prediction meets confidence threshold
is_confident = confidence >= self.confidence_threshold

# Flag for manual review if below threshold
needs_review = not is_confident
```

### Device Compatibility
- **CPU**: Fully supported for inference
- **MPS (Apple Silicon)**: Training supported, inference uses CPU fallback
- **CUDA**: Supported if available

## Future Enhancements

1. **Expanded Dataset**: Collect more labeled injury data
2. **Multi-Sport Support**: Extend to other sports
3. **Real-time Integration**: Connect to Twitter API for live classification
4. **Player Name Extraction**: Identify specific players mentioned
5. **Temporal Analysis**: Track injury status changes over time
6. **Ensemble Methods**: Combine with other injury detection models

## Dependencies

```
torch>=2.0.0
transformers>=4.20.0
scikit-learn>=1.0.0
pandas>=1.3.0
numpy>=1.21.0
```

## Model Artifacts

The trained model includes:
- **pytorch_model.bin**: Fine-tuned BioBERT weights
- **config.json**: Model configuration
- **tokenizer files**: BioBERT tokenizer
- **label_mappings.json**: Class label encodings and confidence threshold

## Conclusion

The BioBERT injury severity classifier provides a robust foundation for automated injury analysis in the NBA parlay project. With confidence thresholding, it balances automation with reliability, ensuring that only high-quality predictions are used for critical betting and fantasy decisions while flagging uncertain cases for human review.

The model's biomedical pre-training gives it a significant advantage in understanding injury-related language, making it well-suited for sports injury classification tasks despite the relatively small training dataset.
