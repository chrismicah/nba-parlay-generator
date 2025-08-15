#!/usr/bin/env python3
"""
Dynamic Correlation Rules Model - JIRA-022A

Graph Neural Network implementation for identifying hidden correlations between
different bet types using historical bet outcomes from SQLite database.

Key Features:
- GNN-based correlation detection
- Historical bet outcome analysis
- Dynamic correlation scoring
- Integration with ParlayBuilder for correlated leg detection
"""

import logging
import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import json
import pickle
from datetime import datetime, timezone
import re

# ML/GNN imports
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import GCNConv, GATConv, global_mean_pool
    from torch_geometric.data import Data, DataLoader
    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False

# Always import sklearn (more commonly available)
try:
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


@dataclass
class BetNode:
    """Represents a bet as a node in the correlation graph."""
    bet_id: int
    game_id: str
    market_type: str  # 'h2h', 'spreads', 'totals', 'player_props'
    team: Optional[str]
    player: Optional[str]
    line_value: Optional[float]
    odds: float
    outcome: Optional[bool]  # True=win, False=loss, None=open
    
    def to_feature_vector(self) -> List[float]:
        """Convert bet node to feature vector for GNN."""
        features = []
        
        # Market type encoding (one-hot)
        market_types = ['h2h', 'spreads', 'totals', 'player_props', 'other']
        market_one_hot = [1.0 if self.market_type == mt else 0.0 for mt in market_types]
        features.extend(market_one_hot)
        
        # Odds (normalized)
        features.append(min(max(self.odds, 1.0), 10.0) / 10.0)  # Normalize to [0.1, 1.0]
        
        # Line value (normalized, 0 if None)
        if self.line_value is not None:
            features.append(min(max(self.line_value, -50.0), 50.0) / 50.0)  # Normalize to [-1, 1]
        else:
            features.append(0.0)
        
        # Has team/player flags
        features.append(1.0 if self.team else 0.0)
        features.append(1.0 if self.player else 0.0)
        
        return features


@dataclass
class CorrelationEdge:
    """Represents a correlation between two bets."""
    bet1_id: int
    bet2_id: int
    correlation_type: str  # 'same_game', 'same_team', 'same_player', 'market_related'
    strength: float  # 0.0 to 1.0
    is_correlated: bool  # True if historically correlated outcomes


class BetDataProcessor:
    """Processes historical bet data for GNN training."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        if HAS_SKLEARN:
            self.market_encoder = LabelEncoder()
            self.team_encoder = LabelEncoder()
            self.scaler = StandardScaler()
        else:
            self.market_encoder = None
            self.team_encoder = None
            self.scaler = None
        
    def extract_bet_features(self, leg_description: str) -> Dict[str, Any]:
        """Extract structured features from leg description."""
        features = {
            'market_type': 'other',
            'team': None,
            'player': None,
            'line_value': None,
            'bookmaker': None
        }
        
        desc_lower = leg_description.lower()
        
        # Extract market type
        if any(keyword in desc_lower for keyword in ['ml', 'moneyline', 'h2h']):
            features['market_type'] = 'h2h'
        elif any(keyword in desc_lower for keyword in ['spread', '+', '-', 'ats']):
            features['market_type'] = 'spreads'
            # Extract line value
            line_match = re.search(r'([+-]?\d+\.?\d*)', leg_description)
            if line_match:
                try:
                    features['line_value'] = float(line_match.group(1))
                except ValueError:
                    pass
        elif any(keyword in desc_lower for keyword in ['over', 'under', 'total', 'o/', 'u/']):
            features['market_type'] = 'totals'
            # Extract total value
            total_match = re.search(r'(\d+\.?\d*)', leg_description)
            if total_match:
                try:
                    features['line_value'] = float(total_match.group(1))
                except ValueError:
                    pass
        elif any(keyword in desc_lower for keyword in ['points', 'assists', 'rebounds', 'pra']):
            features['market_type'] = 'player_props'
        
        # Extract team names (common NBA teams)
        nba_teams = [
            'lakers', 'celtics', 'warriors', 'nets', 'heat', 'bulls', 'knicks',
            'clippers', 'nuggets', 'suns', 'mavericks', 'rockets', 'spurs',
            'thunder', 'jazz', 'blazers', 'kings', 'timberwolves', 'pelicans',
            'magic', 'hawks', 'hornets', 'pistons', 'pacers', 'cavaliers',
            'raptors', 'wizards', 'bucks', '76ers', 'grizzlies'
        ]
        
        for team in nba_teams:
            if team in desc_lower:
                features['team'] = team.title()
                break
        
        # Extract bookmaker
        book_match = re.search(r'\[book:\s*([^\]]+)\]', desc_lower)
        if book_match:
            features['bookmaker'] = book_match.group(1).strip()
        
        return features
    
    def load_historical_data(self, min_date: Optional[str] = None) -> List[BetNode]:
        """Load historical bet data from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT bet_id, game_id, leg_description, odds, is_win, created_at
            FROM bets 
            WHERE is_win IS NOT NULL
        """
        params = []
        
        if min_date:
            query += " AND created_at >= ?"
            params.append(min_date)
        
        query += " ORDER BY created_at"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        bet_nodes = []
        for row in rows:
            features = self.extract_bet_features(row['leg_description'])
            
            bet_node = BetNode(
                bet_id=row['bet_id'],
                game_id=row['game_id'],
                market_type=features['market_type'],
                team=features['team'],
                player=features['player'],
                line_value=features['line_value'],
                odds=row['odds'],
                outcome=bool(row['is_win']) if row['is_win'] is not None else None
            )
            bet_nodes.append(bet_node)
        
        logger.info(f"Loaded {len(bet_nodes)} historical bet nodes")
        return bet_nodes
    
    def identify_correlations(self, bet_nodes: List[BetNode]) -> List[CorrelationEdge]:
        """Identify potential correlations between bets."""
        correlations = []
        
        # Group bets by parlay to find same-parlay correlations
        parlay_groups = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for bet_node in bet_nodes:
            cursor.execute("SELECT parlay_id FROM bets WHERE bet_id = ?", (bet_node.bet_id,))
            result = cursor.fetchone()
            if result:
                parlay_id = result[0]
                if parlay_id not in parlay_groups:
                    parlay_groups[parlay_id] = []
                parlay_groups[parlay_id].append(bet_node)
        
        conn.close()
        
        # Find correlations within parlays
        for parlay_id, parlay_bets in parlay_groups.items():
            if len(parlay_bets) < 2:
                continue
                
            for i, bet1 in enumerate(parlay_bets):
                for bet2 in parlay_bets[i+1:]:
                    correlation_type = self._determine_correlation_type(bet1, bet2)
                    if correlation_type:
                        strength = self._calculate_correlation_strength(bet1, bet2, correlation_type)
                        
                        # Determine if historically correlated (simplified)
                        is_correlated = self._are_outcomes_correlated(bet1, bet2)
                        
                        correlations.append(CorrelationEdge(
                            bet1_id=bet1.bet_id,
                            bet2_id=bet2.bet_id,
                            correlation_type=correlation_type,
                            strength=strength,
                            is_correlated=is_correlated
                        ))
        
        logger.info(f"Identified {len(correlations)} potential correlations")
        return correlations
    
    def _determine_correlation_type(self, bet1: BetNode, bet2: BetNode) -> Optional[str]:
        """Determine the type of correlation between two bets."""
        if bet1.game_id == bet2.game_id:
            return 'same_game'
        elif bet1.team and bet2.team and bet1.team == bet2.team:
            return 'same_team'
        elif bet1.player and bet2.player and bet1.player == bet2.player:
            return 'same_player'
        elif bet1.market_type == bet2.market_type:
            return 'market_related'
        return None
    
    def _calculate_correlation_strength(self, bet1: BetNode, bet2: BetNode, correlation_type: str) -> float:
        """Calculate correlation strength based on bet characteristics."""
        if correlation_type == 'same_game':
            return 0.9  # High correlation for same game
        elif correlation_type == 'same_team':
            return 0.7  # Medium-high for same team
        elif correlation_type == 'same_player':
            return 0.8  # High for same player
        elif correlation_type == 'market_related':
            return 0.3  # Low for same market type
        return 0.1
    
    def _are_outcomes_correlated(self, bet1: BetNode, bet2: BetNode) -> bool:
        """Simplified correlation detection based on outcomes."""
        if bet1.outcome is None or bet2.outcome is None:
            return False
        
        # For demo purposes, assume same-game bets are correlated if both won or both lost
        if bet1.game_id == bet2.game_id:
            return bet1.outcome == bet2.outcome
        
        return False


class CorrelationGNN(nn.Module):
    """Graph Neural Network for bet correlation modeling."""
    
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 1):
        super(CorrelationGNN, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # Graph convolution layers
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.conv3 = GCNConv(hidden_dim, hidden_dim // 2)
        
        # Attention mechanism
        self.attention = GATConv(hidden_dim // 2, hidden_dim // 4, heads=4, concat=True)
        
        # Classification layers
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, output_dim),
            nn.Sigmoid()
        )
        
    def forward(self, x, edge_index, batch=None):
        """Forward pass through the GNN."""
        # Graph convolutions with residual connections
        h1 = F.relu(self.conv1(x, edge_index))
        h2 = F.relu(self.conv2(h1, edge_index))
        h3 = F.relu(self.conv3(h2, edge_index))
        
        # Attention mechanism
        h_att = self.attention(h3, edge_index)
        
        # Global pooling for graph-level prediction
        if batch is not None:
            h_pooled = global_mean_pool(h_att, batch)
        else:
            h_pooled = torch.mean(h_att, dim=0, keepdim=True)
        
        # Classification
        correlation_score = self.classifier(h_pooled)
        
        return correlation_score


class DynamicCorrelationModel:
    """Main class for dynamic correlation rules modeling."""
    
    def __init__(self, db_path: str, model_save_path: str = "models/correlation_model"):
        self.db_path = db_path
        self.model_save_path = Path(model_save_path)
        self.model_save_path.mkdir(parents=True, exist_ok=True)
        
        self.data_processor = BetDataProcessor(db_path)
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"Initialized CorrelationModel with device: {self.device}")
    
    def prepare_training_data(self, min_date: Optional[str] = None) -> Tuple[List[Any], List[int]]:
        """Prepare training data for GNN."""
        if not HAS_TORCH_GEOMETRIC:
            raise ImportError("PyTorch Geometric required for GNN training")
        
        # Load historical data
        bet_nodes = self.data_processor.load_historical_data(min_date)
        correlations = self.data_processor.identify_correlations(bet_nodes)
        
        if not bet_nodes or not correlations:
            raise ValueError("Insufficient data for training")
        
        # Convert to graph data
        graphs = []
        labels = []
        
        # Group correlations by parlay for graph construction
        parlay_correlations = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for correlation in correlations:
            # Get parlay IDs for both bets
            cursor.execute("SELECT parlay_id FROM bets WHERE bet_id IN (?, ?)", 
                          (correlation.bet1_id, correlation.bet2_id))
            results = cursor.fetchall()
            
            if len(results) == 2 and results[0][0] == results[1][0]:
                parlay_id = results[0][0]
                if parlay_id not in parlay_correlations:
                    parlay_correlations[parlay_id] = []
                parlay_correlations[parlay_id].append(correlation)
        
        conn.close()
        
        # Create graph for each parlay
        for parlay_id, parlay_corrs in parlay_correlations.items():
            if len(parlay_corrs) < 1:
                continue
            
            # Get unique bet IDs in this parlay
            bet_ids = set()
            for corr in parlay_corrs:
                bet_ids.add(corr.bet1_id)
                bet_ids.add(corr.bet2_id)
            
            bet_id_to_idx = {bet_id: idx for idx, bet_id in enumerate(sorted(bet_ids))}
            
            # Get bet nodes for this parlay
            parlay_nodes = [node for node in bet_nodes if node.bet_id in bet_ids]
            parlay_nodes.sort(key=lambda x: x.bet_id)
            
            if len(parlay_nodes) < 2:
                continue
            
            # Create node features
            node_features = []
            for node in parlay_nodes:
                features = node.to_feature_vector()
                node_features.append(features)
            
            x = torch.tensor(node_features, dtype=torch.float)
            
            # Create edge indices and attributes
            edge_indices = []
            edge_attrs = []
            
            for corr in parlay_corrs:
                idx1 = bet_id_to_idx[corr.bet1_id]
                idx2 = bet_id_to_idx[corr.bet2_id]
                
                # Add both directions for undirected graph
                edge_indices.extend([[idx1, idx2], [idx2, idx1]])
                edge_attrs.extend([corr.strength, corr.strength])
            
            if not edge_indices:
                continue
            
            edge_index = torch.tensor(edge_indices, dtype=torch.long).t().contiguous()
            edge_attr = torch.tensor(edge_attrs, dtype=torch.float)
            
            # Create graph data
            if HAS_TORCH_GEOMETRIC:
                from torch_geometric.data import Data
                graph_data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
                graphs.append(graph_data)
            
            # Label: 1 if any correlation is positive, 0 otherwise
            has_correlation = any(corr.is_correlated for corr in parlay_corrs)
            labels.append(1 if has_correlation else 0)
        
        logger.info(f"Prepared {len(graphs)} training graphs")
        return graphs, labels
    
    def train_model(self, epochs: int = 100, batch_size: int = 32, learning_rate: float = 0.001):
        """Train the correlation GNN model."""
        if not HAS_TORCH_GEOMETRIC:
            raise ImportError("PyTorch Geometric required for training")
        
        # Prepare training data
        graphs, labels = self.prepare_training_data()
        
        if len(graphs) < 10:
            logger.warning("Very limited training data. Consider collecting more historical bets.")
        
        # Split data
        if HAS_SKLEARN:
            train_graphs, val_graphs, train_labels, val_labels = train_test_split(
                graphs, labels, test_size=0.2, random_state=42, stratify=labels
            )
        else:
            # Simple split without sklearn
            split_idx = int(0.8 * len(graphs))
            train_graphs, val_graphs = graphs[:split_idx], graphs[split_idx:]
            train_labels, val_labels = labels[:split_idx], labels[split_idx:]
        
        # Create data loaders
        if HAS_TORCH_GEOMETRIC:
            from torch_geometric.data import DataLoader
            train_loader = DataLoader(train_graphs, batch_size=batch_size, shuffle=True)
            val_loader = DataLoader(val_graphs, batch_size=batch_size, shuffle=False)
        else:
            raise ImportError("PyTorch Geometric required for training")
        
        # Initialize model
        input_dim = len(graphs[0].x[0]) if graphs else 9  # Feature vector size
        self.model = CorrelationGNN(input_dim=input_dim).to(self.device)
        
        # Training setup
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.BCELoss()
        
        # Training loop
        best_val_acc = 0.0
        train_losses = []
        val_accuracies = []
        
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            total_loss = 0.0
            
            for batch_idx, batch in enumerate(train_loader):
                batch = batch.to(self.device)
                optimizer.zero_grad()
                
                # Forward pass
                output = self.model(batch.x, batch.edge_index, batch.batch)
                target = torch.tensor([train_labels[i] for i in range(
                    batch_idx * batch_size, min((batch_idx + 1) * batch_size, len(train_labels))
                )], dtype=torch.float).to(self.device).unsqueeze(1)
                
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(train_loader)
            train_losses.append(avg_loss)
            
            # Validation phase
            val_acc = self._evaluate_model(val_loader, val_labels)
            val_accuracies.append(val_acc)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                self.save_model()
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Loss={avg_loss:.4f}, Val Acc={val_acc:.4f}")
        
        logger.info(f"Training completed. Best validation accuracy: {best_val_acc:.4f}")
        
        # Save training history
        history = {
            'train_losses': train_losses,
            'val_accuracies': val_accuracies,
            'best_val_acc': best_val_acc
        }
        
        with open(self.model_save_path / 'training_history.json', 'w') as f:
            json.dump(history, f, indent=2)
        
        return history
    
    def _evaluate_model(self, data_loader, true_labels):
        """Evaluate model performance."""
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for batch_idx, batch in enumerate(data_loader):
                batch = batch.to(self.device)
                output = self.model(batch.x, batch.edge_index, batch.batch)
                pred = (output > 0.5).cpu().numpy().flatten()
                predictions.extend(pred)
        
        if HAS_SKLEARN:
            accuracy = accuracy_score(true_labels, predictions)
        else:
            # Simple accuracy calculation
            accuracy = sum(1 for t, p in zip(true_labels, predictions) if t == p) / len(true_labels)
        return accuracy
    
    def predict_correlation(self, bet_features_1: List[float], bet_features_2: List[float], 
                          correlation_strength: float = 0.5) -> float:
        """Predict correlation score between two potential bet legs."""
        if not self.model:
            self.load_model()
        
        if not self.model:
            logger.warning("No trained model available. Using rule-based correlation.")
            return self._rule_based_correlation(bet_features_1, bet_features_2, correlation_strength)
        
        # Create a simple graph with two nodes
        x = torch.tensor([bet_features_1, bet_features_2], dtype=torch.float).to(self.device)
        edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            correlation_score = self.model(x, edge_index).item()
        
        return correlation_score
    
    def _rule_based_correlation(self, bet_features_1: List[float], bet_features_2: List[float], 
                              correlation_strength: float) -> float:
        """Fallback rule-based correlation when no trained model is available."""
        # Simple heuristic based on market types
        market_types = ['h2h', 'spreads', 'totals', 'player_props', 'other']
        
        # Extract market types from feature vectors
        market1_idx = np.argmax(bet_features_1[:5])
        market2_idx = np.argmax(bet_features_2[:5])
        
        # High correlation if same market type
        if market1_idx == market2_idx:
            return min(0.8, correlation_strength + 0.3)
        
        # Medium correlation for related markets (h2h-spreads, spreads-totals)
        related_pairs = [(0, 1), (1, 2)]  # h2h-spreads, spreads-totals
        if (market1_idx, market2_idx) in related_pairs or (market2_idx, market1_idx) in related_pairs:
            return min(0.6, correlation_strength + 0.1)
        
        return correlation_strength
    
    def save_model(self):
        """Save the trained model and metadata."""
        if self.model:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'model_config': {
                    'input_dim': self.model.input_dim,
                    'hidden_dim': self.model.hidden_dim,
                    'output_dim': self.model.output_dim
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, self.model_save_path / 'correlation_model.pth')
            
            logger.info(f"Model saved to {self.model_save_path}")
    
    def load_model(self):
        """Load a previously trained model."""
        model_file = self.model_save_path / 'correlation_model.pth'
        
        if not model_file.exists():
            logger.warning(f"No saved model found at {model_file}")
            return False
        
        try:
            checkpoint = torch.load(model_file, map_location=self.device)
            config = checkpoint['model_config']
            
            self.model = CorrelationGNN(
                input_dim=config['input_dim'],
                hidden_dim=config['hidden_dim'],
                output_dim=config['output_dim']
            ).to(self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            logger.info(f"Model loaded from {model_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


def main():
    """Main function for testing the correlation model."""
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🧠 Dynamic Correlation Rules Model - JIRA-022A")
        print("=" * 60)
        
        if not HAS_TORCH_GEOMETRIC:
            print("❌ PyTorch Geometric not installed")
            print("Install with: pip install torch torch-geometric")
            return
        
        # Initialize model
        db_path = "data/demo_parlays.sqlite"
        model = DynamicCorrelationModel(db_path)
        
        print(f"📊 Analyzing historical data from {db_path}")
        
        # Load and analyze data
        bet_nodes = model.data_processor.load_historical_data()
        correlations = model.data_processor.identify_correlations(bet_nodes)
        
        print(f"✅ Found {len(bet_nodes)} historical bets")
        print(f"✅ Identified {len(correlations)} potential correlations")
        
        if correlations:
            print(f"\n🔍 Sample correlations:")
            for i, corr in enumerate(correlations[:3]):
                print(f"  {i+1}. Bet {corr.bet1_id} ↔ Bet {corr.bet2_id}")
                print(f"     Type: {corr.correlation_type}, Strength: {corr.strength:.2f}")
                print(f"     Correlated: {'Yes' if corr.is_correlated else 'No'}")
        
        # Prepare training data
        try:
            graphs, labels = model.prepare_training_data()
            print(f"\n📈 Prepared {len(graphs)} training graphs")
            print(f"📊 Label distribution: {sum(labels)} positive, {len(labels) - sum(labels)} negative")
            
            if len(graphs) >= 5:  # Minimum for meaningful training
                print(f"\n🚀 Training GNN model...")
                history = model.train_model(epochs=50, batch_size=4)
                
                print(f"✅ Training completed!")
                print(f"📊 Best validation accuracy: {history['best_val_acc']:.4f}")
                
                # Test prediction
                if bet_nodes and len(bet_nodes) >= 2:
                    node1 = bet_nodes[0]
                    node2 = bet_nodes[1]
                    
                    features1 = node1.to_feature_vector()
                    features2 = node2.to_feature_vector()
                    
                    correlation_score = model.predict_correlation(features1, features2)
                    print(f"\n🎯 Sample prediction:")
                    print(f"   Bet 1: {node1.market_type} @ {node1.odds}")
                    print(f"   Bet 2: {node2.market_type} @ {node2.odds}")
                    print(f"   Correlation Score: {correlation_score:.4f}")
            else:
                print(f"⚠️ Insufficient training data ({len(graphs)} graphs)")
                print(f"💡 Need more historical parlay data for meaningful training")
                
        except Exception as e:
            print(f"⚠️ Training failed: {e}")
            print(f"💡 Using rule-based correlation as fallback")
        
        print(f"\n✅ Dynamic Correlation Model initialized successfully!")
        print(f"🔧 Ready for integration with ParlayBuilder")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
