"""
Discord embed logging system for QuranBot.
Sends beautiful embeds to Discord channels for real-time activity monitoring.
"""

import asyncio
import discord
import json
import os
import time
import aiohttp
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from monitoring.logging.logger import logger
import traceback
from core.mapping.surah_mapper import get_surah_from_filename, get_surah_display_name

class DiscordEmbedLogger:
    """Handles sending formatted embed logs to Discord channels."""
    
    def __init__(self, bot, logs_channel_id: int, target_vc_id: int = 1389675580253016144):
        """Initialize the Discord embed logger."""
        self.bot = bot
        self.logs_channel_id = logs_channel_id
        self.target_vc_id = target_vc_id  # Only track this specific VC
        self.sessions_file = "data/user_vc_sessions.json"
        self.user_sessions: Dict[int, Dict[str, Any]] = {}  # Track user VC sessions
        self.daily_joins: Dict[int, Dict[str, int]] = {}  # Track daily joins per user: {user_id: {date: count}}
        
        # Load existing sessions on startup
        self._load_sessions()
        
    def _get_daily_join_count(self, user_id: int) -> int:
        """Get the number of times a user has joined today."""
        today = date.today().isoformat()
        return self.daily_joins.get(user_id, {}).get(today, 0)
    
    def _increment_daily_join_count(self, user_id: int):
        """Increment the daily join count for a user."""
        today = date.today().isoformat()
        if user_id not in self.daily_joins:
            self.daily_joins[user_id] = {}
        if today not in self.daily_joins[user_id]:
            self.daily_joins[user_id][today] = 0
        self.daily_joins[user_id][today] += 1
        
        # Clean up old dates (keep only last 7 days)
        for user_id_key in list(self.daily_joins.keys()):
            for old_date in list(self.daily_joins[user_id_key].keys()):
                try:
                    old_date_obj = date.fromisoformat(old_date)
                    if (date.today() - old_date_obj).days > 7:
                        del self.daily_joins[user_id_key][old_date]
                except ValueError:
                    # Invalid date format, remove it
                    del self.daily_joins[user_id_key][old_date]
            
            # Remove user if no dates left
            if not self.daily_joins[user_id_key]:
                del self.daily_joins[user_id_key]
        
    async def initialize_existing_users(self):
        """Initialize sessions for users already in the target VC when bot starts."""
        try:
            channel = self.bot.get_channel(self.target_vc_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                for member in channel.members:
                    if member != self.bot.user:  # Don't track the bot itself
                        # Check if they already have a session (from file)
                        if member.id not in self.user_sessions:
                            # Create new session for user already in VC
                            self.user_sessions[member.id] = {
                                'joined_at': datetime.now(),
                                'channel_name': channel.name,
                                'username': member.display_name,
                                'total_time': 0.0,
                                'interactions': 0
                            }
                            logger.info(f"Initialized session for {member.display_name} already in VC")
                        else:
                            # Update their join time to now (since we don't know when they actually joined during downtime)
                            self.user_sessions[member.id]['joined_at'] = datetime.now()
                            self.user_sessions[member.id]['username'] = member.display_name
                            self.user_sessions[member.id]['interactions'] = 0  # Reset interactions for new session
                            logger.info(f"Resumed session for {member.display_name} already in VC")
                
                self._save_sessions()
                logger.info(f"Initialized {len(channel.members)} users already in target VC")
            else:
                logger.warning(f"Could not find target VC {self.target_vc_id} for session initialization")
        except Exception as e:
            logger.error(f"Failed to initialize existing users: {e}")
    
    async def cleanup_sessions(self):
        """Save all sessions before shutdown."""
        try:
            self._save_sessions()
            logger.info("Saved all VC sessions before shutdown")
        except Exception as e:
            logger.error(f"Failed to save sessions during cleanup: {e}")
        
    async def get_logs_channel(self) -> Optional[discord.TextChannel]:
        """Get the logs channel."""
        try:
            logger.debug(f"Looking for logs channel with ID {self.logs_channel_id}")
            channel = self.bot.get_channel(self.logs_channel_id)
            if not channel:
                logger.warning(f"Discord logger: Could not find logs channel {self.logs_channel_id}")
                # Try fetching the channel
                try:
                    channel = await self.bot.fetch_channel(self.logs_channel_id)
                    logger.debug(f"Successfully fetched channel {channel.name} ({channel.id})")
                except Exception as e:
                    logger.error(f"Failed to fetch channel: {str(e)}")
            else:
                logger.debug(f"Found channel {channel.name} ({channel.id})")
            return channel
        except Exception as e:
            logger.error(f"Discord logger error getting channel: {str(e)}\nTraceback: {traceback.format_exc()}")
            return None
    
    def _load_sessions(self):
        """Load existing user sessions from file."""
        try:
            os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to int and string timestamps back to datetime
                    for user_id, session_data in data.items():
                        self.user_sessions[int(user_id)] = {
                            'joined_at': datetime.fromisoformat(session_data['joined_at']),
                            'channel_name': session_data['channel_name'],
                            'username': session_data['username'],
                            'total_time': session_data.get('total_time', 0.0),  # Accumulated time from previous sessions
                            'interactions': session_data.get('interactions', 0)  # Interactions from previous sessions
                        }
                logger.info(f"Loaded {len(self.user_sessions)} existing VC sessions")
            else:
                logger.info("No existing VC sessions file found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load VC sessions: {e}")
            self.user_sessions = {}
    
    def _save_sessions(self):
        """Save current user sessions to file."""
        try:
            os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)
            # Convert datetime objects to strings for JSON serialization
            serializable_data = {}
            for user_id, session_data in self.user_sessions.items():
                # Handle missing fields gracefully
                joined_at = session_data.get('joined_at')
                if joined_at:
                    joined_at_str = joined_at.isoformat() if hasattr(joined_at, 'isoformat') else str(joined_at)
                else:
                    joined_at_str = datetime.now().isoformat()
                
                serializable_data[str(user_id)] = {
                    'joined_at': joined_at_str,
                    'channel_name': session_data.get('channel_name', 'Unknown'),
                    'username': session_data.get('username', 'Unknown'),
                    'total_time': session_data.get('total_time', 0.0),
                    'interactions': session_data.get('interactions', 0)
                }
            
            with open(self.sessions_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            logger.debug(f"Saved {len(self.user_sessions)} VC sessions to file")
        except Exception as e:
            logger.error(f"Failed to save VC sessions: {e}")

    def format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _get_channel_name(self, channel) -> str:
        """Get channel name with proper type handling."""
        if channel is None:
            return 'DM'
        elif isinstance(channel, discord.DMChannel):
            return 'DM'
        elif hasattr(channel, 'name'):
            return channel.name
        else:
            return 'Unknown'
    
    # BOT ACTIVITY EMBEDS
    
    async def log_bot_connected(self, channel_name: str, guild_name: str):
        """Log when bot connects to voice channel."""
        embed = discord.Embed(
            title="🟢 Bot Connected",
            description="Successfully connected to voice channel",
            color=0x00ff00
        )
        
        # Add bot's profile picture
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Last uptime (from bot start time)
        if hasattr(self.bot, 'start_time'):
            uptime = datetime.now() - self.bot.start_time
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            if days > 0:
                uptime_str = f"{days}d {hours:02d}h {minutes:02d}m"
            else:
                uptime_str = f"{hours:02d}h {minutes:02d}m"
                
            embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        
        # Health checks status
        health_status = "✅ All Systems OK"
        if hasattr(self.bot, 'health_checks'):
            failed_checks = getattr(self.bot, 'health_checks', {}).get('failed', [])
            if failed_checks:
                health_status = f"⚠️ Issues Found: {len(failed_checks)}"
        embed.add_field(name="🔍 Health Checks", value=health_status, inline=True)
        
        # Playback status
        embed.add_field(name="⏯️ Status", value="Ready to stream", inline=True)
        
        # Add timestamp
        embed.timestamp = datetime.now()
        embed.set_footer(text=f"Server: {guild_name}")
        
        await self._send_embed(embed)
    
    async def log_bot_disconnected(self, channel_name: str, reason: str = "Unknown"):
        """Log when bot disconnects from voice channel."""
        embed = discord.Embed(
            title="🔴 Bot Disconnected",
            description=f"Disconnected from voice channel",
            color=0xff0000
        )
        embed.add_field(name="❌ Reason", value=reason, inline=True)
        embed.add_field(name="⏰ Status", value="Offline", inline=True)
        
        # Add bot profile picture
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await self._send_embed(embed)
    
    async def log_surah_changed(self, surah_info: Dict[str, Any], reciter: str):
        """Log when bot changes surahs."""
        emoji = self._get_surah_emoji(surah_info.get('number', 0))
        
        embed = discord.Embed(
            title=f"{emoji} Now Playing",
            description=f"**{surah_info.get('english_name', 'Unknown')}**",
            color=0x00aaff
        )
        embed.add_field(name="📖 Surah", value=f"{surah_info.get('number', 0):03d}. {surah_info.get('english_name', 'Unknown')}", inline=True)
        embed.add_field(name="🎵 Reciter", value=reciter, inline=True)
        embed.add_field(name="🔤 Arabic", value=surah_info.get('arabic_name', 'غير معروف'), inline=True)
        
        if surah_info.get('translation'):
            embed.add_field(name="📝 Translation", value=surah_info.get('translation'), inline=False)
        
        # Add bot profile picture
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await self._send_embed(embed)
    
    async def log_reciter_changed(self, old_reciter: str, new_reciter: str, user_name: str):
        """Log when reciter is changed."""
        embed = discord.Embed(
            title="🎤 Reciter Changed",
            description=f"Reciter switched by {user_name}",
            color=0xff9900
        )
        embed.add_field(name="🔄 From", value=old_reciter, inline=True)
        embed.add_field(name="➡️ To", value=new_reciter, inline=True)
        embed.add_field(name="👤 Changed By", value=user_name, inline=True)
        
        # Add bot profile picture since it's a bot state change
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await self._send_embed(embed)
    
    # USER ACTIVITY EMBEDS
    
    async def log_user_joined_vc(self, member: discord.Member, channel_name: str):
        """Log when a user joins the voice channel."""
        # Increment daily join count
        self._increment_daily_join_count(member.id)
        daily_joins = self._get_daily_join_count(member.id)
        
        embed = discord.Embed(
            title="👋 User Joined",
            description=f"<@{member.id}> joined the voice channel",
            color=0x00ff00
        )
        
        # Add user's profile picture
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        # Start tracking session with full information
        join_time = datetime.now()
        self.user_sessions[member.id] = {
            'joined_at': join_time,
            'channel_name': channel_name,
            'username': member.display_name,
            'guild_id': member.guild.id if member.guild else None,
            'guild_name': member.guild.name if member.guild else None,
            'total_time': self.user_sessions.get(member.id, {}).get('total_time', 0.0),  # Preserve total time
            'interactions': 0  # Track interactions during this session
        }
        self._save_sessions()
        
        # Add session info to embed with Discord timestamp format
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(name="Join Time", value=f"<t:{int(join_time.timestamp())}:F>", inline=True)
        embed.add_field(name="Daily Joins", value=f"{daily_joins} time{'s' if daily_joins != 1 else ''} today", inline=True)
        
        await self._send_embed(embed)
    
    async def log_user_left_vc(self, member: discord.Member, channel_name: str):
        """Log when a user leaves the voice channel."""
        # Get daily join count
        daily_joins = self._get_daily_join_count(member.id)
        
        embed = discord.Embed(
            title="👋 User Left",
            description=f"<@{member.id}> left the voice channel",
            color=0xff0000
        )
        
        # Add user's profile picture
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        # Calculate session duration if we were tracking them
        if member.id in self.user_sessions:
            session_data = self.user_sessions[member.id]
            session_start = session_data['joined_at']
            session_end = datetime.now()
            duration = session_end - session_start
            duration_secs = duration.total_seconds()
            
            # Update total time before removing session
            session_data['total_time'] = session_data.get('total_time', 0.0) + duration_secs
            
            # Format durations for display
            session_str = self.format_duration(duration_secs)
            total_str = self.format_duration(session_data['total_time'])
            
            embed.add_field(name="User ID", value=str(member.id), inline=True)
            embed.add_field(name="Session Start", value=f"<t:{int(session_start.timestamp())}:F>", inline=True)
            embed.add_field(name="Session End", value=f"<t:{int(session_end.timestamp())}:F>", inline=True)
            embed.add_field(name="⏱️ Session Duration", value=session_str, inline=True)
            embed.add_field(name="⌛ Total Time", value=total_str, inline=True)
            embed.add_field(name="Daily Joins", value=f"{daily_joins} time{'s' if daily_joins != 1 else ''} today", inline=True)
            
            # Add interactions count
            interactions = session_data.get('interactions', 0)
            embed.add_field(name="Interactions", value=f"{interactions} interaction{'s' if interactions != 1 else ''}", inline=True)
            
            # Save total time to a temporary dict before deleting session
            temp_total = session_data['total_time']
            
            # Clean up session - don't create incomplete session entries
            del self.user_sessions[member.id]
            
            self._save_sessions()
        else:
            # User wasn't tracked, show basic info
            embed.add_field(name="User ID", value=str(member.id), inline=True)
            embed.add_field(name="Leave Time", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
            embed.add_field(name="Daily Joins", value=f"{daily_joins} time{'s' if daily_joins != 1 else ''} today", inline=True)
        
        await self._send_embed(embed)
    
    async def log_user_button_click(self, interaction: discord.Interaction, button_name: str, action_result: Optional[str] = None):
        """Log when a user clicks a button."""
        # Increment interaction count for user if they have an active session
        if interaction.user.id in self.user_sessions:
            self.user_sessions[interaction.user.id]['interactions'] = self.user_sessions[interaction.user.id].get('interactions', 0) + 1
        
        embed = discord.Embed(
            title="📝 User Interaction Log",
            color=0x9b59b6  # Discord purple color
        )
        
        # Add user's profile picture
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
            
        # Core fields (top row)
        user_name = interaction.user.display_name
        if isinstance(interaction.user, discord.Member) and interaction.user.nick:
            user_name = f"{interaction.user.nick} ({interaction.user.name})"
        embed.add_field(name="User", value=f"<@{interaction.user.id}> | {user_name}", inline=True)
        embed.add_field(name="Action", value=f"Button: {button_name}", inline=True)
        embed.add_field(name="Response Time", value=f"{round(interaction.client.latency * 1000)}ms", inline=True)
        
        # Second row
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        
        # Voice status and duration
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member and member.voice:
            duration = self.get_user_session_duration(interaction.user.id)
            if not duration:  # User is in voice but we're not tracking them
                duration = "🔊 In Voice (not tracked)"
            else:
                duration = f"🔊 In Voice ({duration})"
            embed.add_field(name="Voice Status", value=duration, inline=True)
        else:
            self.end_user_session(interaction.user.id)  # Ensure we stop tracking if they're not in voice
            embed.add_field(name="Voice Status", value="❌ Not in Voice", inline=True)
        
        # Bot latency
        embed.add_field(name="Bot Latency", value=f"{round(interaction.client.latency * 1000)}ms", inline=True)
        
        # Current surah info if playing
        if hasattr(interaction.client, 'current_audio_file'):
            current_surah = getattr(interaction.client, 'current_audio_file', 'Unknown')
            if current_surah:
                try:
                    surah_info = get_surah_from_filename(current_surah)
                    surah_num = surah_info.get('number', 0)
                    surah_name = get_surah_display_name(surah_num, include_number=True)
                    arabic_name = surah_info.get('arabic_name', '')
                    translation = surah_info.get('translation', '')
                    
                    embed.add_field(
                        name="Current Surah",
                        value=f"**{surah_name}**\n{arabic_name}\n*{translation}*",
                        inline=False
                    )
                except Exception:
                    embed.add_field(name="Current Surah", value=current_surah.replace('.mp3', ''), inline=False)
        
        # Action result/status if provided
        if action_result:
            status_emoji = "✅" if "success" in action_result.lower() else "❌"
            embed.add_field(name="Status", value=f"{status_emoji} {action_result}", inline=False)
        
        # Add timestamp
        embed.timestamp = datetime.now()
        
        await self._send_embed(embed)
    
    async def log_user_select_interaction(self, interaction: discord.Interaction, select_name: str, selected_value: str, action_result: Optional[str] = None):
        """Log when a user interacts with a select menu."""
        # Increment interaction count for user if they have an active session
        if interaction.user.id in self.user_sessions:
            self.user_sessions[interaction.user.id]['interactions'] = self.user_sessions[interaction.user.id].get('interactions', 0) + 1
        
        embed = discord.Embed(
            title="📝 User Interaction Log",
            color=0x9b59b6  # Discord purple color
        )
        
        # Add user's profile picture
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
            
        # Core fields (top row)
        user_name = interaction.user.display_name
        if isinstance(interaction.user, discord.Member) and interaction.user.nick:
            user_name = f"{interaction.user.nick} ({interaction.user.name})"
        embed.add_field(name="User", value=f"<@{interaction.user.id}> | {user_name}", inline=True)
        embed.add_field(name="Action", value=f"{select_name}: {selected_value}", inline=True)
        embed.add_field(name="Response Time", value=f"{interaction.client.latency * 1000:.0f} ms", inline=True)

        # Second row
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        
        # Voice status
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        if member and member.voice:
            # Calculate session duration if user is in VC
            session_info = self.user_sessions.get(interaction.user.id, {})
            if session_info and 'joined_at' in session_info:
                duration = datetime.now() - session_info['joined_at']
                hours = duration.seconds // 3600
                minutes = (duration.seconds % 3600) // 60
                seconds = duration.seconds % 60
                duration_str = f"🔊 In Voice ({hours:02d}:{minutes:02d}:{seconds:02d})"
            else:
                duration_str = "🔊 In Voice (duration unknown)"
            embed.add_field(name="Voice Status", value=duration_str, inline=True)
        else:
            embed.add_field(name="Voice Status", value="❌ Not in Voice", inline=True)
        
        # Bot latency
        embed.add_field(name="Bot Latency", value=f"{interaction.client.latency * 1000:.0f} ms", inline=True)

        # Current surah info if playing
        if hasattr(interaction.client, 'current_audio_file'):
            current_song = getattr(interaction.client, 'current_audio_file', 'Unknown')
            if current_song:
                try:
                    surah_info = get_surah_from_filename(current_song)
                    surah_num = surah_info.get('number', 0)
                    surah_name = get_surah_display_name(surah_num, include_number=True)
                    arabic_name = surah_info.get('arabic_name', '')
                    translation = surah_info.get('translation', '')
                    
                    embed.add_field(
                        name="Current Surah",
                        value=f"**{surah_name}**\n{arabic_name}\n*{translation}*",
                        inline=False
                    )
                except Exception:
                    embed.add_field(name="Current Surah", value=current_song.replace('.mp3', ''), inline=False)
        
        # Action result/status if provided
        if action_result:
            status_emoji = "✅" if "success" in action_result.lower() else "❌"
            embed.add_field(name="Status", value=f"{status_emoji} {action_result}", inline=False)
        
        # Add timestamp
        embed.timestamp = datetime.now()
        
        await self._send_embed(embed)
    
    # HELPER METHODS
    
    def _get_surah_emoji(self, surah_number: int) -> str:
        """Get emoji for surah (simplified version)."""
        special_emojis = {
            1: "🕋", 2: "🐄", 3: "👨‍👩‍👧‍", 4: "👩", 5: "🍽️", 6: "🐪", 7: "⛰️", 8: "⚔️", 9: "🔄", 10: "🐋",
            11: "👨", 12: "👑", 13: "⚡", 14: "👴", 15: "🗿", 16: "🐝", 17: "🌙", 18: "🕳️", 19: "👸", 20: "📜",
            21: "👥", 22: "🕋", 23: "🙏", 24: "💡", 25: "⚖️", 36: "📖", 55: "🌺", 67: "👑", 112: "💎", 113: "🌅", 114: "👥"
        }
        return special_emojis.get(surah_number, "📖")
    
    async def _send_embed(self, embed: discord.Embed):
        """Send embed to logs channel with retry logic and better error handling."""
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting to send embed to logs channel {self.logs_channel_id} (attempt {attempt + 1}/{max_retries})")
                channel = await self.get_logs_channel()
                
                if not channel:
                    logger.warning(f"Could not send Discord embed - channel {self.logs_channel_id} not found")
                    return
                
                logger.debug(f"Found logs channel {channel.name} ({channel.id})")
                await channel.send(embed=embed)
                logger.debug(f"Successfully sent Discord embed to channel {self.logs_channel_id}")
                return  # Success, exit the retry loop
                
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = getattr(e, 'retry_after', 5)  # Safe access to retry_after
                    logger.warning(f"Rate limited when sending embed, waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(retry_after)
                elif e.status in [500, 502, 503, 504]:  # Server errors
                    logger.warning(f"Discord server error {e.status} when sending embed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                elif e.status == 403:  # Forbidden
                    logger.error(f"Bot lacks permissions to send messages in channel {self.logs_channel_id}")
                    break  # Don't retry permission errors
                else:
                    logger.error(f"HTTP error {e.status} when sending embed: {e.text}")
                    break  # Don't retry on other HTTP errors
                    
            except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, ConnectionError) as e:
                logger.warning(f"Connection error when sending embed: {str(e)}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Unexpected error when sending embed: {str(e)}")
                if attempt == max_retries - 1:  # Only log full traceback on final attempt
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                break  # Don't retry unexpected errors
        
        if attempt == max_retries - 1:
            logger.error(f"Failed to send Discord embed after {max_retries} attempts")

    def start_user_session(self, user_id: int):
        """Start tracking a user's voice session."""
        # Only create session if we have complete data
        # This method is called from button interactions when user is in VC but not tracked
        # We should get the member object to create a proper session
        logger.debug(f"start_user_session called for user {user_id} but incomplete data - skipping")
        # Don't create incomplete sessions - let the proper join event handle it

    def end_user_session(self, user_id: int):
        """End tracking a user's voice session."""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            self._save_sessions()

    def get_user_session_duration(self, user_id: int) -> Optional[str]:
        """Get formatted duration of user's current session."""
        if user_id in self.user_sessions and 'joined_at' in self.user_sessions[user_id]:
            duration = datetime.now() - self.user_sessions[user_id]['joined_at']
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            seconds = duration.seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None 