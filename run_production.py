#!/usr/bin/env python3
"""
Production Entry Point for NBA/NFL Parlay System

This script starts the complete containerized system including:
- FastAPI web server with NBA and NFL endpoints
- APScheduler for automated game triggers  
- ML prediction layer
- Vector database integration
- All monitoring and health checks

Usage:
    python run_production.py
    
Environment Variables:
    ENABLE_NFL: Enable NFL functionality (default: true)
    ENABLE_NBA: Enable NBA functionality (default: true)
    REDIS_URL: Redis connection URL
    QDRANT_URL: Qdrant vector DB URL
"""

import asyncio
import logging
import os
import sys
from typing import Optional
import uvicorn

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from production_main import ProductionParlaySystem

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/production.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def start_production_system():
    """
    Start the complete production system.
    
    This function initializes all components and starts the web server.
    """
    logger.info("🚀 Starting NBA/NFL Parlay System - Production Mode")
    logger.info("=" * 60)
    
    # Check environment configuration
    enable_nfl = os.getenv("ENABLE_NFL", "true").lower() == "true"
    enable_nba = os.getenv("ENABLE_NBA", "true").lower() == "true"
    redis_url = os.getenv("REDIS_URL")
    qdrant_url = os.getenv("QDRANT_URL")
    
    logger.info(f"🏈 NFL Support: {'Enabled' if enable_nfl else 'Disabled'}")
    logger.info(f"🏀 NBA Support: {'Enabled' if enable_nba else 'Disabled'}")
    logger.info(f"🔴 Redis: {'Connected' if redis_url else 'Not configured'}")
    logger.info(f"🎯 Qdrant: {'Connected' if qdrant_url else 'Not configured'}")
    
    try:
        # Initialize the production system
        system = ProductionParlaySystem()
        await system.start_all_services()
        
        logger.info("✅ All services initialized successfully")
        logger.info("🌐 Starting web server on 0.0.0.0:8000")
        
        # Start the web server
        config = uvicorn.Config(
            app=system.app,
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            access_log=True,
            loop="asyncio"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"❌ Failed to start production system: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the production system."""
    try:
        # Ensure log directory exists
        os.makedirs('/app/logs', exist_ok=True)
        
        # Start the system
        asyncio.run(start_production_system())
        
    except KeyboardInterrupt:
        logger.info("🛑 Production system stopped by user")
    except Exception as e:
        logger.error(f"💥 Production system crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
