"""
Health reporter for the Discord Quran Bot.
Sends periodic health status updates to Discord channels.
"""

import asyncio
import discord
from datetime import datetime, timedelta
from typing import Optional
from .health import HealthMonitor

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
                print(f"Health reporter error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def _send_health_report(self):
        """Send a health status report to Discord."""
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                print(f"Health reporter: Could not find channel {self.channel_id}")
                return
                
            health_status = self.health_monitor.get_health_status()
            
            # Create embed
            embed = discord.Embed(
                title="🤖 Quran Bot Health Report",
                description="Hourly status update",
                color=0x00ff00 if health_status['status'] == 'healthy' else 0xff9900,
                timestamp=datetime.now()
            )
            
            # Add fields
            embed.add_field(
                name="⏱️ Uptime",
                value=health_status['uptime'],
                inline=True
            )
            
            embed.add_field(
                name="🎵 Songs Played",
                value=str(health_status['songs_played']),
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
            
            if health_status['current_song']:
                            embed.add_field(
                name="🎵 Currently Playing",
                value=health_status['current_song'],
                inline=False
            )
            
            # Add state information if available
            if hasattr(self.bot, 'state_manager'):
                state_summary = self.bot.state_manager.get_state_summary()
                embed.add_field(
                    name="📊 State Info",
                    value=f"Song Index: {state_summary['current_song_index']}\nTotal Played: {state_summary['total_songs_played']}\nBot Starts: {state_summary['bot_start_count']}",
                    inline=False
                )
                
            # Add footer
            embed.set_footer(text="Quran Bot Health Monitor")
            
            # Send the report
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Failed to send health report: {e}")
            
    async def send_immediate_report(self):
        """Send an immediate health report (for testing)."""
        await self._send_health_report() 