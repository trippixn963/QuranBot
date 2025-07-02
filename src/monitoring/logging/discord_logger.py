"""
Discord embed logging system for QuranBot.
Sends beautiful embeds to Discord channels for real-time activity monitoring.
"""

import asyncio
import discord
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from monitoring.logging.logger import logger

class DiscordEmbedLogger:
    """Handles sending formatted embed logs to Discord channels."""
    
    def __init__(self, bot, logs_channel_id: int, target_vc_id: int = 1389675580253016144):
        """Initialize the Discord embed logger."""
        self.bot = bot
        self.logs_channel_id = logs_channel_id
        self.target_vc_id = target_vc_id  # Only track this specific VC
        self.sessions_file = "data/user_vc_sessions.json"
        self.user_sessions: Dict[int, Dict[str, Any]] = {}  # Track user VC sessions
        
        # Load existing sessions on startup
        self._load_sessions()
        
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
                                'total_time': 0.0
                            }
                            logger.info(f"Initialized session for {member.display_name} already in VC")
                        else:
                            # Update their join time to now (since we don't know when they actually joined during downtime)
                            self.user_sessions[member.id]['joined_at'] = datetime.now()
                            self.user_sessions[member.id]['username'] = member.display_name
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
            channel = self.bot.get_channel(self.logs_channel_id)
            if not channel:
                logger.warning(f"Discord logger: Could not find logs channel {self.logs_channel_id}")
            return channel
        except Exception as e:
            logger.error(f"Discord logger error getting channel: {e}")
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
                            'total_time': session_data.get('total_time', 0.0)  # Accumulated time from previous sessions
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
                serializable_data[str(user_id)] = {
                    'joined_at': session_data['joined_at'].isoformat(),
                    'channel_name': session_data['channel_name'],
                    'username': session_data['username'],
                    'total_time': session_data.get('total_time', 0.0)
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
            description=f"Successfully connected to voice channel",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="🏠 Server", value=guild_name, inline=True)
        embed.add_field(name="⏰ Status", value="Ready to stream", inline=True)
        
        await self._send_embed(embed)
    
    async def log_bot_disconnected(self, channel_name: str, reason: str = "Unknown"):
        """Log when bot disconnects from voice channel."""
        embed = discord.Embed(
            title="🔴 Bot Disconnected",
            description=f"Disconnected from voice channel",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.add_field(name="❌ Reason", value=reason, inline=True)
        embed.add_field(name="⏰ Status", value="Offline", inline=True)
        
        await self._send_embed(embed)
    
    async def log_surah_changed(self, surah_info: Dict[str, Any], reciter: str):
        """Log when bot changes surahs."""
        emoji = self._get_surah_emoji(surah_info.get('number', 0))
        
        embed = discord.Embed(
            title=f"{emoji} Now Playing",
            description=f"**{surah_info.get('english_name', 'Unknown')}**",
            color=0x00aaff,
            timestamp=datetime.now()
        )
        embed.add_field(name="📖 Surah", value=f"{surah_info.get('number', 0):03d}. {surah_info.get('english_name', 'Unknown')}", inline=True)
        embed.add_field(name="🎵 Reciter", value=reciter, inline=True)
        embed.add_field(name="🔤 Arabic", value=surah_info.get('arabic_name', 'غير معروف'), inline=True)
        
        if surah_info.get('translation'):
            embed.add_field(name="📝 Translation", value=surah_info.get('translation'), inline=False)
        
        await self._send_embed(embed)
    
    async def log_reciter_changed(self, old_reciter: str, new_reciter: str, user_name: str):
        """Log when reciter is changed."""
        embed = discord.Embed(
            title="🎤 Reciter Changed",
            description=f"Reciter switched by {user_name}",
            color=0xff9900,
            timestamp=datetime.now()
        )
        embed.add_field(name="🔄 From", value=old_reciter, inline=True)
        embed.add_field(name="➡️ To", value=new_reciter, inline=True)
        embed.add_field(name="👤 Changed By", value=user_name, inline=True)
        
        await self._send_embed(embed)
    
    # USER ACTIVITY EMBEDS
    
    async def log_user_joined_vc(self, member: discord.Member, channel_name: str):
        """Log when a user joins the target voice channel."""
        # Start tracking session (no previous time accumulation)
        self.user_sessions[member.id] = {
            'joined_at': datetime.now(),
            'channel_name': channel_name,
            'username': member.display_name
        }
        
        # Save sessions after each join
        self._save_sessions()
        
        embed = discord.Embed(
            title="🟢 User Joined Quran VC",
            description=f"{member.display_name} joined the Quran voice channel",
            color=0x00ff88,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 User", value=f"<@{member.id}>", inline=True)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await self._send_embed(embed)
    
    async def log_user_left_vc(self, member: discord.Member, channel_name: str):
        """Log when a user leaves the target voice channel with session duration."""
        session_duration = 0.0
        
        if member.id in self.user_sessions:
            session_info = self.user_sessions[member.id]
            # Calculate current session duration
            session_duration = (datetime.now() - session_info['joined_at']).total_seconds()
            
            # Remove the session (reset time tracking)
            del self.user_sessions[member.id]
            self._save_sessions()
        
        embed = discord.Embed(
            title="🔴 User Left Quran VC",
            description=f"{member.display_name} left the Quran voice channel",
            color=0xff4444,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 User", value=f"<@{member.id}>", inline=True)
        
        if session_duration > 0:
            embed.add_field(name="⏱️ Session Time", value=self.format_duration(session_duration), inline=True)
        else:
            embed.add_field(name="⏱️ Duration", value="Unknown", inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await self._send_embed(embed)
    
    async def log_user_button_click(self, interaction: discord.Interaction, button_name: str, action_result: str = None):
        """Log when a user clicks a button."""
        embed = discord.Embed(
            title="🔘 Button Interaction",
            description=f"{interaction.user.display_name} clicked a button",
            color=0x5865f2,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 User", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="🔘 Button", value=button_name, inline=True)
        
        if action_result:
            embed.add_field(name="✅ Result", value=action_result, inline=False)
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        await self._send_embed(embed)
    
    async def log_user_select_interaction(self, interaction: discord.Interaction, select_name: str, selected_value: str, action_result: str = None):
        """Log when a user uses a select menu."""
        embed = discord.Embed(
            title="📋 Select Interaction",
            description=f"{interaction.user.display_name} used a select menu",
            color=0x9932cc,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 User", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="📋 Menu", value=select_name, inline=True)
        embed.add_field(name="✅ Selected", value=selected_value, inline=True)
        
        if action_result:
            embed.add_field(name="🎯 Result", value=action_result, inline=False)
        
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        await self._send_embed(embed)
    
    # HELPER METHODS
    
    def _get_surah_emoji(self, surah_number: int) -> str:
        """Get emoji for surah (simplified version)."""
        special_emojis = {
            1: "🕋", 2: "🐄", 3: "👨‍👩‍👧‍👦", 4: "👩", 5: "🍽️", 6: "🐪", 7: "⛰️", 8: "⚔️", 9: "🔄", 10: "🐋",
            11: "👨", 12: "👑", 13: "⚡", 14: "👴", 15: "🗿", 16: "🐝", 17: "🌙", 18: "🕳️", 19: "👸", 20: "📜",
            21: "👥", 22: "🕋", 23: "🙏", 24: "💡", 25: "⚖️", 36: "📖", 55: "🌺", 67: "👑", 112: "💎", 113: "🌅", 114: "👥"
        }
        return special_emojis.get(surah_number, "📖")
    
    async def _send_embed(self, embed: discord.Embed):
        """Send embed to logs channel."""
        try:
            channel = await self.get_logs_channel()
            if channel:
                await channel.send(embed=embed)
                logger.debug(f"Discord embed sent to channel {self.logs_channel_id}")
            else:
                logger.warning(f"Could not send Discord embed - channel {self.logs_channel_id} not found")
        except Exception as e:
            logger.error(f"Failed to send Discord embed: {e}") 