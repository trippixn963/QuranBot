# =============================================================================
# QuranBot - Control Panel Buttons
# =============================================================================
# Button components for control panel interactions including playback controls,
# navigation buttons, and mode toggles.
# 
# Button Types:
# - Playback Control: Previous/Next surah navigation
# - Mode Toggles: Shuffle and loop mode switches
# - Navigation: Page navigation for dropdown menus
# - Utility: Search modal and panel refresh
# 
# Features:
# - Consistent error handling and user feedback
# - Activity tracking and interaction logging
# - State synchronization with audio manager
# - Visual feedback and button state management
# - Permission validation and voice channel checks
# 
# Design Patterns:
# - Mixin-based functionality composition
# - Standardized interaction handling
# - Error recovery and graceful degradation
# - Real-time state updates and UI synchronization
# =============================================================================

# Standard library imports
import asyncio
from typing import Optional, Any, Dict

# Third-party imports
import discord
from discord.ui import Button

# Local imports - base components
from ..base.components import LoggingMixin
from ..base.interaction_logging import InteractionLoggingMixin

# Local imports - current module
from .common import InteractionHandlerMixin, ButtonStateMixin, ComponentInitMixin, create_audio_callback
from .embeds import create_error_embed, create_success_embed
from .utils import safe_defer, safe_interaction_response, safe_update_message, create_consistent_error_handler

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger

# Local imports - services
from ...services.bot.user_interaction_logger import InteractionStatus


class ControlButton(Button, LoggingMixin, InteractionLoggingMixin):
    """Base class for all control panel buttons with common functionality."""
    
    def __init__(self, *, style: discord.ButtonStyle = discord.ButtonStyle.secondary, 
                 label: Optional[str] = None, emoji: Optional[str] = None, 
                 custom_id: Optional[str] = None, **kwargs):
        super().__init__(style=style, label=label, emoji=emoji, custom_id=custom_id, **kwargs)
        self.interaction_count = 0
        self.error_handler = create_consistent_error_handler("Buttons")
    
    async def handle_error(self, interaction: discord.Interaction, error: Exception):
        """Handle button interaction errors using established error handler pattern."""
        await self.error_handler.handle_error(
            error,
            {
                "operation": "button_interaction",
                "service_name": "ControlPanelButtons",
                "button_type": self.__class__.__name__,
                "user_id": interaction.user.id,
                "interaction_count": self.interaction_count,
                "custom_id": getattr(self, 'custom_id', None),
                "interaction_done": interaction.response.is_done()
            }
        )
        
        embed = create_error_embed(
            "An error occurred while processing your request. Please try again.",
            "Button Error"
        )
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as response_error:
            await self.error_handler.handle_error(
                response_error,
                {
                    "operation": "error_response_delivery",
                    "service_name": "ControlPanelButtons",
                    "button_type": self.__class__.__name__,
                    "user_id": interaction.user.id,
                    "original_error": str(error)
                }
            )


class PreviousButton(ControlButton, InteractionHandlerMixin):
    """Button for skipping to previous surah."""
    
    def __init__(self, audio_manager=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="⏮️",
            label="Previous",
            custom_id="previous_surah"
        )
        self.audio_manager = audio_manager
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Start detailed interaction logging
            interaction_id = await self.start_interaction_logging(
                interaction=interaction,
                component_type="button",
                component_id="previous_surah",
                component_label="Previous Surah Button"
            )
            
            TreeLogger.debug(f"Previous button clicked by {interaction.user.id}", {
                "user": interaction.user.display_name,
                "guild_id": interaction.guild_id
            }, service="ControlPanelButtons")
            
            # Track activity using mixin
            self.track_activity(interaction, "skipped to previous surah")
            
            # Defer interaction
            await safe_defer(interaction)
            
            # Call audio manager
            if self.audio_manager:
                await self.audio_manager.previous_surah()
                # Small delay to let audio manager update its state
                await asyncio.sleep(0.2)
                
            # Update panel to show change
            if hasattr(self.view, 'update_panel'):
                await self.view.update_panel()
                
            TreeLogger.info("Previous surah requested", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "operation": "previous_surah_request"
            }, service="ControlPanelButtons")
            
            # Complete interaction logging with success
            await self.complete_interaction_logging(status=InteractionStatus.SUCCESS)
                
        except Exception as e:
            # Complete interaction logging with error
            await self.complete_interaction_logging(status=InteractionStatus.FAILED, error_message=str(e), error_type=type(e).__name__)
            await self.handle_error(interaction, e)


class NextButton(ControlButton, InteractionHandlerMixin):
    """Button for skipping to next surah."""
    
    def __init__(self, audio_manager=None):
        super().__init__(
            style=discord.ButtonStyle.success,
            emoji="⏭️", 
            label="Next",
            custom_id="next_surah"
        )
        self.audio_manager = audio_manager
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Start detailed interaction logging
            interaction_id = await self.start_interaction_logging(
                interaction=interaction,
                component_type="button",
                component_id="next_surah",
                component_label="Next Surah Button"
            )
            
            TreeLogger.debug(f"Next button clicked by {interaction.user.id}", {
                "user": interaction.user.display_name,
                "guild_id": interaction.guild_id
            }, service="ControlPanelButtons")
            
            # Track activity using mixin
            self.track_activity(interaction, "skipped to next surah")
            
            # Defer interaction
            await safe_defer(interaction)
            
            # Call audio manager
            if self.audio_manager:
                await self.audio_manager.next_surah()
                # Small delay to let audio manager update its state
                await asyncio.sleep(0.2)
                
            # Update panel to show change
            if hasattr(self.view, 'update_panel'):
                await self.view.update_panel()
                
            TreeLogger.info("Next surah requested", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "operation": "next_surah_request"
            }, service="ControlPanelButtons")
            
            # Complete interaction logging with success
            await self.complete_interaction_logging(status=InteractionStatus.SUCCESS)
                
        except Exception as e:
            # Complete interaction logging with error
            await self.complete_interaction_logging(status=InteractionStatus.FAILED, error_message=str(e), error_type=type(e).__name__)
            await self.handle_error(interaction, e)


class ShuffleButton(ControlButton, InteractionHandlerMixin, ButtonStateMixin):
    """Button for toggling shuffle mode."""
    
    def __init__(self, audio_manager=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="🔀",
            label="Shuffle",
            custom_id="toggle_shuffle"
        )
        self.audio_manager = audio_manager
        self.is_shuffled = False
    
    def update_appearance(self, is_shuffled: bool):
        """Update button appearance based on shuffle state."""
        self.is_shuffled = is_shuffled
        self.update_button_state(
            enabled=is_shuffled,
            enabled_style=discord.ButtonStyle.success,
            disabled_style=discord.ButtonStyle.secondary
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Defer interaction immediately to prevent timeout
            await safe_defer(interaction)
            
            # Toggle state first
            old_state = self.is_shuffled
            TreeLogger.debug(f"Shuffle button toggled from {old_state}", {
                "user": interaction.user.display_name,
                "old_state": old_state
            }, service="ControlPanelButtons")
            
            if self.audio_manager:
                await self.audio_manager.toggle_shuffle()
                # Get the new state from audio manager
                self.is_shuffled = getattr(self.audio_manager, 'shuffle_enabled', not old_state)
            else:
                self.is_shuffled = not self.is_shuffled
            
            # Update button appearance
            self.update_appearance(self.is_shuffled)
            
            # Track activity
            action = "enabled shuffle mode" if self.is_shuffled else "disabled shuffle mode"
            self.track_activity(interaction, action)
            
            # Update panel to show change
            if hasattr(self.view, 'update_panel'):
                await self.view.update_panel()
            
            TreeLogger.info(f"Shuffle {'enabled' if self.is_shuffled else 'disabled'}", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "new_state": self.is_shuffled,
                "operation": "shuffle_toggle"
            }, service="ControlPanelButtons")
                
        except Exception as e:
            await self.handle_error(interaction, e)


class LoopButton(ControlButton, InteractionHandlerMixin, ButtonStateMixin):
    """Button for cycling through loop modes."""
    
    def __init__(self, audio_manager=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="🔁",
            label="Loop",
            custom_id="toggle_loop"
        )
        self.audio_manager = audio_manager
        self.is_looping = False
    
    def update_appearance(self, is_looping: bool):
        """Update button appearance based on loop state."""
        self.is_looping = is_looping
        self.update_button_state(
            enabled=is_looping,
            enabled_style=discord.ButtonStyle.success,
            disabled_style=discord.ButtonStyle.secondary,
            enabled_emoji="🔂",
            disabled_emoji="🔁"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Defer interaction immediately to prevent timeout
            await safe_defer(interaction)
            
            # Simple toggle - just flip the state
            old_state = self.is_looping
            self.is_looping = not self.is_looping
            
            TreeLogger.debug(f"Loop button toggled from {old_state} to {self.is_looping}", {
                "user": interaction.user.display_name,
                "old_state": old_state,
                "new_state": self.is_looping
            }, service="ControlPanelButtons")
            
            # Update audio manager if available
            if self.audio_manager:
                # Set loop mode based on toggle state
                if self.is_looping:
                    self.audio_manager.loop_mode = "single"  # Loop current surah
                else:
                    self.audio_manager.loop_mode = "off"     # No loop
            
            # Update button appearance
            self.update_appearance(self.is_looping)
            
            # Track activity
            action = "enabled repeat surah" if self.is_looping else "disabled repeat surah"
            self.track_activity(interaction, action)
            
            # Update panel to show change
            if hasattr(self.view, 'update_panel'):
                await self.view.update_panel()
            
            TreeLogger.info(f"Loop {'enabled' if self.is_looping else 'disabled'}", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "is_looping": self.is_looping
            }, service="ControlPanelButtons")
                
        except Exception as e:
            await self.handle_error(interaction, e)
            await safe_defer(interaction)


class SearchButton(ControlButton, InteractionHandlerMixin):
    """Button for opening search modal."""
    
    def __init__(self, audio_manager=None):
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji="🔍",
            label="Search",
            custom_id="open_search"
        )
        self.audio_manager = audio_manager
    
    async def callback(self, interaction: discord.Interaction):
        try:
            self.interaction_count += 1
            
            # Track activity using mixin
            self.track_activity(interaction, "opened search modal")
            
            # Import here to avoid circular imports
            from ..search.modal import SurahSearchModal
            
            # Create and send search modal
            search_modal = SurahSearchModal(
                audio_manager=self.audio_manager,
                control_panel_view=self.view
            )
            
            await interaction.response.send_modal(search_modal)
            
            TreeLogger.info("Search modal opened", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name
            }, service="ControlPanelButtons")
                
        except Exception as e:
            await self.handle_error(interaction, e)


class PrevPageButton(ControlButton, InteractionHandlerMixin):
    """Button for navigating to previous page in dropdowns."""
    
    def __init__(self, target_dropdown=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="◀️",
            label="Prev Page",
            custom_id="prev_page"
        )
        self.target_dropdown = target_dropdown
    
    async def callback(self, interaction: discord.Interaction):
        """Navigate to previous page"""
        try:
            if hasattr(self.view, 'current_page') and self.view.current_page > 0:
                # Defer first to prevent timeout
                await safe_defer(interaction)
                
                old_page = self.view.current_page
                self.view.current_page -= 1
                
                # Track activity using mixin
                self.track_activity(interaction, "switched to previous page")
                
                # Update dropdown options
                if self.target_dropdown and hasattr(self.target_dropdown, 'update_page_data'):
                    self.target_dropdown.current_page = self.view.current_page
                    self.target_dropdown.update_page_data()
                
                # Force update the panel to refresh embed
                if hasattr(self.view, 'update_panel'):
                    await self.view.update_panel()
            else:
                # At boundary - just defer
                await safe_defer(interaction)
                
        except Exception as e:
            await self.handle_error(interaction, e)
            await safe_defer(interaction)


class NextPageButton(ControlButton, InteractionHandlerMixin):
    """Button for navigating to next page in dropdowns."""
    
    def __init__(self, target_dropdown=None):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="▶️",
            label="Next Page", 
            custom_id="next_page"
        )
        self.target_dropdown = target_dropdown
    
    async def callback(self, interaction: discord.Interaction):
        """Navigate to next page"""
        try:
            max_pages = (114 + 9) // 10  # SURAHS_PER_PAGE = 10
            if hasattr(self.view, 'current_page') and self.view.current_page < max_pages - 1:
                # Defer first to prevent timeout
                await safe_defer(interaction)
                
                old_page = self.view.current_page
                self.view.current_page += 1
                
                # Track activity using mixin
                self.track_activity(interaction, "switched to next page")
                
                # Update dropdown options
                if self.target_dropdown and hasattr(self.target_dropdown, 'update_page_data'):
                    self.target_dropdown.current_page = self.view.current_page
                    self.target_dropdown.update_page_data()
                
                # Force update the panel to refresh embed
                if hasattr(self.view, 'update_panel'):
                    await self.view.update_panel()
            else:
                # At boundary - just defer
                await safe_defer(interaction)
                
        except Exception as e:
            await self.handle_error(interaction, e)
            await safe_defer(interaction)


class RefreshButton(ControlButton, InteractionHandlerMixin):
    """Button for manually refreshing the control panel."""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            label="Refresh",
            custom_id="refresh_panel"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Use standardized interaction handling
            if not await self.handle_interaction_start(interaction, "Panel Refreshed", check_voice=True):
                return
            
            self.log_interaction(interaction, "refresh_panel")
            
            # Force update the control panel
            if hasattr(self.view, 'update_panel'):
                await self.view.update_panel()
            
            TreeLogger.info("Control panel refreshed", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name
            }, service="ControlPanelButtons")
                
        except Exception as e:
            await self.handle_error(interaction, e)