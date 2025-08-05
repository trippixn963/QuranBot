# =============================================================================
# QuranBot - Control Panel View
# =============================================================================
# Main control panel view component that orchestrates UI elements and
# manages real-time state synchronization with the audio system.
#
# Components:
# - Buttons: Playback controls, navigation, and mode toggles
# - Dropdowns: Surah and reciter selection with pagination
# - Embeds: Status displays and information formatting
# - State Management: Real-time audio state synchronization
#
# State Synchronization:
# - Audio Manager Integration: Real-time playback state monitoring
# - Position Tracking: Live progress updates and time display
# - Reciter Management: Dynamic reciter switching and validation
# - Surah Navigation: Seamless surah switching with metadata
#
# User Experience:
# - Real-time Updates: Live status and progress synchronization
# - Activity Tracking: User interaction logging and analytics
# - Error Recovery: Graceful handling of Discord API failures
# - Responsive Design: Immediate feedback and visual updates
#
# Monitoring:
# - Health Checks: Panel responsiveness and error detection
# - Performance Metrics: Update frequency and response time tracking
# - State Validation: Audio manager integration verification
# - Error Recovery: Automatic restoration of failed components
#
# Integration:
# - Audio Manager: Real-time playback state and control
# - Discord API: Message updates and interaction handling
# - Monitoring System: Health checks and maintenance
# - Error Handler: Consistent error recovery patterns
# =============================================================================

# Standard library imports
from datetime import datetime
from typing import Any

# Third-party imports
import discord
from discord import ButtonStyle

# Local imports - config
from ...config.timezone import APP_TIMEZONE

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger

# Local imports - base components
from ..base.components import BaseView

# Local imports - current module
from .buttons import (
    LoopButton,
    NextButton,
    NextPageButton,
    PreviousButton,
    PrevPageButton,
    SearchButton,
    ShuffleButton,
)
from .dropdowns import ReciterSelect, SurahSelect
from .embeds import create_status_embed


class ControlPanelView(BaseView):
    """
    Main control panel view with interactive components.

    Provides control interface for Quran playback including:
    - Real-time status display with progress tracking
    - Surah and reciter selection dropdowns with pagination
    - Playback control buttons (previous, next, shuffle, loop)
    - Search functionality for finding specific surahs
    - User activity tracking and display
    - Smart update intervals based on playback state
    """

    def __init__(self, audio_manager=None, bot=None, message=None, **kwargs):
        super().__init__(
            timeout=None, **kwargs
        )  # No timeout for persistent control panel

        self.audio_manager = audio_manager
        self.bot = bot
        self.message = message

        # State tracking
        self.last_audio_state = {}
        self.last_embed_update = datetime.now(APP_TIMEZONE)
        self.update_failures = 0
        self.max_update_failures = 5

        # Pagination state
        self.current_page = 0

        # Activity tracking
        self.last_activity_user = None
        self.last_activity_time = None
        self.last_activity_action = None

        # Toggle states - will be synced with audio manager
        self.loop_enabled = False
        self.shuffle_enabled = False

        # Component references for pagination
        self.surah_select = None
        self.reciter_select = None

        # Initialize error handler
        self.error_handler = ErrorHandler()

        # Initialize components
        self._setup_components()

        TreeLogger.info(
            "Control panel view initialized",
            {
                "timeout": self.timeout,
                "components_count": len(self.children),
                "current_page": self.current_page,
                "has_audio_manager": bool(self.audio_manager),
            },
            service="ControlPanelView",
        )

    def _setup_components(self):
        """Setup UI components to match the exact screenshot layout."""
        try:
            # Create dropdowns (matching screenshot: "Select a Surah..." and "Select a Reciter...")
            self.surah_select = SurahSelect(audio_manager=self.audio_manager)
            self.surah_select.placeholder = "Select a Surah... (1/12)"

            self.reciter_select = ReciterSelect(
                audio_manager=self.audio_manager,
                audio_folder=(
                    getattr(self.audio_manager, "audio_folder", None)
                    if self.audio_manager
                    else None
                ),
            )
            self.reciter_select.placeholder = "Select a Reciter..."

            # Create buttons matching the screenshot layout
            prev_page_btn = PrevPageButton(target_dropdown=self.surah_select)
            prev_page_btn.emoji = "◀️"
            prev_page_btn.label = "Prev Page"

            next_page_btn = NextPageButton(target_dropdown=self.surah_select)
            next_page_btn.emoji = "▶️"
            next_page_btn.label = "Next Page"

            search_btn = SearchButton(audio_manager=self.audio_manager)
            search_btn.emoji = "🔍"
            search_btn.label = "Search"
            search_btn.style = ButtonStyle.primary

            # Control buttons (bottom row)
            previous_btn = PreviousButton(audio_manager=self.audio_manager)
            previous_btn.emoji = "⏮️"
            previous_btn.label = "Previous"
            previous_btn.style = ButtonStyle.danger

            shuffle_btn = ShuffleButton(audio_manager=self.audio_manager)
            shuffle_btn.emoji = "🔀"
            shuffle_btn.label = "Shuffle"
            shuffle_btn.style = ButtonStyle.secondary

            loop_btn = LoopButton(audio_manager=self.audio_manager)
            loop_btn.emoji = "🔁"
            loop_btn.label = "Loop"
            loop_btn.style = ButtonStyle.secondary

            next_btn = NextButton(audio_manager=self.audio_manager)
            next_btn.emoji = "⏭️"
            next_btn.label = "Next"
            next_btn.style = ButtonStyle.success

            # Add components in exact order from screenshot
            # Row 0: Surah dropdown
            self.add_item(self.surah_select)

            # Row 1: Reciter dropdown
            self.add_item(self.reciter_select)

            # Row 2: Navigation and search buttons (3 buttons)
            prev_page_btn.row = 2
            next_page_btn.row = 2
            search_btn.row = 2
            self.add_item(prev_page_btn)
            self.add_item(next_page_btn)
            self.add_item(search_btn)

            # Row 3: Control buttons (4 buttons)
            previous_btn.row = 3
            shuffle_btn.row = 3
            loop_btn.row = 3
            next_btn.row = 3
            self.add_item(previous_btn)
            self.add_item(shuffle_btn)
            self.add_item(loop_btn)
            self.add_item(next_btn)

            TreeLogger.info(
                "Control panel components setup complete",
                {
                    "total_components": len(self.children),
                    "layout": "balanced_button_distribution",
                },
                service="ControlPanelView",
            )

        except Exception as e:
            TreeLogger.error(
                f"Error setting up control panel components: {e}",
                service="ControlPanelView",
            )
            raise

    async def update_display(self, force_update: bool = False):
        """
        Update the control panel display with current state.

        Args:
            force_update: If True, forces update regardless of state changes

        Raises:
            Exception: If update fails, increments failure counter
        """
        try:
            if not self.message:
                TreeLogger.warning(
                    "No message to update in control panel", service="ControlPanelView"
                )
                return

            # Get current audio state
            audio_state = await self._get_audio_state()

            TreeLogger.info(
                "Control panel update requested",
                {
                    "force_update": force_update,
                    "current_surah": audio_state.get("current_surah", {}),
                    "current_reciter": audio_state.get("current_reciter", {}),
                    "is_playing": audio_state.get("is_playing", False),
                },
                service="ControlPanelView",
            )

            # Check if update is needed (skip check if force_update is True)
            if not force_update and not self._needs_update(audio_state):
                TreeLogger.info(
                    "Control panel update skipped - no changes detected",
                    service="ControlPanelView",
                )
                return

            # Update button states based on audio state
            self._sync_button_states(audio_state)

            # Refresh dropdown options if force_update (handles pagination)
            if force_update and self.surah_select:
                TreeLogger.debug(
                    "Force update detected - refreshing dropdown options",
                    {
                        "current_page": self.surah_select.current_page,
                        "total_pages": self.surah_select.total_pages,
                    },
                    service="ControlPanelView",
                )
                # The dropdown should have already updated its options in the next_page/previous_page method
                # We just need to ensure the view is refreshed

            # Create updated embed with activity tracking
            activity_info = {
                "recent_activity": (
                    self.get_recent_activity(limit=3)
                    if hasattr(self, "get_recent_activity")
                    else []
                ),
                "activity_summary": (
                    self.get_activity_summary()
                    if hasattr(self, "get_activity_summary")
                    else {}
                ),
                "last_activity": (
                    self._get_last_activity_info() if self.last_activity_user else None
                ),
            }

            embed = create_status_embed(audio_state, activity_info)

            # Add bot profile picture as thumbnail (matching screenshot)
            if self.bot and self.bot.user:
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            # Update message - this will refresh the entire view including dropdown options
            await self.message.edit(embed=embed, view=self)

            self.last_audio_state = audio_state.copy()
            self.last_embed_update = datetime.now(APP_TIMEZONE)
            self.update_failures = 0

            TreeLogger.debug(
                "Control panel display updated",
                {
                    "audio_state": {
                        "is_playing": audio_state.get("is_playing", False),
                        "current_surah": audio_state.get("current_surah", {}).get(
                            "number"
                        ),
                        "position": audio_state.get("position", 0),
                    }
                },
                service="ControlPanelView",
            )

        except Exception as e:
            self.update_failures += 1
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "control_panel_display_update",
                    "service_name": "ControlPanelView",
                    "force_update": force_update,
                    "update_failures": self.update_failures,
                    "max_failures": self.max_update_failures,
                    "current_page": self.current_page,
                    "message_exists": self.message is not None,
                    "audio_manager_exists": self.audio_manager is not None,
                    "last_update_time": (
                        self.last_embed_update.isoformat()
                        if self.last_embed_update
                        else None
                    ),
                },
            )

            if self.update_failures >= self.max_update_failures:
                TreeLogger.warning(
                    "Control panel update failures exceeded limit",
                    {"failures": self.update_failures, "stopping_updates": True},
                    service="ControlPanelView",
                )
                await self.stop_updates()

    async def _get_audio_state(self) -> dict[str, Any]:
        """
        Get current audio state from audio manager.

        Returns:
            Dict containing current audio playback state
        """
        if not self.audio_manager:
            TreeLogger.debug(
                "No audio manager available, returning default state",
                service="ControlPanelView",
            )
            return {
                "is_playing": False,
                "is_paused": False,
                "current_surah": {},
                "current_reciter": {},
                "position": 0,
                "duration": 0,
                "volume": 50,
                "progress": 0,
                "loop_mode": "off",
                "shuffle_mode": False,
            }

        try:
            # Get state from audio manager - these methods should exist
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
            volume = getattr(self.audio_manager, "get_volume", lambda: 50)()
            progress = getattr(self.audio_manager, "get_progress", lambda: 0)()

            TreeLogger.debug(
                "Retrieved audio state",
                {
                    "is_playing": is_playing,
                    "is_paused": is_paused,
                    "surah_number": (
                        current_surah.get("number") if current_surah else None
                    ),
                    "reciter": current_reciter.get("name") if current_reciter else None,
                    "position": f"{position:.1f}s",
                    "duration": f"{duration:.1f}s",
                    "progress": f"{progress:.1f}%",
                },
                service="ControlPanelView",
            )

            return {
                "is_playing": is_playing,
                "is_paused": is_paused,
                "current_surah": current_surah,
                "current_reciter": current_reciter,
                "position": position,
                "duration": duration,
                "volume": volume,
                "progress": progress,
                "loop_mode": getattr(
                    self.audio_manager, "get_loop_mode", lambda: "off"
                )(),
                "shuffle_mode": getattr(
                    self.audio_manager, "get_shuffle_mode", lambda: False
                )(),
            }
        except Exception as e:
            TreeLogger.error(
                f"Error getting audio state: {e}", service="ControlPanelView"
            )
            return {
                "is_playing": False,
                "is_paused": False,
                "current_surah": {},
                "current_reciter": {},
                "position": 0,
                "duration": 0,
                "volume": 50,
                "progress": 0,
                "loop_mode": "off",
                "shuffle_mode": False,
            }

    def _needs_update(self, current_state: dict[str, Any]) -> bool:
        """
        Check if display needs updating based on state changes.

        Args:
            current_state: Current audio state to compare against

        Returns:
            True if update is needed, False otherwise
        """
        # Always update if no previous state
        if not self.last_audio_state:
            TreeLogger.debug(
                "No previous state - update needed", service="ControlPanelView"
            )
            return True

        # Check for significant state changes
        significant_changes = [
            "is_playing",
            "is_paused",
            "current_surah",
            "current_reciter",
            "loop_mode",
            "shuffle_mode",
        ]

        for key in significant_changes:
            current_val = current_state.get(key)
            previous_val = self.last_audio_state.get(key)
            if current_val != previous_val:
                TreeLogger.debug(
                    f"State change detected: {key} changed from {previous_val} to {current_val}",
                    service="ControlPanelView",
                )
                return True

        # Update every 30 seconds during playback for progress
        if current_state.get("is_playing", False):
            time_since_update = datetime.now(APP_TIMEZONE) - self.last_embed_update
            if time_since_update.total_seconds() >= 30:
                TreeLogger.debug(
                    f"Periodic update triggered - {time_since_update.total_seconds():.1f}s since last update",
                    service="ControlPanelView",
                )
                return True

        # Update if position changed significantly (more than 5 seconds)
        position_diff = abs(
            current_state.get("position", 0) - self.last_audio_state.get("position", 0)
        )
        if position_diff >= 5:
            TreeLogger.debug(
                f"Position change detected - diff: {position_diff:.1f}s",
                service="ControlPanelView",
            )
            return True

        return False

    def _sync_button_states(self, audio_state: dict[str, Any]):
        """Synchronize button states with current audio state."""
        try:
            for item in self.children:
                if isinstance(item, ShuffleButton):
                    item.update_appearance(audio_state.get("shuffle_mode", False))
                elif isinstance(item, LoopButton):
                    loop_mode = audio_state.get("loop_mode", "off")
                    is_looping = loop_mode == "single"  # Convert to boolean
                    item.update_appearance(is_looping)
        except Exception as e:
            TreeLogger.error(
                f"Error syncing button states: {e}", service="ControlPanelView"
            )

    async def update_panel(self):
        """
        Execute panel update with immediate message edit.

        Simplified update method that directly edits the message with current state.
        Used by dropdowns and buttons for immediate UI updates after state changes.
        """
        try:
            # Check if message still exists
            if not self.message:
                TreeLogger.warning(
                    "No message to update in control panel", service="ControlPanelView"
                )
                return

            # Get current audio state
            audio_state = await self._get_audio_state()

            TreeLogger.info(
                "update_panel called - current audio state",
                {
                    "current_surah": audio_state.get("current_surah", {}),
                    "current_reciter": audio_state.get("current_reciter", {}),
                    "is_playing": audio_state.get("is_playing", False),
                },
                service="ControlPanelView",
            )

            # Create updated embed with activity tracking
            activity_info = {
                "recent_activity": (
                    self.get_recent_activity(limit=3)
                    if hasattr(self, "get_recent_activity")
                    else []
                ),
                "activity_summary": (
                    self.get_activity_summary()
                    if hasattr(self, "get_activity_summary")
                    else {}
                ),
                "last_activity": (
                    self._get_last_activity_info() if self.last_activity_user else None
                ),
            }

            embed = create_status_embed(audio_state, activity_info)

            # Add bot profile picture as thumbnail
            if self.bot and self.bot.user:
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)

            # Update message directly
            await self.message.edit(embed=embed, view=self)

            # Update internal state
            self.last_audio_state = audio_state.copy()
            self.last_embed_update = datetime.now(APP_TIMEZONE)
            self.update_failures = 0

        except discord.NotFound:
            # Message was deleted
            TreeLogger.warning(
                "Control panel message was deleted", service="ControlPanelView"
            )
            if (
                hasattr(self, "update_task")
                and self.update_task
                and not self.update_task.done()
            ):
                self.update_task.cancel()
        except Exception as e:
            TreeLogger.error(f"Error updating panel: {e}", service="ControlPanelView")

    def _update_last_activity(self, user: discord.User, action: str):
        """
        Track and update user interaction history for activity display.

        Maintains a record of the most recent user interaction with the control panel
        for display in the panel embed. Provides context about bot usage
        and helps users understand recent changes to playback state.

        Args:
            user: Discord user who performed the action
            action: Human-readable description of the action performed
        """
        TreeLogger.debug(
            "Updating last activity",
            {
                "user_id": user.id,
                "username": user.display_name,
                "action": action,
                "previous_action": self.last_activity_action,
                "time_since_last": (
                    self._format_time_elapsed(self.last_activity_time)
                    if self.last_activity_time
                    else "N/A"
                ),
            },
            service="ControlPanelView",
        )

        self.last_activity_user = user
        self.last_activity_time = datetime.now(APP_TIMEZONE)
        self.last_activity_action = action

    def _format_time_elapsed(self, activity_time: datetime) -> str:
        """
        Calculate and format human-readable elapsed time since last activity.

        Provides intelligent time formatting that adapts to the duration:
        - Seconds: "42s ago" (for recent activity)
        - Minutes: "15m ago" (for activity within the hour)
        - Hours and minutes: "2h 30m ago" (for activity within the day)
        - Days and hours: "3d 5h ago" (for older activity)
        """
        try:
            now = datetime.now(APP_TIMEZONE)
            elapsed = now - activity_time

            total_seconds = int(elapsed.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s ago"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes}m ago"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                if minutes > 0:
                    return f"{hours}h {minutes}m ago"
                else:
                    return f"{hours}h ago"
            else:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                if hours > 0:
                    return f"{days}d {hours}h ago"
                else:
                    return f"{days}d ago"
        except Exception:
            return "unknown"

    def _get_last_activity_info(self) -> dict[str, Any] | None:
        """
        Get formatted last activity information for embed display.

        Returns activity data in the format expected by the embed creation function,

        Returns:
            Dict containing user info, action, and formatted time elapsed
        """
        if not (
            self.last_activity_user
            and self.last_activity_time
            and self.last_activity_action
        ):
            return None

        try:
            return {
                "user": {
                    "id": self.last_activity_user.id,
                    "display_name": self.last_activity_user.display_name,
                },
                "action": self.last_activity_action,
                "time_elapsed": self._format_time_elapsed(self.last_activity_time),
            }
        except Exception as e:
            TreeLogger.error(
                "Error formatting last activity info",
                {
                    "operation": "format_last_activity_info",
                    "error": str(e),
                    "has_user": bool(self.last_activity_user),
                    "has_time": bool(self.last_activity_time),
                    "has_action": bool(self.last_activity_action),
                },
                service="ControlPanelView",
            )
            return None

    async def start_monitoring(self):
        """Start the control panel monitoring and updates."""
        try:
            # Start update loop
            await self.start_updates(self.audio_manager)

            # Perform initial update
            await self.update_panel()

            TreeLogger.info(
                "Control panel monitoring started",
                {"update_interval": self.update_interval, "smart_updates": True},
                service="ControlPanelView",
            )

        except Exception as e:
            TreeLogger.error(
                f"Error starting control panel monitoring: {e}",
                service="ControlPanelView",
            )

    async def stop_monitoring(self):
        """Stop the control panel monitoring."""
        try:
            await self.stop_updates()

            TreeLogger.info(
                "Control panel monitoring stopped", service="ControlPanelView"
            )

        except Exception as e:
            TreeLogger.error(
                f"Error stopping control panel monitoring: {e}",
                service="ControlPanelView",
            )

    async def on_timeout(self):
        """Handle view timeout (should not occur as timeout is None)."""
        TreeLogger.warning(
            "Control panel view timed out unexpectedly", service="ControlPanelView"
        )
        await self.stop_monitoring()
        await super().on_timeout()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        """Handle interaction errors."""
        await super().on_error(interaction, error, item)

        # Log additional context for control panel errors
        TreeLogger.error(
            f"Control panel interaction error: {error}",
            {
                "item_type": item.__class__.__name__,
                "user_id": interaction.user.id,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "update_failures": self.update_failures,
            },
            service="ControlPanelView",
        )

    def get_status_summary(self) -> dict[str, Any]:
        """Get summary of control panel status for monitoring."""
        return {
            "is_active": self.is_updating,
            "update_interval": self.update_interval,
            "last_update": self.last_embed_update,
            "update_failures": self.update_failures,
            "total_interactions": self.interaction_count,
            "active_users": len(self.user_activity),
            "component_count": len(self.children),
        }
