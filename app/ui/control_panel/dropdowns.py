# =============================================================================
# QuranBot - Control Panel Dropdowns
# =============================================================================
# Select/dropdown components for surah and reciter selection with pagination
# and dynamic option generation.
# 
# Dropdown Types:
# - SurahSelect: Paginated surah selection with Arabic/English names
# - ReciterSelect: Dynamic reciter selection with audio folder scanning
# - QuickJumpSelect: Popular surahs for rapid navigation
# 
# Features:
# - Pagination: 10 items per page for optimal Discord display
# - Dynamic Loading: Automatic option generation from data sources
# - Error Recovery: Fallback options and graceful error handling
# - State Synchronization: Real-time updates with audio manager
# - Activity Tracking: User interaction logging and analytics
# 
# Data Sources:
# - Surah data from COMPLETE_SURAHS_DATA with emojis and metadata
# - Reciter folders scanned from audio directory structure
# - Quick jump options for commonly accessed surahs
# 
# User Experience:
# - Rich formatting with Arabic names and emojis
# - Descriptive labels and tooltips
# - Responsive interaction with immediate feedback
# - Consistent behavior across all dropdown types
# =============================================================================

# Standard library imports
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Third-party imports
import discord
from discord.ui import Select

# Local imports - base components
from ..base.components import LoggingMixin
from ..base.formatters import truncate_text
from ..base.interaction_logging import InteractionLoggingMixin

# Local imports - current module
from .common import InteractionHandlerMixin, ActivityTrackerMixin
from .embeds import create_error_embed
from .utils import safe_defer, safe_interaction_response, safe_update_message, create_consistent_error_handler

# Local imports - core modules
from ...core.errors import ErrorHandler
from ...core.logger import TreeLogger

# Local imports - data
from ...data.surahs_data import get_surah_data_for_page, get_total_pages, COMPLETE_SURAHS_DATA

# Local imports - services
from ...services.bot.user_interaction_logger import InteractionStatus


class PaginatedSelect(Select, LoggingMixin, InteractionLoggingMixin, ActivityTrackerMixin):
    """Base class for paginated select dropdowns."""
    
    def __init__(self, *, placeholder: str = "Select an option...", 
                 max_values: int = 1, min_values: int = 1, **kwargs):
        super().__init__(placeholder=placeholder, max_values=max_values, 
                        min_values=min_values, **kwargs)
        self.current_page = 0
        self.items_per_page = 10  # Show 10 surahs per page for 12 total pages
        self.all_items: List[Dict[str, Any]] = []
        self.total_pages = 0
        self.error_handler = create_consistent_error_handler("Dropdowns")
    
    def update_options(self):
        """Update dropdown options based on current page."""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_items = self.all_items[start_idx:end_idx]
        
        self.options.clear()
        
        for item in current_items:
            self.options.append(discord.SelectOption(
                label=item.get("label", "Unknown"),
                description=item.get("description"),
                value=item.get("value", ""),
                emoji=item.get("emoji")
            ))
        
        # Update placeholder with page info
        if self.total_pages > 1:
            self.placeholder = f"{self.base_placeholder} ({self.current_page + 1}/{self.total_pages})"
        else:
            self.placeholder = self.base_placeholder
    
    async def next_page(self):
        """Navigate to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_options()
    
    async def previous_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_options()
    
    def set_items(self, items: List[Dict[str, Any]]):
        """Set all items and calculate pagination."""
        self.all_items = items
        if len(items) > 0:
            self.total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
        else:
            self.total_pages = 1
        self.current_page = 0
        self.update_options()


class SurahSelect(PaginatedSelect):
    """Dropdown for selecting Surahs with pagination."""
    
    def __init__(self, audio_manager=None, surah_data: Optional[List[Dict[str, Any]]] = None):
        self.base_placeholder = "Select a Surah..."
        super().__init__(
            placeholder=self.base_placeholder,
            custom_id="surah_select"
        )
        self.audio_manager = audio_manager
        
        # Load complete surah data with pagination
        self.load_complete_surah_data()
        
        # Initialize with first page data
        self.update_page_data()
    
    def load_complete_surah_data(self):
        """Load surah data with custom emojis and improved formatting."""
        # Calculate total pages for 10 surahs per page
        self.total_pages = get_total_pages(self.items_per_page)
        
        # Load current page data
        self.update_page_data()
    
    def update_page_data(self):
        """Update dropdown options for current page"""
        try:
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, 114)
            
            # Update placeholder with current page
            total_pages = (114 + self.items_per_page - 1) // self.items_per_page
            self.placeholder = f"{self.base_placeholder} ({self.current_page + 1}/{total_pages})"
            
            # Clear existing options
            self.options.clear()
            
            # Generate new options for current page
            for i in range(start_idx, end_idx):
                surah_number = i + 1
                
                # Get surah data from our data file
                surah_data = None
                for surah in COMPLETE_SURAHS_DATA:
                    if surah["number"] == surah_number:
                        surah_data = surah
                        break
                
                if surah_data:
                    english_name = surah_data["name_english"]
                    arabic_name = surah_data["name_arabic"]
                    emoji = surah_data["emoji"]
                    verses = surah_data["verses"]
                    
                    label = f"{english_name} | {arabic_name}"
                    if len(label) > 100:
                        label = label[:97] + "..."
                    
                    description = f"Surah {surah_number} • {verses} verses"
                    
                    self.options.append(discord.SelectOption(
                        label=label,
                        description=description,
                        value=str(surah_number),
                        emoji=emoji
                    ))
                    
            # Ensure we have at least one option
            if not self.options:
                self.options.append(discord.SelectOption(
                    label="Al-Fatiha | الفاتحة",
                    description="Surah 1 • 7 verses", 
                    value="1",
                    emoji="🌟"
                ))
                    
        except Exception as e:
            TreeLogger.error(f"Error updating page data: {e}", service="ControlPanelDropdowns")
            # Add fallback option to prevent Discord API error
            self.options.clear()
            self.options.append(discord.SelectOption(
                label="Al-Fatiha | الفاتحة",
                description="Surah 1 • 7 verses", 
                value="1",
                emoji="🌟"
            ))
    
    async def callback(self, interaction: discord.Interaction):
        """Process Surah selection"""
        try:
            selected_surah_number = int(self.values[0])
            
            # Get surah name for better activity display
            from ...data.surahs_data import COMPLETE_SURAHS_DATA
            surah_name = "Unknown"
            for surah in COMPLETE_SURAHS_DATA:
                if surah["number"] == selected_surah_number:
                    surah_name = surah["name_english"]
                    break
            
            # Start detailed interaction logging
            interaction_id = await self.start_interaction_logging(
                interaction=interaction,
                component_type="dropdown",
                component_id="surah_select",
                component_label=f"Surah Selection: {surah_name}",
                selected_values=[str(selected_surah_number), surah_name]
            )
            
            # Track activity using mixin (keep existing)
            self.track_activity(interaction, f"selected `{surah_name}`")
            
            # Respond immediately to prevent timeouts
            await safe_defer(interaction)
            
            # Get audio manager from parent view
            if hasattr(self.view, 'audio_manager') and self.view.audio_manager:
                TreeLogger.info(f"Calling change_surah with number: {selected_surah_number}", 
                              service="ControlPanelDropdowns")
                success = await self.view.audio_manager.change_surah(selected_surah_number)
                TreeLogger.info(f"change_surah returned: {success}", 
                              service="ControlPanelDropdowns")
                
                # Small delay to let audio manager update its state
                await asyncio.sleep(0.2)
                
            # Immediately update the panel to show the change
            if hasattr(self.view, 'update_panel'):
                try:
                    TreeLogger.info("Calling update_panel after surah change", 
                                  service="ControlPanelDropdowns")
                    await self.view.update_panel()
                except Exception as e:
                    TreeLogger.error(f"Error updating panel after surah selection: {e}", 
                                   service="ControlPanelDropdowns")
            
            # Complete interaction logging with success
            await self.complete_interaction_logging(status=InteractionStatus.SUCCESS)
                
        except Exception as e:
            # Complete interaction logging with error
            await self.complete_interaction_logging(status=InteractionStatus.FAILED, error_message=str(e), error_type=type(e).__name__)
            
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "surah_selection",
                    "selected_surah": selected_surah_number,
                    "user_id": interaction.user.id
                }
            )
            await safe_defer(interaction)


class ReciterSelect(PaginatedSelect):
    """Dropdown for selecting reciters with automatic audio directory scanning."""
    
    def __init__(self, audio_manager=None, audio_folder: Optional[Path] = None):
        self.base_placeholder = "Select a Reciter..."
        super().__init__(
            placeholder=self.base_placeholder,
            custom_id="reciter_select"
        )
        self.audio_manager = audio_manager
        self.audio_folder = audio_folder
        
        # Load reciter data
        self.load_reciter_data()
    
    def load_reciter_data(self):
        """Scan audio directory and load available reciters."""
        items = []
        
        if not self.audio_folder or not self.audio_folder.exists():
            # Default reciters matching the actual audio folders
            default_reciters = [
                {"name": "Abdul Basit Abdul Samad", "name_arabic": "عبد الباسط عبد الصمد", "folder": "Abdul Basit Abdul Samad"},
                {"name": "Maher Al Muaiqly", "name_arabic": "ماهر المعيقلي", "folder": "Maher Al Muaiqly"},
                {"name": "Muhammad Al Luhaidan", "name_arabic": "محمد اللحيدان", "folder": "Muhammad Al Luhaidan"},
                {"name": "Rashid Al Afasy", "name_arabic": "راشد العفاسي", "folder": "Rashid Al Afasy"},
                {"name": "Saad Al Ghamdi", "name_arabic": "سعد الغامدي", "folder": "Saad Al Ghamdi"},
                {"name": "Yasser Al Dosari", "name_arabic": "ياسر الدوسري", "folder": "Yasser Al Dosari"},
            ]
            
            for reciter in default_reciters:
                label = reciter["name"]
                description = reciter.get("name_arabic", "")
                
                items.append({
                    "label": truncate_text(label, 97),
                    "description": truncate_text(description, 97) if description else None,
                    "value": reciter["folder"],
                    "emoji": "🎙️"
                })
        else:
            # Scan audio directory for reciter folders
            try:
                for folder_path in self.audio_folder.iterdir():
                    if folder_path.is_dir() and not folder_path.name.startswith('.'):
                        folder_name = folder_path.name
                        
                        # Format folder name for display
                        display_name = folder_name.replace('_', ' ').title()
                        
                        # Check if folder has audio files
                        has_audio = any(
                            file.suffix.lower() in ['.mp3', '.wav', '.ogg', '.m4a']
                            for file in folder_path.rglob('*')
                            if file.is_file()
                        )
                        
                        if has_audio:
                            items.append({
                                "label": truncate_text(display_name, 97),
                                "description": f"Folder: {folder_name}",
                                "value": folder_name,
                                "emoji": "🎙️"
                            })
                
                if not items:
                    items.append({
                        "label": "No reciters found",
                        "description": "Audio folder contains no reciter directories",
                        "value": "none",
                        "emoji": "❌"
                    })
                    
            except Exception as e:
                TreeLogger.error(f"Error scanning audio directory: {e}", service="ControlPanelDropdowns")
                items.append({
                    "label": "Error loading reciters",
                    "description": "Could not scan audio directory",
                    "value": "error",
                    "emoji": "❌"
                })
        
        self.set_items(items)
    
    async def callback(self, interaction: discord.Interaction):
        try:
            selected_reciter = self.values[0]
            
            TreeLogger.debug(f"Reciter dropdown selection: {selected_reciter}", {
                "user": interaction.user.display_name,
                "selected_value": self.values[0]
            }, service="ControlPanelDropdowns")
            
            # Format reciter name for better display
            display_name = selected_reciter.replace('_', ' ').title()
            
            # Track activity using mixin
            self.track_activity(interaction, f"switched to `{display_name}`")
            
            # Respond immediately to prevent timeouts
            await safe_defer(interaction)
            
            if selected_reciter in ["none", "error"]:
                return
            
            if not self.audio_manager:
                return
            
            # Change to selected reciter - no success checking
            success = await self.audio_manager.change_reciter(selected_reciter)
            TreeLogger.debug(f"change_reciter returned: {success}", 
                          service="ControlPanelDropdowns")
            
            # Small delay to let audio manager update its state
            await asyncio.sleep(0.2)
            
            # Immediately update the panel to show the change
            if hasattr(self.view, 'update_panel'):
                try:
                    TreeLogger.debug("Calling update_panel after reciter change", 
                                  service="ControlPanelDropdowns")
                    await self.view.update_panel()
                except Exception as e:
                    TreeLogger.error(f"Error updating panel after reciter selection: {e}", 
                                   service="ControlPanelDropdowns")
            
            TreeLogger.info(f"Reciter changed to {selected_reciter}", {
                "user_id": interaction.user.id,
                "username": interaction.user.display_name,
                "reciter": selected_reciter
            }, service="ControlPanelDropdowns")
                
        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "reciter_selection",
                    "selected_reciter": selected_reciter,
                    "user_id": interaction.user.id
                }
            )
            await safe_defer(interaction)


class QuickJumpSelect(Select, LoggingMixin, InteractionLoggingMixin):
    """Quick jump dropdown for common surahs."""
    
    def __init__(self, audio_manager=None):
        # Common/popular surahs for quick access
        quick_options = [
            discord.SelectOption(label="1. Al-Fatiha", description="الفاتحة • The Opening", value="1", emoji="🌟"),
            discord.SelectOption(label="2. Al-Baqarah", description="البقرة • The Cow", value="2", emoji="📖"),
            discord.SelectOption(label="18. Al-Kahf", description="الكهف • The Cave", value="18", emoji="🏔️"),
            discord.SelectOption(label="36. Ya-Sin", description="يس • Ya-Sin", value="36", emoji="💫"),
            discord.SelectOption(label="55. Ar-Rahman", description="الرحمن • The Merciful", value="55", emoji="🌸"),
            discord.SelectOption(label="67. Al-Mulk", description="الملك • The Kingdom", value="67", emoji="👑"),
            discord.SelectOption(label="112. Al-Ikhlas", description="الإخلاص • Sincerity", value="112", emoji="✨"),
            discord.SelectOption(label="113. Al-Falaq", description="الفلق • The Dawn", value="113", emoji="🌅"),
            discord.SelectOption(label="114. An-Nas", description="الناس • Mankind", value="114", emoji="👥"),
        ]
        
        super().__init__(
            placeholder="Quick jump to popular surahs...",
            options=quick_options,
            custom_id="quick_jump"
        )
        self.audio_manager = audio_manager
    
    async def callback(self, interaction: discord.Interaction):
        # Start interaction logging
        selected_surah_number = int(self.values[0])
        interaction_id = await self.start_interaction_logging(
            interaction=interaction,
            component_type="dropdown",
            component_id="quick_jump",
            component_label="Quick Jump Selection",
            selected_values=[str(selected_surah_number)]
        )
        
        try:
            # Check if user is in Quran VC
            if not await self.is_user_in_quran_vc(interaction):
                embed = create_error_embed("You must be in the Quran voice channel to use the control panel.")
                await safe_interaction_response(interaction, embed=embed, ephemeral=True)
                await self.complete_interaction_logging(
                    status=InteractionStatus.PERMISSION_ERROR,
                    error_message="User not in Quran voice channel",
                    error_type="PermissionDenied"
                )
                return
            
            await safe_defer(interaction)
            
            # Start processing timer
            self.start_processing()
            
            if hasattr(self.view, 'track_user_activity'):
                self.view.track_user_activity(interaction.user, f"Quick Jump to Surah {selected_surah_number}")
            
            if not self.audio_manager:
                embed = create_error_embed("Audio manager not available")
                await interaction.followup.send(embed=embed, ephemeral=True)
                await self.complete_interaction_logging(
                    status=InteractionStatus.FAILED,
                    error_message="Audio manager not available",
                    error_type="ServiceUnavailable"
                )
                return
            
            # Change to selected surah
            success = await self.audio_manager.change_surah(selected_surah_number)
            
            if success:
                TreeLogger.info(f"Quick jump to Surah {selected_surah_number}", {
                    "user_id": interaction.user.id,
                    "username": self.format_user_name(interaction),
                    "discord_username": interaction.user.name,
                    "display_name": interaction.user.display_name,
                    "surah_number": selected_surah_number
                }, service="ControlPanelDropdowns")
                
                # Small delay to let audio manager update its state
                await asyncio.sleep(0.2)
                
                # Update the control panel display
                if hasattr(self.view, 'update_panel'):
                    await self.view.update_panel()
                
                await self.complete_interaction_logging(status=InteractionStatus.SUCCESS)
                await interaction.edit_original_response(view=self.view)
            else:
                embed = create_error_embed(f"Could not jump to Surah {selected_surah_number}")
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                await self.complete_interaction_logging(
                    status=InteractionStatus.FAILED,
                    error_message=f"Could not jump to Surah {selected_surah_number}",
                    error_type="OperationFailed"
                )
                
        except Exception as e:
            await self.log_interaction_error(e, {
                "component_type": "dropdown",
                "component_id": "quick_jump",
                "user_id": interaction.user.id,
                "selected_value": self.values[0] if self.values else None
            })
            
            TreeLogger.error(f"Error in quick jump: {e}", service="ControlPanelDropdowns")
            embed = create_error_embed("Error jumping to surah. Please try again.")
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass