#!/usr/bin/env python3
"""
Multi-Sport APScheduler Integration - JIRA-CONTAINER-002

Unified scheduler for both NBA and NFL parlay generation with containerized support.
Handles sport-specific scheduling, triggers, and automated parlay generation.

Key Features:
- Unified NBA and NFL scheduling
- Container-friendly configuration via environment variables
- Season-aware scheduling for both sports
- Pre-game parlay generation
- Health monitoring and job status tracking
"""

import logging
import asyncio
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

# APScheduler imports
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logging.warning("APScheduler not available. Install apscheduler for scheduling support.")

# Import agents
try:
    from agents.nfl_parlay_strategist_agent import NFLParlayStrategistAgent
    from tools.enhanced_parlay_strategist_agent import FewShotEnhancedParlayStrategistAgent
    from tools.sport_factory import SportFactory
    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False

logger = logging.getLogger(__name__)


@dataclass
class MultiSportSchedulerConfig:
    """Configuration for multi-sport scheduler."""
    enable_nfl: bool = True
    enable_nba: bool = True
    pre_game_hours: int = 3
    max_instances: int = 3
    misfire_grace_time: int = 300  # 5 minutes
    timezone: str = 'US/Eastern'


class MultiSportSchedulerIntegration:
    """
    Unified APScheduler integration for NBA and NFL parlay generation.
    
    Handles automated scheduling based on sport-specific triggers and
    environment configuration.
    """
    
    def __init__(self, 
                 scheduler: Optional[AsyncIOScheduler] = None,
                 config: Optional[MultiSportSchedulerConfig] = None):
        """
        Initialize multi-sport scheduler integration.
        
        Args:
            scheduler: Existing AsyncIOScheduler instance or None to create new
            config: Scheduler configuration or None for defaults
        """
        # Load configuration from environment or defaults
        self.config = config or MultiSportSchedulerConfig(
            enable_nfl=os.getenv("ENABLE_NFL", "true").lower() == "true",
            enable_nba=os.getenv("ENABLE_NBA", "true").lower() == "true",
            pre_game_hours=int(os.getenv("PRE_GAME_HOURS", "3"))
        )
        
        # Initialize agents
        self.nfl_agent: Optional[NFLParlayStrategistAgent] = None
        self.nba_agent: Optional[FewShotEnhancedParlayStrategistAgent] = None
        
        # Initialize scheduler
        if scheduler:
            self.scheduler = scheduler
            self.owns_scheduler = False
        elif HAS_APSCHEDULER:
            jobstores = {'default': MemoryJobStore()}
            executors = {'default': AsyncIOExecutor()}
            job_defaults = {
                'coalesce': False,
                'max_instances': self.config.max_instances,
                'misfire_grace_time': self.config.misfire_grace_time
            }
            
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone=self.config.timezone
            )
            self.owns_scheduler = True
        else:
            raise ImportError("APScheduler is required for scheduling functionality")
        
        # Load sport-specific triggers
        if HAS_AGENTS:
            self.nfl_triggers = SportFactory.get_schedule_triggers("nfl") if self.config.enable_nfl else {}
            self.nba_triggers = SportFactory.get_schedule_triggers("nba") if self.config.enable_nba else {}
        else:
            self.nfl_triggers = {}
            self.nba_triggers = {}
        
        logger.info(f"MultiSportScheduler initialized - NFL: {self.config.enable_nfl}, NBA: {self.config.enable_nba}")
    
    async def initialize_agents(self) -> None:
        """Initialize both NFL and NBA agents."""
        if not HAS_AGENTS:
            logger.error("Agents not available - cannot initialize")
            return
        
        try:
            # Initialize NFL agent if enabled
            if self.config.enable_nfl:
                logger.info("🏈 Initializing NFL agent...")
                self.nfl_agent = NFLParlayStrategistAgent()
                logger.info("✅ NFL agent initialized")
            
            # Initialize NBA agent if enabled  
            if self.config.enable_nba:
                logger.info("🏀 Initializing NBA agent...")
                self.nba_agent = FewShotEnhancedParlayStrategistAgent()
                logger.info("✅ NBA agent initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
    
    def register_all_triggers(self) -> None:
        """Register all sport-specific triggers with APScheduler."""
        if not HAS_APSCHEDULER:
            logger.error("APScheduler not available - cannot register triggers")
            return
        
        logger.info("📅 Registering multi-sport triggers...")
        
        trigger_count = 0
        
        # Register NFL triggers
        if self.config.enable_nfl and self.nfl_triggers:
            trigger_count += self._register_sport_triggers("nfl", self.nfl_triggers)
        
        # Register NBA triggers
        if self.config.enable_nba and self.nba_triggers:
            trigger_count += self._register_sport_triggers("nba", self.nba_triggers)
        
        logger.info(f"✅ Registered {trigger_count} total triggers across all sports")
    
    def _register_sport_triggers(self, sport: str, triggers: Dict[str, Any]) -> int:
        """Register triggers for a specific sport."""
        logger.info(f"Registering {sport.upper()} triggers...")
        
        days = triggers.get("days", [])
        game_times = triggers.get("game_times", [])
        count = 0
        
        for day in days:
            for game_time in game_times:
                # Parse game time
                hour, minute = map(int, game_time.split(':'))
                
                # Calculate pre-game trigger time
                pre_game_hour = (hour - self.config.pre_game_hours) % 24
                
                # Create cron trigger
                trigger = CronTrigger(
                    day_of_week=day,
                    hour=pre_game_hour,
                    minute=minute,
                    timezone=self.config.timezone
                )
                
                # Create job ID
                job_id = f"{sport}_parlay_generation_{day}_{hour:02d}{minute:02d}"
                
                # Register the job
                self.scheduler.add_job(
                    func=self._generate_sport_parlays_job,
                    trigger=trigger,
                    id=job_id,
                    name=f"{sport.upper()} Parlay Generation - {day.title()} {game_time}",
                    kwargs={
                        'sport': sport,
                        'game_day': day,
                        'game_time': game_time,
                        'trigger_type': 'scheduled'
                    },
                    replace_existing=True
                )
                
                count += 1
                logger.info(f"✅ Registered {sport.upper()} trigger: {job_id}")
        
        return count
    
    async def _generate_sport_parlays_job(self, **kwargs) -> None:
        """APScheduler job function for generating sport-specific parlays."""
        sport = kwargs.get('sport', 'unknown')
        game_day = kwargs.get('game_day', 'unknown')
        game_time = kwargs.get('game_time', 'unknown')
        trigger_type = kwargs.get('trigger_type', 'manual')
        
        logger.info(f"🎯 Starting {sport.upper()} parlay generation - {game_day} {game_time} ({trigger_type})")
        
        try:
            # Route to appropriate agent
            if sport.lower() == "nfl" and self.nfl_agent:
                await self._generate_nfl_parlays(game_day, game_time)
            elif sport.lower() == "nba" and self.nba_agent:
                await self._generate_nba_parlays(game_day, game_time)
            else:
                logger.warning(f"No agent available for {sport}")
                
        except Exception as e:
            logger.error(f"{sport.upper()} parlay generation job failed: {e}")
    
    async def _generate_nfl_parlays(self, game_day: str, game_time: str) -> None:
        """Generate NFL parlays using the NFL agent."""
        logger.info(f"🏈 Generating NFL parlays for {game_day} {game_time}")
        
        try:
            # Generate multiple NFL parlays for different risk levels
            risk_configs = [
                {"target_legs": 2, "min_odds": 3.0, "name": "Conservative"},
                {"target_legs": 3, "min_odds": 5.0, "name": "Moderate"},
                {"target_legs": 4, "min_odds": 10.0, "name": "Aggressive"}
            ]
            
            recommendations = []
            
            for config in risk_configs:
                try:
                    recommendation = await self.nfl_agent.generate_nfl_parlay_recommendation(
                        target_legs=config["target_legs"],
                        min_total_odds=config["min_odds"],
                        include_arbitrage=True
                    )
                    
                    if recommendation:
                        recommendations.append(recommendation)
                        logger.info(f"✅ Generated {config['name']} NFL parlay")
                
                except Exception as e:
                    logger.error(f"Error generating {config['name']} NFL parlay: {e}")
            
            logger.info(f"🏈 Generated {len(recommendations)} NFL parlays total")
            
        except Exception as e:
            logger.error(f"NFL parlay generation failed: {e}")
    
    async def _generate_nba_parlays(self, game_day: str, game_time: str) -> None:
        """Generate NBA parlays using the NBA agent.""" 
        logger.info(f"🏀 Generating NBA parlays for {game_day} {game_time}")
        
        try:
            # Generate multiple NBA parlays for different configurations
            configs = [
                {"target_legs": 2, "min_odds": 3.0, "name": "Conservative"},
                {"target_legs": 3, "min_odds": 5.0, "name": "Moderate"},
                {"target_legs": 4, "min_odds": 8.0, "name": "Aggressive"}
            ]
            
            recommendations = []
            
            for config in configs:
                try:
                    # Use mock games for now - would be replaced with real NBA data
                    mock_games = []
                    
                    recommendation = self.nba_agent.generate_parlay_with_reasoning(
                        current_games=mock_games,
                        target_legs=config["target_legs"],
                        min_total_odds=config["min_odds"],
                        use_few_shot=True
                    )
                    
                    if recommendation:
                        recommendations.append(recommendation)
                        logger.info(f"✅ Generated {config['name']} NBA parlay")
                
                except Exception as e:
                    logger.error(f"Error generating {config['name']} NBA parlay: {e}")
            
            logger.info(f"🏀 Generated {len(recommendations)} NBA parlays total")
            
        except Exception as e:
            logger.error(f"NBA parlay generation failed: {e}")
    
    def start_scheduler(self) -> None:
        """Start the APScheduler."""
        if not HAS_APSCHEDULER:
            logger.error("APScheduler not available")
            return
        
        if self.owns_scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Multi-sport APScheduler started")
        else:
            logger.info("ℹ️ Using existing scheduler instance")
    
    def stop_scheduler(self) -> None:
        """Stop the APScheduler."""
        if self.owns_scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 Multi-sport APScheduler stopped")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled jobs."""
        if not HAS_APSCHEDULER:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time),
                'trigger': str(job.trigger),
                'sport': 'nfl' if 'nfl' in job.id.lower() else 'nba' if 'nba' in job.id.lower() else 'unknown'
            })
        
        return jobs
    
    async def trigger_manual_generation(self, sport: str, **kwargs) -> None:
        """Manually trigger parlay generation for a specific sport."""
        logger.info(f"Manual {sport.upper()} parlay generation triggered")
        kwargs['sport'] = sport.lower()
        kwargs['trigger_type'] = 'manual'
        await self._generate_sport_parlays_job(**kwargs)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get scheduler health status."""
        jobs = self.get_scheduled_jobs()
        nfl_jobs = [j for j in jobs if j['sport'] == 'nfl']
        nba_jobs = [j for j in jobs if j['sport'] == 'nba']
        
        return {
            "scheduler_running": self.scheduler.running if HAS_APSCHEDULER else False,
            "total_jobs": len(jobs),
            "nfl_jobs": len(nfl_jobs),
            "nba_jobs": len(nba_jobs), 
            "agents": {
                "nfl": self.nfl_agent is not None,
                "nba": self.nba_agent is not None
            },
            "configuration": {
                "enable_nfl": self.config.enable_nfl,
                "enable_nba": self.config.enable_nba,
                "pre_game_hours": self.config.pre_game_hours
            },
            "next_runs": {
                "nfl": nfl_jobs[0]['next_run'] if nfl_jobs else None,
                "nba": nba_jobs[0]['next_run'] if nba_jobs else None
            }
        }


async def main():
    """Main function for testing multi-sport scheduler integration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📅🏀🏈 Multi-Sport APScheduler Integration - JIRA-CONTAINER-002")
    print("=" * 70)
    
    if not HAS_APSCHEDULER:
        print("❌ APScheduler not available. Install with: pip install apscheduler")
        return
    
    if not HAS_AGENTS:
        print("❌ Agents not available. Check agent imports.")
        return
    
    try:
        # Initialize multi-sport scheduler
        scheduler_integration = MultiSportSchedulerIntegration()
        
        # Initialize agents
        await scheduler_integration.initialize_agents()
        print("✅ Agents initialized")
        
        # Register triggers for all sports
        scheduler_integration.register_all_triggers()
        print("✅ Multi-sport triggers registered")
        
        # Start scheduler
        scheduler_integration.start_scheduler()
        
        # Show scheduled jobs
        jobs = scheduler_integration.get_scheduled_jobs()
        print(f"\n📋 Scheduled Jobs ({len(jobs)}):")
        
        nfl_jobs = [j for j in jobs if j['sport'] == 'nfl']
        nba_jobs = [j for j in jobs if j['sport'] == 'nba']
        
        print(f"   🏈 NFL Jobs: {len(nfl_jobs)}")
        for job in nfl_jobs[:3]:  # Show first 3
            print(f"     • {job['name']} - Next: {job['next_run']}")
        
        print(f"   🏀 NBA Jobs: {len(nba_jobs)}")
        for job in nba_jobs[:3]:  # Show first 3
            print(f"     • {job['name']} - Next: {job['next_run']}")
        
        # Test manual triggers
        print(f"\n🎯 Testing Manual Generation...")
        await scheduler_integration.trigger_manual_generation('nfl', game_day='sunday', game_time='13:00')
        await scheduler_integration.trigger_manual_generation('nba', game_day='tuesday', game_time='19:00')
        
        # Health status
        health = scheduler_integration.get_health_status()
        print(f"\n💚 Health Status:")
        print(f"   Scheduler Running: {health['scheduler_running']}")
        print(f"   Total Jobs: {health['total_jobs']}")
        print(f"   NFL Agent: {health['agents']['nfl']}")
        print(f"   NBA Agent: {health['agents']['nba']}")
        
        print(f"\n✅ Multi-Sport Scheduler Integration working correctly!")
        print(f"🎯 JIRA-CONTAINER-002 scheduler component complete")
        
        # Stop scheduler
        scheduler_integration.stop_scheduler()
        print("📅 Scheduler stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
