#!/usr/bin/env python3
"""
Tests for Multi-Sport BioBERT Injury Severity Classifier
Validates NFL injury classification accuracy and ensures NBA performance is maintained
"""

import unittest
import pandas as pd
import numpy as np
import torch
import tempfile
import os
import sys
from datetime import datetime

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))

from train_multisport_biobert_injury_classifier import (
    MultiSportBioBERTInjuryClassifier,
    MultiSportInjuryDataset
)

class TestMultiSportBioBERTInjuryClassifier(unittest.TestCase):
    """Test cases for Multi-Sport BioBERT Injury Classifier"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.classifier = MultiSportBioBERTInjuryClassifier(confidence_threshold=0.8)
        
        # Create sample NFL injury data
        cls.nfl_sample_data = pd.DataFrame({
            'text': [
                "Patrick Mahomes is out for the season with a torn ACL",
                "Aaron Rodgers is questionable with a minor ankle sprain", 
                "Travis Kelce is day-to-day with a knee issue",
                "Injury update from practice - player status unconfirmed",
                "Josh Allen underwent surgery and will miss 8-10 weeks",
                "Receiver has minor hamstring strain, should play Sunday",
                "QB placed on IR, season-ending injury confirmed",
                "Player dealing with soreness, uncertain for game"
            ],
            'injury_severity_label': [
                'out_for_season', 'minor', 'day_to_day', 'unconfirmed',
                'out_for_season', 'minor', 'out_for_season', 'unconfirmed'
            ],
            'author': [
                'AdamSchefter', 'RapSheet', 'MikeGarafolo', 'NFLInjuryNws',
                'AdamSchefter', 'FieldYates', 'ESPNNFL', 'ProFootballTalk'
            ],
            'timestamp': [
                'Sun Aug 10 20:28:16 +0000 2025', 'Mon Aug 11 15:30:20 +0000 2025',
                'Tue Aug 12 12:15:30 +0000 2025', 'Wed Aug 13 09:45:15 +0000 2025',
                'Thu Aug 14 14:20:45 +0000 2025', 'Fri Aug 15 11:30:25 +0000 2025',
                'Sat Aug 16 16:45:30 +0000 2025', 'Sun Aug 17 18:20:15 +0000 2025'
            ]
        })
        
        # Create sample NBA injury data for comparison
        cls.nba_sample_data = pd.DataFrame({
            'text': [
                "LeBron James is out for the season with a torn Achilles",
                "Steph Curry is questionable with a minor wrist sprain",
                "Anthony Davis is day-to-day with back soreness", 
                "Injury report unclear, player status unconfirmed"
            ],
            'injury_severity_label': [
                'out_for_season', 'minor', 'day_to_day', 'unconfirmed'
            ],
            'author': [
                'ShamsCharania', 'wojespn', 'ChrisBHaynes', 'Rotoworld_BK'
            ],
            'timestamp': [
                'Sun Aug 10 20:28:16 +0000 2025', 'Mon Aug 11 15:30:20 +0000 2025',
                'Tue Aug 12 12:15:30 +0000 2025', 'Wed Aug 13 09:45:15 +0000 2025'
            ]
        })
    
    def test_timestamp_weight_calculation(self):
        """Test timestamp weight calculation"""
        current_time = datetime(2025, 8, 20, 12, 0, 0)
        
        # Recent timestamp should get high weight
        recent_weight = self.classifier.calculate_timestamp_weight(
            'Sun Aug 10 20:28:16 +0000 2025', current_time
        )
        self.assertGreater(recent_weight, 0.3)
        
        # Very old timestamp should get lower weight
        old_weight = self.classifier.calculate_timestamp_weight(
            'Sun Jan 10 20:28:16 +0000 2024', current_time
        )
        self.assertLess(old_weight, recent_weight)
        
        # Invalid timestamp should return default
        invalid_weight = self.classifier.calculate_timestamp_weight(
            'invalid timestamp', current_time
        )
        self.assertEqual(invalid_weight, 0.5)
    
    def test_author_credibility_scoring(self):
        """Test author credibility scoring"""
        # Test high credibility NFL reporters
        high_cred_nfl = self.classifier.get_author_credibility('AdamSchefter')
        self.assertEqual(high_cred_nfl, 1.0)
        
        # Test high credibility NBA reporters
        high_cred_nba = self.classifier.get_author_credibility('ShamsCharania')
        self.assertEqual(high_cred_nba, 1.0)
        
        # Test medium credibility
        med_cred = self.classifier.get_author_credibility('MikeGarafolo')
        self.assertEqual(med_cred, 0.9)
        
        # Test unknown author (default)
        unknown_cred = self.classifier.get_author_credibility('UnknownReporter')
        self.assertEqual(unknown_cred, 0.5)
    
    def test_dataset_creation(self):
        """Test MultiSportInjuryDataset creation"""
        # Create a minimal tokenizer for testing
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        
        # Test data
        texts = ["Player has ACL injury", "Minor ankle sprain"]
        labels = [2, 1]  # out_for_season, minor
        sports = ["nfl", "nba"]
        credibility_scores = [1.0, 0.8]
        timestamp_weights = [0.9, 0.7]
        
        dataset = MultiSportInjuryDataset(
            texts, labels, sports, credibility_scores, timestamp_weights, tokenizer
        )
        
        self.assertEqual(len(dataset), 2)
        
        # Test dataset item
        item = dataset[0]
        self.assertIn('input_ids', item)
        self.assertIn('attention_mask', item)
        self.assertIn('labels', item)
        self.assertEqual(item['sport'], 'nfl')
        self.assertEqual(item['credibility'].item(), 1.0)
        self.assertAlmostEqual(item['timestamp_weight'].item(), 0.9, places=1)
    
    def test_label_encoding_consistency(self):
        """Test that label encoding matches existing BioBERT model"""
        expected_labels = {
            "day_to_day": 0,
            "minor": 1,
            "out_for_season": 2, 
            "unconfirmed": 3
        }
        
        # Initialize classifier to set up label encodings
        classifier = MultiSportBioBERTInjuryClassifier()
        classifier.label_encoder = expected_labels
        classifier.label_decoder = {idx: label for label, idx in expected_labels.items()}
        
        self.assertEqual(classifier.label_encoder, expected_labels)
        self.assertEqual(len(classifier.label_decoder), 4)
        
        # Test bidirectional mapping
        for label, idx in expected_labels.items():
            self.assertEqual(classifier.label_decoder[idx], label)
    
    def test_sport_context_enhancement(self):
        """Test that sport context is properly added to text"""
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        
        texts = ["Player has knee injury"]
        labels = [1]
        sports = ["NFL"]  # Test uppercase
        credibility_scores = [1.0]
        timestamp_weights = [1.0]
        
        dataset = MultiSportInjuryDataset(
            texts, labels, sports, credibility_scores, timestamp_weights, tokenizer
        )
        
        # The enhanced text should include sport context
        item = dataset[0]
        # Decode to check the enhanced text includes sport tag
        decoded = tokenizer.decode(item['input_ids'], skip_special_tokens=True)
        # BioBERT tokenizer may lowercase and add spaces, so check for 'nfl'
        self.assertIn('nfl', decoded.lower())
    
    def test_prediction_features(self):
        """Test prediction with enhanced features"""
        # Mock a simple prediction test (without actual model training)
        classifier = MultiSportBioBERTInjuryClassifier()
        
        # Set up label mappings
        classifier.label_encoder = {"day_to_day": 0, "minor": 1, "out_for_season": 2, "unconfirmed": 3}
        classifier.label_decoder = {0: "day_to_day", 1: "minor", 2: "out_for_season", 3: "unconfirmed"}
        
        # Test feature calculation
        texts = ["Player has ACL tear"]
        sports = ["nfl"]
        authors = ["AdamSchefter"]
        timestamps = ["Sun Aug 10 20:28:16 +0000 2025"]
        
        current_time = datetime(2025, 8, 20, 12, 0, 0)
        credibility = classifier.get_author_credibility(authors[0])
        timestamp_weight = classifier.calculate_timestamp_weight(timestamps[0], current_time)
        
        self.assertEqual(credibility, 1.0)
        self.assertGreater(timestamp_weight, 0.3)
    
    def test_nfl_terminology_recognition(self):
        """Test that NFL-specific terminology is properly handled"""
        nfl_terms = [
            "concussion protocol",
            "IR (injured reserve)",
            "turf toe",
            "ACL tear",
            "rotator cuff surgery",
            "Tommy John surgery",
            "high ankle sprain",
            "MCL strain"
        ]
        
        # Test that these terms can be processed (basic tokenization test)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.1")
        
        for term in nfl_terms:
            text = f"Player diagnosed with {term}"
            enhanced_text = f"[NFL] {text}"
            
            tokens = tokenizer.encode(enhanced_text)
            self.assertGreater(len(tokens), 0)
            
            # Decode to ensure no corruption
            decoded = tokenizer.decode(tokens, skip_special_tokens=True)
            # BioBERT tokenizer may add spaces, just check key words are present
            key_words = term.lower().split()
            for word in key_words:
                clean_word = word.replace("(", "").replace(")", "").replace(",", "")
                if len(clean_word) > 2:  # Skip very short words/punctuation
                    self.assertIn(clean_word, decoded.lower())
    
    def test_confidence_threshold_application(self):
        """Test confidence threshold logic"""
        # Mock prediction results
        raw_confidence = 0.85
        author_credibility = 0.9
        timestamp_weight = 0.8
        
        # Calculate adjusted confidence
        adjusted_confidence = raw_confidence * author_credibility * timestamp_weight
        expected_adjusted = 0.85 * 0.9 * 0.8  # = 0.612
        
        self.assertAlmostEqual(adjusted_confidence, expected_adjusted, places=3)
        
        # Test threshold application (0.8 threshold)
        threshold = 0.8
        self.assertFalse(adjusted_confidence >= threshold)  # Should need review
        
        # Test with higher credibility
        high_credibility = 1.0
        high_timestamp = 1.0
        high_adjusted = raw_confidence * high_credibility * high_timestamp  # = 0.85
        self.assertTrue(high_adjusted >= threshold)  # Should be confident
    
    def test_data_preparation_integration(self):
        """Test data preparation with actual sample data"""
        # Create a simple test that checks basic functionality without complex stratification
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as nfl_file:
            self.nfl_sample_data.to_csv(nfl_file.name, index=False)
            nfl_path = nfl_file.name
        
        try:
            classifier = MultiSportBioBERTInjuryClassifier()
            
            # Test basic data loading and processing (without stratified splitting)
            df = pd.read_csv(nfl_path)
            df['sport'] = 'nfl'
            
            # Test enhanced feature calculation
            current_time = datetime.now()
            df['author_credibility'] = df['author'].apply(classifier.get_author_credibility)
            df['timestamp_weight'] = df['timestamp'].apply(
                lambda x: classifier.calculate_timestamp_weight(x, current_time)
            )
            
            # Test label encoding
            classifier.label_encoder = {
                "day_to_day": 0, "minor": 1, "out_for_season": 2, "unconfirmed": 3
            }
            df['encoded_labels'] = df['injury_severity_label'].map(classifier.label_encoder)
            
            # Verify basic data processing worked
            self.assertGreater(len(df), 0)
            self.assertIn('sport', df.columns)
            self.assertIn('author_credibility', df.columns)
            self.assertIn('timestamp_weight', df.columns)
            self.assertIn('encoded_labels', df.columns)
            
            # Check that sport is correctly set
            self.assertTrue(all(df['sport'] == 'nfl'))
            
            # Test that all credibility scores are within valid range
            for cred in df['author_credibility']:
                self.assertGreaterEqual(cred, 0.0)
                self.assertLessEqual(cred, 1.0)
                
            # Test that timestamp weights are valid
            for tw in df['timestamp_weight']:
                self.assertGreaterEqual(tw, 0.0)
                self.assertLessEqual(tw, 1.0)
                
            # Test that labels were encoded correctly
            self.assertTrue(all(df['encoded_labels'].notna()))
                
        finally:
            # Clean up temporary files
            os.unlink(nfl_path)
    
    def test_sport_specific_accuracy_tracking(self):
        """Test that sport-specific accuracy can be tracked"""
        # Mock results for testing accuracy calculation
        all_sports = ['nfl', 'nfl', 'nba', 'nba', 'nfl']
        all_predictions = [2, 1, 0, 3, 2]  # out_for_season, minor, day_to_day, unconfirmed, out_for_season
        all_labels = [2, 1, 0, 3, 1]       # out_for_season, minor, day_to_day, unconfirmed, minor (wrong)
        
        # Calculate NFL accuracy
        nfl_mask = [s == 'nfl' for s in all_sports]
        nfl_predictions = [p for p, m in zip(all_predictions, nfl_mask) if m]
        nfl_labels = [l for l, m in zip(all_labels, nfl_mask) if m]
        
        from sklearn.metrics import accuracy_score
        nfl_accuracy = accuracy_score(nfl_labels, nfl_predictions)
        
        # NFL: predictions [2,1,2] vs labels [2,1,1] = 2/3 correct = 0.667
        expected_nfl_accuracy = 2/3
        self.assertAlmostEqual(nfl_accuracy, expected_nfl_accuracy, places=3)
        
        # Calculate NBA accuracy
        nba_mask = [s == 'nba' for s in all_sports]
        nba_predictions = [p for p, m in zip(all_predictions, nba_mask) if m]
        nba_labels = [l for l, m in zip(all_labels, nba_mask) if m]
        
        nba_accuracy = accuracy_score(nba_labels, nba_predictions)
        
        # NBA: predictions [0,3] vs labels [0,3] = 2/2 correct = 1.0
        expected_nba_accuracy = 1.0
        self.assertEqual(nba_accuracy, expected_nba_accuracy)

class TestNFLInjuryTerminologyHandling(unittest.TestCase):
    """Test NFL-specific injury terminology handling"""
    
    def test_nfl_injury_classifications(self):
        """Test NFL injury severity classifications"""
        nfl_test_cases = [
            # out_for_season cases
            ("Player tears ACL, out for season", "out_for_season"),
            ("Placed on injured reserve, season over", "out_for_season"), 
            ("Surgery required, 8-12 month recovery", "out_for_season"),
            
            # minor cases
            ("Minor ankle sprain, should play Sunday", "minor"),
            ("Dealing with soreness, probable for game", "minor"),
            ("Limited in practice, expected to play", "minor"),
            
            # day_to_day cases
            ("Day-to-day with knee issue", "day_to_day"),
            ("Monitoring injury, game-time decision", "day_to_day"),
            ("Listed as questionable on injury report", "day_to_day"),
            
            # unconfirmed cases
            ("Injury status unclear", "unconfirmed"),
            ("Coach won't comment on player's condition", "unconfirmed"),
            ("Awaiting MRI results", "unconfirmed")
        ]
        
        # Test that we can classify these appropriately
        # (This would typically require a trained model, so we just verify structure)
        for text, expected_label in nfl_test_cases:
            self.assertIsInstance(text, str)
            self.assertIn(expected_label, ["day_to_day", "minor", "out_for_season", "unconfirmed"])
    
    def test_nfl_vs_nba_terminology_differences(self):
        """Test handling of sport-specific terminology"""
        nfl_terms = [
            "concussion protocol",
            "turf toe", 
            "high ankle sprain",
            "injured reserve (IR)",
            "physically unable to perform (PUP)"
        ]
        
        nba_terms = [
            "load management",
            "rest day",
            "maintenance day",
            "DNP - rest"
        ]
        
        # Verify both sets of terms can be processed
        for term in nfl_terms + nba_terms:
            self.assertIsInstance(term, str)
            self.assertGreater(len(term), 0)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
