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
from typing import Optional, Any, Callable

# Third-party imports
import discord

# Local imports - current module
from .embeds import create_error_embed
from .utils import safe_interaction_response, safe_defer

# Local imports - core modules
from ...core.logger import TreeLogger
from ...services.bot.user_interaction_logger import InteractionStatus


class ActivityTrackerMixin:
    """Mixin for consistent activity tracking across components."""
    
    def track_activity(self, interaction: discord.Interaction, action: str):
        """
        Track user activity if the view supports it.
        
        Args:
            interaction: Discord interaction
            action: Description of the action taken
        """
        TreeLogger.debug(f"Tracking activity: {action}", {
            "user": interaction.user.display_name,
            "user_id": interaction.user.id,
            "has_view": hasattr(self, 'view'),
            "has_update_method": hasattr(self.view, '_update_last_activity') if hasattr(self, 'view') else False
        }, service="ActivityTrackerMixin")
        
        if hasattr(self, 'view') and hasattr(self.view, '_update_last_activity'):
            self.view._update_last_activity(interaction.user, action)


class ValidationMixin:
    """Mixin for common validation checks."""
    
    async def check_voice_channel(self, interaction: discord.Interaction) -> bool:
        """
        Check if user is in the Quran voice channel.
        
        Args:
            interaction: Discord interaction
            
        Returns:
            True if user is in voice channel, False otherwise
        """
        if not await self.is_user_in_quran_vc(interaction):
            embed = create_error_embed("You must be in the Quran voice channel to use the control panel.")
            await safe_interaction_response(interaction, embed=embed, ephemeral=True)
            
            # Log if we have interaction logging capability
            if hasattr(self, 'complete_interaction_logging'):
                await self.complete_interaction_logging(
                    status=InteractionStatus.PERMISSION_ERROR,
                    error_message="User not in Quran voice channel",
                    error_type="PermissionDenied"
                )
            return False
        return True


class AudioManagerProxy:
    """Proxy for safe audio manager operations with consistent error handling."""
    
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
    
    async def safe_call(self, method_name: str, *args, **kwargs) -> Optional[Any]:
        """
        Safely call an audio manager method.
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Result of the method call or None if failed
        """
        if not self.audio_manager:
            TreeLogger.warning(f"Audio manager not available for {method_name}", 
                             service="ControlPanelCommon")
            return None
        
        try:
            method = getattr(self.audio_manager, method_name, None)
            if method and callable(method):
                return await method(*args, **kwargs)
            else:
                TreeLogger.error(f"Method {method_name} not found on audio manager", 
                               service="ControlPanelCommon")
                return None
        except Exception as e:
            TreeLogger.error(f"Error calling audio manager.{method_name}: {e}", 
                           service="ControlPanelCommon")
            return None


class ButtonStateMixin:
    """Mixin for consistent button state management."""
    
    def update_button_state(self, enabled: bool, 
                          enabled_style: discord.ButtonStyle = discord.ButtonStyle.success,
                          disabled_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
                          enabled_emoji: Optional[str] = None,
                          disabled_emoji: Optional[str] = None):
        """
        Update button appearance based on state.
        
        Args:
            enabled: Whether the feature is enabled
            enabled_style: Button style when enabled
            disabled_style: Button style when disabled
            enabled_emoji: Emoji when enabled (optional)
            disabled_emoji: Emoji when disabled (optional)
        """
        if enabled:
            self.style = enabled_style
            if enabled_emoji and hasattr(self, 'emoji'):
                self.emoji = enabled_emoji
        else:
            self.style = disabled_style
            if disabled_emoji and hasattr(self, 'emoji'):
                self.emoji = disabled_emoji


class ComponentInitMixin:
    """Mixin for standardized component initialization."""
    
    def init_control_component(self, 
                             style: discord.ButtonStyle = discord.ButtonStyle.secondary,
                             emoji: Optional[str] = None,
                             label: Optional[str] = None,
                             custom_id: Optional[str] = None,
                             audio_manager: Optional[Any] = None):
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
        if hasattr(super(), '__init__'):
            super().__init__(
                style=style,
                emoji=emoji,
                label=label,
                custom_id=custom_id
            )
        
        # Set audio manager if provided
        if audio_manager is not None:
            self.audio_manager = audio_manager
        
        # Initialize interaction count
        if not hasattr(self, 'interaction_count'):
            self.interaction_count = 0


class InteractionHandlerMixin(ActivityTrackerMixin, ValidationMixin):
    """
    Combined mixin for consistent interaction handling.
    Includes activity tracking and validation.
    """
    
    async def handle_interaction_start(self, 
                                     interaction: discord.Interaction, 
                                     action: str,
                                     check_voice: bool = False) -> bool:
        """
        Standard interaction start handling.
        
        Args:
            interaction: Discord interaction
            action: Action description for tracking
            check_voice: Whether to check voice channel
            
        Returns:
            True if interaction can proceed, False otherwise
        """
        # Track activity
        self.track_activity(interaction, action)
        
        # Check voice channel if required
        if check_voice and not await self.check_voice_channel(interaction):
            return False
        
        # Defer the interaction
        await safe_defer(interaction)
        
        # Increment interaction count if we have it
        if hasattr(self, 'interaction_count'):
            self.interaction_count += 1
        
        return True


def create_audio_callback(method_name: str, 
                         action_description: str,
                         service_name: str = "ControlPanel") -> Callable:
    """
    Factory function to create standardized audio callbacks.
    
    Args:
        method_name: Audio manager method to call
        action_description: Description for logging
        service_name: Service name for logging
        
    Returns:
        Async callback function
    """
    async def callback(self, interaction: discord.Interaction):
        try:
            # Use interaction handler if available
            if hasattr(self, 'handle_interaction_start'):
                if not await self.handle_interaction_start(interaction, action_description):
                    return
            else:
                await safe_defer(interaction)
            
            # Call audio manager method
            if hasattr(self, 'audio_manager') and self.audio_manager:
                method = getattr(self.audio_manager, method_name, None)
                if method:
                    await method()
                    
                    TreeLogger.info(f"{action_description} completed", {
                        "user_id": interaction.user.id,
                        "username": interaction.user.display_name,
                        "operation": method_name
                    }, service=service_name)
            
        except Exception as e:
            if hasattr(self, 'handle_error'):
                await self.handle_error(interaction, e)
            else:
                TreeLogger.error(f"Error in {method_name}: {e}", service=service_name)
            await safe_defer(interaction)
    
    return callback