# =============================================================================
# QuranBot - Control Panel Utilities
# =============================================================================
# Utility functions and helper classes for control panel operations including
# permission validation, interaction handling, and error management.
# 
# Core Utilities:
# - Permission Validation: Bot capability and channel access verification
# - Interaction Handling: Safe Discord interaction management
# - Error Management: Consistent error handling and recovery
# - State Synchronization: Audio manager integration utilities
# - Performance Optimization: Smart update intervals and caching
# 
# Interaction Safety:
# - Safe Defer: Prevents interaction timeouts with proper error handling
# - Safe Response: Ensures message delivery with fallback mechanisms
# - Safe Update: Graceful message updates with error recovery
# - Error Handler Creation: Consistent error handling patterns
# 
# Integration Support:
# - Bot Setup: Integration guide and validation
# - Intent Management: Required Discord intents configuration
# - Audio Manager Validation: Service compatibility verification
# - Permission Requirements: Bot capability documentation
# 
# Performance Features:
# - Smart Update Intervals: Dynamic timing based on audio state
# - State Synchronization: Efficient audio manager integration
# - Caching Mechanisms: Reduced API calls and improved responsiveness
# - Resource Management: Memory and performance optimization
# =============================================================================

# Standard library imports
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party imports
import discord

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger


def validate_panel_permissions(channel: discord.TextChannel) -> tuple[bool, str]:
    """
    Validate bot permissions for control panel operation.
    
    Args:
        channel: Discord channel to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not channel:
        return False, "Channel not found"
    
    permissions = channel.permissions_for(channel.guild.me)
    
    required_permissions = {
        "send_messages": permissions.send_messages,
        "embed_links": permissions.embed_links,
        "use_external_emojis": permissions.use_external_emojis,
        "add_reactions": permissions.add_reactions,
        "read_message_history": permissions.read_message_history
    }
    
    missing_permissions = [
        perm_name for perm_name, has_perm in required_permissions.items() 
        if not has_perm
    ]
    
    if missing_permissions:
        return False, f"Missing permissions: {', '.join(missing_permissions)}"
    
    return True, ""


def get_smart_update_interval(audio_state: Dict[str, Any]) -> int:
    """
    Calculate smart update interval based on audio state.
    
    Args:
        audio_state: Current audio state dictionary
        
    Returns:
        Update interval in seconds
    """
    if audio_state.get("is_playing", False):
        return 5  # Faster updates when playing
    elif audio_state.get("is_paused", False):
        return 10  # Medium updates when paused
    else:
        return 15  # Slower updates when stopped


def sync_toggle_states(view, audio_manager) -> Dict[str, Any]:
    """
    Synchronize toggle button states with audio manager.
    
    Args:
        view: Control panel view
        audio_manager: Audio manager instance
        
    Returns:
        Dictionary of current states
    """
    if not audio_manager:
        return {
            "shuffle_mode": False,
            "loop_mode": "off"
        }
    
    try:
        shuffle_mode = getattr(audio_manager, 'get_shuffle_mode', lambda: False)()
        loop_mode = getattr(audio_manager, 'get_loop_mode', lambda: "off")()
        
        # Update button states in view
        for item in view.children:
            if hasattr(item, 'update_appearance'):
                if item.__class__.__name__ == 'ShuffleButton':
                    item.update_appearance(shuffle_mode)
                elif item.__class__.__name__ == 'LoopButton':
                    item.update_appearance(loop_mode)
        
        return {
            "shuffle_mode": shuffle_mode,
            "loop_mode": loop_mode
        }
        
    except Exception as e:
        TreeLogger.error(f"Error syncing toggle states: {e}", service="ControlPanel")
        return {
            "shuffle_mode": False,
            "loop_mode": "off"
        }


def format_control_panel_stats(manager) -> Dict[str, Any]:
    """
    Format control panel statistics for display.
    
    Args:
        manager: Control panel manager instance
        
    Returns:
        Formatted statistics dictionary
    """
    stats = manager.get_stats()
    
    return {
        "active_panels": stats.get("total_active_panels", 0),
        "guilds_served": stats.get("guilds_with_panels", 0),
        "uptime_info": "Available",
        "performance": "Optimal"
    }


def create_integration_guide() -> str:
    """
    Create integration guide for developers.
    
    Returns:
        Formatted integration guide string
    """
    return """
# Control Panel Integration Guide

## Basic Setup
```python
from app.ui import ControlPanelManager

# Initialize manager
panel_manager = ControlPanelManager(bot, audio_manager)

# Create control panel in channel
channel = bot.get_channel(channel_id)
message = await panel_manager.create_control_panel(channel)
```

## Features Included
- ✅ Real-time status display with progress bars
- ✅ Surah and reciter selection with pagination
- ✅ Playback controls (previous, next, shuffle, loop)
- ✅ Intelligent search with multiple formats
- ✅ User activity tracking and display
- ✅ Smart update intervals based on state
- ✅ Health monitoring and error recovery
- ✅ Logging and analytics

## Requirements
- Discord bot with proper permissions
- Audio manager with standard interface
- Voice channel connection capability
"""


class ControlPanelIntegration:
    """Helper class for integrating control panels with existing bots."""
    
    @staticmethod
    async def setup_for_bot(bot, audio_manager, config):
        """
        Setup control panel system for a bot instance.
        
        Args:
            bot: Discord bot instance
            audio_manager: Audio manager instance
            config: Bot configuration
            
        Returns:
            Initialized control panel manager
        """
        try:
            # Create manager
            manager = ControlPanelManager(bot, audio_manager)
            
            # Setup in configured channel if specified
            if hasattr(config, 'panel_channel_id') and config.panel_channel_id:
                success = await manager.setup_control_panel(config.panel_channel_id)
                if success:
                    TreeLogger.info("Control panel auto-setup successful", {
                        "channel_id": config.panel_channel_id
                    }, service="ControlPanelIntegration")
                else:
                    TreeLogger.warning("Control panel auto-setup failed", {
                        "channel_id": config.panel_channel_id
                    }, service="ControlPanelIntegration")
            
            return manager
            
        except Exception as e:
            TreeLogger.error(f"Error setting up control panel integration: {e}", 
                           service="ControlPanelIntegration")
            return None
    
    @staticmethod
    def get_required_intents() -> discord.Intents:
        """Get required Discord intents for control panels."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        return intents
    
    @staticmethod
    def validate_audio_manager(audio_manager) -> tuple[bool, list]:
        """
        Validate audio manager interface for control panel compatibility.
        
        Args:
            audio_manager: Audio manager to validate
            
        Returns:
            Tuple of (is_compatible, missing_methods)
        """
        required_methods = [
            'is_playing', 'is_paused', 'get_current_surah', 'get_current_reciter',
            'get_position', 'get_duration', 'get_loop_mode', 'get_shuffle_mode',
            'change_surah', 'change_reciter', 'previous_surah', 'next_surah',
            'toggle_shuffle', 'cycle_loop_mode'
        ]
        
        missing_methods = []
        
        for method_name in required_methods:
            if not hasattr(audio_manager, method_name):
                missing_methods.append(method_name)
        
        return len(missing_methods) == 0, missing_methods


# =============================================================================
# Interaction Response Utilities - Fix for Race Conditions
# =============================================================================

async def safe_defer(interaction: discord.Interaction, ephemeral: bool = False) -> bool:
    """
    Safely defer an interaction response with race condition protection.
    
    Args:
        interaction: Discord interaction to defer
        ephemeral: Whether response should be ephemeral
        
    Returns:
        True if defer was successful, False if response was already sent
    """
    try:
        is_done = interaction.response.is_done()
        TreeLogger.debug(f"safe_defer called - response already done: {is_done}", {
            "user": interaction.user.display_name if interaction.user else "Unknown",
            "ephemeral": ephemeral,
            "custom_id": getattr(interaction.data, 'custom_id', None) if hasattr(interaction, 'data') else None
        }, service="ControlPanelUtils")
        
        if not is_done:
            await interaction.response.defer(ephemeral=ephemeral)
            TreeLogger.debug("Interaction deferred successfully", service="ControlPanelUtils")
            return True
        return False
    except discord.errors.NotFound:
        # Interaction expired
        TreeLogger.debug("Interaction not found - likely already responded", service="ControlPanelUtils")
        return False
    except Exception as e:
        TreeLogger.warning(f"Failed to defer interaction: {e}", service="ControlPanelUtils")
        return False


async def safe_interaction_response(
    interaction: discord.Interaction,
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    view: Optional[discord.ui.View] = None,
    ephemeral: bool = False
) -> bool:
    """
    Safely send an interaction response with race condition protection.
    
    Args:
        interaction: Discord interaction
        content: Text content to send
        embed: Embed to send
        view: View to attach
        ephemeral: Whether response should be ephemeral
        
    Returns:
        True if response was sent successfully
    """
    try:
        if interaction.response.is_done():
            # Response already sent, use followup
            await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=ephemeral
            )
        else:
            # Send initial response
            await interaction.response.send_message(
                content=content,
                embed=embed,
                view=view,
                ephemeral=ephemeral
            )
        return True
    except discord.errors.NotFound:
        TreeLogger.warning("Interaction expired before response", service="ControlPanelUtils")
        return False
    except Exception as e:
        TreeLogger.error(f"Failed to send interaction response: {e}", service="ControlPanelUtils")
        return False


async def safe_update_message(
    interaction: discord.Interaction,
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    view: Optional[discord.ui.View] = None
) -> bool:
    """
    Safely update an interaction message with race condition protection.
    
    Args:
        interaction: Discord interaction
        content: New text content
        embed: New embed
        view: New view
        
    Returns:
        True if update was successful
    """
    try:
        if interaction.response.is_done():
            # Edit the original message
            await interaction.edit_original_response(
                content=content,
                embed=embed,
                view=view
            )
        else:
            # Send as response since nothing was sent yet
            await interaction.response.edit_message(
                content=content,
                embed=embed,
                view=view
            )
        return True
    except discord.errors.NotFound:
        TreeLogger.warning("Message not found for update", service="ControlPanelUtils")
        return False
    except Exception as e:
        TreeLogger.error(f"Failed to update message: {e}", service="ControlPanelUtils")
        return False


def create_consistent_error_handler(component_name: str) -> ErrorHandler:
    """
    Create a consistent error handler for control panel components.
    
    Args:
        component_name: Name of the component
        
    Returns:
        Configured ErrorHandler instance
    """
    return ErrorHandler()