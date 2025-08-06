"""Control panel dropdown components for QuranBot.

Select/dropdown components for surah and reciter selection with pagination
and dynamic option generation.

Dropdown Types:
- SurahSelect: Paginated surah selection with Arabic/English names
- ReciterSelect: Dynamic reciter selection with audio folder scanning
- QuickJumpSelect: Popular surahs for rapid navigation
"""

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
from pathlib import Path
from typing import Any

# Third-party imports
import discord
from discord.ui import Select

# Local imports - core modules
from ...core.logger import TreeLogger

# Local imports - data
from ...data.surahs_data import (
    COMPLETE_SURAHS_DATA,
    get_total_pages,
)

# Local imports - services
from ...services.bot.user_interaction_logger import InteractionStatus

# Local imports - base components
from ..base.components import LoggingMixin
from ..base.formatters import truncate_text
from ..base.interaction_logging import InteractionLoggingMixin

# Local imports - current module
from .common import ActivityTrackerMixin
from .embeds import create_error_embed
from .utils import (
    create_consistent_error_handler,
    safe_defer,
    safe_interaction_response,
)


class PaginatedSelect(
    Select, LoggingMixin, InteractionLoggingMixin, ActivityTrackerMixin
):
    """Base class for paginated select dropdowns."""

    def __init__(
        self,
        *,
        placeholder: str = "Select an option...",
        max_values: int = 1,
        min_values: int = 1,
        **kwargs,
    ):
        super().__init__(
            placeholder=placeholder,
            max_values=max_values,
            min_values=min_values,
            **kwargs,
        )
        self.current_page = 0
        self.items_per_page = 10  # Show 10 surahs per page for 12 total pages
        self.all_items: list[dict[str, Any]] = []
        self.total_pages = 0
        self.error_handler = create_consistent_error_handler("Dropdowns")

    def update_options(self):
        """
        Update dropdown options based on current page.

        Calculates the items to display for the current page and
        updates the Discord select options accordingly. Also updates
        the placeholder text to show current page information.
        """
        # Calculate page boundaries for item slicing
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_items = self.all_items[start_idx:end_idx]

        # Clear existing options before adding new ones
        self.options.clear()

        # Create Discord select options from current page items
        for item in current_items:
            self.options.append(
                discord.SelectOption(
                    label=item.get("label", "Unknown"),
                    description=item.get("description"),
                    value=item.get("value", ""),
                    emoji=item.get("emoji"),
                )
            )

        # Update placeholder text with pagination info
        if self.total_pages > 1:
            self.placeholder = (
                f"{self.base_placeholder} ({self.current_page + 1}/{self.total_pages})"
            )
        else:
            self.placeholder = self.base_placeholder

    async def next_page(self):
        """
        Navigate to next page if not at the end.

        Advances to the next page of items and updates the dropdown
        options to display the new page content.
        """
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_options()

    async def previous_page(self):
        """
        Navigate to previous page if not at the beginning.

        Goes back to the previous page of items and updates the dropdown
        options to display the previous page content.
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_options()

    def set_items(self, items: list[dict[str, Any]]):
        """Set all items and calculate pagination."""
        self.all_items = items
        if len(items) > 0:
            self.total_pages = (
                len(items) + self.items_per_page - 1
            ) // self.items_per_page
        else:
            self.total_pages = 1
        self.current_page = 0
        self.update_options()


class SurahSelect(PaginatedSelect):
    """Dropdown for selecting Surahs with pagination."""

    def __init__(
        self, audio_manager=None, surah_data: list[dict[str, Any]] | None = None
    ):
        self.base_placeholder = "Select a Surah..."
        super().__init__(placeholder=self.base_placeholder, custom_id="surah_select")
        self.audio_manager = audio_manager

        # Load complete surah data with pagination
        self.load_complete_surah_data()

        # Initialize with first page data
        self.update_page_data()

    def load_complete_surah_data(self):
        """
        Load surah data with custom emojis and improved formatting.

        Initializes the dropdown with complete Quran data including
        Arabic names, English translations, verse counts, and custom
        emojis for each surah. Calculates pagination requirements.
        """
        # Calculate total pages needed for all 114 surahs
        self.total_pages = get_total_pages(self.items_per_page)

        # Initialize with first page of surah data
        self.update_page_data()

    def update_page_data(self):
        """
        Update dropdown options for current page with surah data.

        Generates Discord select options for the current page of surahs,
        including bilingual names, verse counts, and custom emojis.
        Provides fallback options if data loading fails.
        """
        try:
            # STEP 1: Calculate Page Boundaries
            # Determine which surahs to display on current page
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, 114)

            # STEP 2: Update Placeholder with Page Info
            # Show current page number in dropdown placeholder
            total_pages = (114 + self.items_per_page - 1) // self.items_per_page
            self.placeholder = (
                f"{self.base_placeholder} ({self.current_page + 1}/{total_pages})"
            )

            # STEP 3: Clear Existing Options
            # Remove previous page options before adding new ones
            self.options.clear()

            # STEP 4: Generate Options for Current Page
            # Create select options for each surah on this page
            for i in range(start_idx, end_idx):
                surah_number = i + 1

                # STEP 5: Lookup Surah Data
                # Find matching surah data from complete dataset
                surah_data = None
                for surah in COMPLETE_SURAHS_DATA:
                    if surah["number"] == surah_number:
                        surah_data = surah
                        break

                # STEP 6: Create Select Option
                # Format surah information for Discord display
                if surah_data:
                    english_name = surah_data["name_english"]
                    arabic_name = surah_data["name_arabic"]
                    emoji = surah_data["emoji"]
                    verses = surah_data["verses"]

                    # Format label with length limit for Discord
                    label = f"{english_name} | {arabic_name}"
                    if len(label) > 100:
                        label = label[:97] + "..."

                    description = f"Surah {surah_number} • {verses} verses"

                    self.options.append(
                        discord.SelectOption(
                            label=label,
                            description=description,
                            value=str(surah_number),
                            emoji=emoji,
                        )
                    )

            # STEP 7: Fallback Option Validation
            # Ensure at least one option exists to prevent Discord errors
            if not self.options:
                self.options.append(
                    discord.SelectOption(
                        label="Al-Fatiha | الفاتحة",
                        description="Surah 1 • 7 verses",
                        value="1",
                        emoji="🌟",
                    )
                )

        except Exception as e:
            # STEP 8: Error Recovery
            # Provide safe fallback if data loading fails
            TreeLogger.error(
                f"Error updating page data: {e}", service="ControlPanelDropdowns"
            )
            self.options.clear()
            self.options.append(
                discord.SelectOption(
                    label="Al-Fatiha | الفاتحة",
                    description="Surah 1 • 7 verses",
                    value="1",
                    emoji="🌟",
                )
            )

    async def callback(self, interaction: discord.Interaction):
        """
        Process Surah selection from dropdown.

        Handles user selection of a surah from the paginated dropdown,
        updates the audio manager, and refreshes the control panel display.
        """
        try:
            # STEP 1: Extract Selection Data
            # Get selected surah number from dropdown value
            selected_surah_number = int(self.values[0])

            # STEP 2: Lookup Surah Name
            # Find human-readable name for activity tracking
            from ...data.surahs_data import COMPLETE_SURAHS_DATA

            surah_name = "Unknown"
            for surah in COMPLETE_SURAHS_DATA:
                if surah["number"] == selected_surah_number:
                    surah_name = surah["name_english"]
                    break

            # STEP 3: Initialize Interaction Logging
            # Start detailed logging for analytics and debugging
            interaction_id = await self.start_interaction_logging(
                interaction=interaction,
                component_type="dropdown",
                component_id="surah_select",
                component_label=f"Surah Selection: {surah_name}",
                selected_values=[str(selected_surah_number), surah_name],
            )

            # STEP 4: Track User Activity
            # Record selection for display in control panel
            self.track_activity(interaction, f"selected `{surah_name}`")

            # STEP 5: Defer Interaction Response
            # Prevent Discord timeout during audio manager operations
            await safe_defer(interaction)

            # STEP 6: Execute Audio Manager Command
            # Request surah change from audio playback system
            if hasattr(self.view, "audio_manager") and self.view.audio_manager:
                TreeLogger.info(
                    f"Calling change_surah with number: {selected_surah_number}",
                    service="ControlPanelDropdowns",
                )
                success = await self.view.audio_manager.change_surah(
                    selected_surah_number
                )
                TreeLogger.info(
                    f"change_surah returned: {success}", service="ControlPanelDropdowns"
                )

                # Allow time for audio manager to update internal state
                await asyncio.sleep(0.2)

            # STEP 7: Update Control Panel Display
            # Refresh panel to show new surah information
            if hasattr(self.view, "update_panel"):
                try:
                    TreeLogger.info(
                        "Calling update_panel after surah change",
                        service="ControlPanelDropdowns",
                    )
                    await self.view.update_panel()
                except Exception as e:
                    TreeLogger.error(
                        f"Error updating panel after surah selection: {e}",
                        service="ControlPanelDropdowns",
                    )

            # STEP 8: Complete Interaction Logging
            # Mark interaction as successful for analytics
            await self.complete_interaction_logging(status=InteractionStatus.SUCCESS)

        except Exception as e:
            # Complete interaction logging with error
            await self.complete_interaction_logging(
                status=InteractionStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "surah_selection",
                    "selected_surah": selected_surah_number,
                    "user_id": interaction.user.id,
                },
            )
            await safe_defer(interaction)


class ReciterSelect(PaginatedSelect):
    """Dropdown for selecting reciters with automatic audio directory scanning."""

    def __init__(self, audio_manager=None, audio_folder: Path | None = None):
        self.base_placeholder = "Select a Reciter..."
        super().__init__(placeholder=self.base_placeholder, custom_id="reciter_select")
        self.audio_manager = audio_manager
        self.audio_folder = audio_folder

        # Load reciter data
        self.load_reciter_data()

    def load_reciter_data(self):
        """
        Scan audio directory and load available reciters.

        Dynamically discovers available reciters by scanning the audio
        directory structure. Falls back to default reciter list if
        directory scanning fails or no audio folder is configured.
        """
        items = []

        # STEP 1: Check Audio Folder Availability
        # Determine if we can scan for reciters or use defaults
        if not self.audio_folder or not self.audio_folder.exists():
            # STEP 2: Use Default Reciter List
            # Provide known reciters when directory scanning isn't possible
            default_reciters = [
                {
                    "name": "Abdul Basit Abdul Samad",
                    "name_arabic": "عبد الباسط عبد الصمد",
                    "folder": "Abdul Basit Abdul Samad",
                },
                {
                    "name": "Maher Al Muaiqly",
                    "name_arabic": "ماهر المعيقلي",
                    "folder": "Maher Al Muaiqly",
                },
                {
                    "name": "Muhammad Al Luhaidan",
                    "name_arabic": "محمد اللحيدان",
                    "folder": "Muhammad Al Luhaidan",
                },
                {
                    "name": "Rashid Al Afasy",
                    "name_arabic": "راشد العفاسي",
                    "folder": "Rashid Al Afasy",
                },
                {
                    "name": "Saad Al Ghamdi",
                    "name_arabic": "سعد الغامدي",
                    "folder": "Saad Al Ghamdi",
                },
                {
                    "name": "Yasser Al Dosari",
                    "name_arabic": "ياسر الدوسري",
                    "folder": "Yasser Al Dosari",
                },
            ]

            # STEP 3: Format Default Reciters
            # Create dropdown items from default reciter data
            for reciter in default_reciters:
                label = reciter["name"]
                description = reciter.get("name_arabic", "")

                items.append(
                    {
                        "label": truncate_text(label, 97),
                        "description": (
                            truncate_text(description, 97) if description else None
                        ),
                        "value": reciter["folder"],
                        "emoji": "🎙️",
                    }
                )
        else:
            # STEP 4: Scan Audio Directory
            # Dynamically discover reciters from filesystem
            try:
                for folder_path in self.audio_folder.iterdir():
                    # STEP 5: Validate Reciter Folders
                    # Check if folder is a valid reciter directory
                    if folder_path.is_dir() and not folder_path.name.startswith("."):
                        folder_name = folder_path.name

                        # Format folder name for user-friendly display
                        display_name = folder_name.replace("_", " ").title()

                        # STEP 6: Verify Audio Content
                        # Ensure folder contains actual audio files
                        has_audio = any(
                            file.suffix.lower() in [".mp3", ".wav", ".ogg", ".m4a"]
                            for file in folder_path.rglob("*")
                            if file.is_file()
                        )

                        # STEP 7: Add Valid Reciters
                        # Create dropdown item for reciters with audio
                        if has_audio:
                            items.append(
                                {
                                    "label": truncate_text(display_name, 97),
                                    "description": f"Folder: {folder_name}",
                                    "value": folder_name,
                                    "emoji": "🎙️",
                                }
                            )

                # STEP 8: Handle Empty Directory
                # Provide feedback if no reciters found
                if not items:
                    items.append(
                        {
                            "label": "No reciters found",
                            "description": "Audio folder contains no reciter directories",
                            "value": "none",
                            "emoji": "❌",
                        }
                    )

            except Exception as e:
                # STEP 9: Error Recovery
                # Provide error feedback if directory scanning fails
                TreeLogger.error(
                    f"Error scanning audio directory: {e}",
                    service="ControlPanelDropdowns",
                )
                items.append(
                    {
                        "label": "Error loading reciters",
                        "description": "Could not scan audio directory",
                        "value": "error",
                        "emoji": "❌",
                    }
                )

        # STEP 10: Initialize Dropdown Items
        # Set the discovered/default items for pagination
        self.set_items(items)

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_reciter = self.values[0]

            TreeLogger.debug(
                f"Reciter dropdown selection: {selected_reciter}",
                {
                    "user": interaction.user.display_name,
                    "selected_value": self.values[0],
                },
                service="ControlPanelDropdowns",
            )

            # Format reciter name for better display
            display_name = selected_reciter.replace("_", " ").title()

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
            TreeLogger.debug(
                f"change_reciter returned: {success}", service="ControlPanelDropdowns"
            )

            # Small delay to let audio manager update its state
            await asyncio.sleep(0.2)

            # Immediately update the panel to show the change
            if hasattr(self.view, "update_panel"):
                try:
                    TreeLogger.debug(
                        "Calling update_panel after reciter change",
                        service="ControlPanelDropdowns",
                    )
                    await self.view.update_panel()
                except Exception as e:
                    TreeLogger.error(
                        f"Error updating panel after reciter selection: {e}",
                        service="ControlPanelDropdowns",
                    )

            TreeLogger.info(
                f"Reciter changed to {selected_reciter}",
                {
                    "user_id": interaction.user.id,
                    "username": interaction.user.display_name,
                    "reciter": selected_reciter,
                },
                service="ControlPanelDropdowns",
            )

        except Exception as e:
            await self.error_handler.handle_error(
                e,
                {
                    "operation": "reciter_selection",
                    "selected_reciter": selected_reciter,
                    "user_id": interaction.user.id,
                },
            )
            await safe_defer(interaction)


class QuickJumpSelect(Select, LoggingMixin, InteractionLoggingMixin):
    """Quick jump dropdown for common surahs."""

    def __init__(self, audio_manager=None):
        # Common/popular surahs for quick access
        quick_options = [
            discord.SelectOption(
                label="1. Al-Fatiha",
                description="الفاتحة • The Opening",
                value="1",
                emoji="🌟",
            ),
            discord.SelectOption(
                label="2. Al-Baqarah",
                description="البقرة • The Cow",
                value="2",
                emoji="📖",
            ),
            discord.SelectOption(
                label="18. Al-Kahf",
                description="الكهف • The Cave",
                value="18",
                emoji="🏔️",
            ),
            discord.SelectOption(
                label="36. Ya-Sin", description="يس • Ya-Sin", value="36", emoji="💫"
            ),
            discord.SelectOption(
                label="55. Ar-Rahman",
                description="الرحمن • The Merciful",
                value="55",
                emoji="🌸",
            ),
            discord.SelectOption(
                label="67. Al-Mulk",
                description="الملك • The Kingdom",
                value="67",
                emoji="👑",
            ),
            discord.SelectOption(
                label="112. Al-Ikhlas",
                description="الإخلاص • Sincerity",
                value="112",
                emoji="✨",
            ),
            discord.SelectOption(
                label="113. Al-Falaq",
                description="الفلق • The Dawn",
                value="113",
                emoji="🌅",
            ),
            discord.SelectOption(
                label="114. An-Nas",
                description="الناس • Mankind",
                value="114",
                emoji="👥",
            ),
        ]

        super().__init__(
            placeholder="Quick jump to popular surahs...",
            options=quick_options,
            custom_id="quick_jump",
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
            selected_values=[str(selected_surah_number)],
        )

        try:
            # Check if user is in Quran VC
            if not await self.is_user_in_quran_vc(interaction):
                embed = create_error_embed(
                    "You must be in the Quran voice channel to use the control panel."
                )
                await safe_interaction_response(
                    interaction, embed=embed, ephemeral=True
                )
                await self.complete_interaction_logging(
                    status=InteractionStatus.PERMISSION_ERROR,
                    error_message="User not in Quran voice channel",
                    error_type="PermissionDenied",
                )
                return

            await safe_defer(interaction)

            # Start processing timer
            self.start_processing()

            if hasattr(self.view, "track_user_activity"):
                self.view.track_user_activity(
                    interaction.user, f"Quick Jump to Surah {selected_surah_number}"
                )

            if not self.audio_manager:
                embed = create_error_embed("Audio manager not available")
                await interaction.followup.send(embed=embed, ephemeral=True)
                await self.complete_interaction_logging(
                    status=InteractionStatus.FAILED,
                    error_message="Audio manager not available",
                    error_type="ServiceUnavailable",
                )
                return

            # Change to selected surah
            success = await self.audio_manager.change_surah(selected_surah_number)

            if success:
                TreeLogger.info(
                    f"Quick jump to Surah {selected_surah_number}",
                    {
                        "user_id": interaction.user.id,
                        "username": self.format_user_name(interaction),
                        "discord_username": interaction.user.name,
                        "display_name": interaction.user.display_name,
                        "surah_number": selected_surah_number,
                    },
                    service="ControlPanelDropdowns",
                )

                # Small delay to let audio manager update its state
                await asyncio.sleep(0.2)

                # Update the control panel display
                if hasattr(self.view, "update_panel"):
                    await self.view.update_panel()

                await self.complete_interaction_logging(
                    status=InteractionStatus.SUCCESS
                )
                await interaction.edit_original_response(view=self.view)
            else:
                embed = create_error_embed(
                    f"Could not jump to Surah {selected_surah_number}"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

                await self.complete_interaction_logging(
                    status=InteractionStatus.FAILED,
                    error_message=f"Could not jump to Surah {selected_surah_number}",
                    error_type="OperationFailed",
                )

        except Exception as e:
            await self.log_interaction_error(
                e,
                {
                    "component_type": "dropdown",
                    "component_id": "quick_jump",
                    "user_id": interaction.user.id,
                    "selected_value": self.values[0] if self.values else None,
                },
            )

            TreeLogger.error(
                f"Error in quick jump: {e}", service="ControlPanelDropdowns"
            )
            embed = create_error_embed("Error jumping to surah. Please try again.")
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
