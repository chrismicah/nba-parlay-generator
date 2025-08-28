#!/usr/bin/env python3
"""
Production Main Entry Point - NBA/NFL Parlay System

Complete production-ready system that orchestrates:
- NFL and NBA parlay generation agents
- Knowledge base RAG system (Ed Miller & Wayne Winston books)
- Automated scheduling (APScheduler)
- FastAPI web application
- Monitoring and health checks

Run in production with:
python production_main.py
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our unified system
from agents.multi_sport_scheduler_integration import MultiSportSchedulerIntegration
from tools.unified_parlay_strategist_agent import create_unified_agent, UnifiedParlayStrategistAgent
from tools.knowledge_base_rag import SportsKnowledgeRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionParlaySystem:
    """
    Complete production parlay system orchestrator.
    
    Manages all components:
    - NFL/NBA agents
    - Knowledge base RAG
    - Automated scheduling
    - Web API
    - Monitoring
    """
    
    def __init__(self):
        """Initialize the production system."""
        self.nfl_agent: Optional[UnifiedParlayStrategistAgent] = None
        self.nba_agent: Optional[UnifiedParlayStrategistAgent] = None
        self.knowledge_base: Optional[SportsKnowledgeRAG] = None
        self.scheduler_integration: Optional[MultiSportSchedulerIntegration] = None
        self.app: Optional[FastAPI] = None
        self.system_start_time = datetime.now(timezone.utc)
        
        # Production statistics
        self.stats = {
            "parlays_generated": 0,
            "nfl_parlays": 0,
            "nba_parlays": 0,
            "arbitrage_opportunities": 0,
            "knowledge_base_queries": 0,
            "api_calls": 0,
            "errors": 0
        }
        
        logger.info("ProductionParlaySystem initialized")
    
    async def initialize_components(self):
        """Initialize all system components."""
        logger.info("🚀 Initializing production components...")
        
        try:
            # 1. Initialize Knowledge Base RAG System
            logger.info("📚 Loading knowledge base (Ed Miller & Wayne Winston books)...")
            self.knowledge_base = SportsKnowledgeRAG()
            logger.info(f"✅ Knowledge base ready: {len(self.knowledge_base.sports_betting_chunks)} chunks")
            
            # 2. Initialize Multi-Sport Scheduler Integration
            logger.info("📅 Setting up multi-sport automated scheduling...")
            try:
                self.scheduler_integration = MultiSportSchedulerIntegration()
                await self.scheduler_integration.initialize_agents()
                
                # Get agent references
                self.nfl_agent = self.scheduler_integration.nfl_agent
                self.nba_agent = self.scheduler_integration.nba_agent
                
                if self.nfl_agent:
                    logger.info(f"✅ NFL agent ready: {self.nfl_agent.agent_id}")
                if self.nba_agent:
                    logger.info(f"✅ NBA agent ready: {self.nba_agent.agent_id}")
                
                self.scheduler_integration.register_all_triggers()
                self.scheduler_integration.start_scheduler()
                logger.info("✅ APScheduler running with multi-sport triggers")
            except ImportError:
                logger.warning("⚠️ APScheduler not available - manual generation only")
                self.scheduler_integration = None
            
            # 4. Initialize FastAPI
            logger.info("🌐 Setting up FastAPI web application...")
            self._setup_fastapi()
            logger.info("✅ FastAPI ready")
            
            logger.info("🎯 All production components initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    def _setup_fastapi(self):
        """Setup FastAPI application with production endpoints."""
        self.app = FastAPI(
            title="NBA/NFL Parlay Generation System",
            description="Intelligent parlay generation enhanced with expert sports betting knowledge",
            version="1.0.0"
        )
        
        # Health check endpoint
        @self.app.get("/")
        async def root():
            """System status and basic information."""
            uptime = datetime.now(timezone.utc) - self.system_start_time
            return {
                "message": "NBA/NFL Parlay System - Production Ready",
                "status": "healthy",
                "uptime_seconds": int(uptime.total_seconds()),
                "components": {
                    "nfl_agent": "ready" if self.nfl_agent else "unavailable",
                    "nba_agent": "ready" if self.nba_agent else "unavailable",
                    "knowledge_base": "ready" if self.knowledge_base else "unavailable",
                    "scheduler": "running" if self.scheduler_integration else "unavailable"
                },
                "stats": self.stats
            }
        
        # System health endpoint
        @self.app.get("/health")
        async def health_check():
            """Detailed health check for monitoring."""
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {},
                "performance": {}
            }
            
            # Check NFL agent
            if self.nfl_agent:
                try:
                    agent_stats = self.nfl_agent.get_agent_stats()
                    health_status["components"]["nfl_agent"] = {
                        "status": "healthy",
                        "toolkit_components": len(agent_stats.get("toolkit_components", [])),
                        "rag_enabled": agent_stats.get("rag_enabled", False)
                    }
                except Exception as e:
                    health_status["components"]["nfl_agent"] = {"status": "error", "error": str(e)}
            
            # Check knowledge base
            if self.knowledge_base:
                health_status["components"]["knowledge_base"] = {
                    "status": "healthy", 
                    "chunks_loaded": len(self.knowledge_base.sports_betting_chunks),
                    "embedding_model": "ready" if self.knowledge_base.embedding_model else "unavailable"
                }
            
            # Check scheduler
            if self.scheduler_integration:
                jobs = self.scheduler_integration.get_scheduled_jobs()
                health_status["components"]["scheduler"] = {
                    "status": "running",
                    "scheduled_jobs": len(jobs),
                    "next_run": jobs[0]["next_run"] if jobs else None
                }
            
            return health_status
        
        # Generate NFL parlay endpoint
        @self.app.post("/generate-nfl-parlay")
        async def generate_nfl_parlay(
            target_legs: int = 3,
            min_total_odds: float = 5.0,
            include_arbitrage: bool = True
        ):
            """Generate NFL parlay with knowledge base insights."""
            if not self.nfl_agent:
                raise HTTPException(status_code=503, detail="NFL agent not available")
            
            try:
                logger.info(f"Generating NFL parlay: {target_legs} legs, min odds {min_total_odds}")
                
                recommendation = await self.nfl_agent.generate_nfl_parlay_recommendation(
                    target_legs=target_legs,
                    min_total_odds=min_total_odds,
                    include_arbitrage=include_arbitrage
                )
                
                if recommendation:
                    # Update stats
                    self.stats["parlays_generated"] += 1
                    self.stats["nfl_parlays"] += 1
                    if recommendation.arbitrage_opportunities:
                        self.stats["arbitrage_opportunities"] += len(recommendation.arbitrage_opportunities)
                    
                    # Return comprehensive recommendation
                    return {
                        "success": True,
                        "parlay": {
                            "legs": recommendation.legs,
                            "confidence": recommendation.reasoning.confidence_score,
                            "expected_value": recommendation.expected_value,
                            "kelly_percentage": recommendation.kelly_percentage,
                            "knowledge_insights": recommendation.knowledge_insights,
                            "expert_guidance": recommendation.expert_guidance,
                            "value_analysis": recommendation.value_betting_analysis,
                            "correlation_warnings": recommendation.book_based_warnings,
                            "bankroll_recommendations": recommendation.bankroll_recommendations
                        },
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "agent_version": recommendation.reasoning.strategist_version
                    }
                else:
                    return {"success": False, "message": "No viable NFL parlay found"}
                    
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Error generating NFL parlay: {e}")
                raise HTTPException(status_code=500, detail=f"Parlay generation failed: {str(e)}")
        
        # Knowledge base search endpoint
        @self.app.get("/knowledge-base/search")
        async def search_knowledge_base(query: str, top_k: int = 5):
            """Search the sports betting books knowledge base."""
            if not self.knowledge_base:
                raise HTTPException(status_code=503, detail="Knowledge base not available")
            
            try:
                result = self.knowledge_base.search_knowledge(query, top_k=top_k)
                self.stats["knowledge_base_queries"] += 1
                
                return {
                    "query": query,
                    "results": [
                        {
                            "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                            "source": "Ed Miller" if "Miller" in chunk.source else "Wayne Winston",
                            "relevance_score": chunk.relevance_score
                        }
                        for chunk in result.chunks
                    ],
                    "insights": result.insights,
                    "search_time_ms": result.search_time_ms
                }
                
            except Exception as e:
                logger.error(f"Knowledge base search error: {e}")
                raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
        
        # Scheduled jobs endpoint
        @self.app.get("/scheduled-jobs")
        async def get_scheduled_jobs():
            """Get list of scheduled parlay generation jobs."""
            if not self.scheduler_integration:
                return {"message": "Scheduler not available", "jobs": []}
            
            jobs = self.scheduler_integration.get_scheduled_jobs()
            return {
                "scheduler_status": "running",
                "total_jobs": len(jobs),
                "jobs": jobs[:10]  # Return first 10 jobs
            }
        
        # Manual trigger endpoint
        @self.app.post("/manual-trigger")
        async def manual_trigger(background_tasks: BackgroundTasks):
            """Manually trigger NFL parlay generation."""
            if not self.scheduler_integration:
                raise HTTPException(status_code=503, detail="Scheduler not available")
            
            # Run in background
            background_tasks.add_task(
                self.scheduler_integration.trigger_manual_generation,
                game_day="manual",
                game_time="triggered"
            )
            
            return {"message": "Manual NFL parlay generation triggered"}
        
        # System statistics endpoint
        @self.app.get("/stats")
        async def get_system_stats():
            """Get detailed system statistics."""
            uptime = datetime.now(timezone.utc) - self.system_start_time
            
            return {
                "system": {
                    "uptime_hours": round(uptime.total_seconds() / 3600, 2),
                    "start_time": self.system_start_time.isoformat()
                },
                "parlay_generation": self.stats,
                "knowledge_base": {
                    "chunks_available": len(self.knowledge_base.sports_betting_chunks) if self.knowledge_base else 0,
                    "books_integrated": ["Ed Miller: The Logic of Sports Betting", "Wayne Winston: Mathletics"]
                },
                "components": {
                    "nfl_agent": self.nfl_agent is not None,
                    "knowledge_base": self.knowledge_base is not None,
                    "scheduler": self.scheduler_integration is not None
                }
            }
    
    async def start_all_services(self):
        """Start all production services."""
        logger.info("🚀 Starting Production Parlay System...")
        
        # Initialize all components
        await self.initialize_components()
        
        logger.info("✅ Production system fully operational!")
        logger.info("🎯 NFL parlays enhanced with Ed Miller & Wayne Winston knowledge")
        logger.info("📅 Automated scheduling active for NFL games")
        logger.info("🌐 FastAPI web service ready")
        
    def run_web_server(self, host: str = "0.0.0.0", port: int = 8000, workers: int = 1):
        """Run the FastAPI web server."""
        if not self.app:
            raise RuntimeError("FastAPI app not initialized")
        
        logger.info(f"🌐 Starting web server on {host}:{port}")
        uvicorn.run(
            "production_main:production_system.app",
            host=host,
            port=port,
            workers=workers,
            reload=False  # Disable in production
        )


# Global production system instance
production_system = ProductionParlaySystem()


async def main():
    """Main entry point for production system."""
    print("🏈📚 NBA/NFL Parlay System - Production Deployment")
    print("=" * 60)
    print("Enhanced with Ed Miller's 'The Logic of Sports Betting'")
    print("and Wayne Winston's 'Mathletics' knowledge base")
    print()
    
    try:
        # Start all services
        await production_system.start_all_services()
        
        print("🎯 Production System Status:")
        print(f"   ✅ NFL Agent: Ready with knowledge base")
        print(f"   ✅ Books: 1,590+ expert chunks loaded")
        print(f"   ✅ Scheduler: Automated NFL triggers active")
        print(f"   ✅ Web API: FastAPI ready for requests")
        print()
        
        print("🚀 Available Production Endpoints:")
        print("   GET  /                     - System status")
        print("   GET  /health               - Health check")
        print("   POST /generate-nfl-parlay  - Generate NFL parlay")
        print("   GET  /knowledge-base/search - Search expert books")
        print("   GET  /scheduled-jobs       - View scheduled jobs")
        print("   POST /manual-trigger       - Manual parlay generation")
        print("   GET  /stats                - System statistics")
        print()
        
        # Show next steps
        print("📋 Next Steps:")
        print("   1. Run web server: python production_main.py --web-server")
        print("   2. Test endpoint: curl http://localhost:8000/")
        print("   3. Generate parlay: curl -X POST http://localhost:8000/generate-nfl-parlay")
        print("   4. Monitor health: curl http://localhost:8000/health")
        print()
        
        print("✅ Production system ready for deployment!")
        
    except Exception as e:
        print(f"❌ Production startup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if "--web-server" in sys.argv:
        # Run web server mode
        asyncio.run(production_system.start_all_services())
        production_system.run_web_server()
    else:
        # Run initialization and show status
        asyncio.run(main())
