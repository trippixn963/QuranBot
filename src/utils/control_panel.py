# =============================================================================
# QuranBot - Interactive Control Panel
# =============================================================================
# Discord control panel with buttons, dropdowns, and real-time updates
# Features surah selection, reciter switching, and playback controls
# =============================================================================

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ui import Button, Modal, Select, TextInput, View

from .surah_mapper import get_surah_info, search_surahs
from .tree_log import log_error_with_traceback, log_tree_branch, log_tree_final

# =============================================================================
# Configuration
# =============================================================================

SURAHS_PER_PAGE = 10
UPDATE_INTERVAL = 15  # Increased from 5 to 15 seconds to prevent rate limiting


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
            # Log search initiation with user details
            log_tree_branch(
                "search_initiated",
                f"User: {interaction.user.display_name} ({interaction.user.id})",
            )

            query = self.search_input.value.strip()

            if not query:
                log_tree_branch(
                    "search_empty_query", "User submitted empty search query"
                )
                await interaction.response.send_message(
                    "❌ Please enter a search term!", ephemeral=True
                )
                return

            # Log search query details
            log_tree_branch("search_query", f"'{query}' (length: {len(query)} chars)")

            # Search for surahs
            results = search_surahs(query)

            # Log search results count
            log_tree_branch("search_results_count", f"{len(results)} surah(s) found")

            if results:
                # Log found surahs for debugging (first 3)
                result_names = [
                    f"{s.name_transliteration} ({s.number})" for s in results[:3]
                ]
                if len(results) > 3:
                    result_names.append(f"... and {len(results) - 3} more")
                log_tree_branch("search_results_preview", ", ".join(result_names))

            if not results:
                log_tree_branch(
                    "search_no_results", f"No matches found for query '{query}'"
                )
                await interaction.response.send_message(
                    f"❌ No surahs found for '{query}'. Try searching by:\n"
                    f"• **Number**: 1-114 (e.g., '36')\n"
                    f"• **English name**: 'Light', 'Cave', 'Elephant'\n"
                    f"• **Transliterated name**: 'Al-Fatiha', 'Ya-Sin', 'An-Nur'\n"
                    f"• **Arabic name**: 'الفاتحة', 'يس', 'النور'",
                    ephemeral=True,
                )
                return

                # If only one result, show confirmation
            if len(results) == 1:
                surah = results[0]

                # Log single result found
                log_tree_branch(
                    "search_single_result",
                    f"Exact match: {surah.name_transliteration} (#{surah.number})",
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

                embed.add_field(
                    name=f"{surah.emoji} {surah.name_transliteration}",
                    value=f"*{surah.name_arabic}*\n📖 Surah {surah.number:03d} • {surah.verses} verses\n🏛️ {surah.revelation_type.value}",
                    inline=False,
                )

                if surah.meaning:
                    embed.add_field(name="💫 Meaning", value=surah.meaning, inline=True)

                embed.set_footer(text="Choose an action below:")

                log_tree_branch(
                    "search_confirmation_sent",
                    "Single result confirmation embed sent to user",
                )
                await interaction.response.send_message(
                    embed=embed, view=confirmation_view, ephemeral=True
                )
                return

            # Multiple results - show selection view
            log_tree_branch(
                "search_multiple_results",
                f"Showing selection dropdown for {len(results)} results",
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
                    value=f"*{surah.name_arabic}* • Surah {surah.number:03d} • {surah.verses} verses",
                    inline=False,
                )

            if len(results) > 5:
                embed.add_field(
                    name="",
                    value=f"*... and {len(results) - 5} more results*",
                    inline=False,
                )

            log_tree_branch(
                "search_results_sent",
                f"Multiple results embed sent with {min(5, len(results))} visible results",
            )
            await interaction.response.send_message(
                embed=embed, view=search_results_view, ephemeral=True
            )

        except Exception as e:
            log_error_with_traceback("Error in search modal submission", e)
            await interaction.response.send_message(
                "❌ An error occurred while searching. Please try again.",
                ephemeral=True,
            )


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
                    description=f"{surah.name_arabic} • Surah {surah.number:03d} • {surah.verses} verses",
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
            # Log selection from multiple results
            log_tree_branch(
                "search_selection_initiated",
                f"User: {interaction.user.display_name} selecting from results",
            )

            selected_surah_number = int(self.values[0])
            log_tree_branch(
                "search_selected_number",
                f"Selected surah number: {selected_surah_number}",
            )

            surah = get_surah_info(selected_surah_number)

            if not surah:
                log_tree_branch(
                    "search_selection_error",
                    f"Failed to load surah info for number {selected_surah_number}",
                )
                await interaction.response.send_message(
                    "❌ Error loading surah information.", ephemeral=True
                )
                return

            # Log successful selection
            log_tree_branch(
                "search_selection_success",
                f"Selected: {surah.name_transliteration} (#{surah.number})",
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
                value=f"*{surah.name_arabic}*\n📖 Surah {surah.number:03d} • {surah.verses} verses\n🏛️ {surah.revelation_type.value}",
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
            await interaction.response.send_message(
                "❌ An error occurred while selecting the surah.", ephemeral=True
            )


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
            # Log play button interaction
            log_tree_branch(
                "search_play_initiated",
                f"User: {interaction.user.display_name} playing surah from search",
            )
            log_tree_branch(
                "search_play_surah",
                f"Playing: {self.surah.name_transliteration} (#{self.surah.number})",
            )
            log_tree_branch("search_play_query", f"Original query: '{self.query}'")

            # Update last activity in control panel
            if self.control_panel_view:
                self.control_panel_view._update_last_activity(
                    interaction.user,
                    f"searched for '{self.query}' → {self.surah.name_transliteration}",
                )
                log_tree_branch(
                    "search_activity_updated", "Control panel activity tracking updated"
                )

            # Switch to the surah
            if self.audio_manager:
                log_tree_branch(
                    "search_audio_switching",
                    f"Switching audio to surah {self.surah.number}",
                )
                await self.audio_manager.jump_to_surah(self.surah.number)
                log_tree_branch(
                    "search_audio_switched", "Audio manager switched to selected surah"
                )
            else:
                log_tree_branch(
                    "search_no_audio_manager", "No audio manager available for playback"
                )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            embed = discord.Embed(
                title="🎵 Now Playing!",
                description=f"Started playing your selected surah:",
                color=0x00D4AA,
            )

            embed.add_field(
                name=f"{self.surah.emoji} {self.surah.name_transliteration}",
                value=f"*{self.surah.name_arabic}*\n📖 Surah {self.surah.number:03d} • {self.surah.verses} verses",
                inline=False,
            )

            embed.set_footer(text="Enjoy listening! 🎧")

            log_tree_branch("search_play_confirmed", "Now playing embed sent to user")
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
            # Log search again interaction
            log_tree_branch(
                "search_again_initiated",
                f"User: {interaction.user.display_name} searching again",
            )
            log_tree_branch(
                "search_again_previous",
                f"Previous query: '{self.query}' → {self.surah.name_transliteration}",
            )

            search_modal = SurahSearchModal(
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view,
            )

            log_tree_branch(
                "search_again_modal_opened", "New search modal opened for user"
            )
            await interaction.response.send_modal(search_modal)

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
            log_tree_branch(
                "search_cancel_initiated",
                f"User: {interaction.user.display_name} cancelling selection",
            )
            log_tree_branch(
                "search_cancel_details",
                f"Cancelled: '{self.query}' → {self.surah.name_transliteration}",
            )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            embed = discord.Embed(
                title="❌ Selection Cancelled",
                description="Your search selection has been cancelled.",
                color=0x95A5A6,
            )

            embed.set_footer(text="Use the search button again anytime!")

            log_tree_branch(
                "search_cancel_confirmed", "Selection cancelled embed sent to user"
            )
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
                            label=f"{surah_info.emoji} {surah_number:03d}. {surah_info.name_transliteration}",
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

            # Update last activity in parent view
            if hasattr(self.view, "_update_last_activity"):
                surah_info = get_surah_info(selected_surah)
                surah_name = (
                    surah_info.name_transliteration
                    if surah_info
                    else f"Surah {selected_surah}"
                )
                self.view._update_last_activity(
                    interaction.user, f"selected {surah_name}"
                )

            # Get audio manager from parent view
            if hasattr(self.view, "audio_manager") and self.view.audio_manager:
                await self.view.audio_manager.jump_to_surah(selected_surah)

            await interaction.response.defer()

        except Exception as e:
            log_error_with_traceback("Error in surah selection", e)
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

            # Update last activity in parent view
            if hasattr(self.view, "_update_last_activity"):
                reciter_display = selected_reciter.replace("_", " ").title()
                self.view._update_last_activity(
                    interaction.user, f"switched to {reciter_display}"
                )

            # Get audio manager from parent view
            if hasattr(self.view, "audio_manager") and self.view.audio_manager:
                await self.view.audio_manager.switch_reciter(selected_reciter)

            await interaction.response.defer()

        except Exception as e:
            log_error_with_traceback("Error in reciter selection", e)
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
        self.last_activity_time = datetime.now(timezone.utc)
        self.last_activity_action = action

    def _format_time_elapsed(self, activity_time: datetime) -> str:
        """Format time elapsed since activity"""
        try:
            now = datetime.now(timezone.utc)
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
        except Exception:
            return "just now"

    def start_updates(self):
        """Start the 15-second update task"""
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """Update the panel every 15 seconds"""
        while True:
            try:
                await asyncio.sleep(UPDATE_INTERVAL)
                if self.panel_message:
                    await self.update_panel()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in update loop", e)

    async def update_panel(self):
        """Update the control panel embed"""
        try:
            # Check if message still exists before trying to update it
            if not self.panel_message:
                return

            # Try to fetch the message to see if it still exists
            try:
                await self.panel_message.channel.fetch_message(self.panel_message.id)
            except discord.NotFound:
                # Message was deleted, stop trying to update it
                log_tree_branch(
                    "panel_message_deleted",
                    "Control panel message was deleted, stopping updates",
                )
                if self.update_task and not self.update_task.done():
                    self.update_task.cancel()
                return
            except discord.HTTPException:
                # Other HTTP errors, wait and try again later
                return

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
                value=f"**Surah:** {surah_name} - {surah_arabic}",
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
                value=f"**Reciter:** {reciter_text}",
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
                    value=f"**Last Activity:** <@{self.last_activity_user.id}> {self.last_activity_action} • {time_elapsed}",
                    inline=False,
                )

            # Update the message with additional error handling
            try:
                await self.panel_message.edit(embed=embed, view=self)
            except discord.NotFound:
                # Message was deleted during our update
                log_tree_branch(
                    "panel_message_deleted",
                    "Control panel message was deleted during update",
                )
                if self.update_task and not self.update_task.done():
                    self.update_task.cancel()
                return
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    log_tree_branch(
                        "panel_rate_limited",
                        "Control panel update rate limited, skipping",
                    )
                    return
                else:
                    raise

        except Exception as e:
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

    @discord.ui.button(label="⬅️ Prev Page", style=discord.ButtonStyle.secondary, row=2)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        """Go to previous page"""
        try:
            self._update_last_activity(interaction.user, "switched to previous page")

            if self.current_page > 0:
                self.current_page -= 1
                # Update the surah select to new page
                for item in self.children:
                    if isinstance(item, SurahSelect):
                        item.page = self.current_page
                        item._update_options()
                        break
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error in prev page", e)
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Next Page", style=discord.ButtonStyle.secondary, row=2)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Go to next page"""
        try:
            self._update_last_activity(interaction.user, "switched to next page")

            max_pages = (114 + SURAHS_PER_PAGE - 1) // SURAHS_PER_PAGE
            if self.current_page < max_pages - 1:
                self.current_page += 1
                # Update the surah select to new page
                for item in self.children:
                    if isinstance(item, SurahSelect):
                        item.page = self.current_page
                        item._update_options()
                        break
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error in next page", e)
            await interaction.response.defer()

    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.primary, row=2)
    async def search_surah(self, interaction: discord.Interaction, button: Button):
        """Open search modal for finding surahs"""
        try:
            # Log search button interaction
            log_tree_branch(
                "search_button_clicked",
                f"User: {interaction.user.display_name} ({interaction.user.id})",
            )
            self._update_last_activity(interaction.user, "opened search modal")

            search_modal = SurahSearchModal(
                audio_manager=self.audio_manager, control_panel_view=self
            )

            log_tree_branch("search_modal_opened", "Search modal opened for user")
            await interaction.response.send_modal(search_modal)

        except Exception as e:
            log_error_with_traceback("Error opening search modal", e)
            await interaction.response.defer()

    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.danger, row=3)
    async def previous_surah(self, interaction: discord.Interaction, button: Button):
        """Go to previous surah"""
        try:
            self._update_last_activity(interaction.user, "skipped to previous surah")

            if self.audio_manager:
                await self.audio_manager.skip_to_previous()
            await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error skipping to previous", e)
            await interaction.response.defer()

    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.success, row=3)
    async def next_surah(self, interaction: discord.Interaction, button: Button):
        """Go to next surah"""
        try:
            self._update_last_activity(interaction.user, "skipped to next surah")

            if self.audio_manager:
                await self.audio_manager.skip_to_next()
            await interaction.response.defer()
        except Exception as e:
            log_error_with_traceback("Error skipping to next", e)
            await interaction.response.defer()

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, row=4)
    async def toggle_loop(self, interaction: discord.Interaction, button: Button):
        """Toggle loop mode"""
        try:
            # Toggle audio manager's loop state
            if self.audio_manager:
                self.audio_manager.toggle_loop()
                self.loop_enabled = self.audio_manager.is_loop_enabled
            else:
                self.loop_enabled = not self.loop_enabled

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

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, row=4)
    async def toggle_shuffle(self, interaction: discord.Interaction, button: Button):
        """Toggle shuffle mode"""
        try:
            # Toggle audio manager's shuffle state
            if self.audio_manager:
                self.audio_manager.toggle_shuffle()
                self.shuffle_enabled = self.audio_manager.is_shuffle_enabled
            else:
                self.shuffle_enabled = not self.shuffle_enabled

            # Update button style
            button.style = (
                discord.ButtonStyle.success
                if self.shuffle_enabled
                else discord.ButtonStyle.secondary
            )

            # Only show activity message when enabled (not when disabled since that's default)
            if self.shuffle_enabled:
                self._update_last_activity(interaction.user, "enabled shuffle mode")

            await interaction.response.edit_message(view=self)
        except Exception as e:
            log_error_with_traceback("Error toggling shuffle", e)
            await interaction.response.defer()

    def set_panel_message(self, message: discord.Message):
        """Set the panel message for updates"""
        self.panel_message = message
        self.start_updates()

    def cleanup(self):
        """Clean up the view"""
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            log_tree_branch("panel_cleanup", "Control panel update task cancelled")


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
        for panel in _active_panels:
            if panel:
                panel.cleanup()
        _active_panels.clear()
        log_tree_final("all_panels_cleaned", "All control panels cleaned up")
    except Exception as e:
        log_error_with_traceback("Error cleaning up control panels", e)


# =============================================================================
# Setup Functions
# =============================================================================


async def create_control_panel(
    bot, channel: discord.TextChannel, audio_manager=None
) -> Optional[discord.Message]:
    """Create a simple control panel"""
    try:
        log_tree_branch("creating_panel", f"Channel: {channel.name}")

        # Delete all existing messages in the channel first
        try:
            log_tree_branch("clearing_channel", "Deleting existing messages...")
            deleted_count = 0

            # Use a more robust approach to delete messages
            async for message in channel.history(
                limit=100
            ):  # Limit to prevent excessive API calls
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
                    log_tree_branch(
                        "delete_permission", "No permission to delete some messages"
                    )
                    pass
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        log_tree_branch(
                            "delete_rate_limited",
                            "Rate limited while deleting messages",
                        )
                        await asyncio.sleep(1)
                    else:
                        pass  # Skip other HTTP errors

            if deleted_count > 0:
                log_tree_branch(
                    "messages_deleted", f"Deleted {deleted_count} existing messages"
                )
            else:
                log_tree_branch("channel_status", "Channel was already empty")

            # Wait a moment after cleanup to avoid rate limiting
            await asyncio.sleep(1)

        except Exception as e:
            log_error_with_traceback("Error clearing channel", e)

        # Create the view
        view = SimpleControlPanelView(bot, audio_manager)

        # Register for cleanup
        register_control_panel(view)

        # Create initial embed
        embed = discord.Embed(
            description="Loading...",
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
            await asyncio.sleep(2)
            await view.update_panel()

            log_tree_final("panel_created", "✅ Simple control panel created")
            return message

        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                log_tree_branch(
                    "panel_rate_limited", "Rate limited while creating panel"
                )
                await asyncio.sleep(5)
                # Try again after rate limit
                message = await channel.send(embed=embed, view=view)
                view.set_panel_message(message)
                await asyncio.sleep(2)
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
        channel = bot.get_channel(channel_id)
        if not channel:
            log_tree_branch("setup_error", f"Channel {channel_id} not found")
            return False

        message = await create_control_panel(bot, channel, audio_manager)
        return message is not None

    except Exception as e:
        log_error_with_traceback("Error setting up control panel", e)
        return False
