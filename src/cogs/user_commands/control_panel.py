import asyncio
import discord
import os
import traceback
import time
import psutil
import gc
from datetime import datetime
from typing import Optional, Dict, Any
from discord.ui import View, Select, Button
import functools

# Use the main logger from utils
from utils.logger_fixed import logger
from utils.log_helpers import log_async_function_call, log_function_call, log_operation, get_system_metrics, get_discord_context, get_bot_state
from utils.panel_manager import panel_manager

def get_system_metrics():
    """Get comprehensive system metrics"""
    process = psutil.Process()
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent()
    gc_stats = gc.get_stats()
    
    return {
        "memory_rss_mb": memory_info.rss / 1024 / 1024,
        "memory_vms_mb": memory_info.vms / 1024 / 1024,
        "cpu_percent": cpu_percent,
        "gc_collections": len(gc_stats),
        "gc_objects": sum(stat['collections'] for stat in gc_stats),
        "gc_time": sum(stat['collections'] for stat in gc_stats)
    }

def get_user_context(interaction: discord.Interaction) -> Dict[str, Any]:
    """Get comprehensive user context"""
    user = interaction.user
    member = interaction.guild.get_member(user.id) if interaction.guild else None
    
    context = {
        "user_id": user.id,
        "user_name": user.name,
        "user_display_name": user.display_name,
        "user_created_at": user.created_at.isoformat() if user.created_at else None,
        "user_bot": user.bot,
        "user_system": user.system,
        "user_discriminator": getattr(user, 'discriminator', None),
        "user_avatar_url": str(user.avatar.url) if user.avatar else None,
        "user_banner_url": str(user.banner.url) if hasattr(user, 'banner') and user.banner else None,
        "guild_id": interaction.guild.id if interaction.guild else None,
        "guild_name": interaction.guild.name if interaction.guild else None,
        "guild_member_count": interaction.guild.member_count if interaction.guild else None,
        "channel_id": interaction.channel.id if interaction.channel else None,
        "channel_name": getattr(interaction.channel, 'name', 'DM') if interaction.channel else None,
        "channel_type": str(type(interaction.channel).__name__) if interaction.channel else None,
        "interaction_id": interaction.id,
        "interaction_type": str(interaction.type),
        "interaction_token": interaction.token[:10] + "..." if interaction.token else None,
        "interaction_created_at": interaction.created_at.isoformat() if interaction.created_at else None,
        "client_latency": round(interaction.client.latency * 1000, 2) if interaction.client else None,
    }
    
    if member:
        context.update({
            "member_joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "member_nick": member.nick,
            "member_roles": [role.name for role in member.roles],
            "member_role_ids": [role.id for role in member.roles],
            "member_top_role": member.top_role.name if member.top_role else None,
            "member_color": str(member.color) if member.color else None,
            "member_timed_out_until": member.timed_out_until.isoformat() if member.timed_out_until else None,
            "member_voice_state": {
                "channel_id": member.voice.channel.id if member.voice and member.voice.channel else None,
                "channel_name": member.voice.channel.name if member.voice and member.voice.channel else None,
                "deaf": member.voice.deaf if member.voice else None,
                "mute": member.voice.mute if member.voice else None,
                "self_deaf": member.voice.self_deaf if member.voice else None,
                "self_mute": member.voice.self_mute if member.voice else None,
                "streaming": member.voice.self_stream if member.voice else None,
                "video": member.voice.self_video if member.voice else None,
            } if member.voice else None
        })
    
    return context

def get_bot_state(bot) -> Dict[str, Any]:
    """Get comprehensive bot state"""
    try:
        return {
            "bot_user_id": bot.user.id if bot.user else None,
            "bot_user_name": bot.user.name if bot.user else None,
            "bot_guild_count": len(bot.guilds),
            "bot_user_count": len(bot.users),
            "bot_latency": round(bot.latency * 1000, 2),
            "bot_is_ready": bot.is_ready(),
            "bot_ws_closed": bot.is_ws_ratelimited(),
            "current_reciter": getattr(bot, 'current_reciter', None),
            "is_streaming": getattr(bot, 'is_streaming', None),
            "loop_enabled": getattr(bot, 'loop_enabled', None),
            "shuffle_enabled": getattr(bot, 'shuffle_enabled', None),
            "current_audio_file": getattr(bot, 'current_audio_file', None),
            "current_song_index": bot.state_manager.get_current_song_index() if hasattr(bot, 'state_manager') else None,
            "current_song_name": bot.state_manager.get_current_song_name() if hasattr(bot, 'state_manager') else None,
            "available_reciters": bot.get_available_reciters() if hasattr(bot, 'get_available_reciters') else None,
            "audio_files_count": len(bot.get_audio_files()) if hasattr(bot, 'get_audio_files') else None,
        }
    except Exception as e:
        return {"bot_state_error": str(e)}

def log_operation(operation: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
    """Enhanced logging with operation tracking and structured data."""
    level_emoji = {"DEBUG": "", "INFO": "", "WARNING": "", "ERROR": "", "CRITICAL": ""}
    
    # Format timestamp with new format: MM-DD | HH:MM:SS AM/PM
    timestamp = datetime.now().strftime('%m-%d | %I:%M:%S %p')
    
    log_data = {
        "operation": operation,
        "timestamp": timestamp,
        "component": "control_panel"
    }
    
    if extra:
        log_data.update(extra)
    
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        log_data["traceback"] = traceback.format_exc()
        level = "ERROR"
    
    # Include user information in the main log message if available
    user_info = ""
    if extra and "user_name" in extra and "user_id" in extra:
        user_info = f" | 👤 {extra['user_name']} ({extra['user_id']})"
    
    log_message = f"Control Panel - {operation.upper()}{user_info}"
    
    if level == "DEBUG":
        logger.debug(log_message, extra={"extra": log_data})
    elif level == "INFO":
        logger.info(log_message, extra={"extra": log_data})
    elif level == "WARNING":
        logger.warning(log_message, extra={"extra": log_data})
    elif level == "ERROR":
        logger.error(log_message, extra={"extra": log_data})
    elif level == "CRITICAL":
        logger.critical(log_message, extra={"extra": log_data})

def is_in_voice_channel(interaction: discord.Interaction) -> bool:
    """Check if the user is in the voice channel with enhanced logging."""
    try:
        log_operation("check", "DEBUG", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "check_type": "voice_channel"
        })
        
        from utils.config import Config
        target_channel_id = Config.TARGET_CHANNEL_ID
        
        # Check if user has voice state (Member objects have voice state)
        if not isinstance(interaction.user, discord.Member):
            log_operation("check", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "reason": "user_not_member",
                "check_type": "voice_channel"
            })
            return False
        
        member = interaction.user
        if not member.voice or not member.voice.channel:
            log_operation("check", "WARNING", {
                "user_id": member.id,
                "user_name": member.name,
                "reason": "user_not_in_voice",
                "check_type": "voice_channel"
            })
            return False
        
        if member.voice.channel.id == target_channel_id:
            log_operation("check", "INFO", {
                "user_id": member.id,
                "user_name": member.name,
                "voice_channel_id": member.voice.channel.id,
                "voice_channel_name": member.voice.channel.name,
                "check_type": "voice_channel",
                "result": "success"
            })
            return True
        
        log_operation("check", "WARNING", {
            "user_id": member.id,
            "user_name": member.name,
            "user_voice_channel_id": member.voice.channel.id,
            "user_voice_channel_name": member.voice.channel.name,
            "target_channel_id": target_channel_id,
            "check_type": "voice_channel",
            "result": "wrong_channel"
        })
        return False
        
    except Exception as e:
        log_operation("check", "ERROR", {
            "user_id": interaction.user.id if interaction.user else None,
            "check_type": "voice_channel",
            "error_details": "voice_channel_check_failed"
        }, e)
        return False

def log_button_interaction(func):
    """Enhanced decorator to log detailed button interaction metrics"""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, button: Button):
        start_time = time.time()
        button_name = button.label if button.label else button.custom_id
        button_style = str(button.style)
        button_disabled = button.disabled
        button_url = button.url if hasattr(button, 'url') else None
        
        # Get comprehensive context
        user_context = get_user_context(interaction)
        bot_state_before = get_bot_state(self.bot)
        system_metrics_before = get_system_metrics()
        
        # Log button press start with all details
        current_time = datetime.now()
        logger.info(f"BUTTON_INTERACTION_START | Button: {button_name} | Style: {button_style} | Disabled: {button_disabled} | URL: {button_url} | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | ClientLatency: {user_context['client_latency']}ms | BotLatency: {bot_state_before['bot_latency']}ms | Memory: {system_metrics_before['memory_rss_mb']:.1f}MB | CPU: {system_metrics_before['cpu_percent']:.1f}% | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
        
        # Log detailed context
        logger.debug(f"BUTTON_CONTEXT_DETAILED | UserContext: {user_context} | BotStateBefore: {bot_state_before} | SystemMetricsBefore: {system_metrics_before}")
        
        try:
            # Execute the button function
            result = await func(self, interaction, button)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Get state after execution
            bot_state_after = get_bot_state(self.bot)
            system_metrics_after = get_system_metrics()
            
            # Calculate state changes
            state_changes = {}
            for key in bot_state_before:
                if key in bot_state_after and bot_state_before[key] != bot_state_after[key]:
                    state_changes[key] = {
                        "before": bot_state_before[key],
                        "after": bot_state_after[key]
                    }
            
            # Log successful button press completion with all metrics
            current_time = datetime.now()
            logger.info(f"BUTTON_INTERACTION_SUCCESS | Button: {button_name} | ResponseTime: {response_time:.2f}ms | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | StateChanges: {len(state_changes)} | MemoryChange: {system_metrics_after['memory_rss_mb'] - system_metrics_before['memory_rss_mb']:+.1f}MB | CPUChange: {system_metrics_after['cpu_percent'] - system_metrics_before['cpu_percent']:+.1f}% | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
            
            # Log detailed state changes if any
            if state_changes:
                logger.debug(f"BUTTON_STATE_CHANGES | Button: {button_name} | Changes: {state_changes}")
            
            # Log performance metrics
            logger.debug(f"BUTTON_PERFORMANCE_METRICS | Button: {button_name} | ResponseTime: {response_time:.2f}ms | MemoryBefore: {system_metrics_before['memory_rss_mb']:.1f}MB | MemoryAfter: {system_metrics_after['memory_rss_mb']:.1f}MB | CPUBefore: {system_metrics_before['cpu_percent']:.1f}% | CPUAfter: {system_metrics_after['cpu_percent']:.1f}% | GarbageCollections: {system_metrics_after['gc_collections'] - system_metrics_before['gc_collections']}")
            
            return result
            
        except Exception as e:
            # Calculate response time even for errors
            response_time = (time.time() - start_time) * 1000
            
            # Get state after error
            bot_state_after = get_bot_state(self.bot)
            system_metrics_after = get_system_metrics()
            
            # Log button press error with all details
            current_time = datetime.now()
            logger.error(f"BUTTON_INTERACTION_ERROR | Button: {button_name} | ResponseTime: {response_time:.2f}ms | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | Error: {str(e)} | ErrorType: {type(e).__name__} | MemoryBefore: {system_metrics_before['memory_rss_mb']:.1f}MB | MemoryAfter: {system_metrics_after['memory_rss_mb']:.1f}MB | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
            
            # Log full error details
            logger.error(f"BUTTON_ERROR_DETAILED | Button: {button_name} | FullTraceback: {traceback.format_exc()} | UserContext: {user_context} | BotStateBefore: {bot_state_before} | BotStateAfter: {bot_state_after}")
            
            raise
    
    return wrapper

def log_select_interaction(func):
    """Enhanced decorator to log detailed select interaction metrics"""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction):
        start_time = time.time()
        select_name = self.placeholder if hasattr(self, 'placeholder') else "Unknown Select"
        selected_value = self.values[0] if self.values else "None"
        selected_values = self.values if self.values else []
        min_values = self.min_values if hasattr(self, 'min_values') else 1
        max_values = self.max_values if hasattr(self, 'max_values') else 1
        
        # Get comprehensive context
        user_context = get_user_context(interaction)
        bot_state_before = get_bot_state(self.bot)
        system_metrics_before = get_system_metrics()
        
        # Log select interaction start with all details
        current_time = datetime.now()
        logger.info(f"SELECT_INTERACTION_START | Select: {select_name} | SelectedValue: {selected_value} | SelectedValues: {selected_values} | MinValues: {min_values} | MaxValues: {max_values} | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | ClientLatency: {user_context['client_latency']}ms | BotLatency: {bot_state_before['bot_latency']}ms | Memory: {system_metrics_before['memory_rss_mb']:.1f}MB | CPU: {system_metrics_before['cpu_percent']:.1f}% | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
        
        # Log detailed context
        logger.debug(f"SELECT_CONTEXT_DETAILED | UserContext: {user_context} | BotStateBefore: {bot_state_before} | SystemMetricsBefore: {system_metrics_before}")
        
        try:
            # Execute the select function
            result = await func(self, interaction)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Get state after execution
            bot_state_after = get_bot_state(self.bot)
            system_metrics_after = get_system_metrics()
            
            # Calculate state changes
            state_changes = {}
            for key in bot_state_before:
                if key in bot_state_after and bot_state_before[key] != bot_state_after[key]:
                    state_changes[key] = {
                        "before": bot_state_before[key],
                        "after": bot_state_after[key]
                    }
            
            # Log successful select interaction completion with all metrics
            current_time = datetime.now()
            logger.info(f"SELECT_INTERACTION_SUCCESS | Select: {select_name} | SelectedValue: {selected_value} | ResponseTime: {response_time:.2f}ms | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | StateChanges: {len(state_changes)} | MemoryChange: {system_metrics_after['memory_rss_mb'] - system_metrics_before['memory_rss_mb']:+.1f}MB | CPUChange: {system_metrics_after['cpu_percent'] - system_metrics_before['cpu_percent']:+.1f}% | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
            
            # Log detailed state changes if any
            if state_changes:
                logger.debug(f"SELECT_STATE_CHANGES | Select: {select_name} | Changes: {state_changes}")
            
            # Log performance metrics
            logger.debug(f"SELECT_PERFORMANCE_METRICS | Select: {select_name} | ResponseTime: {response_time:.2f}ms | MemoryBefore: {system_metrics_before['memory_rss_mb']:.1f}MB | MemoryAfter: {system_metrics_after['memory_rss_mb']:.1f}MB | CPUBefore: {system_metrics_before['cpu_percent']:.1f}% | CPUAfter: {system_metrics_after['cpu_percent']:.1f}% | GarbageCollections: {system_metrics_after['gc_collections'] - system_metrics_before['gc_collections']}")
            
            return result
            
        except Exception as e:
            # Calculate response time even for errors
            response_time = (time.time() - start_time) * 1000
            
            # Get state after error
            bot_state_after = get_bot_state(self.bot)
            system_metrics_after = get_system_metrics()
            
            # Log select interaction error with all details
            current_time = datetime.now()
            logger.error(f"SELECT_INTERACTION_ERROR | Select: {select_name} | SelectedValue: {selected_value} | ResponseTime: {response_time:.2f}ms | User: {user_context['user_name']} ({user_context['user_id']}) | Guild: {user_context['guild_name']} | Channel: {user_context['channel_name']} | Error: {str(e)} | ErrorType: {type(e).__name__} | MemoryBefore: {system_metrics_before['memory_rss_mb']:.1f}MB | MemoryAfter: {system_metrics_after['memory_rss_mb']:.1f}MB | Date: {current_time.strftime('%m/%d/%Y')} | Time: {current_time.strftime('%I:%M:%S %p')}")
            
            # Log full error details
            logger.error(f"SELECT_ERROR_DETAILED | Select: {select_name} | FullTraceback: {traceback.format_exc()} | UserContext: {user_context} | BotStateBefore: {bot_state_before} | BotStateAfter: {bot_state_after}")
            
            raise
    
    return wrapper

class SurahSelect(Select):
    def __init__(self, bot, page=0):
        from utils.surah_mapper import get_surah_display_name, get_surah_emoji
        current_reciter = getattr(bot, 'current_reciter', None)
        audio_files = bot.get_audio_files() if current_reciter else []
        
        # Get all available surahs
        all_surahs = []
        seen = set()
        for file in audio_files:
            name = os.path.basename(file)
            if name.endswith('.mp3'):
                surah_num = name.split('.')[0]
                if surah_num not in seen:
                    seen.add(surah_num)
                    try:
                        surah_num_int = int(surah_num)
                        surah_name = get_surah_display_name(surah_num_int)
                        all_surahs.append((surah_num_int, surah_num, surah_name))
                    except Exception:
                        continue
        
        # Sort by surah number
        all_surahs.sort(key=lambda x: x[0])
        
        # Calculate pagination
        items_per_page = 25
        total_pages = (len(all_surahs) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(all_surahs))
        
        # Create options for current page
        surah_options = []
        for surah_num_int, surah_num, surah_name in all_surahs[start_idx:end_idx]:
            emoji = get_surah_emoji(surah_num_int)
            # Get just the surah name without the number for cleaner display
            from utils.surah_mapper import get_surah_display_name
            clean_name = get_surah_display_name(surah_num_int, include_number=False)
            surah_options.append(discord.SelectOption(
                label=f"{emoji} {clean_name}",
                value=surah_num,
                description=f"Surah {surah_num_int}"
            ))
        
        # Create placeholder with page info
        placeholder = f"Select Surah... (Page {page + 1}/{total_pages})"
        
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=surah_options, custom_id=f"select_surah_page_{page}")
        self.bot = bot
        self.page = page
        self.total_pages = total_pages
        self.all_surahs = all_surahs
    @log_select_interaction
    async def callback(self, interaction: discord.Interaction):
        # Intensive logging for surah selection
        log_operation("surah", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": getattr(interaction.channel, 'name', 'DM') if interaction.channel else None,
            "action": "surah_selection_started",
            "selected_surah": self.values[0],
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("surah", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "surah_selection_denied",
                "reason": "not_in_voice_channel",
                "selected_surah": self.values[0]
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        surah_num = self.values[0]
        
        # Create surah selection embed
        surah_embed = await create_standard_embed(
            interaction,
            "✅ Surah Selection",
            f"Jumping to Surah {surah_num}...\n\nPlease wait while the bot switches to the selected surah.",
            discord.Color.green()
        )
        
        # Respond immediately to prevent timeout
        await interaction.response.send_message(embed=surah_embed, ephemeral=True)
        
        # Get current state before change
        old_index = self.bot.state_manager.get_current_song_index()
        old_song = self.bot.state_manager.get_current_song_name()
        
        # Set new surah index
        self.bot.state_manager.set_current_song_index_by_surah(surah_num, self.bot.get_audio_files())
        new_index = self.bot.state_manager.get_current_song_index()
        
        # Do the heavy work in the background
        async def restart_playback():
            try:
                # Stop current playback and restart
                self.bot.is_streaming = False
                await asyncio.sleep(2)  # Wait for current playback to stop
                
                # Get the voice client and restart playback
                voice_client = None
                for guild in self.bot.guilds:
                    if guild.voice_client:
                        voice_client = guild.voice_client
                        break
                
                if voice_client and voice_client.is_connected():
                    # Restart playback with new surah
                    self.bot.is_streaming = True
                    # Start a new playback task
                    asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                    
                    # Update control panel to reflect surah change
                    # Note: We would need a reference to the parent view to update the panel status
                    # For now, the status will update on next interaction
                    
                    log_operation("surah", "INFO", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "surah_selection_successful",
                        "selected_surah": surah_num,
                        "old_index": old_index,
                        "new_index": new_index,
                        "old_song": old_song,
                        "voice_client_connected": True,
                        "playback_restarted": True
                    })
                else:
                    log_operation("surah", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "surah_selection_failed",
                        "selected_surah": surah_num,
                        "reason": "voice_client_not_available",
                        "voice_client_found": voice_client is not None,
                        "voice_client_connected": voice_client.is_connected() if voice_client else False
                    })
            except Exception as e:
                log_operation("surah", "ERROR", {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.name,
                    "action": "surah_selection_background_failed",
                    "selected_surah": surah_num,
                    "error": str(e)
                }, e)
        
        # Start the background task
        asyncio.create_task(restart_playback())

class ReciterSelect(Select):
    def __init__(self, bot):
        from utils.config import Config
        reciters = bot.get_available_reciters()
        current_reciter = getattr(bot, 'current_reciter', None)
        options = [discord.SelectOption(label=r, value=r, default=(r==current_reciter)) for r in reciters]
        super().__init__(placeholder="Select Reciter...", min_values=1, max_values=1, options=options, custom_id="select_reciter")
        self.bot = bot
    @log_select_interaction
    async def callback(self, interaction: discord.Interaction):
        # Intensive logging for reciter selection
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
            
        log_operation("reciter", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "reciter_selection_started",
            "selected_reciter": self.values[0],
            "current_reciter": getattr(self.bot, 'current_reciter', 'Unknown'),
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("reciter", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "reciter_selection_denied",
                "reason": "not_in_voice_channel",
                "selected_reciter": self.values[0]
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        reciter = self.values[0]
        current_index = self.bot.state_manager.get_current_song_index()
        current_song = self.bot.state_manager.get_current_song_name()
        surah_num = None
        if current_song:
            try:
                surah_num = current_song.split('.')[0]
            except Exception:
                pass
        
        # Switch reciter
        success = self.bot.set_current_reciter(reciter)
        if not success:
            log_operation("reciter", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "reciter_switch_failed",
                "selected_reciter": reciter,
                "reason": "reciter_not_found"
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Reciter Switch Failed",
                f"Failed to switch to reciter: **{reciter}**\n\nPlease try selecting a different reciter or contact admin if the issue persists.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        # Create reciter switch embed
        reciter_embed = await create_standard_embed(
            interaction,
            "🎤 Reciter Switch",
            f"Switching to **{reciter}**...\n\nPlease wait while the bot switches reciters and resumes playback.",
            discord.Color.green()
        )
        
        # Respond immediately to prevent timeout
        await interaction.response.send_message(embed=reciter_embed, ephemeral=True)
        
        # Get new audio files for the new reciter
        files = self.bot.get_audio_files()
        jump_index = 0
        if surah_num:
            for i, f in enumerate(files):
                if os.path.basename(f).startswith(surah_num):
                    jump_index = i
                    break
        
        # Update state and restart playback
        self.bot.state_manager.set_current_song_index(jump_index)
        
        # Do the heavy work in the background
        async def restart_playback():
            try:
                # Stop current playback and restart
                self.bot.is_streaming = False
                await asyncio.sleep(2)  # Wait for current playback to stop
                
                # Get the voice client and restart playback
                voice_client = None
                for guild in self.bot.guilds:
                    if guild.voice_client:
                        voice_client = guild.voice_client
                        break
                
                if voice_client and voice_client.is_connected():
                    # Restart playback with new reciter
                    self.bot.is_streaming = True
                    # Start a new playback task
                    asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                    
                    # Update control panel to reflect reciter change
                    # Note: We would need a reference to the parent view to update the panel status
                    # For now, the status will update on next interaction
                    
                    log_operation("reciter", "INFO", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "reciter_switch_successful",
                        "selected_reciter": reciter,
                        "surah_num": surah_num,
                        "old_index": current_index,
                        "new_index": jump_index,
                        "old_song": current_song,
                        "voice_client_connected": True,
                        "playback_restarted": True
                    })
                else:
                    log_operation("reciter", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "reciter_switch_failed",
                        "selected_reciter": reciter,
                        "reason": "voice_client_not_available",
                        "voice_client_found": voice_client is not None,
                        "voice_client_connected": voice_client.is_connected() if voice_client else False
                    })
            except Exception as e:
                log_operation("reciter", "ERROR", {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.name,
                    "action": "reciter_switch_background_failed",
                    "selected_reciter": reciter,
                    "error": str(e)
                }, e)
        
        # Start the background task
        asyncio.create_task(restart_playback())
        log_operation("reciter", "INFO", {"user_id": interaction.user.id, "reciter": reciter, "surah_num": surah_num, "action": "select_reciter"})

class ControlPanelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.surah_select = SurahSelect(bot)
        self.reciter_select = ReciterSelect(bot)
        self.current_page = 0
        self.max_pages = (114 + 24) // 25  # Total pages for surahs
        self.panel_message = None  # Store reference to panel message for updates
        self.add_item(self.surah_select)
        self.add_item(self.reciter_select)

    def set_panel_message(self, message):
        """Set the panel message reference for updates."""
        self.panel_message = message
        # Register with panel manager for event-driven updates
        panel_manager.register_panel(self)

    def update_surah_select(self):
        """Update the surah select dropdown with current page"""
        # Remove old surah select
        for item in self.children[:]:
            if isinstance(item, SurahSelect):
                self.remove_item(item)
                break
        
        # Create new surah select for current page
        self.surah_select = SurahSelect(self.bot, self.current_page)
        
        # Find the position of the reciter select to insert surah select before it
        reciter_index = None
        for i, item in enumerate(self.children):
            if isinstance(item, ReciterSelect):
                reciter_index = i
                break
        
        # Insert surah select at the beginning (before reciter)
        if reciter_index is not None:
            self.children.insert(0, self.surah_select)
        else:
            self.add_item(self.surah_select)

    async def update_panel_status(self):
        """Update the control panel with current bot status."""
        if not self.panel_message:
            return
        
        try:
            # Get current bot status for display
            current_reciter = self.bot.get_current_reciter() if hasattr(self.bot, 'get_current_reciter') else "Unknown"
            current_song = self.bot.state_manager.get_current_song_name() if hasattr(self.bot, 'state_manager') else None
            loop_enabled = getattr(self.bot, 'loop_enabled', False)
            shuffle_enabled = getattr(self.bot, 'shuffle_enabled', False)
            is_streaming = getattr(self.bot, 'is_streaming', False)
            
            # Get current surah info
            if current_song:
                try:
                    from utils.surah_mapper import get_surah_from_filename, get_surah_display_name, get_surah_emoji
                    surah_info = get_surah_from_filename(current_song)
                    surah_display = get_surah_display_name(surah_info['number'], include_number=False)
                    surah_emoji = get_surah_emoji(surah_info['number'])
                    current_surah_display = f"{surah_emoji} {surah_display}"
                except:
                    current_surah_display = current_song.replace('.mp3', '')
            else:
                current_surah_display = "Not Playing"
            
            # Create status indicators with user tracking
            if loop_enabled:
                loop_user_id, loop_username = self.bot.state_manager.get_loop_enabled_by()
                if loop_user_id and loop_username:
                    loop_status = f"🔁 ON - <@{loop_user_id}>"
                else:
                    loop_status = "🔁 ON"
            else:
                loop_status = "🔁 OFF"
            shuffle_status = "🔀 ON" if shuffle_enabled else "🔀 OFF"
            streaming_status = "▶️ Playing" if is_streaming else "⏸️ Stopped"
            
            # Create updated embed
            embed = discord.Embed(
                title="🎵 QuranBot Control Panel",
                description=f"**📊 Current Status**\n• **Now Playing**: {current_surah_display}\n• **Reciter**: {current_reciter}\n• **Status**: {streaming_status}\n• **Loop**: {loop_status}\n• **Shuffle**: {shuffle_status}\n\n\n\n\n\n\n\n**⚠️ Beta Testing Notice**\nThis bot is currently in beta testing. If you encounter any bugs or issues, please DM <@259725211664908288> to report them. Your feedback helps improve the bot!",
                color=discord.Color.green()
            )
            
            # Set bot profile picture as thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            # Set creator as author
            try:
                creator = await self.bot.fetch_user(259725211664908288)
                if creator and creator.avatar:
                    embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
            except Exception as e:
                log_operation("error", "WARNING", {
                    "component": "update_panel_status",
                    "action": "creator_avatar_fetch_failed",
                    "error": str(e)
                })
            
            # Update the message with new embed
            await self.panel_message.edit(embed=embed, view=self)
            
            log_operation("success", "INFO", {
                "component": "update_panel_status",
                "action": "panel_updated_successfully",
                "current_surah": current_surah_display,
                "current_reciter": current_reciter,
                "loop_enabled": loop_enabled,
                "shuffle_enabled": shuffle_enabled,
                "is_streaming": is_streaming
            })
            
        except Exception as e:
            log_operation("error", "ERROR", {
                "component": "update_panel_status",
                "action": "panel_update_failed",
                "error": str(e),
                "error_type": type(e).__name__
            }, e)

    # Row 1: Surah & Reciter Selection (Main Controls)
    # Row 2: Page Navigation
    @log_button_interaction
    @discord.ui.button(label="◀️ Previous Page", style=discord.ButtonStyle.secondary, custom_id="surah_prev_page", row=2)
    async def surah_prev_page(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            
            # Create a new view with the updated page
            new_view = ControlPanelView(self.bot)
            new_view.current_page = self.current_page
            
            # Update the surah select to the new page
            for item in new_view.children[:]:
                if isinstance(item, SurahSelect):
                    new_view.remove_item(item)
                    break
            new_view.add_item(SurahSelect(self.bot, self.current_page))
            
            # Update the message with new view
            embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
            await interaction.response.edit_message(embed=embed, view=new_view)
            
            log_operation("page", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "surah_prev_page",
                "new_page": self.current_page + 1,
                "total_pages": SurahSelect(self.bot, self.current_page).total_pages
            })
        else:
            warning_embed = await create_standard_embed(
                interaction,
                "⚠️ Navigation Warning",
                "You are already on the first page of surahs.",
                discord.Color.orange()
            )
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)
    
    @log_button_interaction
    @discord.ui.button(label="Next Page ▶️", style=discord.ButtonStyle.secondary, custom_id="surah_next_page", row=2)
    async def surah_next_page(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            
            # Create a new view with the updated page
            new_view = ControlPanelView(self.bot)
            new_view.current_page = self.current_page
            
            # Update the surah select to the new page
            for item in new_view.children[:]:
                if isinstance(item, SurahSelect):
                    new_view.remove_item(item)
                    break
            new_view.add_item(SurahSelect(self.bot, self.current_page))
            
            # Update the message with new view
            embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
            await interaction.response.edit_message(embed=embed, view=new_view)
            
            log_operation("page", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "surah_next_page", 
                "new_page": self.current_page + 1,
                "total_pages": SurahSelect(self.bot, self.current_page).total_pages
            })
        else:
            warning_embed = await create_standard_embed(
                interaction,
                "⚠️ Navigation Warning",
                "You are already on the last page of surahs.",
                discord.Color.orange()
            )
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)
    
    @log_button_interaction
    @discord.ui.button(label="📋 Credits", style=discord.ButtonStyle.primary, custom_id="credits", row=2)
    async def credits_button(self, interaction: discord.Interaction, button: Button):
        # Intensive logging for credits button
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
        
        log_operation("credits", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "credits_button_clicked",
            "timestamp": datetime.now().isoformat()
        })
        
        # Create credits embed
        credits_embed = await create_standard_embed(
            interaction,
            "📋 QuranBot Credits & Information",
            f"**Thank you for using QuranBot!** 🎵\n\nThis bot provides 24/7 Quran streaming with multiple reciters and interactive controls.\n\n**Current Status:**\n• **Reciter**: {self.bot.get_current_reciter()}\n• **Version**: 2.0.0\n• **Status**: Online ✅",
            discord.Color.blue()
        )
        
        # Send as ephemeral message
        await interaction.response.send_message(embed=credits_embed, ephemeral=True)
        
        log_operation("credits", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "action": "credits_displayed",
            "current_reciter": self.bot.get_current_reciter(),
            "current_surah": self.bot.state_manager.get_current_song_name().split('.')[0] if self.bot.state_manager.get_current_song_name() else 'Unknown',
            "bot_status": "online"
        })
    
    # Row 3: Playback Controls
    @log_button_interaction
    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.danger, custom_id="previous", row=3)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        # Intensive logging for previous button
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
        
        log_operation("prev", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "previous_button_clicked",
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("prev", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "previous_button_denied",
                "reason": "not_in_voice_channel"
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        idx = self.bot.state_manager.get_current_song_index()
        if idx > 0:
            # Get current state before change
            old_index = idx
            old_song = self.bot.state_manager.get_current_song_name()
            
            # Set new index
            self.bot.state_manager.set_current_song_index(idx-1)
            new_index = idx-1
            new_song = self.bot.state_manager.get_current_song_name()
            
            # Get surah info for display
            from utils.surah_mapper import get_surah_from_filename, get_surah_display_name
            try:
                if new_song:
                    surah_info = get_surah_from_filename(new_song)
                    surah_display = get_surah_display_name(surah_info['number'])
                else:
                    surah_display = "Unknown Surah"
            except:
                surah_display = "Unknown Surah"
            
            # Create previous surah embed
            prev_embed = await create_standard_embed(
                interaction,
                "⏮️ Previous Surah",
                f"Switching to previous surah: **{surah_display}**\n\nPlease wait while the bot switches to the previous surah.",
                discord.Color.green()
            )
            
            # Respond immediately to prevent timeout
            await interaction.response.send_message(embed=prev_embed, ephemeral=True)
            
            # Do the heavy work in the background
            async def restart_playback():
                try:
                    # Stop current playback and restart
                    self.bot.is_streaming = False
                    await asyncio.sleep(2)  # Wait for current playback to stop
                    
                    # Get the voice client and restart playback
                    voice_client = None
                    for guild in self.bot.guilds:
                        if guild.voice_client:
                            voice_client = guild.voice_client
                            break
                    
                    if voice_client and voice_client.is_connected():
                        # Restart playback with new surah
                        self.bot.is_streaming = True
                        # Start a new playback task
                        asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                        
                        # Panel will update automatically via state change events
                        
                        log_operation("prev", "INFO", {
                            "user_id": interaction.user.id,
                            "user_name": interaction.user.name,
                            "action": "previous_successful",
                            "old_index": old_index,
                            "new_index": new_index,
                            "old_song": old_song,
                            "new_song": new_song,
                            "voice_client_connected": True,
                            "playback_restarted": True
                        })
                    else:
                        log_operation("prev", "ERROR", {
                            "user_id": interaction.user.id,
                            "user_name": interaction.user.name,
                            "action": "previous_failed",
                            "reason": "voice_client_not_available",
                            "voice_client_found": voice_client is not None,
                            "voice_client_connected": voice_client.is_connected() if voice_client else False
                        })
                except Exception as e:
                    log_operation("prev", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "previous_background_failed",
                        "error": str(e)
                    }, e)
            
            # Start the background task
            asyncio.create_task(restart_playback())
        else:
            warning_embed = await create_standard_embed(
                interaction,
                "⚠️ Already at First Surah",
                "You are already at the first surah. There are no previous surahs to go to.",
                discord.Color.orange()
            )
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)
    
    @log_button_interaction
    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="loop", row=3)
    async def loop_button(self, interaction: discord.Interaction, button: Button):
        # Intensive logging for loop button
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
        
        log_operation("loop", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "loop_button_clicked",
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("loop", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "loop_button_denied",
                "reason": "not_in_voice_channel"
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        # Toggle loop mode
        loop_enabled = self.bot.toggle_loop(interaction.user.id, interaction.user.name)
        
        # Update button appearance
        if loop_enabled:
            button.style = discord.ButtonStyle.success
            button.label = "🔁 Loop ON"
            loop_embed = await create_standard_embed(
                interaction,
                "🔁 Loop Mode Enabled",
                "Loop mode is now enabled. The current surah will repeat until you turn it off.",
                discord.Color.green()
            )
        else:
            button.style = discord.ButtonStyle.secondary
            button.label = "🔁 Loop"
            loop_embed = await create_standard_embed(
                interaction,
                "🔁 Loop Mode Disabled",
                "Loop mode is now disabled. Surahs will play in order.",
                discord.Color.blue()
            )
        
        log_operation("loop", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "action": "loop_toggle_successful",
            "loop_enabled": loop_enabled,
            "current_surah": self.bot.current_audio_file
        })
        
        await interaction.response.send_message(embed=loop_embed, ephemeral=True)
        
        # Update the control panel status to reflect the loop change
        await panel_manager.trigger_manual_update()
    
    @log_button_interaction
    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id="shuffle", row=3)
    async def shuffle_button(self, interaction: discord.Interaction, button: Button):
        # Intensive logging for shuffle button
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
        
        log_operation("shuffle", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "shuffle_button_clicked",
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("shuffle", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "shuffle_button_denied",
                "reason": "not_in_voice_channel"
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        # Toggle shuffle mode
        shuffle_enabled = self.bot.toggle_shuffle()
        
        # Update button appearance
        if shuffle_enabled:
            button.style = discord.ButtonStyle.success
            button.label = "🔀 Shuffle ON"
            shuffle_embed = await create_standard_embed(
                interaction,
                "🔀 Shuffle Mode Enabled",
                "Shuffle mode is now enabled. Surahs will play in random order.",
                discord.Color.green()
            )
        else:
            button.style = discord.ButtonStyle.secondary
            button.label = "🔀 Shuffle"
            shuffle_embed = await create_standard_embed(
                interaction,
                "🔀 Shuffle Mode Disabled",
                "Shuffle mode is now disabled. Surahs will play in order.",
                discord.Color.blue()
            )
        
        log_operation("shuffle", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "action": "shuffle_toggle_successful",
            "shuffle_enabled": shuffle_enabled,
            "total_surahs": len(self.bot.get_audio_files())
        })
        
        await interaction.response.send_message(embed=shuffle_embed, ephemeral=True)
        
        # Update the control panel status to reflect the shuffle change
        await panel_manager.trigger_manual_update()
    
    @log_button_interaction
    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.success, custom_id="skip", row=3)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        # Intensive logging for next button
        channel_name = getattr(interaction.channel, 'name', 'DM') if interaction.channel else None
        
        log_operation("next", "INFO", {
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "user_display_name": interaction.user.display_name,
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else None,
            "channel_id": interaction.channel.id if interaction.channel else None,
            "channel_name": channel_name,
            "action": "next_button_clicked",
            "timestamp": datetime.now().isoformat()
        })
        
        if not is_in_voice_channel(interaction):
            log_operation("next", "WARNING", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "action": "next_button_denied",
                "reason": "not_in_voice_channel"
            })
            error_embed = await create_standard_embed(
                interaction,
                "❌ Access Denied",
                "You must be in the voice channel to use this feature.",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        files = self.bot.get_audio_files()
        idx = self.bot.state_manager.get_current_song_index()
        if idx < len(files)-1:
            # Get current state before change
            old_index = idx
            old_song = self.bot.state_manager.get_current_song_name()
            
            # Set new index
            self.bot.state_manager.set_current_song_index(idx+1)
            new_index = idx+1
            new_song = self.bot.state_manager.get_current_song_name()
            
            # Get surah info for display
            from utils.surah_mapper import get_surah_from_filename, get_surah_display_name
            try:
                if new_song:
                    surah_info = get_surah_from_filename(new_song)
                    surah_display = get_surah_display_name(surah_info['number'])
                else:
                    surah_display = "Unknown Surah"
            except:
                surah_display = "Unknown Surah"
            
            # Create next surah embed
            next_embed = await create_standard_embed(
                interaction,
                "⏭️ Next Surah",
                f"Switching to next surah: **{surah_display}**\n\nPlease wait while the bot switches to the next surah.",
                discord.Color.green()
            )
            
            # Respond immediately to prevent timeout
            await interaction.response.send_message(embed=next_embed, ephemeral=True)
            
            # Do the heavy work in the background
            async def restart_playback():
                try:
                    # Stop current playback and restart
                    self.bot.is_streaming = False
                    await asyncio.sleep(2)  # Wait for current playback to stop
                    
                    # Get the voice client and restart playback
                    voice_client = None
                    for guild in self.bot.guilds:
                        if guild.voice_client:
                            voice_client = guild.voice_client
                            break
                    
                    if voice_client and voice_client.is_connected():
                        # Restart playback with new surah
                        self.bot.is_streaming = True
                        # Start a new playback task
                        asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                        
                        # Panel will update automatically via state change events
                        
                        log_operation("next", "INFO", {
                            "user_id": interaction.user.id,
                            "user_name": interaction.user.name,
                            "action": "next_successful",
                            "old_index": old_index,
                            "new_index": new_index,
                            "old_song": old_song,
                            "new_song": new_song,
                            "voice_client_connected": True,
                            "playback_restarted": True
                        })
                    else:
                        log_operation("next", "ERROR", {
                            "user_id": interaction.user.id,
                            "user_name": interaction.user.name,
                            "action": "next_failed",
                            "reason": "voice_client_not_available",
                            "voice_client_found": voice_client is not None,
                            "voice_client_connected": voice_client.is_connected() if voice_client else False
                        })
                except Exception as e:
                    log_operation("next", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "action": "next_background_failed",
                        "error": str(e)
                    }, e)
            
            # Start the background task
            asyncio.create_task(restart_playback())
        else:
            warning_embed = await create_standard_embed(
                interaction,
                "⚠️ Already at Last Surah",
                "You are already at the last surah. There are no more surahs to go to.",
                discord.Color.orange()
            )
            await interaction.response.send_message(embed=warning_embed, ephemeral=True)
    


async def setup(bot):
    """Setup the control panel and create the panel with enhanced logging."""
    try:
        log_operation("init", "INFO", {
            "component": "setup",
            "bot_name": bot.user.name if bot.user else "Unknown"
        })
        
        # Create the control panel in the specified channel
        try:
            from utils.config import Config
            panel_channel_id = Config.PANEL_CHANNEL_ID
        except ImportError as e:
            log_operation("error", "CRITICAL", {
                "component": "setup",
                "error_details": "config_import_failed",
                "error": str(e)
            })
            return
        except AttributeError as e:
            log_operation("error", "CRITICAL", {
                "component": "setup",
                "error_details": "panel_channel_id_not_found",
                "error": str(e)
            })
            return
        
        log_operation("init", "INFO", {
            "component": "setup",
            "panel_channel_id": panel_channel_id
        })
        
        async def create_panel():
            """Create the control panel in the specified text channel with enhanced logging."""
            try:
                log_operation("panel", "INFO", {
                    "component": "create_panel",
                    "panel_channel_id": panel_channel_id
                })
                
                # Find the panel channel directly
                panel_channel = None
                for guild in bot.guilds:
                    try:
                        channel = guild.get_channel(panel_channel_id)
                        if channel:
                            if isinstance(channel, discord.TextChannel):
                                panel_channel = channel
                                log_operation("channel", "INFO", {
                                    "component": "create_panel",
                                    "channel_id": channel.id,
                                    "channel_name": channel.name,
                                    "guild_id": guild.id,
                                    "guild_name": guild.name
                                })
                                break
                    except Exception as e:
                        log_operation("error", "WARNING", {
                            "component": "create_panel",
                            "error_details": "guild_channel_search_failed",
                            "guild_id": guild.id,
                            "error": str(e)
                        })
                        continue
                
                if not panel_channel:
                    log_operation("error", "ERROR", {
                        "component": "create_panel",
                        "panel_channel_id": panel_channel_id,
                        "error_details": "channel_not_found",
                        "available_guilds": [guild.name for guild in bot.guilds]
                    })
                    return
                
                # Check if a control panel already exists and delete it
                try:
                    async for message in panel_channel.history(limit=50):
                        # Check if this message has our control panel embed
                        if (message.embeds and 
                            message.embeds[0].title == "🎵 QuranBot Control Panel" and
                            message.author == bot.user):
                            
                            log_operation("check", "INFO", {
                                "component": "create_panel",
                                "action": "existing_panel_found",
                                "message_id": message.id,
                                "channel_name": panel_channel.name
                            })
                            
                            # Delete the existing panel
                            try:
                                await message.delete()
                                log_operation("delete", "INFO", {
                                    "component": "create_panel",
                                    "action": "existing_panel_deleted",
                                    "message_id": message.id,
                                    "channel_name": panel_channel.name
                                })
                            except Exception as e:
                                log_operation("delete", "WARNING", {
                                    "component": "create_panel",
                                    "action": "panel_deletion_failed",
                                    "message_id": message.id,
                                    "error": str(e)
                                })
                            
                            break  # Found and deleted the panel, break out of the loop
                except Exception as e:
                    log_operation("check", "WARNING", {
                        "component": "create_panel",
                        "action": "history_check_failed",
                        "error_details": "could_not_check_history",
                        "error": str(e)
                    })
                
                # Get current bot status for display
                try:
                    current_reciter = bot.get_current_reciter() if hasattr(bot, 'get_current_reciter') else "Unknown"
                    current_song = bot.state_manager.get_current_song_name() if hasattr(bot, 'state_manager') else None
                    loop_enabled = getattr(bot, 'loop_enabled', False)
                    shuffle_enabled = getattr(bot, 'shuffle_enabled', False)
                    is_streaming = getattr(bot, 'is_streaming', False)
                    
                    # Get current surah info
                    if current_song:
                        try:
                            from utils.surah_mapper import get_surah_from_filename, get_surah_display_name, get_surah_emoji
                            surah_info = get_surah_from_filename(current_song)
                            surah_display = get_surah_display_name(surah_info['number'], include_number=False)
                            surah_emoji = get_surah_emoji(surah_info['number'])
                            current_surah_display = f"{surah_emoji} {surah_display}"
                        except:
                            current_surah_display = current_song.replace('.mp3', '')
                    else:
                        current_surah_display = "Not Playing"
                    
                    # Create status indicators with user tracking
                    if loop_enabled:
                        loop_user_id, loop_username = bot.state_manager.get_loop_enabled_by()
                        if loop_user_id and loop_username:
                            loop_status = f"🔁 ON - <@{loop_user_id}>"
                        else:
                            loop_status = "🔁 ON"
                    else:
                        loop_status = "🔁 OFF"
                    shuffle_status = "🔀 ON" if shuffle_enabled else "🔀 OFF"
                    streaming_status = "▶️ Playing" if is_streaming else "⏸️ Stopped"
                    
                except Exception as e:
                    # Fallback values if there's an error getting status
                    current_reciter = "Unknown"
                    current_surah_display = "Unknown"
                    loop_status = "🔁 OFF"
                    shuffle_status = "🔀 OFF"
                    streaming_status = "⏸️ Stopped"
                
                # Create the control panel embed with dynamic status
                embed = discord.Embed(
                    title="🎵 QuranBot Control Panel",
                    description=f"**📊 Current Status**\n• **Now Playing**: {current_surah_display}\n• **Reciter**: {current_reciter}\n• **Status**: {streaming_status}\n• **Loop**: {loop_status}\n• **Shuffle**: {shuffle_status}\n\n\n\n\n\n\n\n**⚠️ Beta Testing Notice**\nThis bot is currently in beta testing. If you encounter any bugs or issues, please DM <@259725211664908288> to report them. Your feedback helps improve the bot!",
                    color=discord.Color.green()
                )
                
                # Set bot profile picture as thumbnail
                if bot.user and bot.user.avatar:
                    embed.set_thumbnail(url=bot.user.avatar.url)
                
                # Set creator as author
                try:
                    creator = await bot.fetch_user(259725211664908288)
                    if creator and creator.avatar:
                        embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
                except Exception as e:
                    log_operation("error", "WARNING", {
                        "component": "create_panel",
                        "action": "creator_avatar_fetch_failed",
                        "error": str(e)
                    })
                
                # No footer, no timestamp - completely clean as requested
                
                # Send the panel with buttons
                view = ControlPanelView(bot)
                message = await panel_channel.send(embed=embed, view=view)
                
                # Store the message reference in the view for updates
                view.set_panel_message(message)
                
                log_operation("success", "INFO", {
                    "component": "create_panel",
                    "action": "panel_created",
                    "channel_name": panel_channel.name,
                    "message_id": message.id
                })
                
            except Exception as e:
                print(traceback.format_exc())
                log_operation("error", "ERROR", {
                    "component": "create_panel",
                    "error_details": "panel_creation_failed",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "error_type": type(e).__name__
                }, e)
        
        # Schedule panel creation after bot is ready
        async def delayed_create_panel():
            """Create panel after a delay to ensure bot is fully connected."""
            try:
                log_operation("init", "INFO", {
                    "component": "delayed_create_panel",
                    "delay_seconds": 3
                })
                
                await asyncio.sleep(3)  # Wait 3 seconds for bot to fully connect
                await create_panel()
                
            except Exception as e:
                log_operation("error", "ERROR", {
                    "component": "delayed_create_panel",
                    "error_details": "delayed_panel_creation_failed",
                    "error": str(e),
                    "error_type": type(e).__name__
                }, e)
        
        bot.loop.create_task(delayed_create_panel())
        log_operation("success", "INFO", {
            "component": "setup",
            "action": "delayed_panel_task_created"
        })
        
    except Exception as e:
        log_operation("error", "CRITICAL", {
            "component": "setup",
            "error_details": "setup_failed",
            "error": str(e),
            "error_type": type(e).__name__
        }, e) 

async def create_standard_embed(interaction: discord.Interaction, title: str, description: str, color: discord.Color) -> discord.Embed:
    """Create a standardized embed with admin author and bot thumbnail - clean format only."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # Add creator as author and bot as thumbnail
    try:
        creator = await interaction.client.fetch_user(259725211664908288)
        if creator and creator.avatar and creator.display_name:
            embed.set_author(name=creator.display_name, icon_url=creator.avatar.url)
    except Exception as e:
        log_operation("error", "WARNING", {
            "action": "creator_avatar_fetch_failed",
            "error": str(e)
        })
    
    if interaction.client.user and interaction.client.user.avatar:
        embed.set_thumbnail(url=interaction.client.user.avatar.url)
    
    # No footer, no fields - clean format only
    return embed 