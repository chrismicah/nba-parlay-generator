#!/usr/bin/env python3
"""
Parlay Confidence Predictor - JIRA-019

Production-ready inference pipeline for the RoBERTa parlay confidence classifier.
Provides easy-to-use interface for predicting parlay confidence from reasoning text.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Set up logging
logger = logging.getLogger(__name__)


class ParlayConfidencePredictor:
    """
    Production inference pipeline for parlay confidence prediction.
    
    Loads a trained RoBERTa model and provides methods for predicting
    confidence levels from parlay reasoning text.
    """
    
    def __init__(self, model_path: str = "models/parlay_confidence_classifier"):
        """
        Initialize the confidence predictor.
        
        Args:
            model_path: Path to the trained model directory
        """
        self.model_path = Path(model_path)
        self.model = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.is_loaded = False
        
        # Label mappings (will be loaded from model metadata)
        self.label2id = {"low_confidence": 0, "high_confidence": 1}
        self.id2label = {0: "low_confidence", 1: "high_confidence"}
        
        logger.info(f"Initialized ParlayConfidencePredictor with model path: {model_path}")
        logger.info(f"Using device: {self.device}")
    
    def load_model(self) -> None:
        """Load the trained model and tokenizer."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        try:
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Load training metadata if available
            metadata_path = self.model_path / "training_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    if 'label2id' in metadata:
                        self.label2id = metadata['label2id']
                        self.id2label = {int(k): v for k, v in metadata['id2label'].items()}
            
            self.is_loaded = True
            logger.info(f"Successfully loaded model from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict(self, reasoning_text: str, return_probabilities: bool = True) -> Dict[str, Any]:
        """
        Predict confidence level for parlay reasoning text.
        
        Args:
            reasoning_text: The parlay reasoning text to analyze
            return_probabilities: Whether to return confidence probabilities
            
        Returns:
            Dictionary with prediction results
        """
        if not self.is_loaded:
            self.load_model()
        
        if not reasoning_text.strip():
            raise ValueError("Reasoning text cannot be empty")
        
        try:
            # Tokenize the input
            inputs = self.tokenizer(
                reasoning_text,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                prediction = torch.argmax(logits, dim=-1)
            
            # Prepare results
            predicted_label = self.id2label[prediction.item()]
            confidence_scores = {
                "low_confidence": probabilities[0][0].item(),
                "high_confidence": probabilities[0][1].item()
            }
            
            result = {
                "predicted_confidence": predicted_label,
                "max_confidence_score": max(confidence_scores.values()),
                "prediction_certainty": abs(confidence_scores["high_confidence"] - 0.5) * 2  # 0-1 scale
            }
            
            if return_probabilities:
                result["confidence_probabilities"] = confidence_scores
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def predict_batch(self, reasoning_texts: List[str], 
                     batch_size: int = 16) -> List[Dict[str, Any]]:
        """
        Predict confidence for multiple reasoning texts.
        
        Args:
            reasoning_texts: List of reasoning texts to analyze
            batch_size: Batch size for processing
            
        Returns:
            List of prediction results
        """
        if not self.is_loaded:
            self.load_model()
        
        if not reasoning_texts:
            return []
        
        results = []
        
        for i in range(0, len(reasoning_texts), batch_size):
            batch_texts = reasoning_texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch_texts,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Make predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                predictions = torch.argmax(logits, dim=-1)
            
            # Process batch results
            for j, (pred, probs) in enumerate(zip(predictions, probabilities)):
                predicted_label = self.id2label[pred.item()]
                confidence_scores = {
                    "low_confidence": probs[0].item(),
                    "high_confidence": probs[1].item()
                }
                
                result = {
                    "predicted_confidence": predicted_label,
                    "max_confidence_score": max(confidence_scores.values()),
                    "prediction_certainty": abs(confidence_scores["high_confidence"] - 0.5) * 2,
                    "confidence_probabilities": confidence_scores
                }
                results.append(result)
        
        return results
    
    def analyze_parlay_reasoning(self, reasoning_text: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of parlay reasoning including confidence prediction.
        
        Args:
            reasoning_text: The parlay reasoning text to analyze
            
        Returns:
            Detailed analysis results
        """
        prediction = self.predict(reasoning_text)
        
        # Extract basic metrics from reasoning text
        word_count = len(reasoning_text.split())
        line_count = len(reasoning_text.split('\n'))
        has_injury_intel = 'injury' in reasoning_text.lower()
        has_line_movement = 'line movement' in reasoning_text.lower() or 'moved' in reasoning_text.lower()
        has_sharp_money = 'sharp' in reasoning_text.lower()
        has_public_betting = 'public' in reasoning_text.lower()
        
        # Confidence indicators
        confidence_keywords = ['confident', 'strong', 'edge', 'value', 'advantage']
        concern_keywords = ['concern', 'risk', 'uncertain', 'questionable', 'caution']
        
        confidence_mentions = sum(1 for keyword in confidence_keywords if keyword in reasoning_text.lower())
        concern_mentions = sum(1 for keyword in concern_keywords if keyword in reasoning_text.lower())
        
        analysis = {
            "confidence_prediction": prediction,
            "reasoning_analysis": {
                "word_count": word_count,
                "line_count": line_count,
                "has_injury_intel": has_injury_intel,
                "has_line_movement": has_line_movement,
                "has_sharp_money_indicators": has_sharp_money,
                "has_public_betting_info": has_public_betting,
                "confidence_keyword_count": confidence_mentions,
                "concern_keyword_count": concern_mentions,
                "confidence_to_concern_ratio": confidence_mentions / max(concern_mentions, 1)
            },
            "recommendation": self._generate_recommendation(prediction, reasoning_text)
        }
        
        return analysis
    
    def _generate_recommendation(self, prediction: Dict[str, Any], reasoning_text: str) -> str:
        """Generate a recommendation based on the confidence prediction."""
        confidence = prediction["predicted_confidence"]
        certainty = prediction["prediction_certainty"]
        
        if confidence == "high_confidence":
            if certainty > 0.8:
                return "STRONG BUY: High confidence prediction with strong model certainty. Consider larger bet size."
            elif certainty > 0.6:
                return "BUY: High confidence prediction with moderate certainty. Proceed with standard bet size."
            else:
                return "WEAK BUY: High confidence prediction but low certainty. Consider smaller bet size."
        else:
            if certainty > 0.8:
                return "AVOID: Low confidence prediction with strong model certainty. Skip this parlay."
            elif certainty > 0.6:
                return "CAUTION: Low confidence prediction with moderate certainty. High risk if proceeding."
            else:
                return "UNCERTAIN: Low confidence prediction with low certainty. Model is unsure - gather more information."
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self.is_loaded:
            return {"status": "Model not loaded"}
        
        info = {
            "status": "Model loaded",
            "model_path": str(self.model_path),
            "device": str(self.device),
            "label_mapping": self.id2label,
            "num_parameters": sum(p.numel() for p in self.model.parameters()),
            "trainable_parameters": sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        }
        
        # Add training metadata if available
        metadata_path = self.model_path / "training_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                training_metadata = json.load(f)
                info["training_metadata"] = training_metadata
        
        return info


class ParlayConfidenceIntegration:
    """
    Integration class for incorporating confidence prediction into parlay building workflow.
    """
    
    def __init__(self, predictor: Optional[ParlayConfidencePredictor] = None):
        """
        Initialize the integration.
        
        Args:
            predictor: Pre-initialized predictor instance (optional)
        """
        self.predictor = predictor or ParlayConfidencePredictor()
    
    def enhance_parlay_recommendation(self, parlay_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a parlay recommendation with confidence prediction.
        
        Args:
            parlay_recommendation: Parlay recommendation with reasoning
            
        Returns:
            Enhanced recommendation with confidence analysis
        """
        if 'reasoning' not in parlay_recommendation:
            raise ValueError("Parlay recommendation must include 'reasoning' field")
        
        reasoning_text = parlay_recommendation['reasoning']
        
        # Get confidence analysis
        confidence_analysis = self.predictor.analyze_parlay_reasoning(reasoning_text)
        
        # Enhance the recommendation
        enhanced_recommendation = parlay_recommendation.copy()
        enhanced_recommendation.update({
            "ai_confidence_analysis": confidence_analysis,
            "confidence_score": confidence_analysis["confidence_prediction"]["max_confidence_score"],
            "bet_recommendation": confidence_analysis["recommendation"],
            "model_certainty": confidence_analysis["confidence_prediction"]["prediction_certainty"]
        })
        
        return enhanced_recommendation
    
    def filter_recommendations_by_confidence(self, recommendations: List[Dict[str, Any]], 
                                           min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        Filter parlay recommendations by confidence threshold.
        
        Args:
            recommendations: List of parlay recommendations
            min_confidence: Minimum confidence score threshold
            
        Returns:
            Filtered recommendations meeting confidence criteria
        """
        filtered = []
        
        for rec in recommendations:
            enhanced_rec = self.enhance_parlay_recommendation(rec)
            
            if enhanced_rec["confidence_score"] >= min_confidence:
                filtered.append(enhanced_rec)
        
        # Sort by confidence score (highest first)
        filtered.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        return filtered


def main():
    """Main function for testing the confidence predictor."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🎯 Parlay Confidence Predictor - JIRA-019")
        print("=" * 50)
        
        # Initialize predictor
        predictor = ParlayConfidencePredictor()
        
        # Check if model exists
        if not predictor.model_path.exists():
            print("⚠️ Trained model not found. Training model first...")
            
            # Import and run training
            from tools.train_parlay_confidence_classifier import main as train_main
            train_main()
            
            print("✅ Model training completed. Loading for inference...")
        
        # Load model
        print("📥 Loading trained model...")
        predictor.load_model()
        
        # Show model info
        model_info = predictor.get_model_info()
        print(f"Model Status: {model_info['status']}")
        print(f"Parameters: {model_info['num_parameters']:,}")
        print(f"Device: {model_info['device']}")
        
        # Test with sample reasoning
        sample_reasoning = """PARLAY ANALYSIS (3 legs):

LEG 1: Lakers -3.5 (-110)
Odds: 1.91 at DraftKings
• Lakers are 18-6 ATS as home favorites this season
• LeBron James confirmed healthy after questionable tag
• Sharp money moved line from -2.5 to -3.5 despite 60% public on opponent

LEG 2: Warriors vs Suns Under 225.5 (-105)
Odds: 1.95 at FanDuel
• Both teams missing key offensive players
• Last 5 meetings averaged 218 points
• Professional under action moved total from 228 to 225.5

LEG 3: Celtics Moneyline (-180)
Odds: 1.56 at BetMGM
• Celtics 15-3 at home this season
• Opponent on back-to-back after overtime game
• All injury reports clear for Celtics

OVERALL ASSESSMENT:
Combined odds: 5.98
Risk assessment: Low risk - Strong fundamentals across all legs
Value assessment: Strong value with sharp money alignment"""
        
        print("\n🧪 Testing confidence prediction...")
        print("Sample reasoning (abbreviated):")
        print(sample_reasoning[:200] + "...")
        
        # Make prediction
        result = predictor.analyze_parlay_reasoning(sample_reasoning)
        
        print(f"\n📊 Confidence Analysis Results:")
        print(f"Predicted Confidence: {result['confidence_prediction']['predicted_confidence']}")
        print(f"Confidence Score: {result['confidence_prediction']['max_confidence_score']:.3f}")
        print(f"Model Certainty: {result['confidence_prediction']['prediction_certainty']:.3f}")
        print(f"Recommendation: {result['recommendation']}")
        
        print(f"\n📈 Reasoning Analysis:")
        analysis = result['reasoning_analysis']
        print(f"Word Count: {analysis['word_count']}")
        print(f"Has Injury Intel: {analysis['has_injury_intel']}")
        print(f"Has Sharp Money Indicators: {analysis['has_sharp_money_indicators']}")
        print(f"Confidence Keywords: {analysis['confidence_keyword_count']}")
        print(f"Concern Keywords: {analysis['concern_keyword_count']}")
        
        # Test integration
        print(f"\n🔗 Testing Integration...")
        integration = ParlayConfidenceIntegration(predictor)
        
        sample_recommendation = {
            "parlay_id": "test_parlay_001",
            "legs": [
                {"team": "Lakers", "bet": "-3.5", "odds": 1.91},
                {"team": "Warriors vs Suns", "bet": "Under 225.5", "odds": 1.95},
                {"team": "Celtics", "bet": "ML", "odds": 1.56}
            ],
            "total_odds": 5.98,
            "reasoning": sample_reasoning
        }
        
        enhanced_rec = integration.enhance_parlay_recommendation(sample_recommendation)
        
        print(f"Enhanced Recommendation:")
        print(f"AI Confidence Score: {enhanced_rec['confidence_score']:.3f}")
        print(f"Bet Recommendation: {enhanced_rec['bet_recommendation']}")
        print(f"Model Certainty: {enhanced_rec['model_certainty']:.3f}")
        
        print(f"\n✅ JIRA-019 Inference Pipeline Complete!")
        print(f"🎯 Confidence predictor ready for production use")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
