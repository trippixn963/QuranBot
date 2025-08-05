# =============================================================================
# QuranBot - Control Panel Manager
# =============================================================================
# Core orchestration for control panel lifecycle management.
# Handles panel creation, updates, cleanup, and multi-guild coordination.
#
# Responsibilities:
# - Panel lifecycle: creation, updates, cleanup
# - Guild coordination: multi-guild support with limits
# - State synchronization: audio manager integration
# - Error recovery: Discord API failure handling
# - Resource management: memory and performance optimization
#
# Architecture:
# - Panel registry: active panel tracking with metadata
# - Permission validation: bot capability and channel access
# - Message management: Discord message lifecycle
# - Monitoring integration: health checks and maintenance
# - Error handling: recovery patterns and logging
#
# Features:
# - Multi-guild support with configurable limits
# - Automatic inactive panel cleanup
# - Permission-aware message management
# - Real-time state synchronization
# - Comprehensive logging and monitoring
#
# Integration:
# - Audio Manager: playback state integration
# - Discord API: message and interaction management
# - Monitoring System: health checks and maintenance
# - Error Handler: consistent error recovery
# =============================================================================

# Standard library imports
import asyncio
from datetime import datetime
from typing import Any

# Third-party imports
import discord

# Local imports - config
from ...config.timezone import APP_TIMEZONE

# Local imports - core modules
from ...core.logger import TreeLogger

# Local imports - current module
from .embeds import create_status_embed
from .monitor import ControlPanelMonitor
from .view import ControlPanelView


class ControlPanelManager:
    """
    Manager for Discord control panel lifecycle and coordination.

    Handles panel creation, monitoring, updates, and cleanup.
    Provides integration with the bot's audio system and manages
    multiple control panels across different channels.
    """

    def __init__(self, bot, audio_manager=None):
        self.bot = bot
        self.audio_manager = audio_manager

        # Track active control panels
        self.active_panels: dict[int, dict[str, Any]] = {}  # channel_id -> panel_info

        # Monitoring system
        self.monitor = ControlPanelMonitor(self)

        # Configuration
        self.max_panels_per_guild = 3
        self.panel_timeout_hours = 24

        TreeLogger.info(
            "Control panel manager initialized",
            {
                "max_panels_per_guild": self.max_panels_per_guild,
                "panel_timeout_hours": self.panel_timeout_hours,
            },
            service="ControlPanelManager",
        )

    async def create_control_panel(
        self, channel: discord.TextChannel, replace_existing: bool = True
    ) -> discord.Message | None:
        """
        Create a new control panel in the specified channel.

        Performs panel creation with:
        - Permission validation for bot and channel access
        - Guild panel limit enforcement
        - Channel cleanup and message management
        - Control panel view creation and initialization
        - Panel tracking and monitoring setup
        - Error handling and recovery

        Args:
            channel: Discord channel to create panel in
            replace_existing: Whether to replace existing panel in channel

        Returns:
            Discord message containing the control panel, or None if failed
        """
        try:
            channel_id = channel.id
            guild_id = channel.guild.id

            TreeLogger.debug(
                "Starting control panel creation",
                {
                    "channel_id": channel_id,
                    "channel_name": channel.name,
                    "guild_id": guild_id,
                    "guild_name": channel.guild.name,
                    "replace_existing": replace_existing,
                    "existing_panels_count": len(self.active_panels),
                },
                service="ControlPanelManager",
            )

            # STEP 1: Permission Validation
            # Check if bot has necessary permissions to create and manage panels
            if not self._check_permissions(channel):
                TreeLogger.warning(
                    "Insufficient permissions for control panel",
                    {"channel_id": channel_id, "guild_id": guild_id},
                    service="ControlPanelManager",
                )
                return None

            # STEP 2: Guild Panel Limit Enforcement
            # Ensure we don't exceed maximum panels per guild
            guild_panels = [
                p for p in self.active_panels.values() if p["guild_id"] == guild_id
            ]
            if len(guild_panels) >= self.max_panels_per_guild and not replace_existing:
                TreeLogger.warning(
                    "Guild panel limit reached",
                    {
                        "guild_id": guild_id,
                        "active_panels": len(guild_panels),
                        "limit": self.max_panels_per_guild,
                    },
                    service="ControlPanelManager",
                )
                return None

            # STEP 3: Channel Cleanup and Preparation
            # Remove any existing messages in the channel before creating new panel
            await self._cleanup_channel_messages(channel)

            # STEP 4: Cleanup Completion Wait
            # Wait a moment for cleanup operations to complete
            await asyncio.sleep(1.0)

            # STEP 5: Existing Panel Removal
            # Remove existing panel in channel if replacement is requested
            if replace_existing and channel_id in self.active_panels:
                await self.remove_control_panel(channel_id)

            # STEP 6: Control Panel View Creation
            # Create the interactive control panel view with all components
            view = ControlPanelView(audio_manager=self.audio_manager, bot=self.bot)

            # Create initial embed
            audio_state = await self._get_initial_audio_state()
            embed = create_status_embed(audio_state)

            # Add bot profile picture as thumbnail
            if self.bot and self.bot.user:
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            # Send control panel message
            TreeLogger.debug(
                "Sending control panel message",
                {
                    "channel_id": channel_id,
                    "embed_color": embed.color,
                    "view_components": len(view.children),
                },
                service="ControlPanelManager",
            )

            message = await channel.send(embed=embed, view=view)

            TreeLogger.debug(
                "Control panel message sent",
                {"message_id": message.id, "channel_id": channel_id},
                service="ControlPanelManager",
            )

            # Update view with message reference
            view.message = message

            # Register panel
            panel_info = {
                "message": message,
                "view": view,
                "channel_id": channel_id,
                "guild_id": guild_id,
                "created_at": datetime.now(APP_TIMEZONE),
                "last_interaction": datetime.now(APP_TIMEZONE),
            }

            self.active_panels[channel_id] = panel_info

            # Start monitoring
            await view.start_monitoring()

            TreeLogger.info(
                "Control panel created successfully",
                {
                    "channel_id": channel_id,
                    "guild_id": guild_id,
                    "message_id": message.id,
                    "total_active_panels": len(self.active_panels),
                },
                service="ControlPanelManager",
            )

            return message

        except Exception as e:
            TreeLogger.error(
                f"Error creating control panel: {e}",
                {
                    "channel_id": getattr(channel, "id", None),
                    "guild_id": (
                        getattr(channel.guild, "id", None)
                        if hasattr(channel, "guild")
                        else None
                    ),
                },
                service="ControlPanelManager",
            )
            return None

    async def remove_control_panel(self, channel_id: int) -> bool:
        """
        Remove control panel from specified channel.

        Performs cleanup including:
        - Panel deregistration from active panels
        - Message deletion if accessible
        - View cleanup and monitoring stop
        - Error handling and logging

        Args:
            channel_id: ID of channel containing panel to remove

        Returns:
            True if panel was removed successfully
        """
        try:
            if channel_id not in self.active_panels:
                return False

            panel_info = self.active_panels[channel_id]

            # Stop monitoring
            if panel_info["view"]:
                await panel_info["view"].stop_monitoring()

            # Delete message if possible
            try:
                if panel_info["message"]:
                    await panel_info["message"].delete()
            except discord.NotFound:
                pass  # Message already deleted
            except discord.Forbidden:
                TreeLogger.warning(
                    "Cannot delete control panel message (no permissions)",
                    {"channel_id": channel_id, "message_id": panel_info["message"].id},
                    service="ControlPanelManager",
                )

            # Remove from tracking
            del self.active_panels[channel_id]

            TreeLogger.info(
                "Control panel removed",
                {"channel_id": channel_id, "remaining_panels": len(self.active_panels)},
                service="ControlPanelManager",
            )

            return True

        except Exception as e:
            TreeLogger.error(
                f"Error removing control panel: {e}",
                {"channel_id": channel_id},
                service="ControlPanelManager",
            )
            return False

    async def refresh_all_panels(self):
        """
        Refresh all active control panels.

        Updates all registered panels with current audio state
        and forces display updates regardless of state changes.
        """
        try:
            refresh_tasks = []

            for channel_id, panel_info in self.active_panels.items():
                if panel_info["view"]:
                    refresh_tasks.append(panel_info["view"].update_panel())

            if refresh_tasks:
                await asyncio.gather(*refresh_tasks, return_exceptions=True)

                TreeLogger.info(
                    "All control panels refreshed",
                    {"panel_count": len(refresh_tasks)},
                    service="ControlPanelManager",
                )

        except Exception as e:
            TreeLogger.error(
                f"Error refreshing control panels: {e}", service="ControlPanelManager"
            )

    async def cleanup_inactive_panels(self):
        """
        Remove inactive or stale control panels.

        Removes panels that have exceeded timeout period or
        are no longer accessible due to permission changes.
        """
        try:
            current_time = datetime.now(APP_TIMEZONE)
            panels_to_remove = []

            for channel_id, panel_info in self.active_panels.items():
                # Check if panel is too old
                age = current_time - panel_info["created_at"]
                if age.total_seconds() > (self.panel_timeout_hours * 3600):
                    panels_to_remove.append(channel_id)
                    continue

                # Check if message still exists
                try:
                    await panel_info["message"].fetch()
                except discord.NotFound:
                    panels_to_remove.append(channel_id)
                    continue
                except discord.Forbidden:
                    # Can't check, but assume it exists
                    pass

            # Remove inactive panels
            for channel_id in panels_to_remove:
                await self.remove_control_panel(channel_id)

            if panels_to_remove:
                TreeLogger.info(
                    "Inactive control panels cleaned up",
                    {
                        "removed_count": len(panels_to_remove),
                        "remaining_panels": len(self.active_panels),
                    },
                    service="ControlPanelManager",
                )

        except Exception as e:
            TreeLogger.error(
                f"Error cleaning up control panels: {e}", service="ControlPanelManager"
            )

    async def setup_control_panel(self, channel_id: int) -> bool:
        """
        Setup control panel in specified channel (convenience method).

        Args:
            channel_id: ID of channel to setup panel in

        Returns:
            True if setup was successful
        """
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                TreeLogger.error(
                    "Channel not found for control panel setup",
                    {"channel_id": channel_id},
                    service="ControlPanelManager",
                )
                return False

            message = await self.create_control_panel(channel)
            return message is not None

        except Exception as e:
            TreeLogger.error(
                f"Error setting up control panel: {e}",
                {"channel_id": channel_id},
                service="ControlPanelManager",
            )
            return False

    async def _cleanup_channel_messages(self, channel: discord.TextChannel) -> None:
        """
        Clean up existing messages in the control panel channel.

        Performs message management including:
        - Permission validation for message management
        - Message history scanning and pattern detection
        - Control panel message identification logic
        - Rate-limited message deletion
        - Error handling and permission recovery
        - Logging and statistics

        Args:
            channel: Discord channel to clean up
        """
        try:
            # STEP 1: Permission Validation for Message Management
            # Check if bot has permission to manage messages in the channel
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.manage_messages:
                TreeLogger.warning(
                    "No permission to delete messages in control panel channel",
                    {"channel_id": channel.id, "guild_id": channel.guild.id},
                    service="ControlPanelManager",
                )
                return

            # STEP 2: Cleanup Initialization and Logging
            # Log the start of cleanup operation with channel details
            TreeLogger.info(
                "Starting control panel channel cleanup",
                {
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "guild_id": channel.guild.id,
                },
                service="ControlPanelManager",
            )

            # STEP 3: Message Collection and Detection Setup
            # Initialize variables for message tracking and deletion
            deleted_count = 0
            messages_to_delete = []

            try:
                # STEP 4: Message History Scanning
                # Scan recent messages (last 50) to find control panel messages
                async for message in channel.history(limit=50):
                    # STEP 5: Control Panel Message Detection Logic
                    # Identify messages that are likely control panel messages
                    if message.author == self.bot.user:
                        # STEP 6: Multi-Criteria Message Identification
                        # Check multiple indicators to identify control panel messages
                        is_control_panel = (
                            message.embeds  # Has embeds (status displays)
                            or message.components  # Has buttons/dropdowns (interactive elements)
                            or "Surah"
                            in (message.content or "")  # Contains surah information
                            or "Reciter"
                            in (message.content or "")  # Contains reciter information
                            or "🎵"
                            in (
                                message.content or ""
                            )  # Has music emoji (playback indicator)
                            or "▰" in (message.content or "")
                            or "▱"
                            in (
                                message.content or ""
                            )  # Has progress bar (playback progress)
                        )

                        if is_control_panel:
                            # STEP 7: Control Panel Message Collection
                            # Add identified control panel messages to deletion queue
                            messages_to_delete.append(message)
                        else:
                            # STEP 8: Non-Control Panel Message Logging
                            # Log messages that are skipped to prevent confusion
                            TreeLogger.info(
                                "Skipping non-control-panel bot message",
                                {
                                    "channel_id": channel.id,
                                    "message_id": message.id,
                                    "content_preview": (
                                        message.content[:50]
                                        if message.content
                                        else "[no content]"
                                    ),
                                },
                                service="ControlPanelManager",
                            )

                # STEP 9: Deletion Queue Summary Logging
                # Log the number of messages identified for deletion
                TreeLogger.info(
                    f"Found {len(messages_to_delete)} bot messages to delete",
                    {
                        "channel_id": channel.id,
                        "messages_count": len(messages_to_delete),
                    },
                    service="ControlPanelManager",
                )

                # STEP 10: Rate-Limited Message Deletion
                # Delete messages with delays to avoid Discord rate limits
                for message in messages_to_delete:
                    try:
                        # STEP 11: Individual Message Deletion with Error Handling
                        # Delete each message with error handling
                        await message.delete()
                        deleted_count += 1

                        TreeLogger.info(
                            "Deleted old control panel message",
                            {
                                "channel_id": channel.id,
                                "message_id": message.id,
                                "message_content_preview": (
                                    message.content[:50]
                                    if message.content
                                    else "[embed]"
                                ),
                            },
                            service="ControlPanelManager",
                        )

                        # STEP 12: Rate Limiting Delay
                        # Small delay to avoid Discord API rate limits
                        await asyncio.sleep(0.5)

                    except discord.NotFound:
                        # STEP 13: Already Deleted Message Handling
                        # Handle case where message was already deleted
                        TreeLogger.info(
                            "Message already deleted",
                            {"channel_id": channel.id, "message_id": message.id},
                            service="ControlPanelManager",
                        )

                    except discord.Forbidden:
                        # STEP 14: Permission Error Handling
                        # Handle permission errors for individual messages
                        TreeLogger.warning(
                            "Cannot delete message (no permissions)",
                            {"channel_id": channel.id, "message_id": message.id},
                            service="ControlPanelManager",
                        )

                    except Exception as e:
                        # STEP 15: General Error Handling
                        # Handle any other errors during message deletion
                        TreeLogger.error(
                            f"Error deleting message: {e}",
                            {
                                "channel_id": channel.id,
                                "message_id": message.id,
                                "error_type": type(e).__name__,
                            },
                            service="ControlPanelManager",
                        )

            except discord.Forbidden:
                # STEP 16: Channel History Permission Error
                # Handle permission errors for reading channel history
                TreeLogger.warning(
                    "Cannot read channel history (no permissions)",
                    {"channel_id": channel.id},
                    service="ControlPanelManager",
                )

            if deleted_count > 0:
                TreeLogger.info(
                    f"Successfully cleaned up {deleted_count} old control panel messages",
                    {
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "deleted_count": deleted_count,
                    },
                    service="ControlPanelManager",
                )
            else:
                TreeLogger.info(
                    "No old control panel messages found to clean up",
                    {"channel_id": channel.id, "channel_name": channel.name},
                    service="ControlPanelManager",
                )

        except Exception as e:
            TreeLogger.error(
                f"Error cleaning up channel messages: {e}",
                {"channel_id": getattr(channel, "id", None)},
                service="ControlPanelManager",
            )

    def _check_permissions(self, channel: discord.TextChannel) -> bool:
        """Check if bot has required permissions in channel."""
        permissions = channel.permissions_for(channel.guild.me)

        required_permissions = [
            permissions.send_messages,
            permissions.embed_links,
            permissions.use_external_emojis,
            permissions.add_reactions,
        ]

        return all(required_permissions)

    async def _get_initial_audio_state(self) -> dict[str, Any]:
        """Get initial audio state for new control panels."""
        if not self.audio_manager:
            return {
                "is_playing": False,
                "is_paused": False,
                "current_surah": {},
                "current_reciter": {},
                "position": 0,
                "duration": 0,
                "loop_mode": "off",
                "shuffle_mode": False,
            }

        try:
            # Get state from audio manager - these are sync methods
            is_playing = getattr(self.audio_manager, "is_playing", lambda: False)()
            is_paused = getattr(self.audio_manager, "is_paused", lambda: False)()
            current_surah = getattr(
                self.audio_manager, "get_current_surah", lambda: {}
            )()
            current_reciter = getattr(
                self.audio_manager, "get_current_reciter", lambda: {}
            )()
            position = getattr(self.audio_manager, "get_position", lambda: 0)()
            duration = getattr(self.audio_manager, "get_duration", lambda: 0)()
            loop_mode = getattr(self.audio_manager, "get_loop_mode", lambda: "off")()
            shuffle_mode = getattr(
                self.audio_manager, "get_shuffle_mode", lambda: False
            )()

            return {
                "is_playing": is_playing,
                "is_paused": is_paused,
                "current_surah": current_surah,
                "current_reciter": current_reciter,
                "position": position,
                "duration": duration,
                "loop_mode": loop_mode,
                "shuffle_mode": shuffle_mode,
            }
        except Exception as e:
            TreeLogger.error(
                f"Error getting initial audio state: {e}", service="ControlPanelManager"
            )
            return {
                "is_playing": False,
                "is_paused": False,
                "current_surah": {},
                "current_reciter": {},
                "position": 0,
                "duration": 0,
                "loop_mode": "off",
                "shuffle_mode": False,
            }

    def get_panel_info(self, channel_id: int) -> dict[str, Any] | None:
        """Get information about control panel in specific channel."""
        return self.active_panels.get(channel_id)

    def get_all_panels_info(self) -> dict[int, dict[str, Any]]:
        """Get information about all active control panels."""
        return self.active_panels.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get control panel manager statistics."""
        total_panels = len(self.active_panels)
        guilds_with_panels = len(
            set(p["guild_id"] for p in self.active_panels.values())
        )

        return {
            "total_active_panels": total_panels,
            "guilds_with_panels": guilds_with_panels,
            "max_panels_per_guild": self.max_panels_per_guild,
            "panel_timeout_hours": self.panel_timeout_hours,
        }

    async def shutdown(self):
        """Shutdown control panel manager and cleanup all panels."""
        try:
            TreeLogger.info(
                "Shutting down control panel manager",
                {"active_panels": len(self.active_panels)},
                service="ControlPanelManager",
            )

            # Stop monitoring
            if self.monitor:
                await self.monitor.stop()

            # Remove all panels
            panel_ids = list(self.active_panels.keys())
            for channel_id in panel_ids:
                await self.remove_control_panel(channel_id)

            TreeLogger.info(
                "Control panel manager shutdown complete", service="ControlPanelManager"
            )

        except Exception as e:
            TreeLogger.error(
                f"Error during control panel manager shutdown: {e}",
                service="ControlPanelManager",
            )
