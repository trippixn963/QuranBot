# =============================================================================
# QuranBot - Interactive Control Panel
# =============================================================================
# Discord control panel with buttons, dropdowns, and real-time updates
# Features surah selection, reciter switching, and playback controls
# =============================================================================

import asyncio
from datetime import UTC, datetime
import os

import discord
from discord.ui import Button, Modal, Select, TextInput, View

from .discord_logger import get_discord_logger
from .surah_mapper import get_surah_info, search_surahs
from .tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_user_interaction,
)

# =============================================================================
# Configuration
# =============================================================================

SURAHS_PER_PAGE = 10
UPDATE_INTERVAL = 2  # Reduced from 15 to 2 seconds for faster response


# =============================================================================
# Search Modal
# =============================================================================


class SurahSearchModal(Modal):
    """Modal for searching surahs by name or number"""

    def __init__(self, audio_manager=None, control_panel_view=None):
        super().__init__(title="🔍 Search for a Surah")
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view

        # Add search input
        self.search_input = TextInput(
            label="Search by name or number",
            placeholder="e.g., 'Fatiha', 'البقرة', 'Light', '36', 'Ya-Sin'",
            style=discord.TextStyle.short,
            max_length=100,
            required=True,
        )
        self.add_item(self.search_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission"""
        try:
            query = self.search_input.value.strip()

            if not query:
                log_perfect_tree_section(
                    "Surah Search - Empty Query",
                    [
                        (
                            "user",
                            f"{interaction.user.display_name} ({interaction.user.id})",
                        ),
                        ("status", "❌ Empty search query submitted"),
                        ("action", "Requesting user to enter search term"),
                    ],
                    "🔍",
                )
                embed = discord.Embed(
                    title="❌ Empty Search Query",
                    description="Please enter a search term!",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَّـــــا")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Search for surahs
            results = search_surahs(query)

            # Log search with results
            log_perfect_tree_section(
                "Surah Search - Query Processed",
                [
                    (
                        "user",
                        f"{interaction.user.display_name} ({interaction.user.id})",
                    ),
                    ("query", f"'{query}' (length: {len(query)} chars)"),
                    ("results_count", f"{len(results)} surah(s) found"),
                ],
                "🔍",
            )

            if not results:
                log_perfect_tree_section(
                    "Surah Search - No Results",
                    [
                        ("query", f"'{query}'"),
                        ("status", "❌ No matches found"),
                        ("action", "Sending search guidance to user"),
                    ],
                    "🔍",
                )
                embed = discord.Embed(
                    title="❌ No Results Found",
                    description=f"No surahs found for '{query}'.",
                    color=0xFF6B6B,
                )
                embed.add_field(
                    name="💡 Try searching by:",
                    value="• **Number**: 1-114 (e.g., '36')\n• **English name**: 'Light', 'Cave', 'Elephant'\n• **Transliterated name**: 'Al-Fatiha', 'Ya-Sin', 'An-Nur'\n• **Arabic name**: 'الفاتحة', 'يس', 'النور'",
                    inline=False,
                )
                embed.set_footer(text="Created by حَـــــنَّـــــا")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

                # If only one result, show confirmation
            if len(results) == 1:
                surah = results[0]

                # Log single result found
                log_perfect_tree_section(
                    "Surah Search - Single Result",
                    [
                        ("query", f"'{query}'"),
                        (
                            "result",
                            f"Exact match: {surah.name_transliteration} (#{surah.number})",
                        ),
                        ("action", "Showing confirmation dialog"),
                    ],
                    "🔍",
                )

                # Show confirmation embed with options
                confirmation_view = SurahConfirmationView(
                    surah=surah,
                    query=query,
                    audio_manager=self.audio_manager,
                    control_panel_view=self.control_panel_view,
                )

                embed = discord.Embed(
                    title="🔍 Surah Found!",
                    description=f"Found the perfect match for your search '{query}':",
                    color=0x2ECC71,
                )

                # Add bot's profile picture as thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)

                embed.add_field(
                    name=f"{surah.emoji} {surah.name_transliteration}",
                    value=f"*{surah.name_arabic}*\n📖 Surah {surah.number} • {surah.verses} verses\n🏛️ {surah.revelation_type.value}",
                    inline=False,
                )

                if surah.meaning:
                    embed.add_field(name="💫 Meaning", value=surah.meaning, inline=True)

                embed.set_footer(text="Choose an action below:")

                log_perfect_tree_section(
                    "Surah Search - Confirmation Sent",
                    [
                        ("surah", f"{surah.name_transliteration} (#{surah.number})"),
                        ("embed_type", "Single result confirmation"),
                        ("status", "✅ Sent to user"),
                    ],
                    "📤",
                )
                await interaction.response.send_message(
                    embed=embed, view=confirmation_view, ephemeral=True
                )
                return

            # Multiple results - show selection view
            log_perfect_tree_section(
                "Surah Search - Multiple Results",
                [
                    ("query", f"'{query}'"),
                    ("results_count", f"{len(results)} surahs found"),
                    ("action", "Showing selection dropdown"),
                ],
                "🔍",
            )

            search_results_view = SearchResultsView(
                results=results,
                query=query,
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view,
            )

            embed = discord.Embed(
                title=f"🔍 Search Results for '{query}'",
                description=f"Found {len(results)} surah(s). Select one below:",
                color=0x3498DB,
            )

            # Add results to embed
            for i, surah in enumerate(results[:5], 1):  # Show max 5 in embed
                embed.add_field(
                    name=f"{i}. {surah.emoji} {surah.name_transliteration}",
                    value=f"*{surah.name_arabic}* • Surah {surah.number} • {surah.verses} verses",
                    inline=False,
                )

            if len(results) > 5:
                embed.add_field(
                    name="",
                    value=f"*... and {len(results) - 5} more results*",
                    inline=False,
                )

            log_perfect_tree_section(
                "Surah Search - Results Sent",
                [
                    ("results_total", len(results)),
                    ("results_visible", min(5, len(results))),
                    ("embed_type", "Multiple results selection"),
                    ("status", "✅ Sent to user"),
                ],
                "📤",
            )
            await interaction.response.send_message(
                embed=embed, view=search_results_view, ephemeral=True
            )

        except Exception as e:
            log_error_with_traceback("Error in search modal submission", e)
            embed = discord.Embed(
                title="❌ Search Error",
                description="An error occurred while searching. Please try again.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)


# =============================================================================
# Search Results View
# =============================================================================


class SearchResultsView(View):
    """View for displaying search results with selection"""

    def __init__(self, results, query, audio_manager=None, control_panel_view=None):
        super().__init__(timeout=60)
        self.results = results
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view

        # Add select dropdown for results
        self.add_item(
            SearchResultsSelect(results, query, audio_manager, control_panel_view)
        )

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class SearchResultsSelect(Select):
    """Select dropdown for search results"""

    def __init__(self, results, query, audio_manager=None, control_panel_view=None):
        self.results = results
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view

        options = []
        for surah in results[:25]:  # Discord limit is 25 options
            options.append(
                discord.SelectOption(
                    label=f"{surah.emoji} {surah.name_transliteration}",
                    description=f"{surah.name_arabic} • Surah {surah.number} • {surah.verses} verses",
                    value=str(surah.number),
                )
            )

        super().__init__(
            placeholder="Select a surah from the search results...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle surah selection from search results"""
        try:
            selected_surah_number = int(self.values[0])
            surah = get_surah_info(selected_surah_number)

            if not surah:
                log_perfect_tree_section(
                    "Search Selection - Error",
                    [
                        (
                            "search_selection_error",
                            f"Failed to load surah info for number {selected_surah_number}",
                        ),
                    ],
                    "❌",
                )
                embed = discord.Embed(
                    title="❌ Surah Loading Error",
                    description="Error loading surah information.",
                    color=0xFF6B6B,
                )
                embed.set_footer(text="Created by حَـــــنَّـــــا")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Log successful selection
            log_perfect_tree_section(
                "Search Selection - Success",
                [
                    (
                        "search_selection_initiated",
                        f"User: {interaction.user.display_name} selecting from results",
                    ),
                    (
                        "search_selected_number",
                        f"Selected surah number: {selected_surah_number}",
                    ),
                    (
                        "search_selection_success",
                        f"Selected: {surah.name_transliteration} (#{surah.number})",
                    ),
                ],
                "✅",
            )

            # Show confirmation embed with options
            confirmation_view = SurahConfirmationView(
                surah=surah,
                query=self.query,
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view,
            )

            embed = discord.Embed(
                title="✅ Surah Selected!",
                description=f"You selected from your search results for '{self.query}':",
                color=0x2ECC71,
            )

            embed.add_field(
                name=f"{surah.emoji} {surah.name_transliteration}",
                value=f"*{surah.name_arabic}*\n📖 Surah {surah.number} • {surah.verses} verses\n🏛️ {surah.revelation_type.value}",
                inline=False,
            )

            if surah.meaning:
                embed.add_field(name="💫 Meaning", value=surah.meaning, inline=True)

            embed.set_footer(text="Choose an action below:")

            await interaction.response.send_message(
                embed=embed, view=confirmation_view, ephemeral=True
            )

        except Exception as e:
            log_error_with_traceback("Error in search results selection", e)
            embed = discord.Embed(
                title="❌ Selection Error",
                description="An error occurred while selecting the surah.",
                color=0xFF6B6B,
            )
            embed.set_footer(text="Created by حَـــــنَّـــــا")
            await interaction.response.send_message(embed=embed, ephemeral=True)


# =============================================================================
# Surah Confirmation View
# =============================================================================


class SurahConfirmationView(View):
    """View for confirming surah selection with play/search again options"""

    def __init__(self, surah, query, audio_manager=None, control_panel_view=None):
        super().__init__(timeout=60)
        self.surah = surah
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(
        label="🎵 Play This Surah", style=discord.ButtonStyle.primary, row=0
    )
    async def play_surah(self, interaction: discord.Interaction, button: Button):
        """Play the selected surah"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="search_confirm",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description=f"Confirmed search result: {self.surah.name_transliteration}",
                details={
                    "surah_number": self.surah.number,
                    "surah_name": self.surah.name_transliteration,
                    "original_query": self.query,
                    "action": "play",
                },
            )

            # Update last activity in control panel
            if self.control_panel_view:
                self.control_panel_view._update_last_activity(
                    interaction.user,
                    f"searched for '{self.query}' → `{self.surah.name_transliteration}`",
                )

            # Switch to the surah
            if self.audio_manager:
                await self.audio_manager.jump_to_surah(self.surah.number)

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            embed = discord.Embed(
                title="🎵 Now Playing!",
                description="Started playing your selected surah:",
                color=0x00D4AA,
            )

            embed.add_field(
                name=f"{self.surah.emoji} {self.surah.name_transliteration}",
                value=f"`{self.surah.name_arabic}` - {self.surah.verses} verses",
                inline=False,
            )

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            log_error_with_traceback("Error playing surah from confirmation", e)
            await interaction.response.send_message(
                "❌ An error occurred while starting playback.", ephemeral=True
            )

    @discord.ui.button(
        label="🔍 Search Again", style=discord.ButtonStyle.secondary, row=0
    )
    async def search_again(self, interaction: discord.Interaction, button: Button):
        """Open search modal again"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="search_retry",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Requested new search from confirmation",
                details={
                    "rejected_surah": self.surah.name_transliteration,
                    "original_query": self.query,
                },
            )

            modal = SurahSearchModal(
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view,
            )

            await interaction.response.send_modal(modal)

        except Exception as e:
            log_error_with_traceback("Error opening search modal again", e)
            await interaction.response.send_message(
                "❌ An error occurred while opening search.", ephemeral=True
            )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel_selection(self, interaction: discord.Interaction, button: Button):
        """Cancel the selection"""
        try:
            # Log cancellation interaction
            log_perfect_tree_section(
                "Search Selection - Cancelled",
                [
                    (
                        "search_cancel_initiated",
                        f"User: {interaction.user.display_name} cancelling selection",
                    ),
                    (
                        "search_cancel_details",
                        f"Cancelled: '{self.query}' → {self.surah.name_transliteration}",
                    ),
                ],
                "❌",
            )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            embed = discord.Embed(
                title="❌ Selection Cancelled",
                description="Your search selection has been cancelled.",
                color=0xE74C3C,
            )

            embed.set_footer(text="Use the search button again anytime!")

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            log_error_with_traceback("Error cancelling selection", e)
            await interaction.response.defer()


# =============================================================================
# Simple Surah Select
# =============================================================================


class SurahSelect(Select):
    """Simple surah selection dropdown"""

    def __init__(self, bot, page: int = 0):
        self.bot = bot
        self.page = page

        # Calculate total pages
        total_pages = (114 + SURAHS_PER_PAGE - 1) // SURAHS_PER_PAGE

        super().__init__(
            placeholder=f"Select a Surah... ({page + 1}/{total_pages})",
            min_values=1,
            max_values=1,
            custom_id=f"surah_select_{page}",
            row=0,
        )

        self._update_options()

    def _update_options(self):
        """Update select options for current page"""
        try:
            start_idx = self.page * SURAHS_PER_PAGE
            end_idx = min(start_idx + SURAHS_PER_PAGE, 114)

            # Update placeholder text
            total_pages = (114 + SURAHS_PER_PAGE - 1) // SURAHS_PER_PAGE
            self.placeholder = f"Select a Surah... ({self.page + 1}/{total_pages})"

            self.options.clear()

            for i in range(start_idx, end_idx):
                surah_number = i + 1
                surah_info = get_surah_info(surah_number)

                if surah_info:
                    self.options.append(
                        discord.SelectOption(
                            label=f"{surah_info.emoji} {surah_number}. {surah_info.name_transliteration}",
                            description=surah_info.name_arabic,
                            value=str(surah_number),
                        )
                    )

        except Exception as e:
            log_error_with_traceback("Error updating surah options", e)

    async def callback(self, interaction: discord.Interaction):
        """Handle surah selection"""
        try:
            selected_surah = int(self.values[0])

            # Get surah info for logging
            surah_info = get_surah_info(selected_surah)
            surah_name = (
                surah_info.name_transliteration
                if surah_info
                else f"Surah {selected_surah}"
            )

            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="dropdown_surah",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description=f"Selected {surah_name} from dropdown",
                details={
                    "surah_number": selected_surah,
                    "surah_name": surah_name,
                    "page": self.page + 1,
                },
            )

            # Log to enhanced webhook router first, then fallback to discord logger
            try:
                from src.core.di_container import get_container
                container = get_container()
                if container:
                    enhanced_webhook = container.get("enhanced_webhook_router")
                    if enhanced_webhook and hasattr(enhanced_webhook, "log_control_panel_activity"):
                        await enhanced_webhook.log_control_panel_activity(
                            admin_name=interaction.user.display_name,
                            admin_id=interaction.user.id,
                            action="Surah selection",
                            action_details={
                                "surah_number": str(selected_surah),
                                "surah_name": surah_name,
                                "page": str(self.page + 1),
                                "selection_method": "dropdown",
                                "total_pages": str((114 + 9) // 10)  # SURAHS_PER_PAGE = 10
                            },
                            admin_avatar_url=interaction.user.avatar.url if interaction.user.avatar else None
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)
                # Fallback to old discord logger
                discord_logger = get_discord_logger()
                if discord_logger:
                    try:
                        user_avatar_url = (
                            interaction.user.avatar.url
                            if interaction.user.avatar
                            else interaction.user.default_avatar.url
                        )
                        await discord_logger.log_user_interaction(
                            "dropdown_surah",
                            interaction.user.display_name,
                            interaction.user.id,
                            f"selected {surah_name} from the surah dropdown",
                            {
                                "Surah Number": str(selected_surah),
                                "Surah Name": surah_name,
                                "Page": str(self.page + 1),
                                "Action": "Surah Selection",
                            },
                            user_avatar_url,
                        )
                    except:
                        pass

            # Update last activity in parent view
            if hasattr(self.view, "_update_last_activity"):
                self.view._update_last_activity(
                    interaction.user, f"selected `{surah_name}`"
                )

            # Respond to interaction immediately to prevent timeout
            await interaction.response.defer()

            # Get audio manager from parent view
            if hasattr(self.view, "audio_manager") and self.view.audio_manager:
                await self.view.audio_manager.jump_to_surah(selected_surah)

            # Immediately update the panel to show the change
            if hasattr(self.view, "update_panel"):
                try:
                    await self.view.update_panel()
                except Exception as e:
                    log_error_with_traceback(
                        "Error updating panel after surah selection", e
                    )

        except Exception as e:
            log_error_with_traceback("Error in surah selection", e)
            if not interaction.response.is_done():
                await interaction.response.defer()


# =============================================================================
# Simple Reciter Select
# =============================================================================


class ReciterSelect(Select):
    """Simple reciter selection dropdown"""

    def __init__(self, bot):
        self.bot = bot

        super().__init__(
            placeholder="Select a Reciter...",
            min_values=1,
            max_values=1,
            custom_id="reciter_select",
            row=1,
        )

        self._update_options()

    def _update_options(self):
        """Update reciter options"""
        try:
            # Get available reciters from audio folder
            reciters = []
            audio_folder = "audio"

            if os.path.exists(audio_folder):
                for item in os.listdir(audio_folder):
                    folder_path = os.path.join(audio_folder, item)
                    if os.path.isdir(folder_path):
                        reciters.append(item)

            # Arabic names mapping
            arabic_names = {
                "Abdul Basit Abdul Samad": "عبد الباسط عبد الصمد",
                "Maher Al Muaiqly": "ماهر المعيقلي",
                "Muhammad Al Luhaidan": "محمد اللحيدان",
                "Rashid Al Afasy": "راشد العفاسي",
                "Saad Al Ghamdi": "سعد الغامدي",
                "Yasser Al Dosari": "ياسر الدوسري",
            }

            self.options.clear()

            for reciter in sorted(reciters):
                # Clean up reciter name for display
                display_name = reciter.replace("_", " ").title()

                # Get Arabic name
                arabic_name = arabic_names.get(display_name, "")

                # Create label with English name and Arabic as description
                label = f"🎤 {display_name}"
                description = arabic_name if arabic_name else None

                self.options.append(
                    discord.SelectOption(
                        label=label,
                        description=description,
                        value=reciter,
                    )
                )

        except Exception as e:
            log_error_with_traceback("Error updating reciter options", e)

    async def callback(self, interaction: discord.Interaction):
        """Handle reciter selection"""
        try:
            selected_reciter = self.values[0]

            # Clean up reciter name for logging
            reciter_display = selected_reciter.replace("_", " ").title()

            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="dropdown_reciter",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description=f"Selected reciter: {reciter_display}",
                details={
                    "selected_reciter": selected_reciter,
                    "reciter_display": reciter_display,
                    "previous_reciter": getattr(
                        self.view, "current_reciter", "Unknown"
                    ),
                },
            )

            # Log to Discord with user profile picture

            discord_logger = get_discord_logger()
            if discord_logger:
                try:
                    user_avatar_url = (
                        interaction.user.avatar.url
                        if interaction.user.avatar
                        else interaction.user.default_avatar.url
                    )
                    await discord_logger.log_user_interaction(
                        "dropdown_reciter",
                        interaction.user.display_name,
                        interaction.user.id,
                        f"selected reciter: {reciter_display}",
                        {
                            "Selected Reciter": selected_reciter,
                            "Reciter Display": reciter_display,
                            "Previous Reciter": getattr(
                                self.view, "current_reciter", "Unknown"
                            ),
                            "Action": "Reciter Selection",
                        },
                        user_avatar_url,
                    )
                except:
                    pass

            # Update last activity in parent view
            if hasattr(self.view, "_update_last_activity"):
                self.view._update_last_activity(
                    interaction.user, f"switched to `{reciter_display}`"
                )

            # Respond to interaction immediately to prevent timeout
            await interaction.response.defer()

            # Get audio manager from parent view
            if hasattr(self.view, "audio_manager") and self.view.audio_manager:
                await self.view.audio_manager.switch_reciter(selected_reciter)

            # Immediately update the panel to show the change
            if hasattr(self.view, "update_panel"):
                try:
                    await self.view.update_panel()
                except Exception as e:
                    log_error_with_traceback(
                        "Error updating panel after reciter selection", e
                    )

        except Exception as e:
            log_error_with_traceback("Error in reciter selection", e)
            if not interaction.response.is_done():
                await interaction.response.defer()


# =============================================================================
# Simple Control Panel View
# =============================================================================


class SimpleControlPanelView(View):
    """Simple, clean control panel for 24/7 bot"""

    def __init__(self, bot, audio_manager=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.audio_manager = audio_manager
        self.panel_message = None
        self.current_page = 0

        # Last activity tracking
        self.last_activity_user = None
        self.last_activity_time = None
        self.last_activity_action = None

        # Toggle states - will be synced with audio manager
        self.loop_enabled = False
        self.shuffle_enabled = False

        # Add components
        self.add_item(SurahSelect(bot, self.current_page))
        self.add_item(ReciterSelect(bot))

        # Start update task
        self.update_task = None

    def _update_last_activity(self, user: discord.User, action: str):
        """Update last activity tracking"""
        self.last_activity_user = user
        self.last_activity_time = datetime.now(UTC)
        self.last_activity_action = action

    def _format_time_elapsed(self, activity_time: datetime) -> str:
        """Format time elapsed since activity"""
        try:
            now = datetime.now(UTC)
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
                return f"{hours}h {minutes}m ago"
            else:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                return f"{days}d {hours}h ago"
        except (TypeError, ValueError, OverflowError):
            # Handle time calculation errors gracefully
            return "just now"

    def start_updates(self):
        """Start the 2-second update task"""
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """Update the panel with smart intervals based on audio state"""
        while True:
            try:
                # Determine smart update interval based on audio state
                update_interval = self._get_smart_update_interval()

                await asyncio.sleep(update_interval)
                if self.panel_message:
                    await self.update_panel()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in update loop", e)

    def _get_smart_update_interval(self) -> int:
        """Get smart update interval based on current audio state"""
        try:
            if not self.audio_manager:
                return 30  # Fallback when no audio manager

            status = self.audio_manager.get_playback_status()
            if not status:
                return 30  # Fallback when no status

            is_playing = status.get("is_playing", False)
            is_paused = status.get("is_paused", False)
            current_time = status.get("current_time", 0)
            total_time = status.get("total_time", 0)

            # Check if audio is finished (at max progress)
            if (
                total_time > 0 and current_time >= total_time - 1
            ):  # Within 1 second of end
                return 60  # Finished audio: 60 seconds (reduce rate limiting)
            elif is_paused:
                return 20  # Paused audio: 20 seconds
            elif is_playing:
                return 10  # Active playback: 10 seconds
            else:
                return 30  # Fallback: 30 seconds

        except Exception as e:
            log_error_with_traceback("Error calculating smart update interval", e)
            return 30  # Safe fallback

    def _create_panel_embed(self) -> discord.Embed:
        """Create the control panel embed with current status"""
        try:
            # Get current status
            current_surah = 1
            current_reciter = "Unknown"
            time_display = "No time available"

            # Get info from audio manager
            if self.audio_manager:
                status = self.audio_manager.get_playback_status()
                if status:
                    current_surah = status.get("current_surah", 1)
                    current_reciter = status.get("current_reciter", "Unknown")

                    # Get time display
                    current_time = status.get("current_time", 0)
                    total_time = status.get("total_time", 0)

                    if total_time > 0:
                        current_str = self._format_time(current_time)
                        total_str = self._format_time(total_time)
                        time_display = f"{current_str} / {total_str}"

            # Get surah info
            surah_info = get_surah_info(current_surah)
            if not surah_info:
                surah_name = f"Surah {current_surah}"
                surah_arabic = ""
                surah_emoji = "📖"
            else:
                surah_name = surah_info.name_transliteration
                surah_arabic = surah_info.name_arabic
                surah_emoji = surah_info.emoji

            # Create embed
            embed = discord.Embed(
                color=0x00D4AA,
            )

            # Add bot's profile picture as thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            elif self.bot.user:
                # Fallback to default avatar if no custom avatar
                embed.set_thumbnail(url=self.bot.user.default_avatar.url)

            embed.add_field(
                name="",
                value=f"**Surah:** `{surah_name} - {surah_arabic}`",
                inline=True,
            )

            # Get Arabic name for reciter
            reciter_display = current_reciter.replace("_", " ").title()
            arabic_names = {
                "Abdul Basit Abdul Samad": "عبد الباسط عبد الصمد",
                "Maher Al Muaiqly": "ماهر المعيقلي",
                "Muhammad Al Luhaidan": "محمد اللحيدان",
                "Rashid Al Afasy": "راشد العفاسي",
                "Saad Al Ghamdi": "سعد الغامدي",
                "Yasser Al Dosari": "ياسر الدوسري",
            }
            reciter_arabic = arabic_names.get(reciter_display, "")

            if reciter_arabic:
                reciter_text = f"{reciter_display} - {reciter_arabic}"
            else:
                reciter_text = reciter_display

            embed.add_field(
                name="",
                value=f"**Reciter:** `{reciter_text}`",
                inline=True,
            )

            # Clean up time display to remove emoji
            clean_time_display = time_display.replace("🎵 ", "").replace("⏸️ ", "")
            embed.add_field(
                name="", value=f"**Progress:** `{clean_time_display}`", inline=True
            )

            # Add progress bar if we have time information
            if self.audio_manager:
                status = self.audio_manager.get_playback_status()
                if status:
                    current_time = status.get("current_time", 0)
                    total_time = status.get("total_time", 0)

                    if total_time > 0:
                        progress_bar = self._create_progress_bar(
                            current_time, total_time
                        )
                        embed.add_field(
                            name="",
                            value=f"```{progress_bar}```",
                            inline=False,
                        )

            # Add last activity field
            if (
                self.last_activity_user
                and self.last_activity_time
                and self.last_activity_action
            ):
                time_elapsed = self._format_time_elapsed(self.last_activity_time)
                embed.add_field(
                    name="",
                    value=f"**Last Activity:** <@{self.last_activity_user.id}> {self.last_activity_action} • `{time_elapsed}`",
                    inline=False,
                )

            return embed

        except Exception as e:
            log_error_with_traceback("Error creating panel embed", e)
            # Return a basic embed on error
            return discord.Embed(
                description="❌ Error loading panel information",
                color=0xFF6B6B,
            )

    async def update_panel(self):
        """Update the control panel embed with monitoring and alerts"""
        global _control_panel_monitor

        try:
            # Check if message still exists before trying to update it
            if not self.panel_message:
                _control_panel_monitor.record_failure(
                    "no_message", "Panel message is None"
                )
                return

            # Try to fetch the message to see if it still exists
            try:
                await self.panel_message.channel.fetch_message(self.panel_message.id)
            except discord.NotFound:
                # Message was deleted, stop trying to update it
                _control_panel_monitor.record_failure(
                    "message_deleted", "Control panel message was deleted"
                )
                log_perfect_tree_section(
                    "Control Panel - Message Deleted",
                    [
                        (
                            "panel_message_deleted",
                            "Control panel message was deleted, stopping updates",
                        ),
                    ],
                    "🗑️",
                )
                if self.update_task and not self.update_task.done():
                    self.update_task.cancel()
                return
            except discord.HTTPException as e:
                # Other HTTP errors, wait and try again later
                _control_panel_monitor.record_failure(
                    "http_error", f"HTTP {e.status}: {e!s}"
                )
                return

            # Create embed using helper method
            embed = self._create_panel_embed()

            # Update the message with additional error handling
            try:
                await self.panel_message.edit(embed=embed, view=self)
                # Record successful update
                _control_panel_monitor.record_success()

            except discord.NotFound:
                # Message was deleted during our update
                _control_panel_monitor.record_failure(
                    "message_deleted_during_update", "Message deleted during update"
                )
                log_perfect_tree_section(
                    "Control Panel - Message Deleted",
                    [
                        ("status", "⚠️ Panel message was deleted during update"),
                        ("action", "Cancelling update task"),
                        ("result", "Panel update stopped"),
                    ],
                    "🗑️",
                )
                if self.update_task and not self.update_task.done():
                    self.update_task.cancel()
                return
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    retry_after = getattr(e, "retry_after", 60)
                    _control_panel_monitor.record_failure(
                        "rate_limited", f"Rate limited for {retry_after}s"
                    )
                    log_perfect_tree_section(
                        "Control Panel - Rate Limited",
                        [
                            ("status", "⚠️ Update rate limited"),
                            ("http_status", "429"),
                            ("retry_after", f"{retry_after}s"),
                            ("action", "Skipping this update"),
                        ],
                        "⏱️",
                    )

                    # Send Discord notification about control panel rate limiting

                    discord_logger = get_discord_logger()
                    if discord_logger:
                        try:
                            await discord_logger.log_rate_limit(
                                event="control_panel_update",
                                retry_after=retry_after,
                                context={
                                    "Component": "Control Panel",
                                    "Action": "Panel Update",
                                    "Impact": "Skipped update cycle",
                                },
                            )
                        except Exception as log_error:
                            log_error_with_traceback(
                                "Failed to send control panel rate limit notification",
                                log_error,
                            )

                    return
                else:
                    _control_panel_monitor.record_failure(
                        "http_error", f"HTTP {e.status}: {e!s}"
                    )
                    raise

        except Exception as e:
            _control_panel_monitor.record_failure("update_error", str(e))
            log_error_with_traceback("Error updating panel", e)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or H:MM:SS"""
        try:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"  # H:MM:SS (no leading zero for hours)
            else:
                return f"{minutes:02d}:{secs:02d}"  # MM:SS

        except Exception:
            return "00:00"

    def _create_progress_bar(
        self, current_time: float, total_time: float, length: int = 20
    ) -> str:
        """Create a visual progress bar with percentage"""
        try:
            if total_time <= 0:
                return "▱" * length + " 0%"

            # Calculate progress percentage
            progress = min(
                current_time / total_time, 1.0
            )  # Ensure it doesn't exceed 100%
            filled_length = int(length * progress)

            # Create the bar
            filled_bar = "▰" * filled_length
            empty_bar = "▱" * (length - filled_length)
            percentage = int(progress * 100)

            return f"{filled_bar}{empty_bar} {percentage}%"

        except Exception:
            return "▱" * length + " 0%"

    async def update_panel_for_page_change(self, interaction: discord.Interaction):
        """Helper to update the panel after page navigation"""
        try:
            # Update the surah select to new page
            for item in self.children:
                if isinstance(item, SurahSelect):
                    item.page = self.current_page
                    item._update_options()
                    break

            # Update the panel content immediately to show current progress
            embed = self._create_panel_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            log_error_with_traceback("Error updating panel after page change", e)
            await interaction.response.defer()

    @discord.ui.button(label="⬅️ Prev Page", style=discord.ButtonStyle.secondary, row=2)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        """Go to previous page"""
        try:
            if self.current_page > 0:
                old_page = self.current_page
                self.current_page -= 1

                # Log user interaction in dedicated section
                log_user_interaction(
                    interaction_type="button_navigation",
                    user_name=interaction.user.display_name,
                    user_id=interaction.user.id,
                    action_description="Navigated to previous surah page",
                    details={
                        "old_page": old_page + 1,
                        "new_page": self.current_page + 1,
                        "direction": "previous",
                    },
                )

                discord_logger = get_discord_logger()
                if discord_logger:
                    try:
                        user_avatar_url = (
                            interaction.user.avatar.url
                            if interaction.user.avatar
                            else interaction.user.default_avatar.url
                        )
                        await discord_logger.log_user_interaction(
                            "button_navigation",
                            interaction.user.display_name,
                            interaction.user.id,
                            f"navigated to previous surah page (page {self.current_page + 1})",
                            {
                                "Old Page": str(old_page + 1),
                                "New Page": str(self.current_page + 1),
                                "Direction": "Previous",
                                "Action": "Page Navigation",
                            },
                            user_avatar_url,
                        )
                    except:
                        pass

                self._update_last_activity(
                    interaction.user, "switched to previous page"
                )

                await self.update_panel_for_page_change(interaction)
            else:
                await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error in prev page", e)
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Next Page", style=discord.ButtonStyle.secondary, row=2)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Go to next page"""
        try:
            max_pages = (114 + SURAHS_PER_PAGE - 1) // SURAHS_PER_PAGE
            if self.current_page < max_pages - 1:
                old_page = self.current_page
                self.current_page += 1

                # Log user interaction in dedicated section
                log_user_interaction(
                    interaction_type="button_navigation",
                    user_name=interaction.user.display_name,
                    user_id=interaction.user.id,
                    action_description="Navigated to next surah page",
                    details={
                        "old_page": old_page + 1,
                        "new_page": self.current_page + 1,
                        "direction": "next",
                        "max_pages": max_pages,
                    },
                )

                self._update_last_activity(interaction.user, "switched to next page")

                await self.update_panel_for_page_change(interaction)
            else:
                await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error in next page", e)
            await interaction.response.defer()

    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.primary, row=2)
    async def search_surah(self, interaction: discord.Interaction, button: Button):
        """Open search modal for finding surahs"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_search",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Opened surah search modal",
                details={"modal_type": "surah_search"},
            )

            # Log to Discord with user profile picture

            discord_logger = get_discord_logger()
            if discord_logger:
                try:
                    user_avatar_url = (
                        interaction.user.avatar.url
                        if interaction.user.avatar
                        else interaction.user.default_avatar.url
                    )
                    await discord_logger.log_user_interaction(
                        "button_search",
                        interaction.user.display_name,
                        interaction.user.id,
                        "opened the surah search modal",
                        {"Modal Type": "Surah Search", "Action": "Search Modal Opened"},
                        user_avatar_url,
                    )
                except:
                    pass

            self._update_last_activity(interaction.user, "opened search modal")

            search_modal = SurahSearchModal(
                audio_manager=self.audio_manager, control_panel_view=self
            )

            await interaction.response.send_modal(search_modal)

        except Exception as e:
            log_error_with_traceback("Error opening search modal", e)
            await interaction.response.defer()

    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.danger, row=3)
    async def previous_surah(self, interaction: discord.Interaction, button: Button):
        """Go to previous surah"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_skip",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Skipped to previous surah",
                details={
                    "direction": "previous",
                    "audio_manager_available": self.audio_manager is not None,
                },
            )

            self._update_last_activity(interaction.user, "skipped to previous surah")

            # Respond to interaction immediately to prevent timeout
            await interaction.response.defer()

            if self.audio_manager:
                await self.audio_manager.skip_to_previous()

            # The audio manager's skip method now handles panel updates
            # after confirming the audio has actually changed
            # No need for immediate panel update here
        except Exception as e:
            log_error_with_traceback("Error skipping to previous", e)
            if not interaction.response.is_done():
                await interaction.response.defer()

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, row=3)
    async def toggle_shuffle(self, interaction: discord.Interaction, button: Button):
        """Toggle shuffle mode"""
        try:
            # Toggle audio manager's shuffle state
            old_state = self.shuffle_enabled
            if self.audio_manager:
                self.audio_manager.toggle_shuffle()
                self.shuffle_enabled = self.audio_manager.is_shuffle_enabled
            else:
                self.shuffle_enabled = not self.shuffle_enabled

            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_toggle",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description=f"Toggled shuffle mode: {old_state} → {self.shuffle_enabled}",
                details={
                    "feature": "shuffle",
                    "old_state": old_state,
                    "new_state": self.shuffle_enabled,
                    "audio_manager_available": self.audio_manager is not None,
                },
            )

            # Update button style
            button.style = (
                discord.ButtonStyle.success
                if self.shuffle_enabled
                else discord.ButtonStyle.secondary
            )

            # Only show activity message when enabled
            if self.shuffle_enabled:
                self._update_last_activity(interaction.user, "enabled shuffle mode")

            await interaction.response.edit_message(view=self)
        except Exception as e:
            log_error_with_traceback("Error toggling shuffle", e)
            await interaction.response.defer()

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, row=3)
    async def toggle_loop(self, interaction: discord.Interaction, button: Button):
        """Toggle individual surah loop mode (24/7 playback continues regardless)"""
        try:
            # Toggle audio manager's loop state
            old_state = self.loop_enabled
            if self.audio_manager:
                self.audio_manager.toggle_loop()
                self.loop_enabled = self.audio_manager.is_loop_enabled
            else:
                self.loop_enabled = not self.loop_enabled

            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_toggle",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description=f"Toggled individual surah loop: {old_state} → {self.loop_enabled}",
                details={
                    "feature": "individual_surah_loop",
                    "old_state": old_state,
                    "new_state": self.loop_enabled,
                    "behavior": (
                        "Individual surah repeat"
                        if self.loop_enabled
                        else "Normal progression"
                    ),
                    "continuous_playback": "24/7 mode always active",
                    "audio_manager_available": self.audio_manager is not None,
                },
            )

            # Update button style
            button.style = (
                discord.ButtonStyle.success
                if self.loop_enabled
                else discord.ButtonStyle.secondary
            )

            # Only show activity message when enabled (not when disabled since that's default)
            if self.loop_enabled:
                self._update_last_activity(interaction.user, "enabled loop mode")

            await interaction.response.edit_message(view=self)
        except Exception as e:
            log_error_with_traceback("Error toggling loop", e)
            await interaction.response.defer()

    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.success, row=3)
    async def next_surah(self, interaction: discord.Interaction, button: Button):
        """Go to next surah"""
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_skip",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Skipped to next surah",
                details={
                    "direction": "next",
                    "audio_manager_available": self.audio_manager is not None,
                },
            )

            # Log to Discord with user profile picture

            discord_logger = get_discord_logger()
            if discord_logger:
                try:
                    user_avatar_url = (
                        interaction.user.avatar.url
                        if interaction.user.avatar
                        else interaction.user.default_avatar.url
                    )
                    await discord_logger.log_user_interaction(
                        "button_skip",
                        interaction.user.display_name,
                        interaction.user.id,
                        "skipped to the next surah",
                        {
                            "Direction": "Next",
                            "Audio Manager": (
                                "Available" if self.audio_manager else "Not Available"
                            ),
                            "Action": "Skip Next",
                        },
                        user_avatar_url,
                    )
                except:
                    pass

            self._update_last_activity(interaction.user, "skipped to next surah")

            # Respond to interaction immediately to prevent timeout
            await interaction.response.defer()

            if self.audio_manager:
                await self.audio_manager.skip_to_next()

            # The audio manager's skip method now handles panel updates
            # after confirming the audio has actually changed
            # No need for immediate panel update here
        except Exception as e:
            log_error_with_traceback("Error skipping to next", e)
            if not interaction.response.is_done():
                await interaction.response.defer()

    def set_panel_message(self, message: discord.Message):
        """Set the panel message for updates"""
        self.panel_message = message
        self.start_updates()

    def cleanup(self):
        """Clean up the view"""
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            log_perfect_tree_section(
                "Control Panel - Cleanup",
                [
                    ("status", "✅ Update task cancelled"),
                    ("action", "Panel cleanup completed"),
                ],
                "🧹",
            )


# =============================================================================
# Global Control Panel Management
# =============================================================================

# Keep track of active control panels
_active_panels = []


def register_control_panel(panel_view):
    """Register a control panel for cleanup"""
    _active_panels.append(panel_view)


def cleanup_all_control_panels():
    """Clean up all active control panels"""
    try:
        cleaned_count = 0
        for (
            panel
        ) in _active_panels.copy():  # Use copy to avoid modification during iteration
            if panel:
                try:
                    panel.cleanup()
                    cleaned_count += 1
                except Exception as e:
                    log_error_with_traceback("Error cleaning up individual panel", e)

        _active_panels.clear()

        log_perfect_tree_section(
            "Control Panel - Global Cleanup",
            [
                ("panels_cleaned", cleaned_count),
                ("status", "✅ All control panels cleaned up"),
                ("action", "Ready for new panel creation"),
            ],
            "🧹",
        )
    except Exception as e:
        log_error_with_traceback("Error cleaning up control panels", e)
        # Force clear the list even if cleanup failed
        _active_panels.clear()


# =============================================================================
# Control Panel Monitoring
# =============================================================================


class ControlPanelMonitor:
    """Monitor control panel health and send Discord alerts"""

    def __init__(self):
        self.consecutive_failures = 0
        self.last_successful_update = datetime.now(UTC)
        self.last_alert_sent = None
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.failure_threshold = 3  # Alert after 3 consecutive failures
        self.is_panel_healthy = True

    def record_success(self):
        """Record a successful panel update"""
        if self.consecutive_failures > 0:
            # Panel recovered
            self.consecutive_failures = 0
            self.last_successful_update = datetime.now(UTC)
            if not self.is_panel_healthy:
                self.is_panel_healthy = True
                asyncio.create_task(self._send_recovery_alert())
        else:
            self.last_successful_update = datetime.now(UTC)

    def record_failure(self, error_type: str, error_message: str):
        """Record a panel update failure"""
        self.consecutive_failures += 1

        # Send alert if threshold reached and cooldown passed
        if (
            self.consecutive_failures >= self.failure_threshold
            and self.is_panel_healthy
            and self._should_send_alert()
        ):
            self.is_panel_healthy = False
            asyncio.create_task(self._send_failure_alert(error_type, error_message))

    def _should_send_alert(self) -> bool:
        """Check if enough time has passed since last alert"""
        if not self.last_alert_sent:
            return True

        time_since_last = datetime.now(UTC) - self.last_alert_sent
        return time_since_last.total_seconds() >= self.alert_cooldown

    async def _send_failure_alert(self, error_type: str, error_message: str):
        """Send Discord alert for control panel failure"""
        try:
            discord_logger = get_discord_logger()
            if discord_logger:
                self.last_alert_sent = datetime.now(UTC)

                time_since_success = datetime.now(UTC) - self.last_successful_update
                minutes_down = int(time_since_success.total_seconds() / 60)

                await discord_logger.log_critical_error(
                    "Control Panel Failure Detected",
                    None,
                    {
                        "Component": "Control Panel",
                        "Error Type": error_type,
                        "Error Message": error_message[:500],
                        "Consecutive Failures": str(self.consecutive_failures),
                        "Time Since Success": f"{minutes_down} minutes ago",
                        "Impact": "Control panel not updating - user interface affected",
                        "Status": "❌ Control Panel Down",
                        "Action Required": "Check bot connection and restart if needed",
                    },
                )

                log_perfect_tree_section(
                    "Control Panel Monitor - Alert Sent",
                    [
                        ("alert_type", "Control Panel Failure"),
                        ("consecutive_failures", str(self.consecutive_failures)),
                        ("time_since_success", f"{minutes_down}m ago"),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "🚨",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send control panel failure alert", e)

    async def _send_recovery_alert(self):
        """Send Discord alert for control panel recovery"""
        try:
            discord_logger = get_discord_logger()
            if discord_logger:
                await discord_logger.log_success(
                    "Control Panel Recovered",
                    {
                        "Component": "Control Panel",
                        "Status": "✅ Control Panel Restored",
                        "Recovery Time": datetime.now(UTC).strftime("%H:%M:%S UTC"),
                        "Action": "Panel updates resumed successfully",
                    },
                )

                log_perfect_tree_section(
                    "Control Panel Monitor - Recovery",
                    [
                        ("status", "✅ Panel recovered"),
                        (
                            "recovery_time",
                            datetime.now(UTC).strftime("%H:%M:%S"),
                        ),
                        ("discord_alert", "✅ Sent"),
                    ],
                    "✅",
                )
        except Exception as e:
            log_error_with_traceback("Failed to send control panel recovery alert", e)


# Global monitor instance
_control_panel_monitor = ControlPanelMonitor()


# =============================================================================
# Setup Functions
# =============================================================================


async def create_control_panel(
    bot, channel: discord.TextChannel, audio_manager=None
) -> discord.Message | None:
    """Create a simple control panel"""
    try:
        log_perfect_tree_section(
            "Control Panel - Creation Started",
            [
                ("channel", channel.name),
                ("channel_id", str(channel.id)),
                ("audio_manager", "Connected" if audio_manager else "Not available"),
            ],
            "🎛️",
        )

        # Clean up any existing control panels first
        cleanup_all_control_panels()

        # Delete all existing messages in the channel first
        try:
            deleted_count = 0
            failed_deletions = 0

            # Use a more robust approach to delete messages
            async for message in channel.history(limit=100):
                try:
                    await message.delete()
                    deleted_count += 1
                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.1)
                except discord.NotFound:
                    # Message already deleted
                    pass
                except discord.Forbidden:
                    # No permission to delete
                    failed_deletions += 1
                    log_perfect_tree_section(
                        "Control Panel - Delete Permission Error",
                        [
                            ("status", "⚠️ No permission to delete some messages"),
                            ("message_id", str(message.id)),
                            ("action", "Continuing with panel creation"),
                        ],
                        "🚫",
                    )
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        retry_after = getattr(e, "retry_after", 2)
                        log_perfect_tree_section(
                            "Control Panel - Delete Rate Limited",
                            [
                                ("status", "⚠️ Rate limited while deleting messages"),
                                ("retry_after", f"{retry_after}s"),
                                ("action", f"Waiting {retry_after} seconds"),
                            ],
                            "⏱️",
                        )

                        # Send Discord notification about message deletion rate limiting

                        discord_logger = get_discord_logger()
                        if discord_logger:
                            try:
                                await discord_logger.log_rate_limit(
                                    event="control_panel_message_deletion",
                                    retry_after=retry_after,
                                    context={
                                        "Component": "Control Panel",
                                        "Action": "Message Deletion",
                                        "Impact": "Cleanup delayed",
                                    },
                                )
                            except Exception as log_error:
                                log_error_with_traceback(
                                    "Failed to send message deletion rate limit notification",
                                    log_error,
                                )

                        await asyncio.sleep(retry_after)
                        # Try to delete the message again after rate limit
                        try:
                            await message.delete()
                            deleted_count += 1
                        except:
                            failed_deletions += 1
                    else:
                        failed_deletions += 1
                        log_perfect_tree_section(
                            "Control Panel - Delete HTTP Error",
                            [
                                (
                                    "status",
                                    f"⚠️ HTTP {e.status} error deleting message",
                                ),
                                ("message_id", str(message.id)),
                                ("action", "Skipping message"),
                            ],
                            "🚫",
                        )

            if deleted_count > 0:
                log_perfect_tree_section(
                    "Control Panel - Channel Cleared",
                    [
                        ("messages_deleted", deleted_count),
                        ("failed_deletions", failed_deletions),
                        ("status", "✅ Channel cleared successfully"),
                    ],
                    "🧹",
                )
            else:
                log_perfect_tree_section(
                    "Control Panel - Channel Status",
                    [
                        ("messages_deleted", 0),
                        ("failed_deletions", failed_deletions),
                        ("status", "✅ Channel was already empty"),
                    ],
                    "📭",
                )

            # Wait a moment after cleanup to avoid rate limiting
            await asyncio.sleep(2)

        except Exception as e:
            log_error_with_traceback("Error clearing channel", e)

        # Create the view
        view = SimpleControlPanelView(bot, audio_manager)

        # Register for cleanup
        register_control_panel(view)

        # Create initial embed
        embed = discord.Embed(
            description="🔄 Initializing control panel...",
            color=0x00D4AA,
        )

        # Add bot's profile picture as thumbnail
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        elif bot.user:
            # Fallback to default avatar if no custom avatar
            embed.set_thumbnail(url=bot.user.default_avatar.url)

        # Send the message with error handling
        try:
            message = await channel.send(embed=embed, view=view)
            view.set_panel_message(message)

            # Initial update with delay to prevent rate limiting
            await asyncio.sleep(3)
            await view.update_panel()

            log_perfect_tree_section(
                "Control Panel - Creation Complete",
                [
                    ("status", "✅ Simple control panel created"),
                    ("channel", channel.name),
                    ("message_id", str(message.id)),
                    ("view_registered", "Yes"),
                    ("auto_updates", "Enabled (15s interval)"),
                ],
                "🎛️",
            )
            return message

        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = getattr(e, "retry_after", 5)
                log_perfect_tree_section(
                    "Control Panel - Rate Limited on Creation",
                    [
                        ("status", "⚠️ Rate limited while creating panel"),
                        ("retry_after", f"{retry_after}s"),
                        ("action", f"Waiting {retry_after} seconds and retrying"),
                        ("http_status", "429"),
                    ],
                    "⏱️",
                )

                # Send Discord notification about panel creation rate limiting

                discord_logger = get_discord_logger()
                if discord_logger:
                    try:
                        await discord_logger.log_rate_limit(
                            event="control_panel_creation",
                            retry_after=retry_after,
                            context={
                                "Component": "Control Panel",
                                "Action": "Panel Creation",
                                "Impact": "Creation delayed",
                            },
                        )
                    except Exception as log_error:
                        log_error_with_traceback(
                            "Failed to send panel creation rate limit notification",
                            log_error,
                        )

                await asyncio.sleep(retry_after)
                # Try again after rate limit
                message = await channel.send(embed=embed, view=view)
                view.set_panel_message(message)
                await asyncio.sleep(3)
                await view.update_panel()
                return message
            else:
                raise

    except Exception as e:
        log_error_with_traceback("Error creating control panel", e)
        return None


async def setup_control_panel(bot, channel_id: int, audio_manager=None) -> bool:
    """Set up the control panel in specified channel"""
    try:
        log_perfect_tree_section(
            "Control Panel - Setup Started",
            [
                ("channel_id", str(channel_id)),
                ("audio_manager", "Connected" if audio_manager else "Not available"),
                ("action", "Initializing control panel setup"),
            ],
            "🎛️",
        )

        channel = bot.get_channel(channel_id)
        if not channel:
            log_perfect_tree_section(
                "Control Panel - Setup Error",
                [
                    ("channel_id", str(channel_id)),
                    ("status", "❌ Channel not found"),
                    ("result", "Setup failed"),
                ],
                "❌",
            )
            return False

        # Ensure we have proper permissions
        if not channel.permissions_for(channel.guild.me).send_messages:
            log_perfect_tree_section(
                "Control Panel - Permission Error",
                [
                    ("channel", channel.name),
                    ("status", "❌ No permission to send messages"),
                    ("result", "Setup failed"),
                ],
                "🚫",
            )
            return False

        if not channel.permissions_for(channel.guild.me).manage_messages:
            log_perfect_tree_section(
                "Control Panel - Permission Warning",
                [
                    ("channel", channel.name),
                    ("status", "⚠️ No permission to manage messages"),
                    ("impact", "Cannot clean up old messages"),
                    ("action", "Continuing with setup"),
                ],
                "⚠️",
            )

        # Clean up any existing panels before creating new one
        cleanup_all_control_panels()

        message = await create_control_panel(bot, channel, audio_manager)

        if message:
            log_perfect_tree_section(
                "Control Panel - Setup Complete",
                [
                    ("channel", channel.name),
                    ("message_id", str(message.id)),
                    ("status", "✅ Control panel setup successful"),
                    ("result", "Panel is now active"),
                ],
                "✅",
            )
            return True
        else:
            log_perfect_tree_section(
                "Control Panel - Setup Failed",
                [
                    ("channel", channel.name),
                    ("status", "❌ Failed to create control panel"),
                    ("result", "Setup failed"),
                ],
                "❌",
            )
            return False

    except Exception as e:
        log_error_with_traceback("Error setting up control panel", e)
        return False
