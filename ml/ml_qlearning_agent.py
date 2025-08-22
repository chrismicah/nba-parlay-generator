#!/usr/bin/env python3
"""
Q-Learning Parlay Agent - ML-QLEARNING-001

Reinforcement Learning agent that learns optimal parlay construction strategies
using Deep Q-Networks (DQN) in a custom Gymnasium environment. The agent learns
to select optimal combinations of betting legs based on Expected Value and
correlation patterns from historical data.

Key Features:
- Custom Gymnasium environment for parlay construction
- Deep Q-Network with experience replay and target networks
- State representation with EV, correlation, and market features
- Action space for adding/removing legs from parlays
- Reward function based on historical outcome simulation
- Integration with existing ParlayBuilder system
- Evaluation against random baseline strategies
"""

import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import random
import pickle
from collections import deque, namedtuple
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

# Gymnasium imports
try:
    import gymnasium as gym
    from gymnasium import spaces
    HAS_GYMNASIUM = True
except ImportError:
    HAS_GYMNASIUM = False
    gym = spaces = None

# Set up logging
logger = logging.getLogger(__name__)

# PyTorch device selection
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Experience tuple for replay buffer
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])


@dataclass
class QLearningConfig:
    """Configuration for Q-Learning agent."""
    # Environment settings (reduced for stability)
    max_parlay_legs: int = 4
    min_parlay_legs: int = 2
    max_candidate_legs: int = 10  # Reduced from 20
    state_dim: int = 15  # Features per leg + parlay state
    
    # DQN hyperparameters
    learning_rate: float = 1e-4
    batch_size: int = 32
    gamma: float = 0.99  # Discount factor
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    target_update_freq: int = 100  # Episodes
    
    # Network architecture (reduced for stability)
    hidden_dim: int = 128  # Reduced from 256
    dropout_rate: float = 0.2
    
    # Training settings (reduced for faster training)
    num_episodes: int = 1000  # Reduced from 2000
    memory_size: int = 5000   # Reduced from 10000
    min_memory_size: int = 500  # Reduced from 1000
    
    # Evaluation settings
    eval_episodes: int = 1000
    eval_frequency: int = 100
    
    # File paths
    model_save_path: str = "models/qlearning_parlay_agent"
    experience_log_path: str = "data/qlearning_experiences.json"
    
    # Reward settings
    win_reward: float = 1.0
    loss_penalty: float = -0.5
    correlation_penalty: float = -0.1
    ev_bonus_multiplier: float = 2.0


class ParlayLeg:
    """Represents a single parlay leg with features."""
    
    def __init__(self, leg_id: str, odds: float, expected_value: float, 
                 market_type: str, player_name: str = "", sport: str = "nba"):
        self.leg_id = leg_id
        self.odds = odds
        self.expected_value = expected_value
        self.market_type = market_type
        self.player_name = player_name
        self.sport = sport
        
        # Additional computed features
        self.probability = self._odds_to_probability(odds)
        self.kelly_fraction = self._calculate_kelly_fraction()
        self.market_category = self._categorize_market()
    
    def _odds_to_probability(self, odds: float) -> float:
        """Convert American/Decimal odds to implied probability."""
        if odds > 0:  # American positive odds
            return 100 / (odds + 100)
        elif odds < 0:  # American negative odds
            return abs(odds) / (abs(odds) + 100)
        else:  # Decimal odds
            return 1 / odds if odds > 1 else 0.5
    
    def _calculate_kelly_fraction(self) -> float:
        """Calculate Kelly Criterion fraction."""
        if self.expected_value <= 0:
            return 0.0
        
        # Kelly = (bp - q) / b where b=odds, p=true_prob, q=1-p
        true_prob = self.probability + self.expected_value
        if true_prob <= 0 or true_prob >= 1:
            return 0.0
        
        b = abs(self.odds) / 100 if self.odds < 0 else self.odds / 100
        kelly = (b * true_prob - (1 - true_prob)) / b
        return max(0, min(kelly, 0.25))  # Cap at 25%
    
    def _categorize_market(self) -> int:
        """Categorize market type into numeric categories."""
        market_categories = {
            'points': 0, 'rebounds': 1, 'assists': 2, 'steals': 3,
            'blocks': 4, 'threes': 5, 'turnovers': 6, 'minutes': 7,
            'passing_yards': 8, 'rushing_yards': 9, 'receiving_yards': 10,
            'touchdowns': 11, 'receptions': 12, 'interceptions': 13
        }
        
        market_lower = self.market_type.lower()
        for key, value in market_categories.items():
            if key in market_lower:
                return value
        return 14  # Other
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert leg to feature vector for neural network."""
        features = [
            self.odds / 1000.0,  # Normalized odds
            self.expected_value,
            self.probability,
            self.kelly_fraction,
            float(self.market_category) / 14.0,  # Normalized category
            float(self.sport == "nba"),  # Sport indicator
            float(self.sport == "nfl"),
        ]
        return np.array(features, dtype=np.float32)


class ParlayEnvironment(gym.Env):
    """Custom Gymnasium environment for parlay construction."""
    
    def __init__(self, config: QLearningConfig):
        """Initialize parlay environment."""
        super().__init__()
        
        if not HAS_GYMNASIUM:
            raise ImportError("gymnasium required. Install with: pip install gymnasium")
        
        self.config = config
        
        # Action space: 0 = done, 1-N = add leg N, N+1-2N = remove leg N
        max_actions = 1 + (2 * config.max_candidate_legs)
        self.action_space = spaces.Discrete(max_actions)
        
        # State space: leg features + parlay state
        state_size = (config.max_candidate_legs * 7) + 8  # 7 features per leg + 8 parlay features
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(state_size,), dtype=np.float32
        )
        
        # Environment state
        self.candidate_legs = []
        self.current_parlay = []
        self.correlation_matrix = None
        self.historical_outcomes = {}
        self.episode_step = 0
        self.max_episode_steps = 20
        
        logger.info(f"ParlayEnvironment initialized: {max_actions} actions, {state_size} state dims")
    
    def reset(self, seed=None, options=None):
        """Reset environment for new episode."""
        super().reset(seed=seed)
        
        # Generate new candidate legs
        self.candidate_legs = self._generate_candidate_legs()
        self.current_parlay = []
        self.episode_step = 0
        
        # Generate correlation matrix
        self.correlation_matrix = self._generate_correlation_matrix()
        
        # Generate historical outcomes for reward calculation
        self.historical_outcomes = self._generate_historical_outcomes()
        
        state = self._get_state()
        info = {"episode_step": self.episode_step}
        
        return state, info
    
    def step(self, action):
        """Execute action and return next state, reward, done, info."""
        self.episode_step += 1
        
        reward = 0.0
        done = False
        info = {"action_type": "invalid"}
        
        if action == 0:  # Done action
            done = True
            info["action_type"] = "done"
            
            if len(self.current_parlay) >= self.config.min_parlay_legs:
                reward = self._calculate_final_reward()
                info["valid_parlay"] = True
            else:
                reward = -1.0  # Penalty for incomplete parlay
                info["valid_parlay"] = False
                
        elif 1 <= action <= self.config.max_candidate_legs:  # Add leg
            leg_idx = action - 1
            if (leg_idx < len(self.candidate_legs) and 
                len(self.current_parlay) < self.config.max_parlay_legs):
                
                leg = self.candidate_legs[leg_idx]
                if leg.leg_id not in [l.leg_id for l in self.current_parlay]:
                    self.current_parlay.append(leg)
                    reward = self._calculate_step_reward(leg, "add")
                    info["action_type"] = "add_leg"
                    info["leg_added"] = leg.leg_id
        
        elif action > self.config.max_candidate_legs:  # Remove leg
            leg_idx = action - self.config.max_candidate_legs - 1
            if leg_idx < len(self.current_parlay):
                removed_leg = self.current_parlay.pop(leg_idx)
                reward = self._calculate_step_reward(removed_leg, "remove")
                info["action_type"] = "remove_leg"
                info["leg_removed"] = removed_leg.leg_id
        
        # Episode termination conditions
        if (self.episode_step >= self.max_episode_steps or 
            len(self.current_parlay) >= self.config.max_parlay_legs):
            done = True
        
        state = self._get_state()
        info.update({
            "episode_step": self.episode_step,
            "parlay_size": len(self.current_parlay),
            "parlay_ev": sum(leg.expected_value for leg in self.current_parlay)
        })
        
        return state, reward, done, False, info
    
    def _generate_candidate_legs(self) -> List[ParlayLeg]:
        """Generate random candidate legs for episode."""
        legs = []
        sports = ["nba", "nfl"]
        markets = ["points", "rebounds", "assists", "passing_yards", "receiving_yards", "touchdowns"]
        
        for i in range(self.config.max_candidate_legs):
            sport = random.choice(sports)
            market = random.choice(markets)
            
            # Generate realistic odds and EV
            odds = random.uniform(-200, 150)
            ev = random.uniform(-0.1, 0.15)  # -10% to +15% EV
            
            leg = ParlayLeg(
                leg_id=f"leg_{i}_{sport}_{market}",
                odds=odds,
                expected_value=ev,
                market_type=market,
                player_name=f"Player_{i}",
                sport=sport
            )
            legs.append(leg)
        
        return legs
    
    def _generate_correlation_matrix(self) -> np.ndarray:
        """Generate correlation matrix for candidate legs."""
        n_legs = len(self.candidate_legs)
        matrix = np.eye(n_legs, dtype=np.float32)
        
        # Add some realistic correlations
        for i in range(n_legs):
            for j in range(i + 1, n_legs):
                leg1, leg2 = self.candidate_legs[i], self.candidate_legs[j]
                
                # Same player = high correlation
                if leg1.player_name == leg2.player_name:
                    correlation = random.uniform(0.3, 0.8)
                # Same sport/market = medium correlation
                elif leg1.sport == leg2.sport and leg1.market_type == leg2.market_type:
                    correlation = random.uniform(0.1, 0.4)
                # Different = low correlation
                else:
                    correlation = random.uniform(-0.2, 0.2)
                
                matrix[i, j] = matrix[j, i] = correlation
        
        return matrix
    
    def _generate_historical_outcomes(self) -> Dict[str, bool]:
        """Generate historical outcomes for reward calculation."""
        outcomes = {}
        
        for leg in self.candidate_legs:
            # Outcome probability based on EV and some noise
            base_prob = leg.probability
            adjusted_prob = base_prob + leg.expected_value + random.uniform(-0.1, 0.1)
            adjusted_prob = np.clip(adjusted_prob, 0.1, 0.9)
            
            outcomes[leg.leg_id] = random.random() < adjusted_prob
        
        return outcomes
    
    def _get_state(self) -> np.ndarray:
        """Get current environment state."""
        state = np.zeros(self.observation_space.shape[0], dtype=np.float32)
        
        # Encode candidate legs (7 features each)
        for i, leg in enumerate(self.candidate_legs[:self.config.max_candidate_legs]):
            start_idx = i * 7
            state[start_idx:start_idx + 7] = leg.to_feature_vector()
        
        # Encode parlay state (8 features)
        parlay_start = self.config.max_candidate_legs * 7
        
        # Basic parlay features
        state[parlay_start] = len(self.current_parlay) / self.config.max_parlay_legs
        state[parlay_start + 1] = float(len(self.current_parlay) >= self.config.min_parlay_legs)
        
        if self.current_parlay:
            # Parlay statistics
            total_ev = sum(leg.expected_value for leg in self.current_parlay)
            avg_odds = np.mean([leg.odds for leg in self.current_parlay])
            avg_prob = np.mean([leg.probability for leg in self.current_parlay])
            
            state[parlay_start + 2] = total_ev
            state[parlay_start + 3] = avg_odds / 1000.0
            state[parlay_start + 4] = avg_prob
            
            # Correlation features
            if len(self.current_parlay) > 1:
                parlay_indices = [self.candidate_legs.index(leg) for leg in self.current_parlay 
                                 if leg in self.candidate_legs]
                if len(parlay_indices) > 1:
                    correlations = []
                    for i in range(len(parlay_indices)):
                        for j in range(i + 1, len(parlay_indices)):
                            correlations.append(self.correlation_matrix[parlay_indices[i], parlay_indices[j]])
                    
                    state[parlay_start + 5] = np.mean(correlations)
                    state[parlay_start + 6] = np.max(correlations)
        
        # Episode progress
        state[parlay_start + 7] = self.episode_step / self.max_episode_steps
        
        return state
    
    def _calculate_step_reward(self, leg: ParlayLeg, action_type: str) -> float:
        """Calculate immediate reward for adding/removing a leg."""
        if action_type == "add":
            # Reward based on EV and Kelly fraction
            ev_reward = leg.expected_value * self.config.ev_bonus_multiplier
            kelly_reward = leg.kelly_fraction * 0.5
            
            # Penalty for high correlation
            correlation_penalty = 0.0
            if len(self.current_parlay) > 0:
                leg_idx = self.candidate_legs.index(leg) if leg in self.candidate_legs else -1
                if leg_idx >= 0:
                    parlay_indices = [self.candidate_legs.index(l) for l in self.current_parlay 
                                     if l in self.candidate_legs]
                    if parlay_indices:
                        max_correlation = max([self.correlation_matrix[leg_idx, idx] 
                                             for idx in parlay_indices])
                        if max_correlation > 0.5:
                            correlation_penalty = self.config.correlation_penalty * max_correlation
            
            return ev_reward + kelly_reward + correlation_penalty
        
        else:  # remove
            # Small penalty for removing legs
            return -0.1
    
    def _calculate_final_reward(self) -> float:
        """Calculate final reward based on simulated parlay outcome."""
        if not self.current_parlay:
            return 0.0
        
        # Simulate parlay outcome using historical data
        all_hit = all(self.historical_outcomes.get(leg.leg_id, False) for leg in self.current_parlay)
        
        if all_hit:
            # Calculate payout
            total_odds = 1.0
            for leg in self.current_parlay:
                leg_odds = abs(leg.odds) / 100 if leg.odds < 0 else leg.odds / 100
                total_odds *= (1 + leg_odds)
            
            reward = self.config.win_reward * total_odds
        else:
            reward = self.config.loss_penalty
        
        # Bonus for positive EV parlays
        total_ev = sum(leg.expected_value for leg in self.current_parlay)
        if total_ev > 0:
            reward += total_ev * self.config.ev_bonus_multiplier
        
        return reward


class DQN(nn.Module):
    """Deep Q-Network for parlay agent."""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256, dropout_rate: float = 0.2):
        """Initialize DQN architecture."""
        super(DQN, self).__init__()
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Input processing
        self.input_norm = nn.LayerNorm(state_dim)
        
        # Main network
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc4 = nn.Linear(hidden_dim // 2, action_dim)
        
        # Regularization
        self.dropout = nn.Dropout(dropout_rate)
        self.layer_norm1 = nn.LayerNorm(hidden_dim)
        self.layer_norm2 = nn.LayerNorm(hidden_dim)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize network weights."""
        for layer in [self.fc1, self.fc2, self.fc3, self.fc4]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.constant_(layer.bias, 0.0)
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass through network."""
        x = self.input_norm(state)
        
        x = F.relu(self.layer_norm1(self.fc1(x)))
        x = self.dropout(x)
        
        x = F.relu(self.layer_norm2(self.fc2(x)))
        x = self.dropout(x)
        
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        
        return x


class ReplayBuffer:
    """Experience replay buffer for DQN training."""
    
    def __init__(self, capacity: int):
        """Initialize replay buffer."""
        self.buffer = deque(maxlen=capacity)
    
    def push(self, experience: Experience):
        """Add experience to buffer."""
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Sample batch of experiences."""
        return random.sample(self.buffer, batch_size)
    
    def __len__(self) -> int:
        """Return buffer size."""
        return len(self.buffer)


class QLearningParlayAgent:
    """Q-Learning agent for optimal parlay construction."""
    
    def __init__(self, config: QLearningConfig = None):
        """Initialize Q-Learning agent."""
        self.config = config or QLearningConfig()
        
        # Initialize environment
        self.env = ParlayEnvironment(self.config)
        
        # Initialize networks
        state_dim = self.env.observation_space.shape[0]
        action_dim = self.env.action_space.n
        
        self.q_network = DQN(state_dim, action_dim, self.config.hidden_dim, self.config.dropout_rate).to(device)
        self.target_network = DQN(state_dim, action_dim, self.config.hidden_dim, self.config.dropout_rate).to(device)
        
        # Copy weights to target network
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()
        
        # Training components
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=self.config.learning_rate)
        self.replay_buffer = ReplayBuffer(self.config.memory_size)
        
        # Training state
        self.epsilon = self.config.epsilon_start
        self.episode_count = 0
        self.training_history = []
        
        logger.info(f"QLearningParlayAgent initialized: {state_dim} state dims, {action_dim} actions")
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using epsilon-greedy policy."""
        if training and random.random() < self.epsilon:
            return self.env.action_space.sample()
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()
    
    def train_step(self):
        """Perform one training step."""
        if len(self.replay_buffer) < self.config.min_memory_size:
            return None
        
        # Sample batch
        batch = self.replay_buffer.sample(self.config.batch_size)
        
        # Convert to tensors
        states = torch.FloatTensor([e.state for e in batch]).to(device)
        actions = torch.LongTensor([e.action for e in batch]).to(device)
        rewards = torch.FloatTensor([e.reward for e in batch]).to(device)
        next_states = torch.FloatTensor([e.next_state for e in batch]).to(device)
        dones = torch.BoolTensor([e.done for e in batch]).to(device)
        
        # Current Q values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Next Q values from target network
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(1)[0]
            target_q_values = rewards + (self.config.gamma * next_q_values * ~dones)
        
        # Compute loss
        loss = F.mse_loss(current_q_values, target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def train(self, num_episodes: int = None) -> Dict[str, Any]:
        """Train the Q-Learning agent."""
        if num_episodes is None:
            num_episodes = self.config.num_episodes
        
        logger.info(f"Starting Q-Learning training for {num_episodes} episodes...")
        
        episode_rewards = []
        episode_lengths = []
        losses = []
        
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            while not done:
                # Select action
                action = self.select_action(state, training=True)
                
                # Take step
                next_state, reward, done, _, info = self.env.step(action)
                
                # Store experience
                self.replay_buffer.push(Experience(state, action, reward, next_state, done))
                
                # Update state
                state = next_state
                episode_reward += reward
                episode_length += 1
                
                # Train network
                if len(self.replay_buffer) >= self.config.min_memory_size:
                    loss = self.train_step()
                    if loss is not None:
                        losses.append(loss)
            
            # Update target network
            if episode % self.config.target_update_freq == 0:
                self.target_network.load_state_dict(self.q_network.state_dict())
            
            # Decay epsilon
            self.epsilon = max(self.config.epsilon_end, 
                             self.epsilon * self.config.epsilon_decay)
            
            # Record episode statistics
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            self.episode_count += 1
            
            # Logging
            if episode % 100 == 0:
                avg_reward = np.mean(episode_rewards[-100:])
                avg_length = np.mean(episode_lengths[-100:])
                avg_loss = np.mean(losses[-100:]) if losses else 0.0
                
                logger.info(f"Episode {episode}: Avg Reward: {avg_reward:.3f}, "
                           f"Avg Length: {avg_length:.1f}, Loss: {avg_loss:.4f}, "
                           f"Epsilon: {self.epsilon:.3f}")
            
            # Evaluation
            if episode > 0 and episode % self.config.eval_frequency == 0:
                eval_results = self.evaluate(episodes=100)
                logger.info(f"Evaluation at episode {episode}: "
                           f"Avg Reward: {eval_results['avg_reward']:.3f}, "
                           f"Win Rate: {eval_results['win_rate']:.1%}")
        
        # Store training history
        self.training_history.append({
            'episode_rewards': episode_rewards,
            'episode_lengths': episode_lengths,
            'losses': losses,
            'final_epsilon': self.epsilon
        })
        
        logger.info("Training completed!")
        
        return {
            'avg_reward': np.mean(episode_rewards[-100:]),
            'total_episodes': num_episodes,
            'final_epsilon': self.epsilon,
            'training_history': self.training_history[-1]
        }
    
    def evaluate(self, episodes: int = 1000) -> Dict[str, Any]:
        """Evaluate agent performance."""
        self.q_network.eval()
        
        episode_rewards = []
        parlay_sizes = []
        win_count = 0
        
        for episode in range(episodes):
            state, _ = self.env.reset()
            episode_reward = 0
            done = False
            
            while not done:
                action = self.select_action(state, training=False)
                state, reward, done, _, info = self.env.step(action)
                episode_reward += reward
            
            episode_rewards.append(episode_reward)
            parlay_sizes.append(info.get('parlay_size', 0))
            
            if episode_reward > 0:
                win_count += 1
        
        self.q_network.train()
        
        return {
            'avg_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'win_rate': win_count / episodes,
            'avg_parlay_size': np.mean(parlay_sizes),
            'total_episodes': episodes
        }
    
    def infer_parlay(self, candidate_legs: List[Dict[str, Any]], max_legs: int = 5) -> List[Dict[str, Any]]:
        """
        Build optimal parlay from candidate legs using trained agent.
        
        Args:
            candidate_legs: List of leg dictionaries with odds, EV, etc.
            max_legs: Maximum number of legs in parlay
            
        Returns:
            List of selected leg dictionaries
        """
        if not candidate_legs:
            return []
        
        # Convert to ParlayLeg objects
        parlay_legs = []
        for i, leg_data in enumerate(candidate_legs[:self.config.max_candidate_legs]):
            leg = ParlayLeg(
                leg_id=leg_data.get('leg_id', f'infer_leg_{i}'),
                odds=leg_data.get('odds', 0.0),
                expected_value=leg_data.get('expected_value', 0.0),
                market_type=leg_data.get('market_type', 'unknown'),
                player_name=leg_data.get('player_name', ''),
                sport=leg_data.get('sport', 'nba')
            )
            parlay_legs.append(leg)
        
        # Set up environment with these specific legs
        self.env.candidate_legs = parlay_legs
        self.env.current_parlay = []
        self.env.correlation_matrix = self.env._generate_correlation_matrix()
        self.env.episode_step = 0
        
        # Run inference
        state = self.env._get_state()
        selected_legs = []
        done = False
        step_count = 0
        
        self.q_network.eval()
        
        while not done and step_count < self.env.max_episode_steps:
            action = self.select_action(state, training=False)
            state, reward, done, _, info = self.env.step(action)
            step_count += 1
            
            # Track selected legs
            if info.get('action_type') == 'add_leg':
                leg_id = info.get('leg_added')
                for leg_data in candidate_legs:
                    if leg_data.get('leg_id') == leg_id:
                        selected_legs.append(leg_data)
                        break
            
            # Stop if we have enough legs or agent chooses done
            if len(selected_legs) >= max_legs or action == 0:
                done = True
        
        self.q_network.train()
        
        logger.info(f"Inferred parlay with {len(selected_legs)} legs")
        return selected_legs[:max_legs]
    
    def save_model(self, path: str = None):
        """Save trained model."""
        if path is None:
            path = self.config.model_save_path
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config,
            'episode_count': self.episode_count,
            'epsilon': self.epsilon,
            'training_history': self.training_history
        }, f"{path}.pt")
        
        logger.info(f"Model saved to {path}.pt")
    
    def load_model(self, path: str = None):
        """Load trained model."""
        if path is None:
            path = self.config.model_save_path
        
        model_path = Path(f"{path}.pt")
        if not model_path.exists():
            logger.warning(f"Model file not found: {model_path}")
            return False
        
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.episode_count = checkpoint.get('episode_count', 0)
        self.epsilon = checkpoint.get('epsilon', self.config.epsilon_end)
        self.training_history = checkpoint.get('training_history', [])
        
        logger.info(f"Model loaded from {model_path}")
        return True


def random_baseline_agent(candidate_legs: List[Dict[str, Any]], max_legs: int = 5) -> List[Dict[str, Any]]:
    """Random baseline for comparison."""
    if not candidate_legs:
        return []
    
    num_legs = random.randint(2, min(max_legs, len(candidate_legs)))
    return random.sample(candidate_legs, num_legs)


def evaluate_vs_baseline(agent: QLearningParlayAgent, episodes: int = 1000) -> Dict[str, Any]:
    """Evaluate Q-Learning agent vs random baseline."""
    logger.info(f"Evaluating Q-Learning agent vs random baseline over {episodes} episodes...")
    
    agent_rewards = []
    baseline_rewards = []
    
    for episode in range(episodes):
        # Reset environment
        state, _ = agent.env.reset()
        
        # Get candidate legs for this episode
        candidate_legs = [
            {
                'leg_id': leg.leg_id,
                'odds': leg.odds,
                'expected_value': leg.expected_value,
                'market_type': leg.market_type,
                'player_name': leg.player_name,
                'sport': leg.sport
            }
            for leg in agent.env.candidate_legs
        ]
        
        # Agent parlay
        agent_parlay = agent.infer_parlay(candidate_legs)
        agent_reward = agent.env._calculate_final_reward() if agent_parlay else 0.0
        agent_rewards.append(agent_reward)
        
        # Baseline parlay
        baseline_parlay = random_baseline_agent(candidate_legs)
        
        # Simulate baseline reward
        baseline_legs = [leg for leg in agent.env.candidate_legs 
                        if leg.leg_id in [p['leg_id'] for p in baseline_parlay]]
        agent.env.current_parlay = baseline_legs
        baseline_reward = agent.env._calculate_final_reward() if baseline_legs else 0.0
        baseline_rewards.append(baseline_reward)
    
    results = {
        'agent_avg_reward': np.mean(agent_rewards),
        'agent_std_reward': np.std(agent_rewards),
        'baseline_avg_reward': np.mean(baseline_rewards),
        'baseline_std_reward': np.std(baseline_rewards),
        'improvement': np.mean(agent_rewards) - np.mean(baseline_rewards),
        'win_rate_agent': np.mean([r > 0 for r in agent_rewards]),
        'win_rate_baseline': np.mean([r > 0 for r in baseline_rewards]),
        'episodes_evaluated': episodes
    }
    
    logger.info(f"Evaluation Results:")
    logger.info(f"  Agent Avg Reward: {results['agent_avg_reward']:.3f}")
    logger.info(f"  Baseline Avg Reward: {results['baseline_avg_reward']:.3f}")
    logger.info(f"  Improvement: {results['improvement']:.3f}")
    logger.info(f"  Agent Win Rate: {results['win_rate_agent']:.1%}")
    logger.info(f"  Baseline Win Rate: {results['win_rate_baseline']:.1%}")
    
    return results


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 Q-Learning Parlay Agent Demo")
    print("=" * 50)
    
    if not HAS_GYMNASIUM:
        print("❌ gymnasium not installed. Install with: pip install gymnasium")
        exit(1)
    
    # Initialize agent
    print("🏗️ Initializing Q-Learning agent...")
    config = QLearningConfig(
        num_episodes=500,  # Reduced for demo
        eval_frequency=100
    )
    
    agent = QLearningParlayAgent(config)
    
    # Train agent
    print("🚀 Training agent...")
    training_results = agent.train()
    
    print(f"✅ Training completed!")
    print(f"  Final average reward: {training_results['avg_reward']:.3f}")
    print(f"  Total episodes: {training_results['total_episodes']}")
    
    # Evaluate agent
    print("\n📊 Evaluating agent...")
    eval_results = agent.evaluate(episodes=100)
    
    print(f"  Average reward: {eval_results['avg_reward']:.3f}")
    print(f"  Win rate: {eval_results['win_rate']:.1%}")
    print(f"  Average parlay size: {eval_results['avg_parlay_size']:.1f}")
    
    # Test inference
    print("\n🔮 Testing parlay inference...")
    sample_legs = [
        {'leg_id': 'test_1', 'odds': -110, 'expected_value': 0.05, 'market_type': 'points', 'sport': 'nba'},
        {'leg_id': 'test_2', 'odds': 120, 'expected_value': 0.08, 'market_type': 'rebounds', 'sport': 'nba'},
        {'leg_id': 'test_3', 'odds': -150, 'expected_value': 0.03, 'market_type': 'assists', 'sport': 'nba'},
        {'leg_id': 'test_4', 'odds': 180, 'expected_value': 0.12, 'market_type': 'touchdowns', 'sport': 'nfl'},
    ]
    
    inferred_parlay = agent.infer_parlay(sample_legs)
    print(f"  Inferred parlay: {len(inferred_parlay)} legs")
    for leg in inferred_parlay:
        print(f"    • {leg['leg_id']} ({leg['market_type']}) - EV: {leg['expected_value']:.1%}")
    
    # Compare to baseline
    print("\n⚖️ Comparing to random baseline...")
    baseline_comparison = evaluate_vs_baseline(agent, episodes=100)
    
    improvement = baseline_comparison['improvement']
    print(f"  Performance improvement: {improvement:+.3f}")
    print(f"  {'✅ Agent outperforms baseline!' if improvement > 0 else '❌ Baseline performs better'}")
    
    # Save model
    print(f"\n💾 Saving model...")
    agent.save_model()
    
    print("\n✅ Demo completed! Q-Learning agent ready for integration.")
