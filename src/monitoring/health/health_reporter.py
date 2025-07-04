"""
Health reporter for the Discord Quran Bot.
Sends periodic health status updates to Discord channels.
"""

import asyncio
import discord
from datetime import datetime, timedelta
from typing import Optional
from .health import HealthMonitor
from monitoring.logging.logger import logger, log_tree_start, log_tree_item, log_tree_end

class HealthReporter:
    """Health reporter that sends periodic status updates."""
    
    def __init__(self, bot, health_monitor: HealthMonitor, channel_id: int):
        """Initialize the health reporter."""
        self.bot = bot
        self.health_monitor = health_monitor
        self.channel_id = channel_id
        self.report_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start(self):
        """Start the hourly health reporting."""
        self.is_running = True
        self.report_task = asyncio.create_task(self._report_loop())
        
    async def stop(self):
        """Stop the health reporting."""
        self.is_running = False
        if self.report_task:
            self.report_task.cancel()
            try:
                await self.report_task
            except asyncio.CancelledError:
                pass
                
    async def _report_loop(self):
        """Main reporting loop."""
        while self.is_running:
            try:
                await self._send_health_report()
                # Wait for 1 hour (3600 seconds)
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error and continue
                logger.error(f"Health reporter error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def _send_health_report(self):
        """Send a health status report to Discord."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.warning(f"Health reporter: Could not find channel {self.channel_id}")
                return
                
            health_status = self.health_monitor.get_health_status()
            
            log_tree_start("Health Report Summary")
            log_tree_item(f"🔋 Uptime: {health_status['uptime']}")
            log_tree_item(f"🎵 Songs Played: {health_status['songs_played']}")
            log_tree_item(f"❌ Errors: {health_status['errors_count']}")
            log_tree_item(f"🔌 Reconnections: {health_status['reconnections']}")
            log_tree_item(f"📡 Streaming: {'✅ Active' if health_status['is_streaming'] else '❌ Inactive'}")
            log_tree_item(f"📊 Error Rate: {health_status['error_rate']:.2%}", is_last=True)
            log_tree_end()
            
            # Create embed
            embed = discord.Embed(
                title="🤖 Quran Bot Health Report",
                description="Hourly status update",
                color=0x00ff00 if health_status['status'] == 'healthy' else 0xff9900,
                timestamp=datetime.now()
            )

            # Add bot avatar as thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Add fields
            embed.add_field(name="🔋 Uptime", value=health_status['uptime'], inline=True)

            embed.add_field(
                name="📖 Surahs Played",
                value=str(health_status['songs_played']),  # Will update key in next step
                inline=True
            )

            embed.add_field(
                name="❌ Errors",
                value=str(health_status['errors_count']),
                inline=True
            )

            embed.add_field(
                name="🔌 Reconnections",
                value=str(health_status['reconnections']),
                inline=True
            )

            embed.add_field(
                name="📡 Streaming",
                value="✅ Active" if health_status['is_streaming'] else "❌ Inactive",
                inline=True
            )

            embed.add_field(
                name="📊 Error Rate",
                value=f"{health_status['error_rate']:.2%}",
                inline=True
            )

            # Last activity
            if health_status.get('last_activity'):
                embed.add_field(
                    name="🕒 Last Activity",
                    value=health_status['last_activity'].replace('T', ' ')[:19],
                    inline=True
                )

            # Currently Playing Surah
            if health_status['current_song']:
                embed.add_field(
                    name="📖 Current Surah",
                    value=health_status['current_song'],
                    inline=False
                )

            # Recent errors
            if health_status.get('recent_errors'):
                error_lines = [f"• {e.get('message', str(e))[:80]}" for e in health_status['recent_errors']]
                embed.add_field(
                    name="⚠️ Recent Errors",
                    value="\n".join(error_lines) or "None",
                    inline=False
                )

            # Add state information if available
            if hasattr(self.bot, 'state_manager'):
                state_summary = self.bot.state_manager.get_state_summary()
                embed.add_field(
                    name="📊 State Info",
                    value=f"Surah Index: {state_summary['current_song_index']}\nTotal Surahs Played: {state_summary['total_songs_played']}\nBot Starts: {state_summary['bot_start_count']}",
                    inline=False
                )

            # Add version/config and host info (to be filled in next step)
            import platform
            import sys
            version = getattr(self.bot, 'version', 'Unknown')
            embed.add_field(
                name="🛠️ Bot Version",
                value=version,
                inline=True
            )
            embed.add_field(
                name="💻 Host Info",
                value=f"{platform.system()} {platform.release()}\nPython {sys.version_info.major}.{sys.version_info.minor}",
                inline=True
            )

            # Footer with bot name and time
            embed.set_footer(text=f"{self.bot.user.name} • {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

            # Send the report
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send health report: {e}")
            
    async def send_immediate_report(self):
        """Send an immediate health report (for testing)."""
        await self._send_health_report() 