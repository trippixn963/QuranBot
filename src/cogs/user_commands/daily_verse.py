"""
Daily Verse Feature for QuranBot
Sends random verses every 3 hours with dua emoji reactions
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, cast
import asyncio
from monitoring.logging.logger import logger
from monitoring.logging.log_helpers import log_operation
from core.config.config import Config

class DailyVerseManager:
    """Daily verse manager that handles verse scheduling and sending."""
    
    def __init__(self, bot):
        self.bot = bot
        self.verse_pool_file = "data/daily_verses_pool.json"
        self.verse_queue_file = "data/daily_verses_queue.json"
        self.verse_state_file = "data/daily_verses_state.json"
        self.last_verse_time = None
        self.verse_pool = self.load_verse_pool()
        self.verse_queue = self.load_verse_queue()
        self.last_sent_verse = self.load_last_sent_verse()
        self.dua_emoji = "🤲"  # Dua emoji for reactions
        self.daily_verse_task = None
        
        # Initialize queue if empty
        if not self.verse_queue:
            self.reshuffle_verse_queue()
        
        logger.info("Daily verse manager initialized", extra={'event': 'DAILY_VERSE_INIT'})
    
    def load_verse_pool(self) -> List[Dict[str, Any]]:
        """Load verse pool from JSON file."""
        try:
            if os.path.exists(self.verse_pool_file):
                with open(self.verse_pool_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} verses for daily feature", 
                               extra={'event': 'VERSE_POOL_LOADED', 'verse_count': len(data)})
                    return data
            else:
                logger.error(f"Verse pool file not found: {self.verse_pool_file}", extra={'event': 'VERSE_POOL_NOT_FOUND'})
                return []
                
        except Exception as e:
            logger.error(f"Failed to load verse pool: {e}", extra={'event': 'VERSE_POOL_ERROR'})
            return []
    
    def load_verse_queue(self) -> List[Dict[str, Any]]:
        """Load verse queue from JSON file."""
        try:
            if os.path.exists(self.verse_queue_file):
                with open(self.verse_queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded verse queue with {len(data)} verses", 
                               extra={'event': 'VERSE_QUEUE_LOADED', 'queue_count': len(data)})
                    return data
            else:
                logger.info("No verse queue file found, will create new queue", extra={'event': 'VERSE_QUEUE_NOT_FOUND'})
                return []
                
        except Exception as e:
            logger.error(f"Failed to load verse queue: {e}", extra={'event': 'VERSE_QUEUE_ERROR'})
            return []
    
    def save_verse_queue(self):
        """Save verse queue to JSON file."""
        try:
            with open(self.verse_queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.verse_queue, f, indent=2, ensure_ascii=False)
            logger.debug("Verse queue saved successfully", extra={'event': 'VERSE_QUEUE_SAVED'})
        except Exception as e:
            logger.error(f"Failed to save verse queue: {e}", extra={'event': 'VERSE_QUEUE_SAVE_ERROR'})
    
    def load_last_sent_verse(self) -> Optional[Dict[str, Any]]:
        """Load last sent verse from JSON file."""
        try:
            if os.path.exists(self.verse_state_file):
                with open(self.verse_state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Loaded last sent verse state", extra={'event': 'VERSE_STATE_LOADED'})
                    return data.get('last_sent_verse')
            else:
                logger.info("No verse state file found", extra={'event': 'VERSE_STATE_NOT_FOUND'})
                return None
                
        except Exception as e:
            logger.error(f"Failed to load verse state: {e}", extra={'event': 'VERSE_STATE_ERROR'})
            return None
    
    def save_last_sent_verse(self, verse: Dict[str, Any]):
        """Save last sent verse to JSON file."""
        try:
            state_data = {'last_sent_verse': verse, 'last_sent_time': datetime.now().isoformat()}
            with open(self.verse_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            logger.debug("Verse state saved successfully", extra={'event': 'VERSE_STATE_SAVED'})
        except Exception as e:
            logger.error(f"Failed to save verse state: {e}", extra={'event': 'VERSE_STATE_SAVE_ERROR'})
    
    def reshuffle_verse_queue(self):
        """Reshuffle the verse pool and create a new queue."""
        if not self.verse_pool:
            logger.error("No verses in pool to shuffle", extra={'event': 'VERSE_POOL_EMPTY'})
            return
        
        # Create a copy of the pool
        available_verses = self.verse_pool.copy()
        
        # If we have a last sent verse, remove it from available verses to prevent immediate repeat
        if self.last_sent_verse:
            available_verses = [v for v in available_verses if not (
                v['surah'] == self.last_sent_verse['surah'] and 
                v['ayah'] == self.last_sent_verse['ayah']
            )]
        
        # Shuffle the available verses
        random.shuffle(available_verses)
        
        # Set the new queue
        self.verse_queue = available_verses
        self.save_verse_queue()
        
        logger.info(f"Reshuffled verse queue with {len(self.verse_queue)} verses", 
                   extra={'event': 'VERSE_QUEUE_SHUFFLED', 'queue_count': len(self.verse_queue)})
    
    def get_next_verse(self) -> Optional[Dict[str, Any]]:
        """Get the next verse from the queue."""
        if not self.verse_queue:
            logger.info("Verse queue is empty, reshuffling...", extra={'event': 'VERSE_QUEUE_EMPTY'})
            self.reshuffle_verse_queue()
            
            # If still empty after reshuffling, something is wrong
            if not self.verse_queue:
                logger.error("Verse queue still empty after reshuffling", extra={'event': 'VERSE_QUEUE_STILL_EMPTY'})
                return None
        
        # Get the next verse from the queue
        verse = self.verse_queue.pop(0)
        self.save_verse_queue()
        
        logger.debug(f"Selected next verse: {verse['surah_name']} {verse['ayah']}", 
                    extra={'event': 'VERSE_SELECTED', 'surah': verse['surah'], 'ayah': verse['ayah']})
        return verse
    
    def create_verse_embed(self, verse: Dict[str, Any]) -> discord.Embed:
        """Create a beautiful embed for the verse."""
        embed = discord.Embed(
            title=f"📖 Daily Verse - {verse['surah_name']} ({verse['arabic_name']})",
            description=f"**Ayah {verse['ayah']}**",
            color=0x1abc3c  # Green color matching the bot's PFP
        )
        
        # Add Arabic text
        embed.add_field(
            name="🌙 Arabic",
            value=f"```{verse['arabic']}```",
            inline=False
        )
        
        # Add translation in a black code block
        embed.add_field(
            name="📝 Translation",
            value=f"```{verse['translation']}```",
            inline=False
        )
        
        # Remove author and footer, set bot pfp as thumbnail
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        return embed
    
    def get_daily_verse_channel(self) -> Optional[discord.TextChannel]:
        channel_id = getattr(Config, 'DAILY_VERSE_CHANNEL_ID', None)
        if not channel_id:
            logger.error('DAILY_VERSE_CHANNEL_ID is not set in the environment/config!', extra={'event': 'VERSE_CHANNEL_ID_MISSING'})
            return None
        channel = self.bot.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        return None
    
    async def start_daily_verse_task(self):
        """Start the daily verse task."""
        if self.daily_verse_task is None or self.daily_verse_task.done():
            self.daily_verse_task = asyncio.create_task(self.daily_verse_loop())
            logger.info("Daily verse task started", extra={'event': 'VERSE_TASK_STARTED'})
    
    async def daily_verse_loop(self):
        """Main loop for sending daily verses every 3 hours."""
        # Wait a bit for the bot to be fully ready before sending first verse
        await asyncio.sleep(10)  # Wait 10 seconds for bot to be fully connected
        
        # Send first verse immediately
        await self.send_daily_verse()
        
        # Then continue with 3-hour intervals
        while True:
            try:
                await asyncio.sleep(3 * 60 * 60)  # Wait 3 hours
                await self.send_daily_verse()
            except Exception as e:
                logger.error(f"Failed to send daily verse: {e}", extra={'event': 'VERSE_SEND_ERROR'})
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def send_daily_verse(self):
        """Send a daily verse."""
        try:
            # Always use the specified channel
            text_channel = self.get_daily_verse_channel()
            if text_channel is None:
                logger.error(f"Could not find verse channel {text_channel} or it is not a TextChannel", extra={'event': 'VERSE_CHANNEL_NOT_FOUND'})
                return
            
            # Get next verse from queue
            verse = self.get_next_verse()
            if not verse:
                logger.error("No verses available", extra={'event': 'NO_VERSES_AVAILABLE'})
                return
            
            # Create and send embed
            embed = self.create_verse_embed(verse)
            message = await text_channel.send(embed=embed)
            
            # Add dua emoji reaction
            await message.add_reaction(self.dua_emoji)
            
            # Update last verse time and save state
            self.last_verse_time = datetime.now()
            self.last_sent_verse = verse
            self.save_last_sent_verse(verse)
            
            logger.info(f"Daily verse sent: {verse['surah_name']} {verse['ayah']}", 
                       extra={'event': 'VERSE_SENT', 'surah': verse['surah'], 'ayah': verse['ayah'], 'channel_id': text_channel.id})
            
        except Exception as e:
            logger.error(f"Failed to send daily verse: {e}", extra={'event': 'VERSE_SEND_ERROR'})

# Global instance
daily_verse_manager = None

async def setup(bot):
    """Setup the daily verse feature."""
    global daily_verse_manager
    
    try:
        # Initialize the daily verse manager
        daily_verse_manager = DailyVerseManager(bot)
        
        # Add commands to the bot's command tree
        @bot.tree.command(name="sendverse", description="Send a verse now (Admin only)")
        async def send_verse_now(interaction: discord.Interaction):
            """Send a daily verse immediately."""
            try:
                # Check if manager is initialized
                if daily_verse_manager is None:
                    await interaction.response.send_message("❌ Daily verse system not initialized!", ephemeral=True)
                    return
                
                # Permission check
                if not hasattr(interaction.user, 'guild_permissions') or not getattr(interaction.user, 'guild_permissions').administrator:
                    await interaction.response.send_message("❌ You do not have permission to use this command!", ephemeral=True)
                    return
                
                # Get next verse from queue
                verse = daily_verse_manager.get_next_verse()
                if not verse:
                    await interaction.response.send_message("❌ No verses available!", ephemeral=True)
                    return
                
                # Create embed
                embed = daily_verse_manager.create_verse_embed(verse)
                
                # Send to interaction channel (ensure it's a TextChannel)
                if isinstance(interaction.channel, discord.TextChannel):
                    message = await interaction.channel.send(embed=embed)
                    await message.add_reaction(daily_verse_manager.dua_emoji)
                    
                    # Update state
                    daily_verse_manager.last_sent_verse = verse
                    daily_verse_manager.save_last_sent_verse(verse)
                    
                    await interaction.response.send_message("✅ Verse sent!", ephemeral=True)
                    
                    logger.info(f"Manual verse sent: {verse['surah_name']} {verse['ayah']}", 
                               extra={'event': 'MANUAL_VERSE_SENT', 'surah': verse['surah'], 'ayah': verse['ayah'], 'user_id': interaction.user.id})
                else:
                    await interaction.response.send_message("❌ Can only send verses in text channels!", ephemeral=True)
                
            except Exception as e:
                logger.error(f"Failed to send manual verse: {e}", extra={'event': 'MANUAL_VERSE_ERROR'})
                await interaction.response.send_message("❌ Failed to send verse!", ephemeral=True)
        
        @bot.tree.command(name="versestatus", description="Check daily verse status")
        async def verse_status(interaction: discord.Interaction):
            """Check the status of the daily verse feature."""
            try:
                # Check if manager is initialized
                if daily_verse_manager is None:
                    await interaction.response.send_message("❌ Daily verse system not initialized!", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="📖 Daily Verse Status",
                    color=0x00aaff,
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="Pool Size",
                    value=str(len(daily_verse_manager.verse_pool)),
                    inline=True
                )
                
                embed.add_field(
                    name="Queue Size",
                    value=str(len(daily_verse_manager.verse_queue)),
                    inline=True
                )
                
                embed.add_field(
                    name="Channel",
                    value=f"<#{daily_verse_manager.get_daily_verse_channel().id}>",
                    inline=True
                )
                
                embed.add_field(
                    name="Interval",
                    value="Every 3 hours",
                    inline=True
                )
                
                if daily_verse_manager.last_verse_time:
                    embed.add_field(
                        name="Last Sent",
                        value=daily_verse_manager.last_verse_time.strftime("%Y-%m-%d %H:%M:%S"),
                        inline=True
                    )
                
                if daily_verse_manager.last_sent_verse:
                    embed.add_field(
                        name="Last Verse",
                        value=f"{daily_verse_manager.last_sent_verse['surah_name']} {daily_verse_manager.last_sent_verse['ayah']}",
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                
                logger.info(f"Verse status checked by {interaction.user.name}", 
                           extra={'event': 'VERSE_STATUS_CHECK', 'user_id': interaction.user.id})
                
            except Exception as e:
                logger.error(f"Failed to get verse status: {e}", extra={'event': 'VERSE_STATUS_ERROR'})
                await interaction.response.send_message("❌ Failed to get verse status!", ephemeral=True)
        
        @bot.tree.command(name="reshuffleverses", description="Reshuffle the verse queue (Admin only)")
        async def reshuffle_verses(interaction: discord.Interaction):
            """Reshuffle the verse queue manually."""
            try:
                # Check if manager is initialized
                if daily_verse_manager is None:
                    await interaction.response.send_message("❌ Daily verse system not initialized!", ephemeral=True)
                    return
                
                # Permission check
                if not hasattr(interaction.user, 'guild_permissions') or not getattr(interaction.user, 'guild_permissions').administrator:
                    await interaction.response.send_message("❌ You do not have permission to use this command!", ephemeral=True)
                    return
                
                daily_verse_manager.reshuffle_verse_queue()
                
                embed = discord.Embed(
                    title="✅ Verses Reshuffled",
                    description=f"Verse queue has been reshuffled with {len(daily_verse_manager.verse_queue)} verses",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                await interaction.response.send_message(embed=embed)
                
                logger.info(f"Verses reshuffled by {interaction.user.name}", 
                           extra={'event': 'VERSE_RESHUFFLE', 'user_id': interaction.user.id})
                
            except Exception as e:
                logger.error(f"Failed to reshuffle verses: {e}", extra={'event': 'VERSE_RESHUFFLE_ERROR'})
                await interaction.response.send_message("❌ Failed to reshuffle verses!", ephemeral=True)
        
        @bot.tree.command(name="listchannels", description="List all available channels (Admin only)")
        async def list_channels(interaction: discord.Interaction):
            """List all available channels for debugging."""
            try:
                # Permission check
                if not hasattr(interaction.user, 'guild_permissions') or not getattr(interaction.user, 'guild_permissions').administrator:
                    await interaction.response.send_message("❌ You do not have permission to use this command!", ephemeral=True)
                    return
                
                guild = interaction.guild
                if not guild:
                    await interaction.response.send_message("❌ This command can only be used in a guild!", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="📋 Available Channels",
                    description=f"Channels in {guild.name}",
                    color=0x00aaff,
                    timestamp=datetime.now()
                )
                
                text_channels = []
                voice_channels = []
                
                for channel in guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        text_channels.append(f"<#{channel.id}> - {channel.name}")
                    elif isinstance(channel, discord.VoiceChannel):
                        voice_channels.append(f"<#{channel.id}> - {channel.name}")
                
                if text_channels:
                    embed.add_field(
                        name="📝 Text Channels",
                        value="\n".join(text_channels[:10]),  # Limit to first 10
                        inline=False
                    )
                
                if voice_channels:
                    embed.add_field(
                        name="🔊 Voice Channels",
                        value="\n".join(voice_channels[:10]),  # Limit to first 10
                        inline=False
                    )
                
                embed.add_field(
                    name="Total Channels",
                    value=f"Text: {len(text_channels)}, Voice: {len(voice_channels)}",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                logger.info(f"Channel list requested by {interaction.user.name}", 
                           extra={'event': 'CHANNEL_LIST_REQUEST', 'user_id': interaction.user.id})
                
            except Exception as e:
                logger.error(f"Failed to list channels: {e}", extra={'event': 'CHANNEL_LIST_ERROR'})
                await interaction.response.send_message("❌ Failed to list channels!", ephemeral=True)
        
        # Start the daily verse task
        await daily_verse_manager.start_daily_verse_task()
        
        logger.info("Daily verse feature loaded successfully", extra={'event': 'VERSE_COG_LOADED'})
        
    except Exception as e:
        logger.error(f"Failed to load daily verse feature: {e}", extra={'event': 'VERSE_COG_LOAD_ERROR'})
        raise 