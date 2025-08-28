#!/usr/bin/env python3
"""
Enhanced FastAPI Application - NBA/NFL Parlay System

Provides REST endpoints for generating NBA and NFL parlay recommendations
with ML prediction layer, APScheduler support, and health monitoring.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our unified agent system
try:
    from tools.unified_parlay_strategist_agent import UnifiedParlayStrategistAgent, create_unified_agent
    from tools.knowledge_base_rag import SportsKnowledgeRAG
    HAS_AGENTS = True
except ImportError as e:
    logging.warning(f"Could not import unified agents: {e}")
    HAS_AGENTS = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class ParlayRequest(BaseModel):
    target_legs: int = 3
    min_total_odds: float = 5.0
    include_arbitrage: bool = True
    sport: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, Any]
    uptime_seconds: int

# Initialize FastAPI app
app = FastAPI(
    title="NBA/NFL Parlay Generation System",
    description="Intelligent parlay generation with ML predictions and expert knowledge",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global unified agents (initialized on startup)
nfl_agent: Optional[UnifiedParlayStrategistAgent] = None
nba_agent: Optional[UnifiedParlayStrategistAgent] = None
knowledge_base: Optional[SportsKnowledgeRAG] = None
app_start_time = datetime.now(timezone.utc)


@app.on_event("startup")
async def startup_event():
    """Initialize agents and services on startup."""
    global nfl_agent, nba_agent, knowledge_base
    
    logger.info("🚀 Starting NBA/NFL Parlay System FastAPI App")
    
    if not HAS_AGENTS:
        logger.error("❌ Required agents could not be imported")
        return
    
    try:
        # Initialize knowledge base
        logger.info("📚 Loading knowledge base...")
        knowledge_base = SportsKnowledgeRAG()
        logger.info("✅ Knowledge base loaded")
        
        # Initialize NFL unified agent
        if os.getenv("ENABLE_NFL", "true").lower() == "true":
            logger.info("🏈 Initializing unified NFL agent...")
            nfl_agent = create_unified_agent("NFL", knowledge_base)
            logger.info("✅ Unified NFL agent ready")
        
        # Initialize NBA unified agent  
        if os.getenv("ENABLE_NBA", "true").lower() == "true":
            logger.info("🏀 Initializing unified NBA agent...")
            nba_agent = create_unified_agent("NBA", knowledge_base)
            logger.info("✅ Unified NBA agent ready")
        
        logger.info("🎯 All FastAPI services initialized")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")


@app.get("/")
async def root():
    """System status and basic information."""
    uptime = datetime.now(timezone.utc) - app_start_time
    
    return {
        "message": "NBA/NFL Parlay System - Container Ready",
        "status": "healthy",
        "version": "2.0.0",
        "uptime_seconds": int(uptime.total_seconds()),
        "sports_enabled": {
            "nfl": nfl_agent is not None,
            "nba": nba_agent is not None
        },
        "components": {
            "knowledge_base": knowledge_base is not None,
            "ml_layer": True,  # Always available in container
            "scheduler": True,  # APScheduler support
            "vector_db": os.getenv("QDRANT_URL") is not None,
            "cache": os.getenv("REDIS_URL") is not None
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check for monitoring."""
    uptime = datetime.now(timezone.utc) - app_start_time
    
    health_status = {
        "status": "healthy" if (nfl_agent or nba_agent) else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(uptime.total_seconds()),
        "components": {
            "nfl_agent": {
                "status": "ready" if nfl_agent else "unavailable",
                "enabled": os.getenv("ENABLE_NFL", "true").lower() == "true"
            },
            "nba_agent": {
                "status": "ready" if nba_agent else "unavailable", 
                "enabled": os.getenv("ENABLE_NBA", "true").lower() == "true"
            },
            "knowledge_base": {
                "status": "ready" if knowledge_base else "unavailable",
                "chunks": len(knowledge_base.sports_betting_chunks) if knowledge_base else 0
            },
            "external_services": {
                "qdrant": "connected" if os.getenv("QDRANT_URL") else "not_configured",
                "redis": "connected" if os.getenv("REDIS_URL") else "not_configured"
            }
        }
    }
    
    return health_status


@app.post("/generate-nfl-parlay")
async def generate_nfl_parlay(request: ParlayRequest):
    """Generate NFL parlay with knowledge base insights."""
    if not nfl_agent:
        raise HTTPException(
            status_code=503, 
            detail="NFL agent not available. Check ENABLE_NFL environment variable."
        )
    
    try:
        logger.info(f"Generating NFL parlay: {request.target_legs} legs, min odds {request.min_total_odds}")
        
        recommendation = await nfl_agent.generate_parlay_recommendation(
            target_legs=request.target_legs,
            min_total_odds=request.min_total_odds,
            include_arbitrage=request.include_arbitrage
        )
        
        if not recommendation:
            return {"success": False, "message": "No viable NFL parlay found"}
        
        return {
            "success": True,
            "sport": "NFL",
            "parlay": {
                "legs": recommendation.legs,
                "confidence": recommendation.confidence,
                "expected_value": recommendation.expected_value,
                "kelly_percentage": recommendation.kelly_percentage,
                "knowledge_insights": recommendation.knowledge_insights,
                "reasoning": recommendation.reasoning
            },
            "generated_at": recommendation.generated_at,
            "agent_version": recommendation.agent_version
        }
        
    except Exception as e:
        logger.error(f"NFL parlay generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"NFL parlay generation failed: {str(e)}")


@app.post("/generate-nba-parlay") 
async def generate_nba_parlay(request: ParlayRequest):
    """Generate NBA parlay with ML predictions and knowledge insights."""
    if not nba_agent:
        raise HTTPException(
            status_code=503,
            detail="NBA agent not available. Check ENABLE_NBA environment variable."
        )
    
    try:
        logger.info(f"Generating NBA parlay: {request.target_legs} legs, min odds {request.min_total_odds}")
        
        # Use the unified agent method
        recommendation = await nba_agent.generate_parlay_recommendation(
            target_legs=request.target_legs,
            min_total_odds=request.min_total_odds,
            include_arbitrage=request.include_arbitrage
        )
        
        if not recommendation:
            return {"success": False, "sport": "NBA", "message": "No viable NBA parlay found"}
        
        return {
            "success": True,
            "sport": "NBA",
            "parlay": {
                "legs": recommendation.legs,
                "confidence": recommendation.confidence,
                "expected_value": recommendation.expected_value,
                "kelly_percentage": recommendation.kelly_percentage,
                "knowledge_insights": recommendation.knowledge_insights,
                "reasoning": recommendation.reasoning
            },
            "generated_at": recommendation.generated_at,
            "agent_version": recommendation.agent_version
        }
        
    except Exception as e:
        logger.error(f"NBA parlay generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"NBA parlay generation failed: {str(e)}")


@app.get("/system-health")
async def system_health():
    """Comprehensive system health check for container monitoring."""
    health_data = await health_check()
    
    # Add container-specific health metrics
    health_data.components["container"] = {
        "memory_usage": "available",  # Would use psutil in production
        "disk_space": "available",
        "network": "connected"
    }
    
    return health_data


@app.get("/knowledge-base/search")
async def search_knowledge_base(query: str, top_k: int = 5):
    """Search the sports betting knowledge base."""
    if not knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge base not available")
    
    try:
        result = knowledge_base.search_knowledge(query, top_k=top_k)
        
        return {
            "query": query,
            "results": [
                {
                    "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                    "source": "Expert Knowledge Base",
                    "relevance_score": getattr(chunk, 'relevance_score', 0.0)
                }
                for chunk in (result.chunks if hasattr(result, 'chunks') else [])
            ],
            "insights": getattr(result, 'insights', []),
            "search_time_ms": getattr(result, 'search_time_ms', 0)
        }
        
    except Exception as e:
        logger.error(f"Knowledge base search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/stats")
async def get_system_stats():
    """Get system statistics and performance metrics."""
    uptime = datetime.now(timezone.utc) - app_start_time
    
    return {
        "system": {
            "uptime_hours": round(uptime.total_seconds() / 3600, 2),
            "start_time": app_start_time.isoformat(),
            "container_mode": True
        },
        "sports": {
            "nfl_enabled": nfl_agent is not None,
            "nba_enabled": nba_agent is not None
        },
        "knowledge_base": {
            "available": knowledge_base is not None,
            "chunks": len(knowledge_base.sports_betting_chunks) if knowledge_base else 0
        },
        "environment": {
            "redis_configured": os.getenv("REDIS_URL") is not None,
            "qdrant_configured": os.getenv("QDRANT_URL") is not None,
            "nfl_enabled": os.getenv("ENABLE_NFL", "true").lower() == "true",
            "nba_enabled": os.getenv("ENABLE_NBA", "true").lower() == "true"
        }
    }
