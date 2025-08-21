#!/usr/bin/env python3
"""
Simple FastAPI app for NBA/NFL Parlay System (minimal dependencies)
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ParlayRequest(BaseModel):
    target_legs: int = 3
    min_total_odds: float = 5.0
    include_arbitrage: bool = True

class ParlayLeg(BaseModel):
    game: str
    market: str
    selection: str
    odds: float
    book: str

class ParlayResponse(BaseModel):
    success: bool
    sport: str
    parlay: Dict[str, Any]
    generated_at: str
    agent_version: str

# Initialize FastAPI
app = FastAPI(
    title="NBA/NFL Parlay System (Minimal)",
    description="Simple parlay generation system",
    version="1.0.0"
)

# App start time
app_start_time = datetime.now(timezone.utc)

@app.get("/")
async def root():
    """System status."""
    uptime = datetime.now(timezone.utc) - app_start_time
    return {
        "message": "NBA/NFL Parlay System - Minimal Mode",
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": int(uptime.total_seconds()),
        "sports_enabled": {
            "nfl": True,
            "nba": True
        },
        "mode": "minimal"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    uptime = datetime.now(timezone.utc) - app_start_time
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(uptime.total_seconds()),
        "components": {
            "web_server": "running",
            "minimal_mode": True
        }
    }

@app.post("/generate-nfl-parlay", response_model=ParlayResponse)
async def generate_nfl_parlay(request: ParlayRequest):
    """Generate a sample NFL parlay."""
    
    nfl_teams = [
        "Buffalo Bills", "Miami Dolphins", "New England Patriots", "New York Jets",
        "Baltimore Ravens", "Cincinnati Bengals", "Cleveland Browns", "Pittsburgh Steelers",
        "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Tennessee Titans",
        "Denver Broncos", "Kansas City Chiefs", "Las Vegas Raiders", "Los Angeles Chargers",
        "Dallas Cowboys", "New York Giants", "Philadelphia Eagles", "Washington Commanders",
        "Chicago Bears", "Detroit Lions", "Green Bay Packers", "Minnesota Vikings",
        "Atlanta Falcons", "Carolina Panthers", "New Orleans Saints", "Tampa Bay Buccaneers",
        "Arizona Cardinals", "Los Angeles Rams", "San Francisco 49ers", "Seattle Seahawks"
    ]
    
    markets = ["Spread", "Moneyline", "Over/Under", "Player Props"]
    books = ["FanDuel", "DraftKings", "BetMGM", "Caesars"]
    
    legs = []
    for i in range(request.target_legs):
        team1 = random.choice(nfl_teams)
        team2 = random.choice([t for t in nfl_teams if t != team1])
        market = random.choice(markets)
        book = random.choice(books)
        
        if market == "Spread":
            spread = random.choice([-14, -10.5, -7, -3.5, -3, -1.5, 1.5, 3, 3.5, 7, 10.5, 14])
            selection = f"{team1} {spread:+.1f}"
            odds = round(random.uniform(1.8, 2.2), 2)
        elif market == "Moneyline":
            selection = f"{team1} ML"
            odds = round(random.uniform(1.5, 3.5), 2)
        elif market == "Over/Under":
            total = random.choice([38.5, 41.5, 44.5, 47.5, 50.5, 53.5])
            over_under = random.choice(["Over", "Under"])
            selection = f"{over_under} {total}"
            odds = round(random.uniform(1.85, 2.15), 2)
        else:  # Player Props
            selection = f"Player rushing yards Over 75.5"
            odds = round(random.uniform(1.7, 2.3), 2)
        
        legs.append({
            "game": f"{team1} vs {team2}",
            "market": market,
            "selection": selection,
            "odds": odds,
            "book": book
        })
    
    # Calculate total odds
    total_odds = 1.0
    for leg in legs:
        total_odds *= leg["odds"]
    
    return ParlayResponse(
        success=True,
        sport="NFL",
        parlay={
            "legs": legs,
            "total_odds": round(total_odds, 2),
            "confidence": round(random.uniform(0.6, 0.9), 2),
            "reasoning": f"NFL parlay with {len(legs)} legs targeting {request.min_total_odds}+ odds",
            "expected_value": round(random.uniform(-0.1, 0.15), 3),
            "recommendation": "Consider smaller stakes for higher-leg parlays"
        },
        generated_at=datetime.now(timezone.utc).isoformat(),
        agent_version="minimal_v1.0"
    )

@app.post("/generate-nba-parlay", response_model=ParlayResponse)
async def generate_nba_parlay(request: ParlayRequest):
    """Generate a sample NBA parlay."""
    
    nba_teams = [
        "Los Angeles Lakers", "Boston Celtics", "Golden State Warriors", "Brooklyn Nets",
        "Miami Heat", "Chicago Bulls", "New York Knicks", "Los Angeles Clippers",
        "Denver Nuggets", "Phoenix Suns", "Dallas Mavericks", "Houston Rockets",
        "San Antonio Spurs", "Oklahoma City Thunder", "Utah Jazz", "Portland Trail Blazers",
        "Sacramento Kings", "Minnesota Timberwolves", "New Orleans Pelicans", "Orlando Magic",
        "Atlanta Hawks", "Charlotte Hornets", "Detroit Pistons", "Indiana Pacers",
        "Cleveland Cavaliers", "Milwaukee Bucks", "Toronto Raptors", "Philadelphia 76ers",
        "Washington Wizards", "Memphis Grizzlies"
    ]
    
    markets = ["Spread", "Moneyline", "Over/Under", "Player Points"]
    books = ["FanDuel", "DraftKings", "BetMGM", "Caesars"]
    
    legs = []
    for i in range(request.target_legs):
        team1 = random.choice(nba_teams)
        team2 = random.choice([t for t in nba_teams if t != team1])
        market = random.choice(markets)
        book = random.choice(books)
        
        if market == "Spread":
            spread = random.choice([-12.5, -9.5, -6.5, -4.5, -2.5, -1.5, 1.5, 2.5, 4.5, 6.5, 9.5, 12.5])
            selection = f"{team1} {spread:+.1f}"
            odds = round(random.uniform(1.8, 2.2), 2)
        elif market == "Moneyline":
            selection = f"{team1} ML"
            odds = round(random.uniform(1.4, 4.0), 2)
        elif market == "Over/Under":
            total = random.choice([205.5, 210.5, 215.5, 220.5, 225.5, 230.5])
            over_under = random.choice(["Over", "Under"])
            selection = f"{over_under} {total}"
            odds = round(random.uniform(1.85, 2.15), 2)
        else:  # Player Points
            player_points = random.choice([20.5, 22.5, 25.5, 27.5, 30.5])
            selection = f"Player points Over {player_points}"
            odds = round(random.uniform(1.7, 2.3), 2)
        
        legs.append({
            "game": f"{team1} vs {team2}",
            "market": market,
            "selection": selection,
            "odds": odds,
            "book": book
        })
    
    # Calculate total odds
    total_odds = 1.0
    for leg in legs:
        total_odds *= leg["odds"]
    
    return ParlayResponse(
        success=True,
        sport="NBA",
        parlay={
            "legs": legs,
            "total_odds": round(total_odds, 2),
            "confidence": round(random.uniform(0.65, 0.85), 2),
            "reasoning": f"NBA parlay with {len(legs)} legs for entertainment purposes",
            "expected_value": round(random.uniform(-0.08, 0.12), 3),
            "recommendation": "NBA games can be unpredictable - bet responsibly"
        },
        generated_at=datetime.now(timezone.utc).isoformat(),
        agent_version="minimal_v1.0"
    )

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    uptime = datetime.now(timezone.utc) - app_start_time
    
    # Check which API keys are configured
    api_keys_configured = {
        "balldontlie": bool(os.getenv("BALLDONTLIE_API_KEY")),
        "odds_api": bool(os.getenv("THE_ODDS_API_KEY")),
        "nfl_api": bool(os.getenv("api-football")),
        "firecrawl": bool(os.getenv("FIRECRAWL_API_KEY")),
        "twitter": bool(os.getenv("twitter_key")),
        "apify": bool(os.getenv("APIFY_TOKEN"))
    }
    
    return {
        "system": {
            "uptime_hours": round(uptime.total_seconds() / 3600, 2),
            "start_time": app_start_time.isoformat(),
            "mode": "production" if any(api_keys_configured.values()) else "demo"
        },
        "sports": {
            "nfl_enabled": True,
            "nba_enabled": True
        },
        "api_configuration": api_keys_configured,
        "endpoints": [
            "/generate-nfl-parlay",
            "/generate-nba-parlay", 
            "/health",
            "/stats"
        ]
    }
