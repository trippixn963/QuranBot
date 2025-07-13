# =============================================================================
# QuranBot - Discord Logging Module (VPS Monitoring Edition)
# =============================================================================
# This module provides Discord channel logging for 24/7 VPS monitoring.
# It sends important logs, errors, and system events to a designated Discord
# channel for real-time monitoring and debugging.
#
# Key Features:
# - Real-time error logging to Discord
# - System event notifications
# - Rate limiting and spam prevention
# - Rich embed formatting with color coding
# - Automatic log level filtering
# - VPS status monitoring
# - Graceful fallback when Discord is unavailable
# =============================================================================

import asyncio
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import discord
import pytz
from discord.ext import commands

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class DiscordLogger:
    """
    Discord channel logger for VPS monitoring and real-time debugging.
    
    This class provides comprehensive Discord logging capabilities for
    monitoring QuranBot when running 24/7 on a VPS. It sends formatted
    log messages to a designated Discord channel with proper rate limiting
    and error handling.
    
    Features:
    - Real-time error and warning notifications
    - System event logging (startup, shutdown, connections)
    - Rich embed formatting with color coding
    - Rate limiting to prevent spam
    - Automatic log level filtering
    - Graceful fallback when Discord is unavailable
    """
    
    def __init__(self, bot: commands.Bot, log_channel_id: int, dashboard_url: str = ""):
        """
        Initialize the Discord logger.
        
        Args:
            bot: Discord bot instance
            log_channel_id: ID of the Discord channel for logs
            dashboard_url: Optional dashboard URL for monitoring
        """
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.log_channel = None
        self.rate_limit_cache = {}
        self.max_logs_per_minute = 10
        self.enabled = True
        self.dashboard_url = dashboard_url
        
        # User ID to ping for errors (John's Discord ID)
        self.owner_user_id = 155149108183695360  # John's Discord ID
        
        # Color coding for different log levels
        self.level_colors = {
            "INFO": 0x3498db,      # Blue
            "WARNING": 0xf39c12,   # Orange
            "ERROR": 0xe74c3c,     # Red
            "CRITICAL": 0x8b0000,  # Dark Red
            "SUCCESS": 0x27ae60,   # Green
            "SYSTEM": 0x9b59b6,    # Purple
            "USER": 0x1abc9c,      # Teal
        }
        
        # Emojis for different log types
        self.level_emojis = {
            "INFO": "ℹ️",
            "WARNING": "⚠️", 
            "ERROR": "❌",
            "CRITICAL": "🚨",
            "SUCCESS": "✅",
            "SYSTEM": "🔧",
            "USER": "👤",
        }
    
    async def initialize(self):
        """Initialize the Discord logger by getting the log channel."""
        try:
            if self.log_channel_id:
                self.log_channel = self.bot.get_channel(self.log_channel_id)
                if not self.log_channel:
                    log_error_with_traceback(
                        f"Discord log channel {self.log_channel_id} not found",
                        None
                    )
                    self.enabled = False
                    return False
                
                # Send initial heartbeat after a short delay to allow bot to fully initialize
                self.bot.loop.create_task(self._send_initial_heartbeat())
                
                # Start heartbeat task
                self.bot.loop.create_task(self._heartbeat_task())
                return True
            else:
                self.enabled = False
                return False
                
        except Exception as e:
            log_error_with_traceback("Failed to initialize Discord logger", e)
            self.enabled = False
            return False
    
    async def _send_initial_heartbeat(self):
        """Send initial heartbeat after bot startup."""
        try:
            # Wait 5 seconds to allow bot to fully initialize
            await asyncio.sleep(5)
            
            # Send startup heartbeat
            await self._send_heartbeat(is_startup=True)
            
        except Exception as e:
            log_error_with_traceback("Error sending initial heartbeat", e)

    async def _heartbeat_task(self):
        """Send hourly heartbeat with system status and recent logs."""
        while True:
            try:
                # Wait for the next hour mark
                await self._wait_for_next_hour()
                
                # Send heartbeat
                await self._send_heartbeat()
                
            except Exception as e:
                log_error_with_traceback("Error in heartbeat task", e)
                # Wait 5 minutes before retrying
                await asyncio.sleep(300)
    
    async def _wait_for_next_hour(self):
        """Wait until the next hour mark (e.g., 10:00, 11:00, etc.)."""
        try:
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            
            # Calculate next hour
            next_hour = now_est.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            # Calculate seconds to wait
            wait_seconds = (next_hour - now_est).total_seconds()
            
            # Wait until next hour
            await asyncio.sleep(wait_seconds)
            
        except Exception as e:
            log_error_with_traceback("Error calculating next hour", e)
            # Fallback: wait 1 hour
            await asyncio.sleep(3600)
    
    async def _send_heartbeat(self, is_startup: bool = False):
        """Send heartbeat embed with system status and recent logs."""
        if not self.enabled or not self.log_channel:
            return
        
        try:
            # Get system status
            status_data = await self._get_system_status()
            
            # Get recent logs
            recent_logs = self._get_recent_logs()
            
            # Create heartbeat embed
            if is_startup:
                embed = discord.Embed(
                    title="🚀 Startup Heartbeat",
                    description="**Bot initialization complete - System status**",
                    color=0x00ff00 if status_data["overall_status"] == "healthy" else 0xff9900,
                    timestamp=datetime.utcnow()
                )
            else:
                embed = discord.Embed(
                    title="💓 System Heartbeat",
                    description="**Hourly system health check**",
                    color=0x00ff00 if status_data["overall_status"] == "healthy" else 0xff9900,
                    timestamp=datetime.utcnow()
                )
            
            # Add system status fields
            embed.add_field(
                name="🤖 Bot Status",
                value=f"{'✅ Online' if status_data['bot_online'] else '❌ Offline'}",
                inline=True
            )
            
            embed.add_field(
                name="🎵 Audio Playback",
                value=f"{'✅ Playing' if status_data['audio_playing'] else '❌ Stopped'}",
                inline=True
            )
            
            embed.add_field(
                name="🔗 Voice Connection",
                value=f"{'✅ Connected' if status_data['voice_connected'] else '❌ Disconnected'}",
                inline=True
            )
            
            embed.add_field(
                name="📊 System Health",
                value=f"{'✅ Healthy' if status_data['overall_status'] == 'healthy' else '⚠️ Issues Detected'}",
                inline=True
            )
            
            embed.add_field(
                name="⏰ Uptime",
                value=status_data['uptime'],
                inline=True
            )
            
            embed.add_field(
                name="🎯 Current Surah",
                value=status_data['current_surah'],
                inline=True
            )
            
            # Add dashboard link if configured
            if self.dashboard_url:
                embed.add_field(
                    name="🖥️ Dashboard",
                    value=f"[View Dashboard]({self.dashboard_url})",
                    inline=True
                )
            
            # Add recent logs
            if recent_logs:
                embed.add_field(
                    name="📝 Recent Logs (Last 10 lines)",
                    value=f"```python\n{recent_logs}\n```",
                    inline=False
                )
            
            if is_startup:
                embed.set_footer(text=f"QuranBot VPS Startup • {self._get_timestamp()}")
            else:
                embed.set_footer(text=f"QuranBot VPS Heartbeat • {self._get_timestamp()}")
            
            await self.log_channel.send(embed=embed)
            
        except Exception as e:
            log_error_with_traceback("Error sending heartbeat", e)
    
    async def _get_system_status(self) -> Dict[str, str]:
        """Get current system status information."""
        try:
            # Import here to avoid circular imports
            from src.utils.state_manager import state_manager
            
            status = {
                "bot_online": True,  # If we're running this, bot is online
                "audio_playing": False,
                "voice_connected": False,
                "overall_status": "healthy",
                "uptime": "Unknown",
                "current_surah": "Unknown"
            }
            
            # Check voice connection
            if hasattr(self.bot, 'voice_clients') and self.bot.voice_clients:
                voice_client = self.bot.voice_clients[0]
                status["voice_connected"] = voice_client.is_connected()
                status["audio_playing"] = voice_client.is_playing()
            
            # Get current surah from state
            try:
                playback_state = state_manager.load_playback_state()
                if playback_state and "current_surah" in playback_state:
                    current_surah = playback_state["current_surah"]
                    status["current_surah"] = f"{current_surah}. {self._get_surah_name(current_surah)}"
            except:
                pass
            
            # Calculate uptime
            try:
                import psutil
                process = psutil.Process()
                uptime_seconds = time.time() - process.create_time()
                uptime_hours = int(uptime_seconds // 3600)
                uptime_minutes = int((uptime_seconds % 3600) // 60)
                status["uptime"] = f"{uptime_hours}h {uptime_minutes}m"
            except:
                status["uptime"] = "Unknown"
            
            # Determine overall status
            if not status["voice_connected"] or not status["audio_playing"]:
                status["overall_status"] = "warning"
            
            return status
            
        except Exception as e:
            log_error_with_traceback("Error getting system status", e)
            return {
                "bot_online": True,
                "audio_playing": False,
                "voice_connected": False,
                "overall_status": "error",
                "uptime": "Unknown",
                "current_surah": "Unknown"
            }
    
    def _get_surah_name(self, surah_number: int) -> str:
        """Get surah name from number."""
        surah_names = {
            1: "Al-Fatiha", 2: "Al-Baqarah", 3: "Aal-E-Imran", 4: "An-Nisa",
            5: "Al-Maidah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
            9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
            13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
            17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
            21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
            25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
            29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
            33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
            37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
            41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
            45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
            49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
            53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'ah",
            57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahanah",
            61: "As-Saff", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
            65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
            69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
            73: "Al-Muzzammil", 74: "Al-Muddathir", 75: "Al-Qiyamah", 76: "Al-Insan",
            77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at", 80: "Abasa",
            81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
            85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiyah",
            89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
            93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-Alaq",
            97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-Adiyat",
            101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humazah",
            105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
            109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
            113: "Al-Falaq", 114: "An-Nas"
        }
        return surah_names.get(surah_number, f"Surah {surah_number}")
    
    def _get_recent_logs(self) -> str:
        """Get the last 10 lines from the latest log file."""
        try:
            import os
            from pathlib import Path
            
            # Get the latest log file
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            log_date = now_est.strftime("%Y-%m-%d")
            
            log_file_path = Path(f"logs/{log_date}/logs.log")
            
            if not log_file_path.exists():
                return "No recent logs found"
            
            # Read last 10 lines
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_10_lines = lines[-10:] if len(lines) >= 10 else lines
                
                # Clean up the lines and format them
                formatted_lines = []
                for line in last_10_lines:
                    # Remove extra whitespace and newlines
                    clean_line = line.strip()
                    if clean_line:
                        formatted_lines.append(clean_line)
                
                return '\n'.join(formatted_lines)
                
        except Exception as e:
            log_error_with_traceback("Error reading recent logs", e)
            return f"Error reading logs: {str(e)}"
    
    def _get_error_logs(self, lines: int = 20) -> str:
        """Get recent error-related logs from the latest log file."""
        try:
            import os
            from pathlib import Path
            
            # Get the latest log file
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            log_date = now_est.strftime("%Y-%m-%d")
            
            log_file_path = Path(f"logs/{log_date}/logs.log")
            
            if not log_file_path.exists():
                return "No recent error logs found"
            
            # Read recent lines and filter for errors/warnings
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
                # Get last 50 lines and filter for errors/warnings
                recent_lines = all_lines[-50:] if len(all_lines) >= 50 else all_lines
                error_lines = []
                
                for line in recent_lines:
                    line = line.strip()
                    if line and any(keyword in line.lower() for keyword in ['error', 'warning', 'exception', 'traceback', 'failed', 'critical']):
                        error_lines.append(line)
                
                # Return the most recent error lines
                if error_lines:
                    return '\n'.join(error_lines[-lines:]) if len(error_lines) >= lines else '\n'.join(error_lines)
                else:
                    # If no specific error lines found, return recent lines
                    cleaned_lines = []
                    for line in recent_lines[-lines:]:
                        line = line.strip()
                        if line:
                            cleaned_lines.append(line)
                    return '\n'.join(cleaned_lines) if cleaned_lines else "No recent error logs"
                
        except Exception as e:
            return f"Error reading error logs: {str(e)}"
    
    def _check_rate_limit(self, log_type: str) -> bool:
        """
        Check if we're within rate limits for a specific log type.
        
        Args:
            log_type: Type of log to check
            
        Returns:
            bool: True if within rate limits, False if rate limited
        """
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d-%H-%M")
        
        if log_type not in self.rate_limit_cache:
            self.rate_limit_cache[log_type] = {}
        
        if minute_key not in self.rate_limit_cache[log_type]:
            self.rate_limit_cache[log_type][minute_key] = 0
        
        # Clean old entries (older than 2 minutes)
        keys_to_remove = []
        for key in self.rate_limit_cache[log_type].keys():
            try:
                key_time = datetime.strptime(key, "%Y-%m-%d-%H-%M")
                if (now - key_time).total_seconds() > 120:
                    keys_to_remove.append(key)
            except:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.rate_limit_cache[log_type][key]
        
        # Check current minute's count
        current_count = self.rate_limit_cache[log_type][minute_key]
        if current_count >= self.max_logs_per_minute:
            return False
        
        self.rate_limit_cache[log_type][minute_key] += 1
        return True
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp in EST timezone."""
        try:
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            return now_est.strftime("%m/%d %I:%M %p EST")
        except:
            return datetime.now().strftime("%m/%d %I:%M %p")
    
    async def _send_log_embed(
        self, 
        title: str, 
        description: str, 
        level: str = "INFO",
        fields: Optional[List[Dict[str, str]]] = None,
        footer: Optional[str] = None
    ):
        """
        Send a formatted log embed to the Discord channel.
        
        Args:
            title: Embed title
            description: Embed description
            level: Log level (INFO, WARNING, ERROR, etc.)
            fields: List of embed fields
            footer: Optional footer text
        """
        if not self.enabled or not self.log_channel:
            return
        
        # Check rate limiting
        if not self._check_rate_limit(level):
            return
        
        try:
            embed = discord.Embed(
                title=f"{self.level_emojis.get(level, '📝')} {title}",
                description=description,
                color=self.level_colors.get(level, 0x95a5a6),
                timestamp=datetime.utcnow()
            )
            
            # Add fields if provided
            if fields:
                for field in fields[:25]:  # Discord limit is 25 fields
                    embed.add_field(
                        name=field.get("name", "Field"),
                        value=field.get("value", "No value"),
                        inline=field.get("inline", False)
                    )
            
            # Add footer
            if footer:
                embed.set_footer(text=footer)
            else:
                embed.set_footer(text=f"QuranBot VPS • {self._get_timestamp()}")
            
            await self.log_channel.send(embed=embed)
            
        except discord.errors.Forbidden:
            log_error_with_traceback(
                "Discord logger lacks permissions to send messages",
                None
            )
            self.enabled = False
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited by Discord
                retry_after = getattr(e, 'retry_after', 60)
                log_error_with_traceback(f"Discord API rate limited - waiting {retry_after}s", e)
                
                # Note: We can't use our own log_rate_limit method here as it would cause recursion
                # Instead, we log to the console and local files only
                log_perfect_tree_section(
                    "Discord Logger - Rate Limited",
                    [
                        ("status", "🚨 Discord logger itself rate limited"),
                        ("retry_after", f"{retry_after}s"),
                        ("impact", "Discord notifications paused"),
                        ("local_logging", "✅ Still active"),
                    ],
                    "⏳",
                )
            else:
                log_error_with_traceback("Discord HTTP error in logger", e)
        except Exception as e:
            log_error_with_traceback("Error sending Discord log", e)
    
    async def log_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log an error to Discord with full traceback and ping owner.
        
        Args:
            error_message: Error description
            exception: Exception object (if available)
            context: Additional context information
        """
        if not self.enabled:
            return
        
        # Send ping message first
        try:
            ping_message = f"🚨 <@{self.owner_user_id}> **ERROR DETECTED** 🚨\n\n**{error_message}**"
            await self.log_channel.send(ping_message)
        except Exception as e:
            log_error_with_traceback("Failed to send error ping", e)
        
        description = f"**Error:** {error_message}"
        
        fields = []
        
        if exception:
            fields.append({
                "name": "Exception Type",
                "value": f"`{type(exception).__name__}`",
                "inline": True
            })
            fields.append({
                "name": "Exception Message", 
                "value": f"```\n{str(exception)[:1000]}\n```",
                "inline": False
            })
            
            # Add traceback (limited to prevent embed size issues)
            if hasattr(exception, '__traceback__') and exception.__traceback__:
                tb_lines = traceback.format_tb(exception.__traceback__)
                tb_text = ''.join(tb_lines)[:1000]
                fields.append({
                    "name": "Traceback",
                    "value": f"```python\n{tb_text}\n```",
                    "inline": False
                })
        
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        # Add recent error logs
        error_logs = self._get_error_logs(15)
        if error_logs:
            fields.append({
                "name": "📝 Recent Error Logs",
                "value": f"```python\n{error_logs[:1500]}\n```",
                "inline": False
            })
        
        await self._send_log_embed(
            title="Error Detected",
            description=description,
            level="ERROR",
            fields=fields
        )
    
    async def log_critical_error(
        self, 
        error_message: str, 
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a critical error that might affect bot operation and ping owner.
        
        Args:
            error_message: Critical error description
            exception: Exception object (if available)
            context: Additional context information
        """
        if not self.enabled:
            return
        
        # Send urgent ping message first
        try:
            ping_message = f"🚨🚨 <@{self.owner_user_id}> **CRITICAL ERROR** 🚨🚨\n\n**{error_message}**\n\n⚠️ **IMMEDIATE ATTENTION REQUIRED** ⚠️"
            await self.log_channel.send(ping_message)
        except Exception as e:
            log_error_with_traceback("Failed to send critical error ping", e)
        
        description = f"🚨 **CRITICAL ERROR** 🚨\n\n{error_message}"
        
        fields = []
        
        if exception:
            fields.append({
                "name": "Exception Type",
                "value": f"`{type(exception).__name__}`",
                "inline": True
            })
            fields.append({
                "name": "Exception Message",
                "value": f"```\n{str(exception)[:1000]}\n```",
                "inline": False
            })
            
            # Add traceback for critical errors
            if hasattr(exception, '__traceback__') and exception.__traceback__:
                tb_lines = traceback.format_tb(exception.__traceback__)
                tb_text = ''.join(tb_lines)[:1000]
                fields.append({
                    "name": "Traceback",
                    "value": f"```python\n{tb_text}\n```",
                    "inline": False
                })
        
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        # Add recent error logs for critical errors
        error_logs = self._get_error_logs(20)
        if error_logs:
            fields.append({
                "name": "📝 Recent Error Logs",
                "value": f"```python\n{error_logs[:1500]}\n```",
                "inline": False
            })
        
        await self._send_log_embed(
            title="CRITICAL ERROR",
            description=description,
            level="CRITICAL",
            fields=fields
        )
    
    async def log_rate_limit(
        self, 
        event: str,
        retry_after: float,
        endpoint: Optional[str] = None,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a Discord API rate limit event with detailed information.
        
        Args:
            event: The event that triggered the rate limit
            retry_after: Seconds to wait before retrying
            endpoint: API endpoint that was rate limited (if known)
            context: Additional context information
        """
        if not self.enabled:
            return
        
        try:
            # Calculate resume time in EST
            est = pytz.timezone("US/Eastern")
            now_est = datetime.now(est)
            resume_time = now_est + timedelta(seconds=retry_after)
            
            description = (
                f"🚨 **Discord API Rate Limit Triggered**\n\n"
                f"**Event:** `{event}`\n"
                f"**Wait Time:** {retry_after} seconds\n"
                f"**Resume Time:** {resume_time.strftime('%I:%M:%S %p EST')}\n\n"
                f"The bot will automatically resume operations after the rate limit period. "
                f"This is a normal Discord API protection mechanism."
            )
            
            fields = [
                {
                    "name": "⏰ Rate Limit Details",
                    "value": f"**Retry After:** {retry_after}s\n**Status Code:** 429\n**Timestamp:** {self._get_timestamp()}",
                    "inline": True
                },
                {
                    "name": "🎯 Affected Event", 
                    "value": f"**Event:** {event}\n**Auto Resume:** ✅ Yes\n**Manual Action:** ❌ None needed",
                    "inline": True
                }
            ]
            
            if endpoint:
                fields.append({
                    "name": "🌐 API Endpoint",
                    "value": f"`{endpoint}`",
                    "inline": False
                })
            
            if context:
                context_text = []
                for key, value in context.items():
                    if len(str(value)) < 100:  # Avoid overly long context values
                        context_text.append(f"**{key}:** {value}")
                
                if context_text:
                    fields.append({
                        "name": "📋 Additional Context",
                        "value": "\n".join(context_text[:5]),  # Limit to 5 context items
                        "inline": False
                    })
            
            # Add rate limit statistics
            try:
                rate_limit_count = sum(
                    sum(minute_counts.values()) 
                    for minute_counts in self.rate_limit_cache.values()
                )
                fields.append({
                    "name": "📊 Rate Limit Stats",
                    "value": f"**Current Period:** {rate_limit_count} logs\n**Limit:** {self.max_logs_per_minute}/min\n**Status:** {'⚠️ Near Limit' if rate_limit_count > self.max_logs_per_minute * 0.8 else '✅ Normal'}",
                    "inline": True
                })
            except:
                pass
            
            await self._send_log_embed(
                title="Rate Limit Detected",
                description=description,
                level="WARNING",
                fields=fields,
                footer=f"Rate limits help prevent API abuse • Bot will resume automatically"
            )
            
        except Exception as e:
            log_error_with_traceback("Error sending rate limit notification", e)

    async def log_rate_limit(
        self,
        event: str,
        retry_after: float,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a rate limit event.
        
        Args:
            event: Event that was rate limited
            retry_after: Time to wait before retrying
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**Rate Limited:** {event}\n\nRetry after: {retry_after} seconds"
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        fields.append({
            "name": "Retry After",
            "value": f"{retry_after} seconds",
            "inline": True
        })
        
        await self._send_log_embed(
            title="Rate Limit",
            description=description,
            level="WARNING",
            fields=fields
        )

    async def log_warning(
        self, 
        warning_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a warning message.
        
        Args:
            warning_message: Warning description
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**Warning:** {warning_message}"
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_log_embed(
            title="Warning",
            description=description,
            level="WARNING",
            fields=fields
        )
    
    async def log_system_event(
        self, 
        event_name: str, 
        event_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a system event (startup, shutdown, connections, etc.).
        
        Args:
            event_name: Name of the system event
            event_description: Description of the event
            context: Additional context information
        """
        if not self.enabled:
            return
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_log_embed(
            title=event_name,
            description=event_description,
            level="SYSTEM",
            fields=fields
        )
    
    async def log_user_activity(
        self, 
        activity_type: str, 
        user_name: str,
        activity_description: str,
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log important user activities.
        
        Args:
            activity_type: Type of user activity
            user_name: Name of the user
            activity_description: Description of the activity
            context: Additional context information
        """
        if not self.enabled:
            return
        
        description = f"**User:** {user_name}\n**Activity:** {activity_description}"
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_log_embed(
            title=f"User Activity - {activity_type}",
            description=description,
            level="USER",
            fields=fields
        )
    
    async def log_user_interaction(
        self, 
        interaction_type: str, 
        user_name: str, 
        user_id: int,
        action_description: str, 
        details: Optional[Dict[str, str]] = None, 
        user_avatar_url: Optional[str] = None
    ):
        """
        Log user interactions with profile picture thumbnail.
        
        Args:
            interaction_type: Type of interaction (voice_join, button_click, etc.)
            user_name: Display name of the user
            user_id: Discord user ID
            action_description: Description of what the user did
            details: Additional details about the interaction
            user_avatar_url: URL to user's avatar for thumbnail
        """
        if not self.enabled:
            return
        
        # Create interaction type emoji mapping
        interaction_emojis = {
            "voice_join": "🎤",
            "voice_leave": "🚪", 
            "voice_move": "🔄",
            "voice_mute": "🔇",
            "voice_unmute": "🔊",
            "voice_deafen": "🔇",
            "voice_undeafen": "🔊",
            "dua_reaction": "🤲",
            "verse_reaction": "📖",
            "quiz_answer": "🧠",
            "quiz_correct": "✅",
            "quiz_incorrect": "❌",
            "button_click": "🔘",
            "button_navigation": "🧭",
            "button_search": "🔍",
            "button_skip": "⏭️",
            "button_toggle": "🔀",
            "dropdown_select": "📋",
            "dropdown_surah": "📜",
            "dropdown_reciter": "🎙️",
            "search_confirm": "✅",
            "search_retry": "🔄",
            "control_panel": "🎛️",
            "reaction_add": "➕",
            "reaction_remove": "➖",
            "default": "👤"
        }
        
        emoji = interaction_emojis.get(interaction_type, interaction_emojis["default"])
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} User Interaction",
            description=f"**{user_name}** {action_description}",
            color=0x17A2B8,  # Teal
            timestamp=datetime.utcnow()
        )
        
        # Add user profile picture as thumbnail
        if user_avatar_url:
            embed.set_thumbnail(url=user_avatar_url)
        
        # Add interaction details
        embed.add_field(
            name="Interaction Type", 
            value=interaction_type.replace("_", " ").title(), 
            inline=True
        )
        embed.add_field(
            name="User ID", 
            value=str(user_id), 
            inline=True
        )
        embed.add_field(
            name="Time", 
            value=f"<t:{int(datetime.utcnow().timestamp())}:R>", 
            inline=True
        )
        
        if details:
            for key, value in details.items():
                # Limit field value length to prevent embed errors
                field_value = str(value)
                if len(field_value) > 1024:
                    field_value = field_value[:1021] + "..."
                embed.add_field(
                    name=key.replace("_", " ").title(), 
                    value=field_value, 
                    inline=True
                )
        
        embed.set_footer(text=f"QuranBot User Interaction • {self._get_timestamp()}")
        
        try:
            await self.log_channel.send(embed=embed)
        except Exception as e:
            log_error_with_traceback("Failed to send user interaction log", e)
    
    async def log_bot_activity(
        self, 
        activity_type: str, 
        activity_description: str, 
        details: Optional[Dict[str, str]] = None
    ):
        """
        Log bot activities like automatic surah switching, audio management, etc.
        
        Args:
            activity_type: Type of bot activity (surah_switch, audio_start, etc.)
            activity_description: Description of what the bot did
            details: Additional details about the activity
        """
        if not self.enabled:
            return
        
        # Create bot activity emoji mapping
        activity_emojis = {
            "surah_switch": "🔄",
            "surah_start": "▶️",
            "surah_end": "⏹️",
            "audio_start": "🎵",
            "audio_stop": "⏸️",
            "audio_pause": "⏸️",
            "audio_resume": "▶️",
            "reciter_switch": "🎙️",
            "playlist_shuffle": "🔀",
            "playlist_loop": "🔁",
            "voice_connect": "🔗",
            "voice_disconnect": "🔌",
            "voice_reconnect": "🔄",
            "daily_verse": "📖",
            "scheduled_verse": "⏰",
            "quiz_start": "🧠",
            "quiz_end": "🏁",
            "backup_create": "💾",
            "backup_restore": "📥",
            "system_restart": "🔄",
            "system_shutdown": "⏹️",
            "error_recovery": "🔧",
            "default": "🤖"
        }
        
        emoji = activity_emojis.get(activity_type, activity_emojis["default"])
        
        # Create embed
        embed = discord.Embed(
            title=f"{emoji} Bot Activity",
            description=f"**QuranBot** {activity_description}",
            color=0x6C5CE7,  # Purple for bot activities
            timestamp=datetime.utcnow()
        )
        
        # Add bot's profile picture as thumbnail
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        elif self.bot.user:
            embed.set_thumbnail(url=self.bot.user.default_avatar.url)
        
        # Add activity details
        embed.add_field(
            name="Activity Type", 
            value=activity_type.replace("_", " ").title(), 
            inline=True
        )
        embed.add_field(
            name="Time", 
            value=f"<t:{int(datetime.utcnow().timestamp())}:R>", 
            inline=True
        )
        embed.add_field(
            name="Initiated By", 
            value="Automatic System", 
            inline=True
        )
        
        if details:
            for key, value in details.items():
                # Limit field value length to prevent embed errors
                field_value = str(value)
                if len(field_value) > 1024:
                    field_value = field_value[:1021] + "..."
                embed.add_field(
                    name=key.replace("_", " ").title(), 
                    value=field_value, 
                    inline=True
                )
        
        embed.set_footer(text=f"QuranBot Activity • {self._get_timestamp()}")
        
        try:
            await self.log_channel.send(embed=embed)
        except Exception as e:
            log_error_with_traceback("Failed to send bot activity log", e)
    
    async def log_success(
        self, 
        success_message: str, 
        context: Optional[Dict[str, str]] = None
    ):
        """
        Log a success message.
        
        Args:
            success_message: Success description
            context: Additional context information
        """
        if not self.enabled:
            return
        
        fields = []
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value)[:1000],
                    "inline": True
                })
        
        await self._send_log_embed(
            title="Success",
            description=success_message,
            level="SUCCESS",
            fields=fields
        )
    
    async def log_vps_status(
        self, 
        status_type: str,
        status_data: Dict[str, str]
    ):
        """
        Log VPS status information.
        
        Args:
            status_type: Type of status (startup, periodic, shutdown)
            status_data: Dictionary of status information
        """
        if not self.enabled:
            return
        
        description = f"**VPS Status Update:** {status_type}"
        
        fields = []
        for key, value in status_data.items():
            fields.append({
                "name": key.replace("_", " ").title(),
                "value": str(value)[:1000],
                "inline": True
            })
        
        await self._send_log_embed(
            title=f"VPS Status - {status_type}",
            description=description,
            level="SYSTEM",
            fields=fields
        )
    
    def disable(self):
        """Disable Discord logging."""
        self.enabled = False
        log_perfect_tree_section(
            "Discord Logger Disabled",
            [
                ("status", "❌ Discord logging disabled"),
                ("reason", "Error or configuration issue"),
            ],
            "🔇"
        )
    
    def enable(self):
        """Enable Discord logging."""
        self.enabled = True
        log_perfect_tree_section(
            "Discord Logger Enabled",
            [
                ("status", "✅ Discord logging enabled"),
                ("channel_id", str(self.log_channel_id)),
            ],
            "🔔"
        )


# Global Discord logger instance
_discord_logger: Optional[DiscordLogger] = None


def setup_discord_logger(bot: commands.Bot, log_channel_id: int, dashboard_url: str = "") -> DiscordLogger:
    """
    Set up the global Discord logger instance.
    
    Args:
        bot: Discord bot instance
        log_channel_id: ID of the Discord channel for logs
        dashboard_url: Optional dashboard URL for monitoring
        
    Returns:
        DiscordLogger: The initialized Discord logger
    """
    global _discord_logger
    _discord_logger = DiscordLogger(bot, log_channel_id, dashboard_url)
    return _discord_logger


def get_discord_logger() -> Optional[DiscordLogger]:
    """
    Get the global Discord logger instance.
    
    Returns:
        Optional[DiscordLogger]: The Discord logger if initialized, None otherwise
    """
    return _discord_logger


# Convenience functions for easy logging
async def discord_log_error(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log an error to Discord."""
    if _discord_logger:
        await _discord_logger.log_error(error_message, exception, context)


async def discord_log_critical(
    error_message: str, 
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, str]] = None
):
    """Log a critical error to Discord."""
    if _discord_logger:
        await _discord_logger.log_critical_error(error_message, exception, context)


async def discord_log_warning(
    warning_message: str, 
    context: Optional[Dict[str, str]] = None
):
    """Log a warning to Discord."""
    if _discord_logger:
        await _discord_logger.log_warning(warning_message, context)


async def discord_log_system(
    event_name: str, 
    event_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log a system event to Discord."""
    if _discord_logger:
        await _discord_logger.log_system_event(event_name, event_description, context)


async def discord_log_user(
    activity_type: str, 
    user_name: str,
    activity_description: str,
    context: Optional[Dict[str, str]] = None
):
    """Log user activity to Discord."""
    if _discord_logger:
        await _discord_logger.log_user_activity(activity_type, user_name, activity_description, context)


async def discord_log_user_interaction(
    interaction_type: str, 
    user_name: str, 
    user_id: int,
    action_description: str, 
    details: Optional[Dict[str, str]] = None, 
    user_avatar_url: Optional[str] = None
):
    """Log user interaction to Discord."""
    if _discord_logger:
        await _discord_logger.log_user_interaction(interaction_type, user_name, user_id, action_description, details, user_avatar_url)


async def discord_log_bot_activity(
    activity_type: str, 
    activity_description: str, 
    details: Optional[Dict[str, str]] = None
):
    """Log bot activity to Discord."""
    if _discord_logger:
        await _discord_logger.log_bot_activity(activity_type, activity_description, details)


async def discord_log_success(
    success_message: str, 
    context: Optional[Dict[str, str]] = None
):
    """Log a success message to Discord."""
    if _discord_logger:
        await _discord_logger.log_success(success_message, context)


async def discord_log_vps_status(
    status_type: str,
    status_data: Dict[str, str]
):
    """Log VPS status to Discord."""
    if _discord_logger:
        await _discord_logger.log_vps_status(status_type, status_data) 