#!/usr/bin/env python3

# =============================================================================
# QuranBot - Dashboard Monitor (VPS Edition)
# =============================================================================
# This script monitors the web dashboard health and sends Discord alerts
# when the dashboard stops working or encounters errors.
#
# Features:
# - Monitors dashboard HTTP endpoints
# - Checks service status
# - Sends Discord alerts for failures
# - Automatic recovery attempts
# - Detailed error reporting
# - Rate limiting to prevent spam
# =============================================================================

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import discord
from discord.ext import commands

# Add the bot's src directory to Python path
BOT_DIR = "/opt/DiscordBots/QuranBot"
sys.path.insert(0, os.path.join(BOT_DIR, "src"))

# Import the Discord logger
from utils.discord_logger import DiscordLogger

# Configuration
DASHBOARD_URL = "http://localhost:8080"
CHECK_INTERVAL = 300  # 5 minutes
ALERT_COOLDOWN = 1800  # 30 minutes between alerts for same issue
MAX_CONSECUTIVE_FAILURES = 3
RECOVERY_ATTEMPTS = 2

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(BOT_DIR, "config", ".env"))

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID") or "0")
GUILD_ID = int(os.getenv("GUILD_ID") or "0")

class DashboardMonitor:
    """
    Monitors the QuranBot dashboard and sends Discord alerts when issues occur.
    """
    
    def __init__(self):
        self.bot = None
        self.discord_logger = None
        self.last_alert_time = {}
        self.consecutive_failures = 0
        self.is_running = False
        self.session = None
        
        # Health check endpoints
        self.endpoints = [
            "/api/status",
            "/api/system", 
            "/api/logs",
            "/api/audio",
            "/api/discord"
        ]
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{BOT_DIR}/logs/dashboard_monitor.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the Discord bot and logger."""
        try:
            # Create bot instance
            intents = discord.Intents.default()
            intents.message_content = True
            self.bot = commands.Bot(command_prefix='!monitor_', intents=intents)
            
            # Setup Discord logger
            if LOGS_CHANNEL_ID != 0:
                self.discord_logger = DiscordLogger(self.bot, LOGS_CHANNEL_ID)
            
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            self.logger.info("Dashboard monitor initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize dashboard monitor: {e}")
            return False
    
    async def check_dashboard_health(self) -> Dict[str, any]:
        """
        Check the health of the dashboard by testing various endpoints.
        
        Returns:
            Dict containing health status and details
        """
        health_status = {
            "overall_healthy": True,
            "timestamp": datetime.now().isoformat(),
            "endpoints": {},
            "service_status": {},
            "errors": []
        }
        
        try:
            # Check service status first
            health_status["service_status"] = await self._check_service_status()
            
            # Check HTTP endpoints
            for endpoint in self.endpoints:
                endpoint_health = await self._check_endpoint(endpoint)
                health_status["endpoints"][endpoint] = endpoint_health
                
                if not endpoint_health["healthy"]:
                    health_status["overall_healthy"] = False
                    health_status["errors"].append(f"Endpoint {endpoint} failed: {endpoint_health['error']}")
            
            # Check if main dashboard page loads
            main_page_health = await self._check_main_page()
            health_status["main_page"] = main_page_health
            
            if not main_page_health["healthy"]:
                health_status["overall_healthy"] = False
                health_status["errors"].append(f"Main page failed: {main_page_health['error']}")
            
        except Exception as e:
            health_status["overall_healthy"] = False
            health_status["errors"].append(f"Health check failed: {str(e)}")
            self.logger.error(f"Health check error: {e}")
        
        return health_status
    
    async def _check_service_status(self) -> Dict[str, any]:
        """Check the systemd service status."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "quranbot-dashboard"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            is_active = result.returncode == 0
            status = result.stdout.strip()
            
            return {
                "active": is_active,
                "status": status,
                "healthy": is_active
            }
            
        except Exception as e:
            return {
                "active": False,
                "status": "unknown",
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_endpoint(self, endpoint: str) -> Dict[str, any]:
        """Check a specific API endpoint."""
        try:
            url = f"{DASHBOARD_URL}{endpoint}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        return {
                            "healthy": True,
                            "status_code": response.status,
                            "response_time": response.headers.get("X-Response-Time", "unknown"),
                            "data_valid": isinstance(data, dict)
                        }
                    except json.JSONDecodeError:
                        return {
                            "healthy": False,
                            "status_code": response.status,
                            "error": "Invalid JSON response"
                        }
                else:
                    return {
                        "healthy": False,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
                    
        except aiohttp.ClientError as e:
            return {
                "healthy": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def _check_main_page(self) -> Dict[str, any]:
        """Check if the main dashboard page loads correctly."""
        try:
            async with self.session.get(DASHBOARD_URL) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Check for key elements that should be present
                    required_elements = [
                        "QuranBot VPS Dashboard",
                        "Bot Status",
                        "System Resources"
                    ]
                    
                    missing_elements = []
                    for element in required_elements:
                        if element not in text:
                            missing_elements.append(element)
                    
                    if missing_elements:
                        return {
                            "healthy": False,
                            "status_code": response.status,
                            "error": f"Missing elements: {', '.join(missing_elements)}"
                        }
                    else:
                        return {
                            "healthy": True,
                            "status_code": response.status,
                            "page_size": len(text)
                        }
                else:
                    return {
                        "healthy": False,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Page check failed: {str(e)}"
            }
    
    async def send_alert(self, alert_type: str, health_status: Dict[str, any]):
        """Send Discord alert about dashboard issues."""
        if not self.discord_logger:
            return
        
        # Check cooldown
        current_time = time.time()
        if alert_type in self.last_alert_time:
            if current_time - self.last_alert_time[alert_type] < ALERT_COOLDOWN:
                return  # Still in cooldown
        
        self.last_alert_time[alert_type] = current_time
        
        try:
            if alert_type == "dashboard_down":
                await self.discord_logger.log_critical_error(
                    "🚨 Dashboard Monitoring Alert - Dashboard Down",
                    None,
                    {
                        "Alert Type": "Dashboard Down",
                        "Check Time": health_status["timestamp"],
                        "Consecutive Failures": str(self.consecutive_failures),
                        "Errors": "\n".join(health_status["errors"][:5]),  # Limit to 5 errors
                        "Service Status": health_status["service_status"].get("status", "unknown"),
                        "Recovery": "Attempting automatic recovery..."
                    }
                )
            
            elif alert_type == "dashboard_degraded":
                await self.discord_logger.log_error(
                    "⚠️ Dashboard Monitoring Alert - Degraded Performance",
                    None,
                    {
                        "Alert Type": "Degraded Performance",
                        "Check Time": health_status["timestamp"],
                        "Failed Endpoints": str(len([e for e in health_status["endpoints"].values() if not e["healthy"]])),
                        "Errors": "\n".join(health_status["errors"][:3]),
                        "Service Status": health_status["service_status"].get("status", "unknown")
                    }
                )
            
            elif alert_type == "dashboard_recovered":
                await self.discord_logger.log_success(
                    "✅ Dashboard Monitoring - Recovery Confirmed",
                    {
                        "Alert Type": "Recovery Confirmed",
                        "Check Time": health_status["timestamp"],
                        "Recovery Time": str(self.consecutive_failures * CHECK_INTERVAL // 60) + " minutes",
                        "Status": "All systems operational",
                        "Endpoints": f"{len([e for e in health_status['endpoints'].values() if e['healthy']])}/{len(health_status['endpoints'])} healthy"
                    }
                )
        
        except Exception as e:
            self.logger.error(f"Failed to send Discord alert: {e}")
    
    async def attempt_recovery(self) -> bool:
        """Attempt to recover the dashboard service."""
        try:
            self.logger.info("Attempting dashboard recovery...")
            
            # Try restarting the dashboard service
            result = subprocess.run(
                ["systemctl", "restart", "quranbot-dashboard"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("Dashboard service restarted successfully")
                
                # Wait a bit for service to start
                await asyncio.sleep(10)
                
                # Check if recovery was successful
                health_status = await self.check_dashboard_health()
                
                if health_status["overall_healthy"]:
                    self.logger.info("Dashboard recovery successful")
                    return True
                else:
                    self.logger.warning("Dashboard service restarted but still unhealthy")
                    return False
            else:
                self.logger.error(f"Failed to restart dashboard service: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            return False
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        self.is_running = True
        self.logger.info("Dashboard monitoring started")
        
        # Send startup notification
        if self.discord_logger:
            try:
                await self.discord_logger.log_system_event(
                    "Dashboard Monitor Started",
                    "🔍 Dashboard monitoring system is now active",
                    {
                        "Check Interval": f"{CHECK_INTERVAL // 60} minutes",
                        "Alert Cooldown": f"{ALERT_COOLDOWN // 60} minutes",
                        "Max Failures": str(MAX_CONSECUTIVE_FAILURES),
                        "Recovery Attempts": str(RECOVERY_ATTEMPTS)
                    }
                )
            except:
                pass
        
        while self.is_running:
            try:
                # Check dashboard health
                health_status = await self.check_dashboard_health()
                
                if health_status["overall_healthy"]:
                    # Dashboard is healthy
                    if self.consecutive_failures > 0:
                        # Recovery detected
                        await self.send_alert("dashboard_recovered", health_status)
                        self.consecutive_failures = 0
                    
                    self.logger.info("Dashboard health check passed")
                    
                else:
                    # Dashboard has issues
                    self.consecutive_failures += 1
                    self.logger.warning(f"Dashboard health check failed (attempt {self.consecutive_failures})")
                    
                    if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        # Dashboard is considered down
                        await self.send_alert("dashboard_down", health_status)
                        
                        # Attempt recovery
                        for attempt in range(RECOVERY_ATTEMPTS):
                            self.logger.info(f"Recovery attempt {attempt + 1}/{RECOVERY_ATTEMPTS}")
                            if await self.attempt_recovery():
                                break
                            await asyncio.sleep(30)  # Wait between recovery attempts
                    
                    elif self.consecutive_failures == 1:
                        # First failure - send degraded alert
                        await self.send_alert("dashboard_degraded", health_status)
                
                # Wait for next check
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def start(self):
        """Start the dashboard monitor."""
        if not await self.initialize():
            return False
        
        try:
            # Start the bot
            await self.bot.start(DISCORD_TOKEN)
        except Exception as e:
            self.logger.error(f"Failed to start Discord bot: {e}")
            return False
    
    async def stop(self):
        """Stop the dashboard monitor."""
        self.is_running = False
        
        if self.session:
            await self.session.close()
        
        if self.bot:
            await self.bot.close()
        
        self.logger.info("Dashboard monitor stopped")

async def main():
    """Main entry point."""
    monitor = DashboardMonitor()
    
    try:
        # Initialize and start monitoring
        if await monitor.initialize():
            # Start monitoring in background
            monitor_task = asyncio.create_task(monitor.monitor_loop())
            
            # Start Discord bot
            await monitor.bot.start(DISCORD_TOKEN)
            
        else:
            print("Failed to initialize dashboard monitor")
            return 1
            
    except KeyboardInterrupt:
        print("\nShutting down dashboard monitor...")
        await monitor.stop()
        return 0
    except Exception as e:
        print(f"Dashboard monitor error: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 