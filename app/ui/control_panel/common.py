# =============================================================================
# QuranBot - Control Panel Common Utilities
# =============================================================================
# Common utilities and mixins to reduce code duplication across control panel
# components. Provides standardized patterns for frequent operations.
#
# Mixins:
# - ActivityTrackerMixin: Consistent user activity tracking
# - ValidationMixin: Common permission and state validation
# - ButtonStateMixin: Visual state management for buttons
# - ComponentInitMixin: Standardized component initialization
# - InteractionHandlerMixin: Combined activity tracking and validation
#
# Utilities:
# - AudioManagerProxy: Safe audio manager operations with error handling
# - create_audio_callback: Factory for standardized audio callbacks
#
# Benefits:
# - Reduces code duplication across components
# - Ensures consistent behavior and error handling
# - Simplifies component development and maintenance
# - Provides reusable patterns for common operations
# =============================================================================

# Standard library imports
from collections.abc import Callable
from typing import Any

# Third-party imports
import discord

# Local imports - core modules
from ...core.logger import TreeLogger
from ...services.bot.user_interaction_logger import InteractionStatus

# Local imports - current module
from .embeds import create_error_embed
from .utils import safe_defer, safe_interaction_response


class ActivityTrackerMixin:
    """Mixin for consistent activity tracking across components."""

    def track_activity(self, interaction: discord.Interaction, action: str):
        """
        Track user activity if the view supports it.

        Records user interactions for display in the control panel's
        "Last Activity" section, providing context about recent changes
        and helping users understand bot state changes.

        Args:
            interaction: Discord interaction containing user information
            action: Human-readable description of the action taken
        """
        # Log activity tracking attempt with context
        TreeLogger.debug(
            f"Tracking activity: {action}",
            {
                "user": interaction.user.display_name,
                "user_id": interaction.user.id,
                "has_view": hasattr(self, "view"),
                "has_update_method": (
                    hasattr(self.view, "_update_last_activity")
                    if hasattr(self, "view")
                    else False
                ),
            },
            service="ActivityTrackerMixin",
        )

        # Update activity tracking if view supports it
        if hasattr(self, "view") and hasattr(self.view, "_update_last_activity"):
            self.view._update_last_activity(interaction.user, action)


class ValidationMixin:
    """Mixin for common validation checks."""

    async def check_voice_channel(self, interaction: discord.Interaction) -> bool:
        """
        Check if user is in the Quran voice channel.

        Validates that the user has permission to use control panel
        features by verifying they are connected to the designated
        Quran voice channel. Provides user feedback if validation fails.

        Args:
            interaction: Discord interaction to validate

        Returns:
            True if user is in voice channel, False otherwise
        """
        # Perform voice channel validation check
        if not await self.is_user_in_quran_vc(interaction):
            # Create user-friendly error message
            embed = create_error_embed(
                "You must be in the Quran voice channel to use the control panel."
            )
            await safe_interaction_response(interaction, embed=embed, ephemeral=True)

            # Log permission error if interaction logging is available
            if hasattr(self, "complete_interaction_logging"):
                await self.complete_interaction_logging(
                    status=InteractionStatus.PERMISSION_ERROR,
                    error_message="User not in Quran voice channel",
                    error_type="PermissionDenied",
                )
            return False
        return True


class AudioManagerProxy:
    """Proxy for safe audio manager operations with consistent error handling."""

    def __init__(self, audio_manager):
        self.audio_manager = audio_manager

    async def safe_call(self, method_name: str, *args, **kwargs) -> Any | None:
        """
        Safely call an audio manager method with error handling.

        Provides a safe interface for calling audio manager methods
        with comprehensive error handling and logging. Returns None
        on any failure to prevent control panel crashes.

        Args:
            method_name: Name of the method to call on audio manager
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method

        Returns:
            Result of the method call or None if failed
        """
        # Check if audio manager is available
        if not self.audio_manager:
            TreeLogger.warning(
                f"Audio manager not available for {method_name}",
                service="ControlPanelCommon",
            )
            return None

        try:
            # Get method reference with validation
            method = getattr(self.audio_manager, method_name, None)
            if method and callable(method):
                # Execute method with provided arguments
                return await method(*args, **kwargs)
            else:
                # Method not found or not callable
                TreeLogger.error(
                    f"Method {method_name} not found on audio manager",
                    service="ControlPanelCommon",
                )
                return None
        except Exception as e:
            # Log any errors during method execution
            TreeLogger.error(
                f"Error calling audio manager.{method_name}: {e}",
                service="ControlPanelCommon",
            )
            return None


class ButtonStateMixin:
    """Mixin for consistent button state management."""

    def update_button_state(
        self,
        enabled: bool,
        enabled_style: discord.ButtonStyle = discord.ButtonStyle.success,
        disabled_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        enabled_emoji: str | None = None,
        disabled_emoji: str | None = None,
    ):
        """
        Update button appearance based on state with visual feedback.

        Provides consistent visual feedback for toggle buttons by
        changing colors and optionally emojis based on the current
        state. Helps users understand the current mode at a glance.

        Args:
            enabled: Whether the feature is currently enabled
            enabled_style: Button style when feature is enabled (default: success/green)
            disabled_style: Button style when feature is disabled (default: secondary/gray)
            enabled_emoji: Emoji to show when enabled (optional)
            disabled_emoji: Emoji to show when disabled (optional)
        """
        if enabled:
            # Apply enabled styling (typically green/success)
            self.style = enabled_style
            if enabled_emoji and hasattr(self, "emoji"):
                self.emoji = enabled_emoji
        else:
            # Apply disabled styling (typically gray/secondary)
            self.style = disabled_style
            if disabled_emoji and hasattr(self, "emoji"):
                self.emoji = disabled_emoji


class ComponentInitMixin:
    """Mixin for standardized component initialization."""

    def init_control_component(
        self,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        emoji: str | None = None,
        label: str | None = None,
        custom_id: str | None = None,
        audio_manager: Any | None = None,
    ):
        """
        Initialize common control component properties.

        Args:
            style: Button style
            emoji: Button emoji
            label: Button label
            custom_id: Custom ID for the component
            audio_manager: Audio manager instance
        """
        # Call parent init if this is a mixin
        if hasattr(super(), "__init__"):
            super().__init__(style=style, emoji=emoji, label=label, custom_id=custom_id)

        # Set audio manager if provided
        if audio_manager is not None:
            self.audio_manager = audio_manager

        # Initialize interaction count
        if not hasattr(self, "interaction_count"):
            self.interaction_count = 0


class InteractionHandlerMixin(ActivityTrackerMixin, ValidationMixin):
    """
    Combined mixin for consistent interaction handling.
    Includes activity tracking and validation.
    """

    async def handle_interaction_start(
        self, interaction: discord.Interaction, action: str, check_voice: bool = False
    ) -> bool:
        """
        Standard interaction start handling with validation and tracking.

        Provides a consistent pattern for handling the start of any
        control panel interaction, including activity tracking,
        permission validation, and response deferral.

        Args:
            interaction: Discord interaction to process
            action: Human-readable action description for tracking
            check_voice: Whether to validate voice channel membership

        Returns:
            True if interaction can proceed, False if validation failed
        """
        # STEP 1: Activity Tracking
        # Record user action for display in control panel
        self.track_activity(interaction, action)

        # STEP 2: Voice Channel Validation (if required)
        # Check if user has permission to use control panel
        if check_voice and not await self.check_voice_channel(interaction):
            return False

        # STEP 3: Interaction Response Deferral
        # Prevent Discord timeout by deferring response
        await safe_defer(interaction)

        # STEP 4: Interaction Counter Update
        # Track usage statistics if counter is available
        if hasattr(self, "interaction_count"):
            self.interaction_count += 1

        return True


def create_audio_callback(
    method_name: str, action_description: str, service_name: str = "ControlPanel"
) -> Callable:
    """
    Factory function to create standardized audio callbacks.

    Creates consistent callback functions for audio manager operations
    with built-in error handling, logging, and interaction management.
    Reduces code duplication across control panel components.

    Args:
        method_name: Name of audio manager method to call
        action_description: Human-readable description for logging
        service_name: Service name for logging context

    Returns:
        Configured async callback function ready for use
    """

    async def callback(self, interaction: discord.Interaction):
        try:
            # STEP 1: Interaction Handling
            # Use standardized interaction start handling if available
            if hasattr(self, "handle_interaction_start"):
                if not await self.handle_interaction_start(
                    interaction, action_description
                ):
                    return
            else:
                # Fallback: simple defer if no handler available
                await safe_defer(interaction)

            # STEP 2: Audio Manager Method Execution
            # Call the specified audio manager method safely
            if hasattr(self, "audio_manager") and self.audio_manager:
                method = getattr(self.audio_manager, method_name, None)
                if method:
                    await method()

                    # STEP 3: Success Logging
                    # Log successful operation completion
                    TreeLogger.info(
                        f"{action_description} completed",
                        {
                            "user_id": interaction.user.id,
                            "username": interaction.user.display_name,
                            "operation": method_name,
                        },
                        service=service_name,
                    )

        except Exception as e:
            # STEP 4: Error Handling
            # Use component error handler if available, otherwise log
            if hasattr(self, "handle_error"):
                await self.handle_error(interaction, e)
            else:
                TreeLogger.error(f"Error in {method_name}: {e}", service=service_name)
            await safe_defer(interaction)

    return callback
