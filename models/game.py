from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CanonicalGameObject(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    game_time: datetime

    odds: Optional[Dict[str, float]] = Field(default_factory=dict)         # {book: odds}
    injuries: Optional[Dict[str, Any]] = Field(default_factory=dict)       # {player_name: status}
    advanced_stats: Optional[Dict[str, Any]] = Field(default_factory=dict) # {stat_category: value}
    
    shutdown_probability: Optional[float] = Field(ge=0.0, le=1.0, default=0.0)

    class Config:
        extra = "allow" 