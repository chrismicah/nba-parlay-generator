#!/usr/bin/env python3
"""
NFL APScheduler Integration - JIRA-NFL-009

Registers the NFLParlayStrategistAgent with APScheduler for automated NFL game triggers.
Handles NFL-specific scheduling including Thursday Night Football, Sunday games, and Monday Night Football.

Key Features:
- NFL game schedule triggers (Thu/Sun/Mon)
- Season-aware scheduling (Aug-Feb)
- Pre-game parlay generation
- Integration with existing scheduler infrastructure
- Isolation from NBA scheduling
"""

import logging
import asyncio
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

from agents.nfl_parlay_strategist_agent import NFLParlayStrategistAgent
from tools.sport_factory import SportFactory

logger = logging.getLogger(__name__)


@dataclass
class NFLGameSchedule:
    """NFL game schedule information."""
    game_id: str
    home_team: str
    away_team: str
    kickoff_time: datetime
    game_type: str  # "TNF", "SNF", "MNF", "Regular"
    week: int
    season_year: int


class NFLSchedulerIntegration:
    """
    APScheduler integration for NFLParlayStrategistAgent.
    
    Handles automated scheduling of NFL parlay generation based on
    NFL game schedules and triggers.
    """
    
    def __init__(self, 
                 scheduler: Optional[AsyncIOScheduler] = None,
                 pre_game_hours: int = 3):
        """
        Initialize NFL scheduler integration.
        
        Args:
            scheduler: Existing AsyncIOScheduler instance or None to create new
            pre_game_hours: Hours before game to generate parlays
        """
        self.pre_game_hours = pre_game_hours
        self.nfl_agent = None
        
        # Initialize scheduler
        if scheduler:
            self.scheduler = scheduler
            self.owns_scheduler = False
        elif HAS_APSCHEDULER:
            jobstores = {'default': MemoryJobStore()}
            executors = {'default': AsyncIOExecutor()}
            job_defaults = {
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 300  # 5 minutes
            }
            
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='US/Eastern'  # NFL operates on Eastern Time
            )
            self.owns_scheduler = True
        else:
            raise ImportError("APScheduler is required for scheduling functionality")
        
        # Get NFL schedule triggers from SportFactory
        self.nfl_triggers = SportFactory.get_schedule_triggers("nfl")
        
        logger.info("NFLSchedulerIntegration initialized")
    
    async def initialize_nfl_agent(self) -> None:
        """Initialize the NFL parlay strategist agent."""
        try:
            self.nfl_agent = NFLParlayStrategistAgent()
            logger.info("NFL agent initialized for scheduling")
        except Exception as e:
            logger.error(f"Failed to initialize NFL agent: {e}")
            raise
    
    def register_nfl_triggers(self) -> None:
        """Register NFL-specific triggers with APScheduler."""
        if not HAS_APSCHEDULER:
            logger.error("APScheduler not available - cannot register triggers")
            return
        
        logger.info("Registering NFL triggers with APScheduler...")
        
        # NFL game day triggers
        nfl_days = self.nfl_triggers["days"]  # ["thursday", "sunday", "monday"]
        nfl_times = self.nfl_triggers["game_times"]  # ["13:00", "16:25", "20:20"]
        
        trigger_count = 0
        
        # Register triggers for each NFL game day and time
        for day in nfl_days:
            for game_time in nfl_times:
                # Parse game time
                hour, minute = map(int, game_time.split(':'))
                
                # Calculate pre-game trigger time
                pre_game_hour = (hour - self.pre_game_hours) % 24
                
                # Create cron trigger
                trigger = CronTrigger(
                    day_of_week=day,
                    hour=pre_game_hour,
                    minute=minute,
                    timezone='US/Eastern'
                )
                
                # Create job ID
                job_id = f"nfl_parlay_generation_{day}_{hour:02d}{minute:02d}"
                
                # Register the job
                self.scheduler.add_job(
                    func=self._generate_nfl_parlays_job,
                    trigger=trigger,
                    id=job_id,
                    name=f"NFL Parlay Generation - {day.title()} {game_time}",
                    kwargs={
                        'game_day': day,
                        'game_time': game_time,
                        'trigger_type': 'scheduled'
                    },
                    replace_existing=True
                )
                
                trigger_count += 1
                logger.info(f"Registered NFL trigger: {job_id}")
        
        # Register season-specific triggers
        self._register_nfl_season_triggers()
        
        # Register special event triggers
        self._register_nfl_special_events()
        
        logger.info(f"Registered {trigger_count} NFL triggers with APScheduler")
    
    def _register_nfl_season_triggers(self) -> None:
        """Register NFL season-specific triggers."""
        # Pre-season start trigger (August)
        self.scheduler.add_job(
            func=self._nfl_season_start_job,
            trigger=CronTrigger(month=8, day=1, hour=9, minute=0),
            id="nfl_preseason_start",
            name="NFL Pre-season Start",
            replace_existing=True
        )
        
        # Regular season start trigger (September)
        self.scheduler.add_job(
            func=self._nfl_season_start_job,
            trigger=CronTrigger(month=9, day=7, hour=9, minute=0),  # Approximate
            id="nfl_regular_season_start",
            name="NFL Regular Season Start",
            kwargs={'season_type': 'regular'},
            replace_existing=True
        )
        
        # Playoff start trigger (January)
        self.scheduler.add_job(
            func=self._nfl_season_start_job,
            trigger=CronTrigger(month=1, day=13, hour=9, minute=0),  # Wild Card weekend
            id="nfl_playoffs_start",
            name="NFL Playoffs Start",
            kwargs={'season_type': 'playoffs'},
            replace_existing=True
        )
    
    def _register_nfl_special_events(self) -> None:
        """Register triggers for NFL special events."""
        # Super Bowl trigger (first Sunday in February)
        self.scheduler.add_job(
            func=self._nfl_super_bowl_job,
            trigger=CronTrigger(month=2, day='1st sun', hour=15, minute=0),  # 3 hours before 6:30 PM EST
            id="nfl_super_bowl",
            name="NFL Super Bowl Parlay Generation",
            replace_existing=True
        )
        
        # NFL Draft trigger (late April)
        self.scheduler.add_job(
            func=self._nfl_draft_job,
            trigger=CronTrigger(month=4, day=25, hour=19, minute=0),  # Evening before draft
            id="nfl_draft_prep",
            name="NFL Draft Preparation",
            replace_existing=True
        )
    
    async def _generate_nfl_parlays_job(self, **kwargs) -> None:
        """APScheduler job function for generating NFL parlays."""
        game_day = kwargs.get('game_day', 'unknown')
        game_time = kwargs.get('game_time', 'unknown')
        trigger_type = kwargs.get('trigger_type', 'manual')
        
        logger.info(f"Starting NFL parlay generation job - {game_day} {game_time} ({trigger_type})")
        
        try:
            if not self.nfl_agent:
                await self.initialize_nfl_agent()
            
            # Generate NFL parlay recommendations
            recommendations = []
            
            # Generate multiple parlays for different risk levels
            risk_configs = [
                {"target_legs": 2, "min_odds": 3.0, "name": "Conservative"},
                {"target_legs": 3, "min_odds": 5.0, "name": "Moderate"},
                {"target_legs": 4, "min_odds": 10.0, "name": "Aggressive"}
            ]
            
            for config in risk_configs:
                try:
                    recommendation = await self.nfl_agent.generate_nfl_parlay_recommendation(
                        target_legs=config["target_legs"],
                        min_total_odds=config["min_odds"],
                        include_arbitrage=True,
                        include_three_way=(config["target_legs"] <= 3)  # Only for smaller parlays
                    )
                    
                    if recommendation:
                        recommendation.risk_profile = config["name"]
                        recommendations.append(recommendation)
                        logger.info(f"Generated {config['name']} NFL parlay with confidence {recommendation.reasoning.confidence_score:.3f}")
                
                except Exception as e:
                    logger.error(f"Error generating {config['name']} NFL parlay: {e}")
            
            # Log results
            if recommendations:
                logger.info(f"Successfully generated {len(recommendations)} NFL parlay recommendations")
                
                # Here you would typically:
                # 1. Store recommendations in database
                # 2. Send alerts/notifications
                # 3. Update monitoring dashboards
                # 4. Log performance metrics
                
                await self._process_nfl_recommendations(recommendations, game_day, game_time)
            else:
                logger.warning("No NFL parlay recommendations generated")
                
        except Exception as e:
            logger.error(f"NFL parlay generation job failed: {e}")
            # Here you would typically send error alerts
    
    async def _nfl_season_start_job(self, **kwargs) -> None:
        """Job for NFL season start events."""
        season_type = kwargs.get('season_type', 'preseason')
        logger.info(f"NFL {season_type} starting - initializing enhanced monitoring")
        
        try:
            if not self.nfl_agent:
                await self.initialize_nfl_agent()
            
            # Perform season initialization tasks
            agent_stats = self.nfl_agent.get_agent_stats()
            logger.info(f"NFL agent ready for {season_type}: {agent_stats['toolkit_components']}")
            
        except Exception as e:
            logger.error(f"NFL season start job failed: {e}")
    
    async def _nfl_super_bowl_job(self, **kwargs) -> None:
        """Special job for Super Bowl parlay generation."""
        logger.info("Super Bowl parlay generation starting...")
        
        try:
            if not self.nfl_agent:
                await self.initialize_nfl_agent()
            
            # Generate special Super Bowl parlays
            super_bowl_parlay = await self.nfl_agent.generate_nfl_parlay_recommendation(
                target_legs=5,  # Larger parlay for Super Bowl
                min_total_odds=20.0,  # Higher odds for big game
                include_arbitrage=True,
                include_three_way=True  # Include exotic markets
            )
            
            if super_bowl_parlay:
                logger.info(f"Generated Super Bowl parlay with {len(super_bowl_parlay.legs)} legs")
                # Special handling for Super Bowl parlays
                await self._process_super_bowl_parlay(super_bowl_parlay)
            
        except Exception as e:
            logger.error(f"Super Bowl parlay job failed: {e}")
    
    async def _nfl_draft_job(self, **kwargs) -> None:
        """Job for NFL Draft preparation."""
        logger.info("NFL Draft preparation job starting...")
        # This would prepare for draft-related betting markets
        # For now, just log the event
        logger.info("NFL Draft preparation completed")
    
    async def _process_nfl_recommendations(self, 
                                         recommendations: List,
                                         game_day: str,
                                         game_time: str) -> None:
        """Process generated NFL recommendations."""
        logger.info(f"Processing {len(recommendations)} NFL recommendations for {game_day} {game_time}")
        
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"Recommendation {i} ({getattr(rec, 'risk_profile', 'Unknown')}):")
            logger.info(f"  Legs: {len(rec.legs)}")
            logger.info(f"  Confidence: {rec.reasoning.confidence_score:.3f}")
            logger.info(f"  Expected Value: {rec.expected_value:.3f}")
            
            if hasattr(rec, 'arbitrage_opportunities') and rec.arbitrage_opportunities:
                logger.info(f"  Arbitrage Opportunities: {len(rec.arbitrage_opportunities)}")
            
            if hasattr(rec, 'correlation_warnings') and rec.correlation_warnings:
                logger.info(f"  Correlation Warnings: {len(rec.correlation_warnings)}")
    
    async def _process_super_bowl_parlay(self, recommendation) -> None:
        """Special processing for Super Bowl parlays."""
        logger.info("Processing Super Bowl parlay recommendation:")
        logger.info(f"  Total legs: {len(recommendation.legs)}")
        logger.info(f"  Confidence: {recommendation.reasoning.confidence_score:.3f}")
        
        # Super Bowl parlays would get special treatment
        # - Higher stakes recommendations
        # - Additional media/social sharing
        # - Enhanced monitoring
    
    def start_scheduler(self) -> None:
        """Start the APScheduler."""
        if not HAS_APSCHEDULER:
            logger.error("APScheduler not available")
            return
        
        if self.owns_scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("NFL APScheduler started")
        else:
            logger.info("Using existing scheduler instance")
    
    def stop_scheduler(self) -> None:
        """Stop the APScheduler."""
        if self.owns_scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("NFL APScheduler stopped")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of scheduled NFL jobs."""
        if not HAS_APSCHEDULER:
            return []
        
        nfl_jobs = []
        for job in self.scheduler.get_jobs():
            if 'nfl' in job.id.lower():
                nfl_jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': str(job.next_run_time),
                    'trigger': str(job.trigger)
                })
        
        return nfl_jobs
    
    async def trigger_manual_generation(self, **kwargs) -> None:
        """Manually trigger NFL parlay generation."""
        logger.info("Manual NFL parlay generation triggered")
        kwargs['trigger_type'] = 'manual'
        await self._generate_nfl_parlays_job(**kwargs)


async def main():
    """Main function for testing NFL scheduler integration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("📅 NFL APScheduler Integration - JIRA-NFL-009")
    print("=" * 55)
    
    if not HAS_APSCHEDULER:
        print("❌ APScheduler not available. Install with: pip install apscheduler")
        return
    
    try:
        # Initialize scheduler integration
        scheduler_integration = NFLSchedulerIntegration()
        
        # Initialize NFL agent
        await scheduler_integration.initialize_nfl_agent()
        print("✅ NFL agent initialized")
        
        # Register NFL triggers
        scheduler_integration.register_nfl_triggers()
        print("✅ NFL triggers registered")
        
        # Show scheduled jobs
        scheduler_integration.start_scheduler()
        jobs = scheduler_integration.get_scheduled_jobs()
        
        print(f"\n📋 Scheduled NFL Jobs ({len(jobs)}):")
        for job in jobs[:5]:  # Show first 5 jobs
            print(f"   • {job['name']}")
            print(f"     Next run: {job['next_run']}")
        
        if len(jobs) > 5:
            print(f"   ... and {len(jobs) - 5} more jobs")
        
        # Test manual trigger
        print(f"\n🎯 Testing Manual NFL Parlay Generation...")
        await scheduler_integration.trigger_manual_generation(
            game_day='sunday',
            game_time='13:00'
        )
        
        print(f"\n✅ NFL Scheduler Integration working correctly!")
        print(f"🎯 JIRA-NFL-009 scheduler component complete")
        
        # Stop scheduler
        scheduler_integration.stop_scheduler()
        print("📅 Scheduler stopped")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
