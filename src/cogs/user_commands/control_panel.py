"""
Control panel for the Quran Bot.
Provides a persistent view with buttons and select menus for controlling playback.
"""

import asyncio
import discord
import os
import traceback
import time
import psutil
import gc
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any
from discord.ui import View, Select, Button, Modal, TextInput
import functools
from discord import app_commands

# Updated imports for new structure
from monitoring.logging.logger import logger
from monitoring.logging.log_helpers import log_async_function_call, log_function_call, log_operation, get_system_metrics, get_discord_context, get_bot_state
from core.state.panel_manager import panel_manager
from core.mapping.surah_mapper import get_surah_names, get_surah_emoji, get_surah_info
from core.config.config import Config, set_loop_user, set_shuffle_user

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
    """Check if the user is in the correct voice channel."""
    if not interaction.guild:
        return False
        
    # Get the bot's voice client
    voice_client = interaction.guild.voice_client
    if not voice_client:
        return False
        
    # Get the user's voice state
    if not isinstance(interaction.user, discord.Member):
        return False
        
    voice_state = interaction.user.voice
    if not voice_state:
        return False
        
    # Check if user is in the same channel as the bot
    return voice_state.channel == voice_client.channel

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
            # Log detailed user information
            user = interaction.user
            member = interaction.guild.get_member(user.id) if interaction.guild else None
            
            logger.info(f"├─ 👤 User Details: {user.name}#{user.discriminator} (ID: {user.id})", 
                       extra={'event': 'BUTTON_USER_DETAILS', 'user_id': user.id, 'username': user.name, 'discriminator': user.discriminator})
            logger.info(f"├─ 🏠 Guild: {interaction.guild.name if interaction.guild else 'DM'} (ID: {interaction.guild.id if interaction.guild else 'DM'})", 
                       extra={'event': 'BUTTON_USER_DETAILS', 'guild_id': interaction.guild.id if interaction.guild else None, 'guild_name': interaction.guild.name if interaction.guild else 'DM'})
            logger.info(f"├─ 📅 Account Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}", 
                       extra={'event': 'BUTTON_USER_DETAILS', 'account_created': user.created_at.isoformat()})
            if member:
                logger.info(f"├─ 🎭 Roles: {len(member.roles)} roles", 
                           extra={'event': 'BUTTON_USER_DETAILS', 'role_count': len(member.roles)})
                logger.info(f"├─ 📍 Joined Server: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S') if member.joined_at else 'Unknown'}", 
                           extra={'event': 'BUTTON_USER_DETAILS', 'joined_at': member.joined_at.isoformat() if member.joined_at else None})
            channel_name = interaction.channel.name if interaction.channel and hasattr(interaction.channel, 'name') else 'DM'
            channel_id = interaction.channel.id if interaction.channel and hasattr(interaction.channel, 'id') else 'DM'
            logger.info(f"└─ 💬 Channel: {channel_name} (ID: {channel_id})", 
                       extra={'event': 'BUTTON_USER_DETAILS', 'channel_id': channel_id, 'channel_name': channel_name})
            
            # Log to Discord
            await self.bot.discord_logger.log_user_button_click(interaction, button_name)
            
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
            # Log detailed user information
            user = interaction.user
            member = interaction.guild.get_member(user.id) if interaction.guild else None
            
            logger.info(f"├─ 👤 User Details: {user.name}#{user.discriminator} (ID: {user.id})", 
                       extra={'event': 'SELECT_USER_DETAILS', 'user_id': user.id, 'username': user.name, 'discriminator': user.discriminator})
            logger.info(f"├─ 🏠 Guild: {interaction.guild.name if interaction.guild else 'DM'} (ID: {interaction.guild.id if interaction.guild else 'DM'})", 
                       extra={'event': 'SELECT_USER_DETAILS', 'guild_id': interaction.guild.id if interaction.guild else None, 'guild_name': interaction.guild.name if interaction.guild else 'DM'})
            logger.info(f"├─ 📅 Account Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}", 
                       extra={'event': 'SELECT_USER_DETAILS', 'account_created': user.created_at.isoformat()})
            if member:
                logger.info(f"├─ 🎭 Roles: {len(member.roles)} roles", 
                           extra={'event': 'SELECT_USER_DETAILS', 'role_count': len(member.roles)})
                logger.info(f"├─ 📍 Joined Server: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S') if member.joined_at else 'Unknown'}", 
                           extra={'event': 'SELECT_USER_DETAILS', 'joined_at': member.joined_at.isoformat() if member.joined_at else None})
            channel_name = interaction.channel.name if interaction.channel and hasattr(interaction.channel, 'name') else 'DM'
            channel_id = interaction.channel.id if interaction.channel and hasattr(interaction.channel, 'id') else 'DM'
            logger.info(f"└─ 💬 Channel: {channel_name} (ID: {channel_id})", 
                       extra={'event': 'SELECT_USER_DETAILS', 'channel_id': channel_id, 'channel_name': channel_name})
            
            # Log to Discord
            await self.bot.discord_logger.log_user_select_interaction(interaction, select_name, selected_value)
            
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
        from core.mapping.surah_mapper import get_surah_names, get_surah_emoji
        
        super().__init__(
            placeholder="Select a Surah",
            min_values=1,
            max_values=1,
            custom_id=f"surah_select_{page}",
            row=0,
            options=[]
        )
        self.bot = bot
        self.page = page
        
        # Initialize options for the current page
        self.update_options()

    def update_options(self):
        """Update options dynamically based on current page and available surahs."""
        from core.mapping.surah_mapper import get_surah_names, get_surah_emoji
        
        # Clear existing options
        self.options.clear()
        
        try:
            # Get all surah names
            surah_names = get_surah_names()
            if not surah_names:
                raise Exception("No surah names found")
            
            # Calculate start and end indices for current page (10 surahs per page)
            surahs_per_page = 10
            start_index = self.page * surahs_per_page
            end_index = start_index + surahs_per_page
            
            # Get surahs for current page
            page_surahs = surah_names[start_index:end_index]
            
            # Create options for current page
            for i, surah_name in enumerate(page_surahs, start_index + 1):
                emoji = get_surah_emoji(i)
                # Get Arabic name if available
                arabic_name = self.get_arabic_name(i)
                display_name = f"{emoji} {surah_name}"
                if arabic_name:
                    display_name += f" ({arabic_name})"
                
                self.options.append(
                    discord.SelectOption(
                        label=display_name,
                        value=str(i),
                        description=f"Surah {i} - {surah_name}"
                    )
                )
                
        except Exception as e:
            # Fallback to hardcoded options if dynamic loading fails
            log_operation("update_options", "WARNING", {
                "error": f"Failed to load dynamic surah options: {str(e)}",
                "page": self.page
            })
            
            # Complete fallback surahs list (all 114 surahs)
            all_fallback_surahs = [
                ("🕋", "Al-Fatiha", "الفاتحة"), ("🐄", "Al-Baqarah", "البقرة"), ("👨‍👩‍👧‍👦", "Aal-Imran", "آل عمران"),
                ("👩", "An-Nisa", "النساء"), ("🍽️", "Al-Ma'idah", "المائدة"), ("🐪", "Al-An'am", "الأنعام"),
                ("🏔️", "Al-A'raf", "الأعراف"), ("💰", "Al-Anfal", "الأنفال"), ("🔄", "At-Tawbah", "التوبة"),
                ("🐄", "Yunus", "يونس"), ("🌿", "Hud", "هود"), ("👑", "Yusuf", "يوسف"), ("⚡", "Ar-Ra'd", "الرعد"),
                ("🌱", "Ibrahim", "إبراهيم"), ("🗿", "Al-Hijr", "الحجر"), ("🐝", "An-Nahl", "النحل"),
                ("🌙", "Al-Isra", "الإسراء"), ("🏛️", "Al-Kahf", "الكهف"), ("👶", "Maryam", "مريم"),
                ("📜", "Ta-Ha", "طه"), ("👨‍👩‍👧‍👦", "Al-Anbya", "الأنبياء"), ("🕋", "Al-Hajj", "الحج"),
                ("🙏", "Al-Mu'minun", "المؤمنون"), ("💡", "An-Nur", "النور"), ("📖", "Al-Furqan", "الفرقان"),
                ("📝", "Ash-Shu'ara", "الشعراء"), ("🐜", "An-Naml", "النمل"), ("📚", "Al-Qasas", "القصص"),
                ("🕷️", "Al-Ankabut", "العنكبوت"), ("🏛️", "Ar-Rum", "الروم"), ("🌳", "Luqman", "لقمان"),
                ("🙇", "As-Sajdah", "السجدة"), ("👥", "Al-Ahzab", "الأحزاب"), ("👑", "Saba", "سبأ"),
                ("🌟", "Fatir", "فاطر"), ("📜", "Ya-Sin", "يس"), ("☁️", "As-Saffat", "الصافات"),
                ("📜", "Sad", "ص"), ("🌪️", "Az-Zumar", "الزمر"), ("🛡️", "Ghafir", "غافر"),
                ("📋", "Fussilat", "فصلت"), ("🤝", "Ash-Shura", "الشورى"), ("💎", "Az-Zukhruf", "الزخرف"),
                ("💨", "Ad-Dukhan", "الدخان"), ("🦴", "Al-Jathiyah", "الجاثية"), ("🏜️", "Al-Ahqaf", "الأحقاف"),
                ("⚔️", "Muhammad", "محمد"), ("🏆", "Al-Fath", "الفتح"), ("🏠", "Al-Hujurat", "الحجرات"),
                ("📜", "Qaf", "ق"), ("💨", "Adh-Dhariyat", "الذاريات"), ("🏔️", "At-Tur", "الطور"),
                ("⭐", "An-Najm", "النجم"), ("🌙", "Al-Qamar", "القمر"), ("💝", "Ar-Rahman", "الرحمن"),
                ("⚡", "Al-Waqi'ah", "الواقعة"), ("⚔️", "Al-Hadid", "الحديد"), ("💬", "Al-Mujadila", "المجادلة"),
                ("🏃", "Al-Hashr", "الحشر"), ("🔍", "Al-Mumtahanah", "الممتحنة"), ("📋", "As-Saf", "الصف"),
                ("🕌", "Al-Jumu'ah", "الجمعة"), ("🎭", "Al-Munafiqun", "المنافقون"), ("💰", "At-Taghabun", "التغابن"),
                ("💔", "At-Talaq", "الطلاق"), ("🚫", "At-Tahrim", "التحريم"), ("👑", "Al-Mulk", "الملك"),
                ("✒️", "Al-Qalam", "القلم"), ("⚡", "Al-Haqqah", "الحاقة"), ("🪜", "Al-Ma'arij", "المعارج"),
                ("🚢", "Nuh", "نوح"), ("👻", "Al-Jinn", "الجن"), ("🧥", "Al-Muzzammil", "المزمل"),
                ("🧥", "Al-Muddathir", "المدثر"), ("⚰️", "Al-Qiyamah", "القيامة"), ("👤", "Al-Insan", "الإنسان"),
                ("💨", "Al-Mursalat", "المرسلات"), ("📢", "An-Naba", "النبأ"), ("💨", "An-Nazi'at", "النازعات"),
                ("😠", "Abasa", "عبس"), ("🌅", "At-Takwir", "التكوير"), ("🌌", "Al-Infitar", "الإنفطار"),
                ("⚖️", "Al-Mutaffifin", "المطففين"), ("🌌", "Al-Inshiqaq", "الإنشقاق"), ("⭐", "Al-Buruj", "البروج"),
                ("⭐", "At-Tariq", "الطارق"), ("⬆️", "Al-A'la", "الأعلى"), ("😱", "Al-Ghashiyah", "الغاشية"),
                ("🌅", "Al-Fajr", "الفجر"), ("🏘️", "Al-Balad", "البلد"), ("☀️", "Ash-Shams", "الشمس"),
                ("🌙", "Al-Layl", "الليل"), ("🌅", "Ad-Duha", "الضحى"), ("💪", "Ash-Sharh", "الشرح"),
                ("🌳", "At-Tin", "التين"), ("📜", "Al-Alaq", "العلق"), ("🌟", "Al-Qadr", "القدر"),
                ("📋", "Al-Bayyinah", "البينة"), ("🌋", "Az-Zalzalah", "الزلزلة"), ("🐎", "Al-Adiyat", "العاديات"),
                ("⚡", "Al-Qari'ah", "القارعة"), ("💰", "At-Takathur", "التكاثر"), ("⏰", "Al-Asr", "العصر"),
                ("🗡️", "Al-Humazah", "الهمزة"), ("🐘", "Al-Fil", "الفيل"), ("🏠", "Quraish", "قريش"),
                ("🤝", "Al-Ma'un", "الماعون"), ("🌊", "Al-Kawthar", "الكوثر"), ("❌", "Al-Kafirun", "الكافرون"),
                ("🏆", "An-Nasr", "النصر"), ("🔥", "Al-Masad", "المسد"), ("🕋", "Al-Ikhlas", "الإخلاص"),
                ("🌅", "Al-Falaq", "الفلق"), ("👥", "An-Nas", "الناس")
            ]
            
            # Calculate start and end indices for current page (10 surahs per page)
            surahs_per_page = 10
            start_index = self.page * surahs_per_page
            end_index = start_index + surahs_per_page
            
            # Get surahs for current page
            page_surahs = all_fallback_surahs[start_index:end_index]
            
            # Create options for current page
            for i, (emoji, name, arabic) in enumerate(page_surahs, start_index + 1):
                self.options.append(
                    discord.SelectOption(
                        label=f"{emoji} {name} ({arabic})",
                        value=str(i),
                        description=f"Surah {i} - {name}"
                    )
                )
    
    def get_arabic_name(self, surah_number):
        """Get Arabic name for a surah number."""
        arabic_names = {
            1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
            6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
            11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
            16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
            21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
            26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
            31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
            36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
            41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
            46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
            51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
            56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
            61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
            66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
            71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
            76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
            81: "التكوير", 82: "الإنفطار", 83: "المطففين", 84: "الإنشقاق", 85: "البروج",
            86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
            91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
            96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
            101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
            106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
            111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس"
        }
        return arabic_names.get(surah_number, "")

    @log_select_interaction
    async def callback(self, interaction: discord.Interaction):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            selected_surah = int(self.values[0])
            
            # Get the current state
            current_reciter = self.bot.current_reciter
            current_surah = self.bot.state_manager.get_current_song_index()
            
            # Log the selection
            log_operation("surah_select", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "selected_surah": selected_surah,
                "current_reciter": current_reciter,
                "current_surah": current_surah
            })

            # Update the bot's state
            self.bot.state_manager.set_current_song_index(selected_surah - 1)
            
            # Define restart_playback function
            async def restart_playback():
                try:
                    # Stop current playback
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
                        
                        # Update the panel status
                        view = self.view
                        if isinstance(view, ControlPanelView):
                            await view.update_panel_status()
                    else:
                        raise Exception("Voice client not available or not connected")
                        
                except Exception as e:
                    log_operation("restart_playback", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "selected_surah": selected_surah,
                        "error": str(e)
                    })
                    await interaction.followup.send(f"❌ Error restarting playback: {str(e)}", ephemeral=True, delete_after=300)

            # Acknowledge the interaction
            await interaction.response.defer()
            
            # Restart playback
            await restart_playback()
            
            # Get surah name for confirmation
            from core.mapping.surah_mapper import get_surah_display_name
            surah_name = get_surah_display_name(selected_surah)
            arabic_name = self.get_arabic_name(selected_surah)
            
            # Record last activity for surah change
            Config.set_last_activity(
                action=f"Switched to Surah {selected_surah}",
                user_id=interaction.user.id,
                user_name=interaction.user.name
            )

            # Send confirmation with details
            confirmation_embed = await create_response_embed(
                interaction, 
                "✅ Surah Selected", 
                f"**Now playing Surah {selected_surah}: {surah_name}**" + (f"\n*{arabic_name}*" if arabic_name else ""), 
                discord.Color.green()
            )
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            
        except ValueError:
            error_embed = await create_response_embed(
                interaction, 
                "❌ Invalid Selection", 
                "Invalid surah selection. Please try again.", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except Exception as e:
            log_operation("surah_select", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error selecting surah: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

class ReciterSelect(Select):
    def __init__(self, bot):
        super().__init__(
            placeholder="Select a Reciter",
            min_values=1,
            max_values=1,
            custom_id="reciter_select",
            row=1,
            options=[]
        )
        self.bot = bot
        
        # Initialize options dynamically
        self.update_options()

    def update_options(self):
        """Update options dynamically based on available reciters."""
        try:
            # Get available reciters from the bot
            if hasattr(self.bot, 'get_available_reciters'):
                reciter_options = self.bot.get_available_reciters()
            else:
                # Fallback to config method
                from core.config.config import Config
                reciter_options = Config.get_available_reciters()
            
            # Create select options with Arabic names as descriptions
            options = []
            for reciter in reciter_options:
                # Get the folder name for this reciter
                from core.config.config import Config
                folder_name = Config.get_folder_name_from_display(reciter)
                arabic_name = Config.get_reciter_arabic_name(folder_name)
                
                # Create description with Arabic name
                description = arabic_name if arabic_name else f"Reciter: {reciter}"
                
                options.append(
                    discord.SelectOption(
                        label=reciter,
                        value=reciter,
                        description=description
                    )
                )
            
            # Update the options
            self.options = options
            
            log_operation("update_options", "INFO", {
                "reciter_options_count": len(options),
                "options": [opt.label for opt in options[:3]]  # First 3 for logging
            })
            
        except Exception as e:
            # Fallback to hardcoded options if dynamic loading fails
            log_operation("update_options", "WARNING", {
                "error": f"Failed to load dynamic reciter options: {str(e)}"
            })
            
            # Fallback options with Arabic names
            fallback_options = [
                discord.SelectOption(label="Saad Al Ghamdi", value="Saad Al Ghamdi", description="سعد الغامدي"),
                discord.SelectOption(label="Maher Al Muaiqly", value="Maher Al Muaiqly", description="ماهر المعيقلي"),
                discord.SelectOption(label="Muhammad Al Luhaidan", value="Muhammad Al Luhaidan", description="محمد اللحيدان"),
                discord.SelectOption(label="Rashid Al Afasy", value="Rashid Al Afasy", description="مشاري راشد العفاسي"),
                discord.SelectOption(label="Abdul Basit Abdul Samad", value="Abdul Basit Abdul Samad", description="عبد الباسط عبد الصمد"),
                discord.SelectOption(label="Yasser Al Dosari", value="Yasser Al Dosari", description="ياسر الدوسري")
            ]
            
            self.options = fallback_options

    @log_select_interaction
    async def callback(self, interaction: discord.Interaction):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            selected_reciter = self.values[0]

            # Get the current state
            current_reciter = self.bot.current_reciter
            current_surah = self.bot.state_manager.get_current_song_index()

            # Log the selection
            log_operation("reciter_select", "INFO", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "selected_reciter": selected_reciter,
                "current_reciter": current_reciter,
                "current_surah": current_surah
            })

            # Update the bot's state
            success = self.bot.set_current_reciter(selected_reciter)

            if not success:
                error_embed = await create_response_embed(
                    interaction, 
                    "❌ Failed", 
                    f"Failed to switch to reciter: {selected_reciter}", 
                    discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
                return

            # Record last activity for reciter change
            Config.set_last_activity(
                action=f"Switched to {selected_reciter}",
                user_id=interaction.user.id,
                user_name=interaction.user.name
            )

            # Define restart_playback function
            async def restart_playback():
                try:
                    # Stop current playback
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
                    else:
                        raise Exception("Voice client not available or not connected")

                except Exception as e:
                    log_operation("restart_playback", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "selected_reciter": selected_reciter,
                        "error": str(e)
                    })
                    await interaction.followup.send(f"Error restarting playback: {str(e)}", ephemeral=True, delete_after=300)

            # Acknowledge the interaction
            await interaction.response.defer()

            # Restart playback
            await restart_playback()

            # Update the panel status regardless of playback status
            view = self.view
            if isinstance(view, ControlPanelView):
                await view.update_panel_status()

        except Exception as e:
            log_operation("reciter_select", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "selected_reciter": selected_reciter,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error selecting reciter: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

class ControlPanelView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.bot = bot
        # Register this panel view with the panel manager
        from core.state.panel_manager import panel_manager
        panel_manager.register_panel(self)
        self.panel_message = None
        self.current_page = 0
        # Add the select menus
        self.surah_select = SurahSelect(bot, self.current_page)
        self.reciter_select = ReciterSelect(bot)
        self.add_item(self.surah_select)
        self.add_item(self.reciter_select)
        # Start background task for periodic updates
        self._background_task = asyncio.create_task(self._periodic_update())

    async def _periodic_update(self):
        from core.state.panel_manager import panel_manager
        while True:
            await asyncio.sleep(20)
            if panel_manager.panel_view is self and self.panel_message:
                await self.update_panel_status()

    def set_panel_message(self, message):
        """Set the reference to the panel message for updates"""
        self.panel_message = message

    def update_surah_select(self):
        """Update the surah select menu with new page"""
        # Remove old surah select
        for item in self.children[:]:
            if isinstance(item, SurahSelect):
                self.remove_item(item)
        
        # Add new surah select with current page
        self.surah_select = SurahSelect(self.bot, self.current_page)
        self.add_item(self.surah_select)

    def get_detailed_status(self, surah_index, surah_name, is_playing):
        """Get detailed status information for the panel."""
        try:
            if surah_index is None or surah_name is None:
                return {
                    'status': "⏸️ **Not Playing**",
                    'surah_info': "*No surah selected*"
                }
            
            # Get surah details
            from core.mapping.surah_mapper import get_surah_display_name, get_surah_emoji
            surah_number = surah_index + 1
            surah_display = get_surah_display_name(surah_number)
            emoji = get_surah_emoji(surah_number)
            arabic_name = self.get_arabic_name(surah_number)
            
            # Format surah info
            surah_info = f"{emoji} **{surah_display}**"
            if arabic_name:
                surah_info += f"\n*{arabic_name}*"
            
            # Get status with duration if available
            if is_playing:
                # Try to get current duration
                duration_info = self.get_duration_info(surah_name)
                status = f"🎵 **Now Playing** {duration_info}"
            else:
                status = "⏸️ **Paused**"
            
            return {
                'status': status,
                'surah_info': surah_info
            }
            
        except Exception as e:
            log_operation("get_detailed_status", "ERROR", {
                "error": str(e)
            })
            return {
                'status': "❓ **Status Unknown**",
                'surah_info': "*Error loading surah info*"
            }
    
    def get_duration_info(self, surah_name):
        """Get duration information for current surah."""
        try:
            if not surah_name:
                return ""
            
            # Try to get duration from bot's method
            if hasattr(self.bot, 'get_audio_duration'):
                from core.config.config import Config
                import os
                audio_path = os.path.join(Config.AUDIO_FOLDER, self.bot.current_reciter, surah_name)
                if os.path.exists(audio_path):
                    duration = self.bot.get_audio_duration(audio_path)
                    if duration:
                        minutes = int(duration // 60)
                        seconds = int(duration % 60)
                        return f"({minutes}:{seconds:02d})"
            
            return ""
            
        except Exception:
            return ""
    
    def get_arabic_name(self, surah_number):
        """Get Arabic name for a surah number."""
        arabic_names = {
            1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
            6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
            11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
            16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
            21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
            26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
            31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
            36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
            41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
            46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
            51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
            56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
            61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
            66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
            71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
            76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
            81: "التكوير", 82: "الإنفطار", 83: "المطففين", 84: "الإنشقاق", 85: "البروج",
            86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
            91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
            96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
            101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
            106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
            111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس"
        }
        return arabic_names.get(surah_number, "")

    async def update_panel_status(self):
        """Update the panel message with current status"""
        if not self.panel_message:
            return
        try:
            # Get current state
            current_reciter = self.bot.current_reciter or "*Not selected*"
            current_surah_index = self.bot.state_manager.get_current_song_index()
            current_surah_name = self.bot.state_manager.get_current_song_name()
            is_playing = self.bot.voice_client and self.bot.voice_client.is_playing() if hasattr(self.bot, 'voice_client') else False
            loop_enabled = getattr(self.bot, 'loop_enabled', False)
            shuffle_enabled = getattr(self.bot, 'shuffle_enabled', False)

            # Get surah info
            surah_display = "*Not playing*"
            surah_emoji = ""
            surah_number = None
            if current_surah_index is not None:
                from core.mapping.surah_mapper import get_surah_info, get_surah_emoji
                surah_number = current_surah_index + 1
                surah_info = get_surah_info(surah_number)
                # Use non-padded surah number
                surah_display = f"{surah_number}. {surah_info['english_name']}"
                surah_emoji = get_surah_emoji(surah_number)

            # Get timer info
            timer_line = ""
            if current_surah_name and hasattr(self.bot, 'get_audio_duration'):
                import os
                from core.config.config import Config
                audio_path = os.path.join(Config.AUDIO_FOLDER, self.bot.current_reciter, current_surah_name)
                if os.path.exists(audio_path):
                    total_duration = self.bot.get_audio_duration(audio_path)
                    # Try to get current playback time if available
                    current_time = 0
                    if hasattr(self.bot, 'get_current_playback_time'):
                        current_time = self.bot.get_current_playback_time()
                    # Clamp current_time to total_duration
                    if total_duration is not None:
                        current_time = min(current_time, total_duration)
                    minutes = int(current_time // 60)
                    seconds = int(current_time % 60)
                    total_minutes = int(total_duration // 60)
                    total_seconds = int(total_duration % 60)
                    timer_line = f"`{minutes}:{seconds:02d} / {total_minutes}:{total_seconds:02d}`"

            # Status icons
            status_icon = "▶️" if is_playing else "⏸️"
            loop_icon = "🔁" if loop_enabled else "🔁"
            shuffle_icon = "🔀" if shuffle_enabled else "🔀"
            
            # Loop status with user tracking
            if loop_enabled:
                loop_user_id = Config.get_loop_user()
                if loop_user_id:
                    loop_status = f"ON - <@{loop_user_id}>"
                else:
                    loop_status = "ON"
            else:
                loop_status = "OFF"
            
            # Shuffle status with user tracking
            if shuffle_enabled:
                shuffle_user_id = Config.get_shuffle_user()
                if shuffle_user_id:
                    shuffle_status = f"ON - <@{shuffle_user_id}>"
                else:
                    shuffle_status = "ON"
            else:
                shuffle_status = "OFF"

            # Build the Markdown-style status block with extra spacing
            status_block = f"• **Now Playing:** {surah_emoji} {surah_display}  \n"
            if timer_line:
                status_block += f"{timer_line}\n"
            status_block += (
                f"\n"
                f"• **Reciter:** 🎤 {current_reciter}  \n"
                f"\n"
                f"• **Loop:** {loop_icon} {loop_status}  \n"
                f"\n"
                f"• **Shuffle:** {shuffle_icon} {shuffle_status}  \n"
            )

            # Add Last Activity to status block (only show for 15 minutes after action)
            if Config.should_show_last_activity():
                last_activity = Config.get_last_activity()
                if last_activity:
                    last_action = last_activity.get('action', 'Unknown')
                    last_user_id = last_activity.get('user_id', None)
                    last_user_mention = f'<@{last_user_id}>' if last_user_id else 'Unknown'
                    last_time = Config.get_last_activity_discord_time()
                    
                    if last_time:
                        last_activity_line = f"\n**Last Activity:** {last_action} by {last_user_mention} at {last_time}"
                    else:
                        last_activity_line = f"\n**Last Activity:** {last_action} by {last_user_mention}"
                    
                    status_block += last_activity_line

            # Create the embed
            embed = discord.Embed(
                title="🕌 QuranBot Control Panel",
                color=discord.Color.green()
            )
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.add_field(name="\u200b", value=status_block, inline=False)
            # No footer - removed as requested

            await self.panel_message.edit(embed=embed)
        except discord.errors.HTTPException as e:
            if e.status in [500, 502, 503, 504, 429]:  # Server errors or rate limit
                log_operation("update_panel", "WARNING", {
                    "error": f"Discord server error {e.status}: {e.text}",
                    "retry_later": True
                })
            else:
                log_operation("update_panel", "ERROR", {"error": f"HTTP error {e.status}: {e.text}"})
        except (aiohttp.ClientError, aiohttp.ServerDisconnectedError, ConnectionError) as e:
            log_operation("update_panel", "WARNING", {
                "error": f"Connection error: {str(e)}",
                "retry_later": True
            })
        except Exception as e:
            log_operation("update_panel", "ERROR", {"error": str(e)})

    @log_button_interaction
    @discord.ui.button(label="◀️ Previous Page", style=discord.ButtonStyle.secondary, custom_id="surah_prev_page", row=2)
    async def surah_prev_page(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            await interaction.response.send_message("You must be in the correct voice channel to use this!", ephemeral=True, delete_after=300)
            return

        try:
            # Calculate new page
            self.current_page = max(0, self.current_page - 1)
            
            # Update the surah select menu
            self.update_surah_select()
            
            # Update the message
            await interaction.response.edit_message(view=self, delete_after=300)
            
        except Exception as e:
            log_operation("prev_page", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error changing page: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="Next Page ▶️", style=discord.ButtonStyle.secondary, custom_id="surah_next_page", row=2)
    async def surah_next_page(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            # Calculate new page
            from core.mapping.surah_mapper import get_surah_names
            surah_names = get_surah_names()
            items_per_page = 10  # Match the SurahSelect pagination
            max_pages = (len(surah_names) + items_per_page - 1) // items_per_page
            self.current_page = min(self.current_page + 1, max_pages - 1)
            
            # Update the surah select menu
            self.update_surah_select()
            
            # Update the message
            await interaction.response.edit_message(view=self, delete_after=300)
            
        except Exception as e:
            log_operation("next_page", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error changing page: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.danger, custom_id="previous", row=3)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return
        try:
            # Get current state
            current_index = self.bot.state_manager.get_current_song_index()
            
            if current_index is None or current_index <= 0:
                warning_embed = await create_response_embed(
                    interaction, 
                    "⚠️ Not Playing", 
                    "Not currently playing or at the first surah!", 
                    discord.Color.orange()
                )
                await interaction.response.send_message(embed=warning_embed, ephemeral=True, delete_after=300)
                return
            
            # Update state
            self.bot.state_manager.set_current_song_index(current_index - 1)
            
            # Record last activity for previous
            Config.set_last_activity(
                action="Went to Previous Surah",
                user_id=interaction.user.id,
                user_name=interaction.user.name
            )
            
            # Define restart_playback function
            async def restart_playback():
                try:
                    # Stop current playback
                    self.bot.is_streaming = False
                    await asyncio.sleep(2)  # Wait for current playback to stop
                    
                    # Get the voice client and restart playback
                    voice_client = None
                    for guild in self.bot.guilds:
                        if guild.voice_client:
                            voice_client = guild.voice_client
                            break
                    
                    if voice_client and voice_client.is_connected():
                        # Restart playback with previous surah
                        self.bot.is_streaming = True
                        # Start a new playback task
                        asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                        
                        # Update the panel status
                        await self.update_panel_status()
                    else:
                        raise Exception("Voice client not available or not connected")
                    
                except Exception as e:
                    log_operation("restart_playback", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "error": str(e)
                    })
                    error_embed = await create_response_embed(
                        interaction,
                        "❌ Error",
                        f"Error restarting playback: {str(e)}",
                        discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            # Acknowledge the interaction
            await interaction.response.defer()
            
            # Restart playback
            await restart_playback()
            
            # Send confirmation
            confirmation_embed = await create_response_embed(
                interaction,
                "✅ Previous Surah",
                "Playing previous surah",
                discord.Color.green()
            )
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
        except Exception as e:
            log_operation("previous", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error playing previous surah: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="loop", row=3)
    async def loop_button(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            # Toggle loop state
            self.bot.loop_enabled = not getattr(self.bot, 'loop_enabled', False)
            
            # Track user who toggled loop
            if self.bot.loop_enabled:
                set_loop_user(interaction.user.id)
                Config.set_last_activity("Enabled Loop", interaction.user.id, interaction.user.name)
            else:
                set_loop_user(None)
                Config.set_last_activity("Disabled Loop", interaction.user.id, interaction.user.name)
            
            # Update button style
            button.style = discord.ButtonStyle.success if self.bot.loop_enabled else discord.ButtonStyle.secondary
            
            # Update the message
            await interaction.response.edit_message(view=self)
            
            # Send confirmation
            status = "enabled" if self.bot.loop_enabled else "disabled"
            confirmation_embed = await create_response_embed(
                interaction,
                "✅ Loop Updated",
                f"Loop mode {status}",
                discord.Color.green()
            )
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            
            # Update panel status
            await self.update_panel_status()
            
        except Exception as e:
            log_operation("loop", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error toggling loop mode: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id="shuffle", row=3)
    async def shuffle_button(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            # Toggle shuffle state
            self.bot.shuffle_enabled = not getattr(self.bot, 'shuffle_enabled', False)
            
            # Track user who toggled shuffle
            if self.bot.shuffle_enabled:
                set_shuffle_user(interaction.user.id)
                Config.set_last_activity("Enabled Shuffle", interaction.user.id, interaction.user.name)
            else:
                set_shuffle_user(None)
                Config.set_shuffle_user(None)
                Config.set_last_activity("Disabled Shuffle", interaction.user.id, interaction.user.name)
            
            # Update button style
            button.style = discord.ButtonStyle.success if self.bot.shuffle_enabled else discord.ButtonStyle.secondary
            
            # Update the message
            await interaction.response.edit_message(view=self)
            
            # Send confirmation
            status = "enabled" if self.bot.shuffle_enabled else "disabled"
            confirmation_embed = await create_response_embed(
                interaction,
                "✅ Shuffle Updated",
                f"Shuffle mode {status}",
                discord.Color.green()
            )
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            
            # Update panel status
            await self.update_panel_status()
            
        except Exception as e:
            log_operation("shuffle", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error toggling shuffle mode: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.success, custom_id="skip", row=3)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction, 
                "🚫 Access Denied", 
                "You must be in the correct voice channel to use this!", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return

        try:
            # Get current state
            current_index = self.bot.state_manager.get_current_song_index()
            
            if current_index is None:
                warning_embed = await create_response_embed(
                    interaction, 
                    "⚠️ Not Playing", 
                    "Not currently playing!", 
                    discord.Color.orange()
                )
                await interaction.response.send_message(embed=warning_embed, ephemeral=True, delete_after=300)
                return
            
            # Update state
            self.bot.state_manager.set_current_song_index(current_index + 1)
            
            # Record last activity for skip
            Config.set_last_activity(
                action="Skipped to Next Surah",
                user_id=interaction.user.id,
                user_name=interaction.user.name
            )
            
            # Define restart_playback function
            async def restart_playback():
                try:
                    # Stop current playback
                    self.bot.is_streaming = False
                    await asyncio.sleep(2)  # Wait for current playback to stop
                    
                    # Get the voice client and restart playback
                    voice_client = None
                    for guild in self.bot.guilds:
                        if guild.voice_client:
                            voice_client = guild.voice_client
                            break
                    
                    if voice_client and voice_client.is_connected():
                        # Restart playback with next surah
                        self.bot.is_streaming = True
                        # Start a new playback task
                        asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                        
                        # Update the panel status
                        await self.update_panel_status()
                    else:
                        raise Exception("Voice client not available or not connected")
                    
                except Exception as e:
                    log_operation("restart_playback", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "error": str(e)
                    })
                    error_embed = await create_response_embed(
                        interaction,
                        "❌ Error",
                        f"Error restarting playback: {str(e)}",
                        discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            # Acknowledge the interaction
            await interaction.response.defer()
            
            # Restart playback
            await restart_playback()
            
            # Send confirmation
            confirmation_embed = await create_response_embed(
                interaction,
                "✅ Next Surah",
                "Playing next surah",
                discord.Color.green()
            )
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
        except Exception as e:
            log_operation("skip", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction, 
                "❌ Error", 
                f"Error playing next surah: {str(e)}", 
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

    @log_button_interaction
    @discord.ui.button(label="🔎 Search", style=discord.ButtonStyle.primary, custom_id="search_surah", row=2)
    async def search_button(self, interaction: discord.Interaction, button: Button):
        try:
            modal = SearchModal(self.bot)
            await interaction.response.send_modal(modal)
        except Exception as e:
            log_operation("search_button", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            error_embed = await create_response_embed(
                interaction,
                "❌ Error",
                f"Error opening search modal: {str(e)}",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)

async def setup(bot):
    """Set up the control panel cog."""
    try:
        # Force reset the panel manager to clear any old state
        panel_manager.reset()
        
        # Create the control panel view
        view = ControlPanelView(bot)
        
        # Ensure select menu options are properly set
        view.surah_select.update_options()
        view.reciter_select.update_options()
        
        # Debug logging
        log_operation("setup", "DEBUG", {
            "surah_options_count": len(view.surah_select.options),
            "reciter_options_count": len(view.reciter_select.options),
            "surah_options": [opt.label for opt in view.surah_select.options[:5]],  # First 5 options
            "reciter_options": [opt.label for opt in view.reciter_select.options]
        })
        
        # Verify options are set
        if not view.surah_select.options:
            log_operation("setup", "ERROR", {
                "error": "Surah select has no options"
            })
            return
            
        if not view.reciter_select.options:
            log_operation("setup", "ERROR", {
                "error": "Reciter select has no options"
            })
            return
        
        # Create the initial embed
        embed = discord.Embed(
            title="🕌 QuranBot Control Panel",
            color=discord.Color.green()
        )
        
        # Add bot's profile picture as thumbnail
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        
        # Create the modern single-field format with initial status
        current_reciter = bot.current_reciter or "*Not selected*"
        current_surah_index = bot.state_manager.get_current_song_index() if hasattr(bot, 'state_manager') else None
        current_surah_name = bot.state_manager.get_current_song_name() if hasattr(bot, 'state_manager') else None
        is_playing = bot.voice_client and bot.voice_client.is_playing() if hasattr(bot, 'voice_client') else False
        loop_enabled = getattr(bot, 'loop_enabled', False)
        shuffle_enabled = getattr(bot, 'shuffle_enabled', False)

        # Get surah info
        surah_display = "*Not playing*"
        surah_emoji = ""
        surah_number = None
        if current_surah_index is not None:
            from core.mapping.surah_mapper import get_surah_info, get_surah_emoji
            surah_number = current_surah_index + 1
            surah_info = get_surah_info(surah_number)
            # Use non-padded surah number
            surah_display = f"{surah_number}. {surah_info['english_name']}"
            surah_emoji = get_surah_emoji(surah_number)

        # Get timer info
        timer_line = ""
        if current_surah_name and hasattr(bot, 'get_audio_duration'):
            import os
            from core.config.config import Config
            audio_path = os.path.join(Config.AUDIO_FOLDER, bot.current_reciter, current_surah_name)
            if os.path.exists(audio_path):
                total_duration = bot.get_audio_duration(audio_path)
                # Try to get current playback time if available
                current_time = 0
                if hasattr(bot, 'get_current_playback_time'):
                    current_time = bot.get_current_playback_time()
                # Clamp current_time to total_duration
                if total_duration is not None:
                    current_time = min(current_time, total_duration)
                minutes = int(current_time // 60)
                seconds = int(current_time % 60)
                total_minutes = int(total_duration // 60)
                total_seconds = int(total_duration % 60)
                timer_line = f"`{minutes}:{seconds:02d} / {total_minutes}:{total_seconds:02d}`"

        # Status icons
        status_icon = "▶️" if is_playing else "⏸️"
        loop_icon = "🔁" if loop_enabled else "🔁"
        shuffle_icon = "🔀" if shuffle_enabled else "🔀"
        
        # Loop status with user tracking
        if loop_enabled:
            loop_user_id = Config.get_loop_user()
            if loop_user_id:
                loop_status = f"ON - <@{loop_user_id}>"
            else:
                loop_status = "ON"
        else:
            loop_status = "OFF"
        
        # Shuffle status with user tracking
        if shuffle_enabled:
            shuffle_user_id = Config.get_shuffle_user()
            if shuffle_user_id:
                shuffle_status = f"ON - <@{shuffle_user_id}>"
            else:
                shuffle_status = "ON"
        else:
            shuffle_status = "OFF"

        # Build the Markdown-style status block with extra spacing
        status_block = f"• **Now Playing:** {surah_emoji} {surah_display}  \n"
        if timer_line:
            status_block += f"{timer_line}\n"
        status_block += (
            f"\n"
            f"• **Reciter:** 🎤 {current_reciter}  \n"
            f"\n"
            f"• **Loop:** {loop_icon} {loop_status}  \n"
            f"\n"
            f"• **Shuffle:** {shuffle_icon} {shuffle_status}  \n"
        )

        # Add Last Activity to status block (only show for 15 minutes after action)
        if Config.should_show_last_activity():
            last_activity = Config.get_last_activity()
            if last_activity:
                last_action = last_activity.get('action', 'Unknown')
                last_user_id = last_activity.get('user_id', None)
                last_user_mention = f'<@{last_user_id}>' if last_user_id else 'Unknown'
                last_time = Config.get_last_activity_discord_time()
                
                if last_time:
                    last_activity_line = f"\n**Last Activity:** {last_action} by {last_user_mention} at {last_time}"
                else:
                    last_activity_line = f"\n**Last Activity:** {last_action} by {last_user_mention}"
                
                status_block += last_activity_line

        # Add the single field with the status block
        embed.add_field(name="\u200b", value=status_block, inline=False)
        # No footer - removed as requested

        # Define create_panel function
        async def create_panel():
            try:
                # Get the target channel
                from core.config.config import Config
                panel_channel_id = Config.PANEL_CHANNEL_ID
                
                # Find the channel
                channel = None
                for guild in bot.guilds:
                    channel = guild.get_channel(panel_channel_id)
                    if channel:
                        break
                
                if not channel:
                    log_operation("setup", "ERROR", {
                        "error": "Panel channel not found",
                        "panel_channel_id": panel_channel_id
                    })
                    return
                
                # Delete all messages in the channel (clear the whole chat)
                try:
                    log_operation("setup", "INFO", {
                        "action": "clearing_channel",
                        "channel_id": channel.id,
                        "channel_name": channel.name
                    })
                    
                    # Delete all messages in the channel
                    deleted_count = 0
                    async for message in channel.history(limit=None):  # No limit to delete all messages
                        try:
                            await message.delete()
                            deleted_count += 1
                        except Exception as delete_error:
                            # Skip messages we can't delete (e.g., too old)
                            continue
                    
                    log_operation("setup", "INFO", {
                        "action": "channel_cleared",
                        "deleted_count": deleted_count,
                        "channel_id": channel.id
                    })
                    
                except Exception as e:
                    log_operation("setup", "WARNING", {
                        "error": f"Failed to clear channel: {str(e)}",
                        "channel_id": channel.id
                    })
                
                # Ensure options are still set before sending
                view.surah_select.update_options()
                view.reciter_select.update_options()
                
                # Debug logging before sending
                log_operation("setup", "DEBUG", {
                    "before_send_surah_options_count": len(view.surah_select.options),
                    "before_send_reciter_options_count": len(view.reciter_select.options),
                    "surah_options": [opt.label for opt in view.surah_select.options[:3]],
                    "reciter_options": [opt.label for opt in view.reciter_select.options[:3]]
                })
                
                # Ensure we have at least one option for each select menu
                if not view.surah_select.options:
                    log_operation("setup", "WARNING", {
                        "error": "Surah select has no options, adding fallback"
                    })
                    view.surah_select.options.append(
                        discord.SelectOption(
                            label="1. Al-Fatiha",
                            value="1",
                            description="Play Al-Fatiha"
                        )
                    )
                
                if not view.reciter_select.options:
                    log_operation("setup", "WARNING", {
                        "error": "Reciter select has no options, adding fallback"
                    })
                    view.reciter_select.options.append(
                        discord.SelectOption(
                            label="Saad Al Ghamdi",
                            value="Saad Al Ghamdi",
                            description="Switch to Saad Al Ghamdi"
                        )
                    )
                
                # Send the new panel
                panel_message = await channel.send(embed=embed, view=view)
                
                # Store the message reference
                view.set_panel_message(panel_message)
                
                log_operation("setup", "INFO", {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "guild_id": channel.guild.id,
                    "guild_name": channel.guild.name,
                    "panel_message_id": panel_message.id
                })
                
            except Exception as e:
                log_operation("setup", "ERROR", {
                    "error": str(e)
                })
        
        # Create the panel with delay
        async def delayed_create_panel():
            try:
                # Wait for bot to be ready
                await bot.wait_until_ready()
                
                # Wait additional time for guilds to be available
                await asyncio.sleep(5)
                
                # Create the panel
                await create_panel()
                
            except Exception as e:
                log_operation("setup", "ERROR", {
                    "error": str(e),
                    "phase": "delayed_create"
                })
        
        # Start the delayed panel creation
        asyncio.create_task(delayed_create_panel())
        
    except Exception as e:
        log_operation("setup", "ERROR", {
            "error": str(e),
            "phase": "initial_setup"
        })

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
            pass  # No author settings as requested in cleanup
    except Exception as e:
        log_operation("error", "WARNING", {
            "action": "creator_avatar_fetch_failed",
            "error": str(e)
        })
    
    if interaction.client.user and interaction.client.user.avatar:
        embed.set_thumbnail(url=interaction.client.user.avatar.url)
    
    # No footer, no fields - clean format only
    return embed

async def create_response_embed(interaction: discord.Interaction, title: str, description: str, color: discord.Color = discord.Color.green()) -> discord.Embed:
    """Create a standardized response embed with bot thumbnail and no footer."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    # Add bot's profile picture as thumbnail
    if interaction.client.user and interaction.client.user.avatar:
        embed.set_thumbnail(url=interaction.client.user.avatar.url)
    
    # No footer - clean format
    return embed

class SearchModal(Modal, title="🔍 Search Surah"):
    """Modal for searching surahs by name or number."""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
        self.search_input = TextInput(
            label="Enter surah name or number",
            placeholder="e.g., 'Al-Fatiha', 'Fatiha', '1', or '001'",
            min_length=1,
            max_length=50,
            required=True
        )
        self.add_item(self.search_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            search_term = self.search_input.value.strip().lower()
            
            # Search for surah by number or name
            found_surah = None
            
            # Try to find by number first
            if search_term.isdigit():
                surah_number = int(search_term)
                if 1 <= surah_number <= 114:
                    found_surah = get_surah_info(surah_number)
            
            # If not found by number, search by name
            if not found_surah:
                for i in range(1, 115):
                    surah_info = get_surah_info(i)
                    english_name = surah_info['english_name'].lower()
                    arabic_name = surah_info['arabic_name'].lower()
                    translation = surah_info['translation'].lower()
                    
                    # Check if search term matches any part of the name
                    if (search_term in english_name or 
                        search_term in arabic_name or 
                        search_term in translation or
                        english_name.startswith(search_term) or
                        arabic_name.startswith(search_term)):
                        found_surah = surah_info
                        break
            
            if found_surah:
                # Get surah emoji
                emoji = get_surah_emoji(found_surah['number'])
                
                # Create success embed
                success_embed = await create_response_embed(
                    interaction,
                    f"✅ Found Surah",
                    f"**{emoji} {found_surah['english_name']} ({found_surah['arabic_name']})**\n"
                    f"*{found_surah['translation']}*\n\n"
                    f"**Surah Number:** {found_surah['number']:03d}",
                    discord.Color.green()
                )
                
                # Add action buttons
                view = SearchResultView(self.bot, found_surah['number'])
                
                await interaction.response.send_message(
                    embed=success_embed, 
                    view=view, 
                    ephemeral=True, 
                    delete_after=300
                )
                
                # Log the search
                log_operation("surah_search", "INFO", {
                    "user_id": interaction.user.id,
                    "user_name": interaction.user.name,
                    "search_term": search_term,
                    "found_surah": found_surah['english_name'],
                    "surah_number": found_surah['number']
                })
                
            else:
                # Create error embed
                error_embed = await create_response_embed(
                    interaction,
                    "❌ Surah Not Found",
                    f"No surah found matching '{self.search_input.value}'\n\n"
                    "Try searching by:\n"
                    "• Surah number (1-114)\n"
                    "• English name (e.g., 'Al-Fatiha')\n"
                    "• Arabic name\n"
                    "• Partial name (e.g., 'Fatiha')",
                    discord.Color.red()
                )
                
                await interaction.response.send_message(
                    embed=error_embed, 
                    ephemeral=True, 
                    delete_after=300
                )
                
        except Exception as e:
            log_operation("search_modal", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "error": str(e)
            })
            
            error_embed = await create_response_embed(
                interaction,
                "❌ Search Error",
                f"An error occurred while searching: {str(e)}",
                discord.Color.red()
            )
            
            await interaction.response.send_message(
                embed=error_embed, 
                ephemeral=True, 
                delete_after=300
            )

class SearchResultView(View):
    """View for search results with action buttons."""
    
    def __init__(self, bot, surah_number):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot = bot
        self.surah_number = surah_number
    
    @discord.ui.button(label="🎵 Play This Surah", style=discord.ButtonStyle.success, row=0)
    async def play_surah(self, interaction: discord.Interaction, button: Button):
        if not is_in_voice_channel(interaction):
            error_embed = await create_response_embed(
                interaction,
                "🚫 Access Denied",
                "You must be in the correct voice channel to use this!",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
            return
        
        try:
            # Update state to the selected surah (surah_number - 1 because index is 0-based)
            self.bot.state_manager.set_current_song_index(self.surah_number - 1)
            
            # Define restart_playback function
            async def restart_playback():
                try:
                    # Stop current playback
                    self.bot.is_streaming = False
                    await asyncio.sleep(2)  # Wait for current playback to stop
                    
                    # Get the voice client and restart playback
                    voice_client = None
                    for guild in self.bot.guilds:
                        if guild.voice_client:
                            voice_client = guild.voice_client
                            break
                    
                    if voice_client and voice_client.is_connected():
                        # Restart playback with selected surah
                        self.bot.is_streaming = True
                        # Start a new playback task
                        asyncio.create_task(self.bot.play_quran_files(voice_client, voice_client.channel))
                        
                        # Update the panel status
                        self.bot.state_manager.set_last_change("search_play", interaction.user.id, interaction.user.name, f"Surah {self.surah_number}")
                        
                        # Record last activity for surah change
                        from core.config.config import Config
                        Config.set_last_activity(
                            action=f"Switched to Surah {self.surah_number}",
                            user_id=interaction.user.id,
                            user_name=interaction.user.name
                        )
                        
                        # Update the panel status by triggering a manual update
                        from core.state.panel_manager import panel_manager
                        if panel_manager.panel_view:
                            await panel_manager.panel_view.update_panel_status()
                        else:
                            await panel_manager.trigger_manual_update()
                    else:
                        raise Exception("Voice client not available or not connected")
                    
                except Exception as e:
                    log_operation("search_play_restart", "ERROR", {
                        "user_id": interaction.user.id,
                        "user_name": interaction.user.name,
                        "error": str(e)
                    })
                    await interaction.followup.send(f"Error restarting playback: {str(e)}", ephemeral=True, delete_after=300)
            
            # Acknowledge the interaction
            await interaction.response.defer()
            
            # Restart playback
            await restart_playback()
            
            # Get surah info for confirmation
            surah_info = get_surah_info(self.surah_number)
            emoji = get_surah_emoji(self.surah_number)
            
            # Send confirmation
            success_embed = await create_response_embed(
                interaction,
                "✅ Playing Surah",
                f"Now playing: **{emoji} {surah_info['english_name']}**",
                discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True, delete_after=300)
            
        except Exception as e:
            log_operation("search_play", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "surah_number": self.surah_number,
                "error": str(e)
            })
            
            error_embed = await create_response_embed(
                interaction,
                "❌ Error",
                f"Error playing surah: {str(e)}",
                discord.Color.red()
            )
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
    
    @discord.ui.button(label="📋 Show Info", style=discord.ButtonStyle.secondary, row=0)
    async def show_info(self, interaction: discord.Interaction, button: Button):
        try:
            surah_info = get_surah_info(self.surah_number)
            emoji = get_surah_emoji(self.surah_number)
            
            # Create info embed
            info_embed = await create_response_embed(
                interaction,
                f"📋 {emoji} {surah_info['english_name']}",
                f"**Arabic Name:** {surah_info['arabic_name']}\n"
                f"**Translation:** {surah_info['translation']}\n"
                f"**Surah Number:** {surah_info['number']:03d}",
                discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=info_embed, ephemeral=True, delete_after=300)
            
        except Exception as e:
            log_operation("search_info", "ERROR", {
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "surah_number": self.surah_number,
                "error": str(e)
            })
            
            error_embed = await create_response_embed(
                interaction,
                "❌ Error",
                f"Error showing surah info: {str(e)}",
                discord.Color.red()
            )
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True, delete_after=300)
