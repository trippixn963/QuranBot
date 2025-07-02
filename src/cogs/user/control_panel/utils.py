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
from monitoring.logging.logger import logger
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation, get_system_metrics, get_discord_context, get_bot_state
from core.state.panel_manager import panel_manager

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
        
        from core.config.config import Config
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
            "user_id": interaction.user.id,
            "user_name": interaction.user.name,
            "check_type": "voice_channel",
            "error": str(e),
            "error_type": type(e).__name__
        }, e)
        return False

def log_button_interaction(func):
    """Enhanced decorator for logging button interactions with comprehensive context."""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, button: Button):
        start_time = time.time()
        
        # Get comprehensive context
        user_context = get_user_context(interaction)
        system_metrics = get_system_metrics()
        bot_state = get_bot_state(self.bot)
        
        try:
            # Pre-interaction logging
            log_operation("interaction", "INFO", {
                **user_context,
                "button_label": button.label,
                "button_custom_id": button.custom_id,
                "button_style": str(button.style),
                "function_name": func.__name__,
                "system_metrics": system_metrics,
                "bot_state": bot_state,
                "stage": "pre_execution"
            })
            
            # Execute the actual function
            result = await func(self, interaction, button)
            
            end_time = time.time()
            execution_time = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
            
            # Discord embed logging for button interaction
            try:
                if hasattr(self.bot, 'discord_logger'):
                    button_name = button.label or button.custom_id or "Unknown Button"
                    await self.bot.discord_logger.log_user_button_click(
                        interaction, 
                        button_name,
                        f"Executed in {execution_time}ms"
                    )
            except Exception as discord_log_error:
                logger.warning(f"Failed to log button interaction to Discord: {discord_log_error}")
            
            # Post-interaction logging
            log_operation("interaction", "INFO", {
                **user_context,
                "button_label": button.label,
                "button_custom_id": button.custom_id,
                "function_name": func.__name__,
                "execution_time_ms": execution_time,
                "stage": "post_execution",
                "status": "success"
            })
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = round((end_time - start_time) * 1000, 2)
            
            log_operation("interaction", "ERROR", {
                **user_context,
                "button_label": button.label,
                "button_custom_id": button.custom_id,
                "function_name": func.__name__,
                "execution_time_ms": execution_time,
                "stage": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, e)
            raise
    
    return wrapper

def log_select_interaction(func):
    """Enhanced decorator for logging select interactions with comprehensive context."""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction):
        start_time = time.time()
        
        # Get comprehensive context
        user_context = get_user_context(interaction)
        system_metrics = get_system_metrics()
        bot_state = get_bot_state(self.bot)
        
        try:
            # Pre-interaction logging
            log_operation("select", "INFO", {
                **user_context,
                "select_placeholder": self.placeholder,
                "select_custom_id": self.custom_id,
                "selected_values": interaction.data.get('values', []) if interaction.data else [],
                "function_name": func.__name__,
                "system_metrics": system_metrics,
                "bot_state": bot_state,
                "stage": "pre_execution"
            })
            
            # Execute the actual function
            result = await func(self, interaction)
            
            end_time = time.time()
            execution_time = round((end_time - start_time) * 1000, 2)
            
            # Discord embed logging for select interaction
            try:
                if hasattr(self.bot, 'discord_logger'):
                    select_name = self.placeholder or getattr(self, 'custom_id', 'Unknown Select')
                    selected_values = interaction.data.get('values', []) if interaction.data else []
                    selected_value = selected_values[0] if selected_values else "None"
                    await self.bot.discord_logger.log_user_select_interaction(
                        interaction,
                        select_name,
                        selected_value,
                        f"Executed in {execution_time}ms"
                    )
            except Exception as discord_log_error:
                logger.warning(f"Failed to log select interaction to Discord: {discord_log_error}")
            
            # Post-interaction logging
            log_operation("select", "INFO", {
                **user_context,
                "select_placeholder": self.placeholder,
                "selected_values": interaction.data.get('values', []) if interaction.data else [],
                "function_name": func.__name__,
                "execution_time_ms": execution_time,
                "stage": "post_execution",
                "status": "success"
            })
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = round((end_time - start_time) * 1000, 2)
            
            log_operation("select", "ERROR", {
                **user_context,
                "select_placeholder": self.placeholder,
                "selected_values": interaction.data.get('values', []) if interaction.data else [],
                "function_name": func.__name__,
                "execution_time_ms": execution_time,
                "stage": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }, e)
            raise
    
    return wrapper
