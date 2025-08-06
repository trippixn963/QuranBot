"""Interaction logging mixin for QuranBot UI components.

Mixin class for UI components to automatically log user interactions
with comprehensive state tracking and performance metrics.
"""

# =============================================================================

import time
from typing import Any

from ...core.logger import TreeLogger
from ...services.bot.user_interaction_logger import InteractionStatus


class InteractionLoggingMixin:
    """
    Mixin for UI components to automatically log user interactions.

    This mixin provides methods to:
    - Start logging control panel interactions
    - Complete logging with response times and status
    - Get before/after state for comparison
    - Handle errors with proper logging
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction_start_time: float | None = None
        self._current_interaction_id: str | None = None
        self._processing_start_time: float | None = None

    async def start_interaction_logging(
        self,
        interaction,
        component_type: str,
        component_id: str,
        component_label: str,
        selected_values: list[str] | None = None,
        input_values: dict[str, str] | None = None,
    ) -> str:
        """
        Start logging a user interaction.

        Args:
            interaction: Discord interaction object
            component_type: Type of component (button, dropdown, modal)
            component_id: ID of the component
            component_label: Label/name of the component
            selected_values: Values selected in dropdown
            input_values: Values entered in modal

        Returns:
            Interaction ID for tracking
        """
        try:
            self._interaction_start_time = time.time()

            # Get current bot state
            state_before = await self._get_current_state()

            # Get user interaction logger from bot
            bot = (
                getattr(self.view, "bot", None)
                if hasattr(self, "view")
                else getattr(self, "bot", None)
            )
            if not bot:
                TreeLogger.warning(
                    "Cannot log interaction - no bot reference",
                    {"component_type": component_type, "component_id": component_id},
                    service="InteractionLogging",
                )
                return ""

            user_logger = bot.services.get("user_interaction_logger")
            if not user_logger:
                TreeLogger.warning(
                    "User interaction logger not available",
                    {"component_type": component_type, "component_id": component_id},
                    service="InteractionLogging",
                )
                return ""

            # Start logging
            self._current_interaction_id = (
                await user_logger.log_control_panel_interaction(
                    interaction=interaction,
                    component_type=component_type,
                    component_id=component_id,
                    component_label=component_label,
                    state_before=state_before,
                    selected_values=selected_values,
                    input_values=input_values,
                )
            )

            return self._current_interaction_id

        except Exception as e:
            TreeLogger.error(
                f"Error starting interaction logging: {e}",
                None,
                {"component_type": component_type, "component_id": component_id},
                service="InteractionLogging",
            )
            return ""

    async def complete_interaction_logging(
        self,
        status: InteractionStatus,
        error_message: str | None = None,
        error_type: str | None = None,
    ) -> None:
        """
        Complete logging of a user interaction.

        Args:
            status: Final status of the interaction
            error_message: Error message if failed
            error_type: Type of error if failed
        """
        try:
            if not self._current_interaction_id or not self._interaction_start_time:
                return

            current_time = time.time()

            # Calculate response time (time to respond to Discord)
            response_time_ms = (current_time - self._interaction_start_time) * 1000

            # Calculate processing time (time to actually process the request)
            processing_time_ms = 0.0
            processing_start_time = getattr(self, "_processing_start_time", None)
            if processing_start_time:
                processing_time_ms = (current_time - processing_start_time) * 1000
            else:
                processing_time_ms = (
                    response_time_ms  # If no separate processing time tracked
                )

            # Get current state after interaction
            state_after = await self._get_current_state()

            # Get user interaction logger from bot
            bot = (
                getattr(self.view, "bot", None)
                if hasattr(self, "view")
                else getattr(self, "bot", None)
            )
            if not bot:
                return

            user_logger = bot.services.get("user_interaction_logger")
            if not user_logger:
                return

            # Complete logging
            await user_logger.complete_control_panel_interaction(
                interaction_id=self._current_interaction_id,
                response_time_ms=response_time_ms,
                processing_time_ms=processing_time_ms,
                status=status,
                state_after=state_after,
                error_message=error_message,
                error_type=error_type,
            )

            # Reset tracking variables
            self._interaction_start_time = None
            self._current_interaction_id = None
            self._processing_start_time = None

        except Exception as e:
            TreeLogger.error(
                f"Error completing interaction logging: {e}",
                None,
                {"interaction_id": self._current_interaction_id},
                service="InteractionLogging",
            )

    def start_processing(self) -> None:
        """Mark the start of actual processing (after Discord response)."""
        self._processing_start_time = time.time()

    async def _get_current_state(self) -> dict[str, Any]:
        """
        Get current bot state for comparison.

        Returns:
            Dict with current bot state
        """
        try:
            # Try to get audio manager from view or self
            audio_manager = None

            if hasattr(self, "view") and hasattr(self.view, "audio_manager"):
                audio_manager = self.view.audio_manager
            elif hasattr(self, "audio_manager"):
                audio_manager = self.audio_manager

            if not audio_manager:
                return {}

            # Get current state using the same methods as control panel
            return {
                "is_playing": getattr(audio_manager, "is_playing", lambda: False)(),
                "is_paused": getattr(audio_manager, "is_paused", lambda: False)(),
                "current_surah": getattr(
                    audio_manager, "get_current_surah", lambda: {}
                )(),
                "current_reciter": getattr(
                    audio_manager, "get_current_reciter", lambda: {}
                )(),
                "position": getattr(audio_manager, "get_position", lambda: 0)(),
                "duration": getattr(audio_manager, "get_duration", lambda: 0)(),
                "loop_mode": getattr(audio_manager, "get_loop_mode", lambda: "off")(),
                "shuffle_mode": getattr(
                    audio_manager, "get_shuffle_mode", lambda: False
                )(),
            }

        except Exception as e:
            TreeLogger.error(
                f"Error getting current state: {e}",
                None,
                {"component": self.__class__.__name__},
                service="InteractionLogging",
            )
            return {}

    async def log_interaction_error(
        self, error: Exception, interaction_context: dict[str, Any]
    ) -> None:
        """
        Log an interaction error.

        Args:
            error: The exception that occurred
            interaction_context: Context about the interaction
        """
        try:
            await self.complete_interaction_logging(
                status=InteractionStatus.FAILED,
                error_message=str(error),
                error_type=type(error).__name__,
            )

        except Exception as e:
            TreeLogger.error(
                f"Error logging interaction error: {e}",
                None,
                {"original_error": str(error), "context": interaction_context},
                service="InteractionLogging",
            )

    def format_user_name(self, interaction) -> str:
        """
        Format username as 'discord_username (server_nickname)'.

        Args:
            interaction: Discord interaction object

        Returns:
            Formatted username string
        """
        try:
            user = interaction.user
            member = getattr(interaction, "member", None)

            if member and member.nick and member.nick != user.name:
                return f"{user.name} ({member.nick})"
            else:
                return user.name

        except Exception:
            return getattr(interaction.user, "name", "Unknown User")

    async def is_user_in_quran_vc(self, interaction) -> bool:
        """
        Check if the user is currently in the configured Quran voice channel.

        Args:
            interaction: Discord interaction object

        Returns:
            True if user is in Quran VC, False otherwise
        """
        try:
            # Get bot instance
            bot = (
                getattr(self.view, "bot", None)
                if hasattr(self, "view")
                else getattr(self, "bot", None)
            )
            if not bot:
                TreeLogger.warning("No bot instance found for voice channel check")
                return False

            # Get configured Quran voice channel ID
            quran_vc_id = getattr(bot.config, "voice_channel_id", None)
            if not quran_vc_id:
                TreeLogger.warning("No configured Quran VC ID found")
                return False  # No configured Quran VC

            # Get member object - try multiple methods
            member = getattr(interaction, "member", None)
            if not member:
                # Try to get member from guild and user
                try:
                    guild = interaction.guild
                    if guild:
                        member = guild.get_member(interaction.user.id)
                        if not member:
                            # Try fetching from API
                            member = await guild.fetch_member(interaction.user.id)
                except Exception as e:
                    TreeLogger.warning(f"Could not fetch member: {e}")

                if not member:
                    TreeLogger.warning("No member object found in interaction")
                    return False

            # Debug logging
            user_vc_id = None
            if member.voice and member.voice.channel:
                user_vc_id = member.voice.channel.id

            TreeLogger.info(
                "Voice channel check",
                {
                    "user_id": interaction.user.id,
                    "username": interaction.user.name,
                    "configured_vc_id": quran_vc_id,
                    "user_vc_id": user_vc_id,
                    "user_in_voice": member.voice is not None,
                    "user_in_correct_vc": (
                        user_vc_id == quran_vc_id if user_vc_id else False
                    ),
                },
            )

            # Check if member is in voice and in the right channel
            if member.voice and member.voice.channel:
                return member.voice.channel.id == quran_vc_id

            return False

        except Exception as e:
            TreeLogger.error(
                f"Error checking user voice channel: {e}",
                None,
                {"user_id": getattr(interaction.user, "id", None)},
                service="InteractionLogging",
            )
            return False
