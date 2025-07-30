# =============================================================================
# QuranBot - Real-time Bot Status Monitor
# =============================================================================
# Monitors bot status and updates dashboard statistics in real-time
# =============================================================================

import asyncio
import json
import time
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Dict, Optional, Any
import discord
try:
    import psutil
except ImportError:
    psutil = None

from ..core.logger import StructuredLogger
from ..services.database_service import QuranBotDatabaseService


class BotStatusMonitor:
    """
    Real-time bot status monitor for dashboard integration.
    
    Features:
    - Updates bot_statistics table with real-time data
    - Creates discord_api_monitor.json for performance metrics
    - Tracks gateway connection status
    - Monitors API calls and response times
    - Records system events and errors
    """
    
    def __init__(self, bot: discord.Client, db_service: QuranBotDatabaseService, data_dir: Path):
        self.bot = bot
        self.db_service = db_service
        self.logger = StructuredLogger(__name__)
        self.data_dir = data_dir
        self.metrics_file = data_dir / "discord_api_monitor.json"
        
        # Tracking variables
        self.start_time = time.time()
        self.api_calls = []
        self.gateway_latency_history = []
        self.error_count = 0
        self.command_count = 0
        self.message_count = 0
        
        # Ensure metrics file exists
        self._initialize_metrics_file()
        
    def _initialize_metrics_file(self):
        """Initialize metrics file if it doesn't exist"""
        if not self.metrics_file.exists():
            initial_data = {
                "api_metrics": [],
                "health_history": [],
                "rate_limits": {},
                "last_update": datetime.now(UTC).isoformat()
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(initial_data, f, indent=2)
                
    async def start(self):
        """Start the monitoring tasks"""
        await self.logger.info("Starting Bot Status Monitor")
        
        # Record bot startup
        await self.record_bot_startup()
        
        # Start monitoring tasks
        asyncio.create_task(self._update_loop())
        asyncio.create_task(self._metrics_loop())
        
    async def record_bot_startup(self):
        """Record bot startup in database"""
        try:
            await self.db_service.update_bot_statistics(
                last_startup=datetime.now(UTC).isoformat(),
                total_sessions=1  # Will be incremented from current value
            )
            
            # Log system event
            await self.db_service.log_system_event(
                event_type="bot_startup",
                event_data=json.dumps({
                    "bot_id": str(self.bot.user.id) if self.bot.user else "unknown",
                    "bot_name": str(self.bot.user) if self.bot.user else "unknown",
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                severity="info"
            )
            
            await self.logger.info("Bot startup recorded in database")
            
        except Exception as e:
            await self.logger.error(f"Failed to record bot startup: {e}")
            
    async def _update_loop(self):
        """Main update loop for bot statistics"""
        while True:
            try:
                await self.update_bot_statistics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                await self.logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _metrics_loop(self):
        """Update performance metrics file"""
        while True:
            try:
                await self.update_metrics_file()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                await self.logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(10)
                
    async def update_bot_statistics(self):
        """Update bot statistics in database"""
        try:
            runtime_hours = (time.time() - self.start_time) / 3600
            
            # Get current stats from database
            current_stats = await self.db_service.get_bot_statistics()
            
            # Calculate new values - only use fields that exist in the table
            total_runtime = current_stats.get('total_runtime_hours', 0) + runtime_hours
            total_sessions = current_stats.get('total_sessions', 0)
            total_completed = current_stats.get('total_completed_sessions', 0)
            
            # Update database with only valid fields
            await self.db_service.update_bot_statistics(
                total_runtime_hours=total_runtime,
                total_sessions=total_sessions,  # Keep existing
                total_completed_sessions=total_completed,  # Keep existing
                last_startup=current_stats.get('last_startup'),  # Keep existing
                favorite_reciter=current_stats.get('favorite_reciter', 'Saad Al Ghamdi')
            )
            
            # Reset counters
            self.command_count = 0
            self.message_count = 0
            self.error_count = 0
            
        except Exception as e:
            await self.logger.error(f"Failed to update bot statistics: {e}")
            
    async def update_metrics_file(self):
        """Update performance metrics JSON file"""
        try:
            # Load existing data
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
                
            # Add current health status
            health_status = {
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "online" if self.bot.is_ready() else "offline",
                "gateway_connected": self.bot.is_ready(),
                "gateway_latency": self.bot.latency if self.bot.is_ready() else 0,
                "shard_count": len(self.bot.shards) if hasattr(self.bot, 'shards') else 1,
                "guild_count": len(self.bot.guilds) if self.bot.is_ready() else 0,
                "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024 if psutil else 0.0,
                "cpu_percent": psutil.Process().cpu_percent(interval=0.1) if psutil else 0.0
            }
            
            # Keep only last 100 health records
            data['health_history'].append(health_status)
            data['health_history'] = data['health_history'][-100:]
            
            # Add recent API metrics
            if self.api_calls:
                data['api_metrics'].extend(self.api_calls)
                data['api_metrics'] = data['api_metrics'][-1000:]  # Keep last 1000
                self.api_calls = []  # Clear after adding
                
            data['last_update'] = datetime.now(UTC).isoformat()
            
            # Write back to file
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            await self.logger.error(f"Failed to update metrics file: {e}")
            
    def record_api_call(self, endpoint: str, response_time: float, status_code: int):
        """Record an API call for metrics"""
        self.api_calls.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "endpoint": endpoint,
            "response_time": response_time,
            "status_code": status_code
        })
        
    def record_command(self, command_name: str, guild_id: Optional[int] = None):
        """Record a command execution"""
        self.command_count += 1
        
    def record_message(self):
        """Record a message processed"""
        self.message_count += 1
        
    def record_error(self, error_type: str, error_message: str):
        """Record an error"""
        self.error_count += 1
        
    async def record_quiz_sent(self, user_id: str, question_id: str):
        """Record quiz question sent"""
        try:
            # Get current quiz stats and update
            current_stats = await self.db_service.get_quiz_statistics()
            questions_sent = current_stats.get('questions_sent', 0) + 1
            
            await self.db_service.update_quiz_statistics(
                questions_sent=questions_sent
            )
            
            # Log event
            await self.db_service.log_system_event(
                event_type="quiz_sent",
                event_data=json.dumps({
                    "user_id": user_id,
                    "question_id": question_id,
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                severity="info"
            )
            
        except Exception as e:
            await self.logger.error(f"Failed to record quiz sent: {e}")
            
    async def record_quiz_answered(self, user_id: str, correct: bool):
        """Record quiz answer"""
        try:
            # Get current quiz stats and update
            current_stats = await self.db_service.get_quiz_statistics()
            total_attempts = current_stats.get('total_attempts', 0) + 1
            correct_answers = current_stats.get('correct_answers', 0)
            
            if correct:
                correct_answers += 1
                
            await self.db_service.update_quiz_statistics(
                total_attempts=total_attempts,
                correct_answers=correct_answers
            )
            
            # Log event
            await self.db_service.log_system_event(
                event_type="quiz_answered",
                event_data=json.dumps({
                    "user_id": user_id,
                    "correct": correct,
                    "timestamp": datetime.now(UTC).isoformat()
                }),
                severity="info"
            )
            
        except Exception as e:
            await self.logger.error(f"Failed to record quiz answer: {e}")
            
    async def shutdown(self):
        """Clean shutdown of monitor"""
        try:
            # Record shutdown - only update valid fields
            await self.db_service.update_bot_statistics(
                last_shutdown=datetime.now(UTC).isoformat()
            )
            
            # Final metrics update
            await self.update_metrics_file()
            
            await self.logger.info("Bot Status Monitor shutdown complete")
            
        except Exception as e:
            await self.logger.error(f"Error during monitor shutdown: {e}")