"""
Log management command for the Quran Bot.
Combines log viewing, system monitoring, and basic maintenance in one command.
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import psutil
import platform
from datetime import datetime, timedelta
import re

class LogCommands(commands.Cog):
    """Log management command."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="logs", description="View logs, system info, and bot status")
    @app_commands.describe(
        action="What to show",
        lines="Number of log lines to show (default: 50, max: 200)",
        search="Search term to filter logs"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Recent Logs", value="logs"),
        app_commands.Choice(name="System Info", value="system"),
        app_commands.Choice(name="Bot Status", value="status"),
        app_commands.Choice(name="Error Logs", value="errors"),
        app_commands.Choice(name="All Info", value="all")
    ])
    async def logs(self, interaction: discord.Interaction, action: str = "all", lines: int = 50, search: str = None):
        """View logs, system information, and bot status."""
        await interaction.response.defer()
        
        try:
            if action == "all":
                # Show comprehensive overview
                embed = await self._get_system_overview()
                await interaction.followup.send(embed=embed)
                
                # Also show recent logs
                logs_embed = await self._get_recent_logs(lines, search)
                await interaction.followup.send(embed=logs_embed)
                
            elif action == "logs":
                embed = await self._get_recent_logs(lines, search)
                await interaction.followup.send(embed=embed)
                
            elif action == "system":
                embed = await self._get_system_info()
                await interaction.followup.send(embed=embed)
                
            elif action == "status":
                embed = await self._get_bot_status()
                await interaction.followup.send(embed=embed)
                
            elif action == "errors":
                embed = await self._get_error_logs(lines, search)
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to get {action}: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
    
    async def _get_system_overview(self):
        """Get comprehensive system overview."""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Bot process info
            process = psutil.Process()
            bot_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Bot status
            latency = round(self.bot.latency * 1000)
            uptime = "Unknown"
            if hasattr(self.bot, 'health_monitor'):
                uptime = self.bot.health_monitor.get_uptime_string()
            
            embed = discord.Embed(
                title="🤖 Bot System Overview",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            # System info
            embed.add_field(
                name="💻 System",
                value=f"OS: {platform.system()} {platform.release()}\nPython: {platform.python_version()}",
                inline=True
            )
            
            embed.add_field(
                name="🔄 CPU & Memory",
                value=f"CPU: {cpu_percent:.1f}%\nMemory: {memory.percent:.1f}%\nBot Memory: {bot_memory:.1f} MB",
                inline=True
            )
            
            embed.add_field(
                name="💿 Disk",
                value=f"Used: {disk.percent:.1f}%\nFree: {disk.free / 1024 / 1024 / 1024:.1f} GB",
                inline=True
            )
            
            # Bot info
            embed.add_field(
                name="🤖 Bot Status",
                value=f"Uptime: {uptime}\nLatency: {latency}ms\nGuilds: {len(self.bot.guilds)}",
                inline=True
            )
            
            # Connection status
            status_emoji = "🟢" if self.bot.is_ready() else "🔴"
            embed.add_field(
                name="📡 Connection",
                value=f"{status_emoji} {'Connected' if self.bot.is_ready() else 'Disconnected'}",
                inline=True
            )
            
            # Health status
            if hasattr(self.bot, 'health_monitor'):
                health = self.bot.health_monitor.get_health_status()
                embed.add_field(
                    name="📊 Health",
                    value=f"Songs: {health['songs_played']}\nErrors: {health['errors_count']}\nReconnections: {health['reconnections']}",
                    inline=True
                )
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ System Info Error",
                description=f"Failed to get system info: {str(e)}",
                color=0xff0000
            )
    
    async def _get_recent_logs(self, lines: int, search: str = None):
        """Get recent logs."""
        try:
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                return discord.Embed(
                    title="❌ No Logs Found",
                    description="Logs directory does not exist.",
                    color=0xff0000
                )
            
            # Find most recent log file
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
            if not log_files:
                return discord.Embed(
                    title="❌ No Log Files",
                    description="No log files found.",
                    color=0xff0000
                )
            
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
            latest_log = os.path.join(logs_dir, log_files[0])
            
            # Read log file
            with open(latest_log, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Filter by search term
            if search:
                log_lines = [line for line in log_lines if search.lower() in line.lower()]
            
            # Limit lines
            lines = min(lines, 200)
            log_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
            
            if not log_lines:
                return discord.Embed(
                    title="📋 No Logs Found",
                    description=f"No logs found matching: {search or 'all logs'}",
                    color=0xff9900
                )
            
            # Create log content
            log_content = ''.join(log_lines)
            
            # Split if too long
            if len(log_content) > 4000:
                log_content = log_content[-4000:] + "\n\n... (truncated)"
            
            embed = discord.Embed(
                title="📋 Recent Logs",
                description=f"```\n{log_content}\n```",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Summary",
                value=f"Showing {len(log_lines)} lines from {log_files[0]}",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Log Error",
                description=f"Failed to read logs: {str(e)}",
                color=0xff0000
            )
    
    async def _get_system_info(self):
        """Get detailed system information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network info
            network = psutil.net_io_counters()
            
            embed = discord.Embed(
                title="🖥️ Detailed System Info",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="💻 Platform",
                value=f"OS: {platform.system()} {platform.release()}\nArchitecture: {platform.machine()}\nPython: {platform.python_version()}",
                inline=False
            )
            
            embed.add_field(
                name="🔄 CPU",
                value=f"Usage: {cpu_percent:.1f}%\nCores: {psutil.cpu_count()}\nFrequency: {psutil.cpu_freq().current:.0f} MHz",
                inline=True
            )
            
            embed.add_field(
                name="💾 Memory",
                value=f"Total: {memory.total / 1024 / 1024 / 1024:.1f} GB\nUsed: {memory.percent:.1f}%\nAvailable: {memory.available / 1024 / 1024 / 1024:.1f} GB",
                inline=True
            )
            
            embed.add_field(
                name="💿 Disk",
                value=f"Total: {disk.total / 1024 / 1024 / 1024:.1f} GB\nUsed: {disk.percent:.1f}%\nFree: {disk.free / 1024 / 1024 / 1024:.1f} GB",
                inline=True
            )
            
            embed.add_field(
                name="📡 Network",
                value=f"Bytes Sent: {network.bytes_sent / 1024 / 1024:.1f} MB\nBytes Recv: {network.bytes_recv / 1024 / 1024:.1f} MB",
                inline=True
            )
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ System Info Error",
                description=f"Failed to get system info: {str(e)}",
                color=0xff0000
            )
    
    async def _get_bot_status(self):
        """Get detailed bot status."""
        try:
            latency = round(self.bot.latency * 1000)
            uptime = "Unknown"
            health_status = {}
            
            if hasattr(self.bot, 'health_monitor'):
                uptime = self.bot.health_monitor.get_uptime_string()
                health_status = self.bot.health_monitor.get_health_status()
            
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=0x00ff00 if self.bot.is_ready() else 0xff0000,
                timestamp=datetime.now()
            )
            
            # Connection status
            status_emoji = "🟢" if self.bot.is_ready() else "🔴"
            embed.add_field(
                name="📡 Connection",
                value=f"{status_emoji} {'Connected' if self.bot.is_ready() else 'Disconnected'}\nLatency: {latency}ms",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Uptime",
                value=uptime,
                inline=True
            )
            
            embed.add_field(
                name="🏠 Guilds",
                value=str(len(self.bot.guilds)),
                inline=True
            )
            
            # Health metrics
            if health_status:
                embed.add_field(
                    name="📊 Performance",
                    value=f"Songs Played: {health_status['songs_played']}\nErrors: {health_status['errors_count']}\nReconnections: {health_status['reconnections']}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎵 Current",
                    value=f"Song: {health_status['current_song'] or 'None'}\nStreaming: {'✅' if health_status['is_streaming'] else '❌'}",
                    inline=True
                )
                
                if health_status['errors_count'] > 0:
                    error_rate = health_status['error_rate']
                    embed.add_field(
                        name="⚠️ Error Rate",
                        value=f"{error_rate:.2%}",
                        inline=True
                    )
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Bot Status Error",
                description=f"Failed to get bot status: {str(e)}",
                color=0xff0000
            )
    
    async def _get_error_logs(self, lines: int, search: str = None):
        """Get error logs specifically."""
        try:
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                return discord.Embed(
                    title="❌ No Logs Found",
                    description="Logs directory does not exist.",
                    color=0xff0000
                )
            
            # Find most recent log file
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
            if not log_files:
                return discord.Embed(
                    title="❌ No Log Files",
                    description="No log files found.",
                    color=0xff0000
                )
            
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
            latest_log = os.path.join(logs_dir, log_files[0])
            
            # Read log file and filter for errors
            with open(latest_log, 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
            
            # Filter for error lines
            error_lines = [line for line in log_lines if 'ERROR' in line or 'Exception' in line or 'Traceback' in line]
            
            # Apply search filter
            if search:
                error_lines = [line for line in error_lines if search.lower() in line.lower()]
            
            # Limit lines
            lines = min(lines, 200)
            error_lines = error_lines[-lines:] if len(error_lines) > lines else error_lines
            
            if not error_lines:
                return discord.Embed(
                    title="📋 No Errors Found",
                    description=f"No error logs found matching: {search or 'all errors'}",
                    color=0x00ff00
                )
            
            # Create error content
            error_content = ''.join(error_lines)
            
            # Split if too long
            if len(error_content) > 4000:
                error_content = error_content[-4000:] + "\n\n... (truncated)"
            
            embed = discord.Embed(
                title="⚠️ Error Logs",
                description=f"```\n{error_content}\n```",
                color=0xff9900,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Summary",
                value=f"Showing {len(error_lines)} error lines from {log_files[0]}",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            return discord.Embed(
                title="❌ Error Log Error",
                description=f"Failed to read error logs: {str(e)}",
                color=0xff0000
            )

async def setup(bot):
    await bot.add_cog(LogCommands(bot)) 