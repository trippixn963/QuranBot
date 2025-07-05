# =============================================================================
# QuranBot - Control Panel Module
# =============================================================================
# Discord UI control panel for managing playback, reciters, and Surah selection
# Features persistent view with buttons and select menus for user interaction
# =============================================================================

import asyncio
import os
import traceback
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View

from .rich_presence import RichPresenceManager
from .surah_mapper import get_surah_info, get_surah_name, validate_surah_number
from .tree_log import (
    log_async_error,
    log_error_with_traceback,
    log_section_start,
    log_tree_branch,
    log_tree_final,
    log_warning_with_context,
)

# =============================================================================
# Control Panel Configuration
# =============================================================================

PANEL_UPDATE_INTERVAL = 5  # seconds - more frequent updates for dynamic feel
SURAHS_PER_PAGE = 10
PANEL_TIMEOUT = None  # Persistent view


# =============================================================================
# Utility Functions
# =============================================================================


def is_user_in_voice_channel(interaction: discord.Interaction) -> bool:
    """Check if user is in the correct voice channel"""
    try:
        if not interaction.guild:
            return False

        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return False

        # Check if bot is in a voice channel
        if not interaction.guild.voice_client:
            return True  # Allow if bot not connected yet

        # Check if user is in the same voice channel as bot
        return interaction.user.voice.channel == interaction.guild.voice_client.channel

    except Exception as e:
        log_error_with_traceback("Error checking voice channel access", e)
        return False


def create_response_embed(
    title: str, description: str, color: discord.Color = discord.Color.blue()
) -> discord.Embed:
    """Create a standardized response embed"""
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow(),
    )


# =============================================================================
# Surah Selection Components
# =============================================================================


class SurahSelect(Select):
    """Select menu for choosing Surahs with pagination"""

    def __init__(self, bot, page: int = 0):
        self.bot = bot
        self.page = page

        super().__init__(
            placeholder="🕌 Select a Surah...",
            min_values=1,
            max_values=1,
            custom_id=f"surah_select_{page}",
            row=0,
        )

        self._update_options()

    def _update_options(self):
        """Update select options based on current page"""
        try:
            log_tree_branch("surah_select", f"Updating options for page {self.page}")

            # Get all surah names
            surah_names = []
            for i in range(1, 115):
                surah_info = get_surah_info(i)
                if surah_info:
                    surah_names.append(
                        {
                            "number": i,
                            "name": surah_info.name_english,
                            "arabic": surah_info.name_arabic,
                            "emoji": surah_info.emoji,
                        }
                    )

            if not surah_names:
                log_warning_with_context(
                    "No Surah names available", "Using fallback options"
                )
                self._add_fallback_options()
                return

            # Calculate page boundaries
            start_idx = self.page * SURAHS_PER_PAGE
            end_idx = min(start_idx + SURAHS_PER_PAGE, len(surah_names))

            # Clear existing options
            self.options.clear()

            # Add options for current page - number and name format
            for i in range(start_idx, end_idx):
                surah_data = surah_names[i]
                surah_number = surah_data["number"]
                surah_info = get_surah_info(surah_number)

                if surah_info:
                    # Format option label - number and English name (no emoji in label)
                    label = f"{surah_number}. {surah_info.name_english}"
                    if len(label) > 100:  # Discord limit
                        label = f"{surah_number}. {surah_info.name_english[:80]}..."

                    # Format description - Arabic name only
                    description = surah_info.name_arabic
                    if len(description) > 100:
                        description = description[:97] + "..."

                    self.options.append(
                        discord.SelectOption(
                            label=label,
                            description=description,
                            value=str(surah_number),
                            emoji=surah_info.emoji,
                        )
                    )

            log_tree_final("surah_options", f"Added {len(self.options)} options")

        except Exception as e:
            log_error_with_traceback("Error updating Surah select options", e)
            self._add_fallback_options()

    def _add_fallback_options(self):
        """Add fallback options if dynamic loading fails"""
        self.options.clear()
        fallback_surahs = [
            ("🕋", "Al-Fatiha", "الفاتحة", 1),
            ("🐄", "Al-Baqarah", "البقرة", 2),
            ("👨‍👩‍👧‍👦", "Aal-Imran", "آل عمران", 3),
            ("👩", "An-Nisa", "النساء", 4),
            ("🍽️", "Al-Ma'idah", "المائدة", 5),
        ]

        for emoji, english, arabic, number in fallback_surahs:
            self.options.append(
                discord.SelectOption(
                    label=f"{number:03d}. {english}",
                    value=str(number),
                    description=f"{arabic} • Surah {number}",
                    emoji=emoji,
                )
            )

    async def callback(self, interaction: discord.Interaction):
        """Handle Surah selection"""
        try:
            log_section_start("Surah Selection", "🕌")
            log_tree_branch(
                "user", f"{interaction.user.display_name} ({interaction.user.id})"
            )

            # Check voice channel access
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot to use this control!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get selected Surah number
            selected_surah = int(self.values[0])
            log_tree_branch("selected_surah", f"Surah {selected_surah}")

            # Use AudioManager if available (get from parent view)
            parent_view = self.view
            if hasattr(parent_view, "audio_manager") and parent_view.audio_manager:
                # Use AudioManager to jump to Surah
                await parent_view.audio_manager.jump_to_surah(selected_surah)

                # Track activity in bot
                surah_info = get_surah_info(selected_surah)
                if surah_info:
                    self._track_activity(
                        interaction, f"Switched to {surah_info.name_english}"
                    )

                    # Send confirmation
                    embed = create_response_embed(
                        "✅ Surah Selected",
                        f"Now playing: **{surah_info.emoji} {surah_info.name_english}**\n"
                        f"*{surah_info.name_arabic}*",
                        discord.Color.green(),
                    )
                else:
                    embed = create_response_embed(
                        "✅ Surah Selected",
                        f"Now playing: **Surah {selected_surah}**",
                        discord.Color.green(),
                    )
            else:
                # Fallback to old method
                if hasattr(self.bot, "state_manager"):
                    self.bot.state_manager.set_current_song_index(selected_surah - 1)

                # Track activity in bot
                surah_info = get_surah_info(selected_surah)
                if surah_info:
                    self._track_activity(
                        interaction, f"Switched to {surah_info.name_english}"
                    )

                # Restart playback
                await self._restart_playback(interaction, selected_surah)

                # Send confirmation
                if surah_info:
                    embed = create_response_embed(
                        "✅ Surah Selected",
                        f"Now playing: **{surah_info.emoji} {surah_info.name_english}**\n"
                        f"*{surah_info.name_arabic}*",
                        discord.Color.green(),
                    )
                else:
                    embed = create_response_embed(
                        "✅ Surah Selected",
                        f"Now playing: **Surah {selected_surah}**",
                        discord.Color.green(),
                    )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            log_tree_final("surah_selection", "✅ Completed successfully")

        except Exception as e:
            log_async_error("surah_select_callback", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to select Surah: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    async def _restart_playback(
        self, interaction: discord.Interaction, surah_number: int
    ):
        """Restart playback with selected Surah"""
        try:
            log_tree_branch("playback_restart", "Stopping current playback")

            # Stop current playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = False

            # Wait for current playback to stop
            await asyncio.sleep(2)

            # Find voice client
            voice_client = None
            for guild in self.bot.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    break

            if not voice_client or not voice_client.is_connected():
                log_warning_with_context(
                    "No voice client available", "Playback restart cancelled"
                )
                return

            # Restart playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = True

            if hasattr(self.bot, "play_quran_files"):
                log_tree_branch("playback_restart", "Starting new playback")
                asyncio.create_task(
                    self.bot.play_quran_files(voice_client, voice_client.channel)
                )

            log_tree_final("playback_restart", "✅ Completed")

        except Exception as e:
            log_async_error("restart_playback", e)
            raise

    def _track_activity(self, interaction: discord.Interaction, action: str):
        """Track user activity for display in panel"""
        try:
            import time

            # Store activity in bot
            if not hasattr(self.bot, "last_activity"):
                self.bot.last_activity = {}

            self.bot.last_activity = {
                "action": action,
                "user_id": interaction.user.id,
                "user_name": interaction.user.display_name,
                "timestamp": time.time(),
            }

            log_tree_branch(
                "user_activity", f"{interaction.user.display_name}: {action}"
            )

        except Exception as e:
            log_error_with_traceback("Error tracking user activity", e)


# =============================================================================
# Reciter Selection Components
# =============================================================================


class ReciterSelect(Select):
    """Select menu for choosing reciters"""

    def __init__(self, bot):
        self.bot = bot

        super().__init__(
            placeholder="🎤 Select a Reciter...",
            min_values=1,
            max_values=1,
            custom_id="reciter_select",
            row=1,
        )

        self._update_options()

    def _update_options(self):
        """Update select options with available reciters"""
        try:
            log_tree_branch("reciter_select", "Updating reciter options")

            # Get available reciters
            reciters = self._get_available_reciters()

            # Clear existing options
            self.options.clear()

            # Add reciter options
            for reciter in reciters:
                self.options.append(
                    discord.SelectOption(
                        label=reciter["name"],
                        value=reciter["folder"],
                        description=reciter["description"],
                        emoji="🎤",
                    )
                )

            log_tree_final("reciter_options", f"Added {len(self.options)} reciters")

        except Exception as e:
            log_error_with_traceback("Error updating reciter options", e)
            self._add_fallback_reciters()

    def _get_available_reciters(self) -> List[Dict]:
        """Get list of available reciters"""
        # Default reciters with Arabic names
        return [
            {
                "name": "Saad Al Ghamdi",
                "folder": "Saad_Al_Ghamdi",
                "description": "سعد الغامدي",
            },
            {
                "name": "Maher Al Muaiqly",
                "folder": "Maher_Al_Muaiqly",
                "description": "ماهر المعيقلي",
            },
            {
                "name": "Abdul Basit Abdul Samad",
                "folder": "Abdul_Basit_Abdul_Samad",
                "description": "عبد الباسط عبد الصمد",
            },
            {
                "name": "Mishary Rashid Alafasy",
                "folder": "Mishary_Rashid_Alafasy",
                "description": "مشاري راشد العفاسي",
            },
            {
                "name": "Yasser Al Dosari",
                "folder": "Yasser_Al_Dosari",
                "description": "ياسر الدوسري",
            },
        ]

    def _add_fallback_reciters(self):
        """Add fallback reciters if dynamic loading fails"""
        self.options.clear()
        self.options.append(
            discord.SelectOption(
                label="Saad Al Ghamdi",
                value="Saad_Al_Ghamdi",
                description="سعد الغامدي",
                emoji="🎤",
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle reciter selection"""
        try:
            log_section_start("Reciter Selection", "🎤")
            log_tree_branch(
                "user", f"{interaction.user.display_name} ({interaction.user.id})"
            )

            # Check voice channel access
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot to use this control!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get selected reciter
            selected_reciter = self.values[0]
            log_tree_branch("selected_reciter", selected_reciter)

            # Use AudioManager if available (get from parent view)
            parent_view = self.view
            if hasattr(parent_view, "audio_manager") and parent_view.audio_manager:
                # Get display name for the reciter
                reciter_name = self._get_reciter_display_name(selected_reciter)

                # Use AudioManager to switch reciter
                await parent_view.audio_manager.switch_reciter(reciter_name)

                # Track activity in bot
                self._track_activity(interaction, f"Switched to {reciter_name}")

                # Send confirmation
                embed = create_response_embed(
                    "✅ Reciter Changed",
                    f"Now using reciter: **🎤 {reciter_name}**",
                    discord.Color.green(),
                )
            else:
                # Fallback to old method
                if hasattr(self.bot, "current_reciter"):
                    self.bot.current_reciter = selected_reciter
                    log_tree_branch(
                        "state_updated", f"Reciter set to {selected_reciter}"
                    )

                # Track activity in bot
                reciter_name = self._get_reciter_display_name(selected_reciter)
                self._track_activity(interaction, f"Switched to {reciter_name}")

                # Restart playback with new reciter
                await self._restart_playback(interaction, selected_reciter)

                # Send confirmation
                embed = create_response_embed(
                    "✅ Reciter Changed",
                    f"Now using reciter: **🎤 {reciter_name}**",
                    discord.Color.green(),
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            log_tree_final("reciter_selection", "✅ Completed successfully")

        except Exception as e:
            log_async_error("reciter_select_callback", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to change reciter: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    def _get_reciter_display_name(self, folder_name: str) -> str:
        """Get display name for reciter folder"""
        name_map = {
            "Saad_Al_Ghamdi": "Saad Al Ghamdi",
            "Maher_Al_Muaiqly": "Maher Al Muaiqly",
            "Abdul_Basit_Abdul_Samad": "Abdul Basit Abdul Samad",
            "Mishary_Rashid_Alafasy": "Mishary Rashid Alafasy",
            "Yasser_Al_Dosari": "Yasser Al Dosari",
        }
        return name_map.get(folder_name, folder_name.replace("_", " "))

    async def _restart_playback(
        self, interaction: discord.Interaction, reciter_folder: str
    ):
        """Restart playback with selected reciter"""
        try:
            log_tree_branch("playback_restart", "Stopping current playback")

            # Stop current playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = False

            # Wait for current playback to stop
            await asyncio.sleep(2)

            # Find voice client
            voice_client = None
            for guild in self.bot.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    break

            if not voice_client or not voice_client.is_connected():
                log_warning_with_context(
                    "No voice client available", "Playback restart cancelled"
                )
                return

            # Restart playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = True

            if hasattr(self.bot, "play_quran_files"):
                log_tree_branch("playback_restart", "Starting new playback")
                asyncio.create_task(
                    self.bot.play_quran_files(voice_client, voice_client.channel)
                )

            log_tree_final("playback_restart", "✅ Completed")

        except Exception as e:
            log_async_error("restart_playback", e)
            raise

    def _track_activity(self, interaction: discord.Interaction, action: str):
        """Track user activity for display in panel"""
        try:
            import time

            # Store activity in bot
            if not hasattr(self.bot, "last_activity"):
                self.bot.last_activity = {}

            self.bot.last_activity = {
                "action": action,
                "user_id": interaction.user.id,
                "user_name": interaction.user.display_name,
                "timestamp": time.time(),
            }

            log_tree_branch(
                "user_activity", f"{interaction.user.display_name}: {action}"
            )

        except Exception as e:
            log_error_with_traceback("Error tracking user activity", e)


# =============================================================================
# Search Modal
# =============================================================================


class SurahSearchModal(Modal, title="🔍 Search Surah"):
    """Modal for searching Surahs by name or number"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

        self.search_input = TextInput(
            label="Enter Surah name or number",
            placeholder="e.g., 'Al-Fatiha', 'Fatiha', '1', or '001'",
            min_length=1,
            max_length=50,
            required=True,
        )
        self.add_item(self.search_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission"""
        try:
            log_section_start("Surah Search", "🔍")
            log_tree_branch(
                "user", f"{interaction.user.display_name} ({interaction.user.id})"
            )

            search_term = self.search_input.value.strip()
            log_tree_branch("search_term", search_term)

            # Search for Surah
            found_surah = self._search_surah(search_term)

            if found_surah:
                # Create success embed with action buttons
                embed = create_response_embed(
                    "✅ Surah Found",
                    f"**{found_surah.emoji} {found_surah.name_english}**\n"
                    f"*{found_surah.name_arabic}*\n\n"
                    f"**Number:** {found_surah.number:03d}\n"
                    f"**Verses:** {found_surah.verses}\n"
                    f"**Type:** {found_surah.revelation_type.value}",
                    discord.Color.green(),
                )

                # Create view with action buttons
                view = SurahSearchResultView(self.bot, found_surah.number)

                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )

                log_tree_final("search_result", f"Found Surah {found_surah['number']}")

            else:
                # Create error embed
                embed = create_response_embed(
                    "❌ Surah Not Found",
                    f"No Surah found matching '{search_term}'\n\n"
                    "**Search tips:**\n"
                    "• Use Surah number (1-114)\n"
                    "• Use English name (e.g., 'Al-Fatiha')\n"
                    "• Use partial name (e.g., 'Fatiha')",
                    discord.Color.red(),
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                log_tree_final("search_result", "No match found")

        except Exception as e:
            log_async_error("surah_search_submit", e)
            embed = create_response_embed(
                "❌ Search Error",
                f"An error occurred while searching: {str(e)}",
                discord.Color.red(),
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    def _search_surah(self, search_term: str) -> Optional[Dict]:
        """Search for Surah by name or number"""
        try:
            search_lower = search_term.lower().strip()

            # Try to find by number first
            if search_lower.isdigit():
                surah_number = int(search_lower)
                if validate_surah_number(surah_number):
                    return get_surah_info(surah_number)

            # Search by name
            for i in range(1, 115):
                surah_info = get_surah_info(i)
                if not surah_info:
                    continue

                # Check English name
                english_name = surah_info.name_english.lower()
                if search_lower in english_name or english_name.startswith(
                    search_lower
                ):
                    return surah_info

                # Check transliteration
                transliteration = surah_info.name_transliteration.lower()
                if search_lower in transliteration or transliteration.startswith(
                    search_lower
                ):
                    return surah_info

            return None

        except Exception as e:
            log_error_with_traceback("Error searching Surah", e)
            return None


# =============================================================================
# Search Result View
# =============================================================================


class SurahSearchResultView(View):
    """View for search results with action buttons"""

    def __init__(self, bot, surah_number: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.bot = bot
        self.surah_number = surah_number

    @discord.ui.button(label="🎵 Play This Surah", style=discord.ButtonStyle.success)
    async def play_surah(self, interaction: discord.Interaction, button: Button):
        """Play the selected Surah"""
        try:
            # Check voice channel access
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot to use this control!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Update bot state
            if hasattr(self.bot, "state_manager"):
                self.bot.state_manager.set_current_song_index(self.surah_number - 1)

            # Restart playback
            await self._restart_playback(interaction)

            # Send confirmation
            surah_info = get_surah_info(self.surah_number)
            embed = create_response_embed(
                "✅ Now Playing",
                f"**{surah_info.emoji} {surah_info.name_english}**\n"
                f"*{surah_info.name_arabic}*",
                discord.Color.green(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            log_async_error("play_surah_from_search", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to play Surah: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    async def _restart_playback(self, interaction: discord.Interaction):
        """Restart playback with selected Surah"""
        try:
            # Stop current playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = False

            await asyncio.sleep(2)

            # Find voice client
            voice_client = None
            for guild in self.bot.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    break

            if not voice_client or not voice_client.is_connected():
                return

            # Restart playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = True

            if hasattr(self.bot, "play_quran_files"):
                asyncio.create_task(
                    self.bot.play_quran_files(voice_client, voice_client.channel)
                )

        except Exception as e:
            log_async_error("restart_playback_from_search", e)
            raise


# =============================================================================
# Main Control Panel View
# =============================================================================


class ControlPanelView(View):
    """Main control panel view with all controls"""

    def __init__(self, bot, audio_manager=None):
        super().__init__(timeout=PANEL_TIMEOUT)
        self.bot = bot
        self.audio_manager = audio_manager
        self.current_page = 0
        self.panel_message = None

        # Add select menus
        self.surah_select = SurahSelect(bot, self.current_page)
        self.reciter_select = ReciterSelect(bot)
        self.add_item(self.surah_select)
        self.add_item(self.reciter_select)

        # Start background update task
        self._update_task = asyncio.create_task(self._periodic_update())

    def set_panel_message(self, message: discord.Message):
        """Set reference to panel message for updates"""
        self.panel_message = message

    async def _periodic_update(self):
        """Periodically update panel status"""
        try:
            while True:
                await asyncio.sleep(PANEL_UPDATE_INTERVAL)
                if self.panel_message:
                    await self.update_panel_status()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_async_error("periodic_panel_update", e)

    async def update_panel_status(self):
        """Update panel message with current status and dynamic elements"""
        try:
            if not self.panel_message:
                log_warning_with_context(
                    "No panel message available", "Skipping update"
                )
                return

            log_tree_branch("panel_update", "Updating panel status")

            # Get current state from AudioManager
            if self.audio_manager:
                status = self.audio_manager.get_playback_status()
                current_reciter = status["current_reciter"]
                current_surah = status["current_surah"]
                is_playing = status["is_playing"]
                is_paused = status["is_paused"]
                loop_enabled = status["is_loop_enabled"]
                shuffle_enabled = status["is_shuffle_enabled"]
            else:
                # Fallback to old method if no AudioManager
                current_reciter = getattr(self.bot, "current_reciter", "*Not selected*")
                current_surah = 1
                is_playing = False
                is_paused = False
                loop_enabled = False
                shuffle_enabled = False

            # Get detailed surah info
            surah_display = "*Not playing*"
            surah_emoji = ""
            timer_line = ""

            if current_surah and validate_surah_number(current_surah):
                surah_info = get_surah_info(current_surah)
                if surah_info:
                    surah_display = f"{surah_info.name_english}"
                    surah_emoji = surah_info.emoji

                    # Get progress bar and timer display from Rich Presence
                    if (
                        hasattr(self.bot, "rich_presence")
                        and self.bot.rich_presence
                        and self.bot.rich_presence.is_active()
                    ):
                        try:
                            # Get current track info from Rich Presence
                            track_info = self.bot.rich_presence.get_current_track_info()
                            log_tree_branch(
                                "progress_debug", f"Track info: {track_info}"
                            )

                            if track_info and track_info.get("duration"):
                                current_time = track_info.get("current_time", 0)
                                total_duration = track_info.get("duration", 0)

                                log_tree_branch(
                                    "progress_times",
                                    f"{current_time:.1f}s / {total_duration:.1f}s",
                                )

                                if total_duration > 0:
                                    # Create progress bar for control panel (longer than Rich Presence)
                                    progress_bar = (
                                        self.bot.rich_presence.get_progress_bar(
                                            current_time, total_duration, length=20
                                        )
                                    )
                                    time_display = (
                                        self.bot.rich_presence.format_time(current_time)
                                        + " / "
                                        + self.bot.rich_presence.format_time(
                                            total_duration
                                        )
                                    )
                                    timer_line = f"`{progress_bar}` {time_display}"
                                    log_tree_branch(
                                        "progress_created", f"Timer line: {timer_line}"
                                    )
                        except Exception as e:
                            log_error_with_traceback("Error getting progress bar", e)

            loop_icon = "🔁"
            shuffle_icon = "🔀"

            # Get user attribution for Loop/Shuffle
            loop_display = "OFF"
            shuffle_display = "OFF"

            if loop_enabled:
                loop_user = getattr(self.bot, "loop_enabled_by", None)
                if loop_user:
                    loop_display = f"ON - <@{loop_user}>"
                else:
                    loop_display = "ON"

            if shuffle_enabled:
                shuffle_user = getattr(self.bot, "shuffle_enabled_by", None)
                if shuffle_user:
                    shuffle_display = f"ON - <@{shuffle_user}>"
                else:
                    shuffle_display = "ON"

            # Build the beautiful status block with proper spacing
            status_block = f"• **Now Playing:** {surah_emoji} {surah_display}  \n"
            if timer_line:
                status_block += f"{timer_line}\n"
            status_block += (
                f"\n"
                f"• **Reciter:** 🎤 {current_reciter}  \n"
                f"\n"
                f"• **Loop:** {loop_icon} {loop_display}  \n"
                f"\n"
                f"• **Shuffle:** {shuffle_icon} {shuffle_display}  \n"
            )

            # Add last activity if available
            last_activity_line = self._get_last_activity_display()
            if last_activity_line:
                status_block += f"\n{last_activity_line}"

            # Create embed with green color (bot is always playing)
            embed_color = discord.Color.green()
            embed = discord.Embed(
                title="🕌 QuranBot Control Panel",
                color=embed_color,
                timestamp=discord.utils.utcnow(),
            )

            # Add bot thumbnail
            if self.bot.user and self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            # Add the status as a single field for better formatting
            embed.add_field(name="\u200b", value=status_block, inline=False)

            # Update button styles based on state
            self._update_button_styles(loop_enabled, shuffle_enabled)

            # Update message with error handling
            try:
                await self.panel_message.edit(embed=embed, view=self)
                log_tree_final("panel_update", "✅ Status updated")
            except discord.NotFound:
                log_warning_with_context(
                    "Control panel message not found", "Message may have been deleted"
                )
                # Clear the panel message reference so it gets recreated
                self.panel_message = None
            except discord.HTTPException as e:
                log_error_with_traceback("HTTP error updating control panel", e)

        except Exception as e:
            log_async_error("update_panel_status", e)

    async def _get_timer_display(self, current_surah_name: str) -> str:
        """Get timer display with progress bar using Rich Presence functions"""
        try:
            if not hasattr(self.bot, "get_audio_duration"):
                return ""

            # Get audio file path
            audio_path = None
            if hasattr(self.bot, "current_reciter") and self.bot.current_reciter:
                # Construct path based on your audio structure
                audio_folder = "audio"  # Adjust this to match your structure
                audio_path = (
                    f"{audio_folder}/{self.bot.current_reciter}/{current_surah_name}"
                )

            if not audio_path or not os.path.exists(audio_path):
                return ""

            # Get duration
            total_duration = await self.bot.get_audio_duration(audio_path)
            if not total_duration:
                return ""

            # Get current playback time (if available)
            current_time = 0
            if hasattr(self.bot, "get_current_playback_time"):
                current_time = self.bot.get_current_playback_time()

            # Clamp current time
            current_time = min(current_time, total_duration)

            # Use Rich Presence functions for consistency
            temp_rp_manager = RichPresenceManager(self.bot)
            progress_bar = temp_rp_manager.get_progress_bar(
                current_time, total_duration
            )
            time_display = (
                temp_rp_manager.format_time(current_time)
                + " / "
                + temp_rp_manager.format_time(total_duration)
            )

            return f"`{progress_bar} {time_display}`"

        except Exception as e:
            log_error_with_traceback("Error getting timer display", e)
            return ""

    def _get_last_activity_display(self) -> str:
        """Get last activity display with user tracking"""
        try:
            # Check if bot has activity tracking
            if hasattr(self.bot, "last_activity"):
                activity = self.bot.last_activity
                if activity and "action" in activity:
                    action = activity["action"]
                    user_id = activity.get("user_id")
                    timestamp = activity.get("timestamp")

                    if user_id:
                        user_mention = f"<@{user_id}>"
                        if timestamp:
                            # Format timestamp for Discord
                            import time

                            discord_timestamp = f"<t:{int(timestamp)}:R>"
                            return f"\n**Last Activity:** {action} by {user_mention} {discord_timestamp}"
                        else:
                            return f"\n**Last Activity:** {action} by {user_mention}"

            return ""
        except Exception as e:
            log_error_with_traceback("Error getting last activity", e)
            return ""

    def _update_button_styles(self, loop_enabled: bool, shuffle_enabled: bool):
        """Update button styles based on current state"""
        try:
            # Update loop button style
            for item in self.children:
                if isinstance(item, Button):
                    if "Loop" in item.label:
                        item.style = (
                            discord.ButtonStyle.success
                            if loop_enabled
                            else discord.ButtonStyle.secondary
                        )
                    elif "Shuffle" in item.label:
                        item.style = (
                            discord.ButtonStyle.success
                            if shuffle_enabled
                            else discord.ButtonStyle.secondary
                        )
        except Exception as e:
            log_error_with_traceback("Error updating button styles", e)

    def _track_user_activity(self, interaction: discord.Interaction, action: str):
        """Track user activity for display in panel"""
        try:
            import time

            # Store activity in bot
            if not hasattr(self.bot, "last_activity"):
                self.bot.last_activity = {}

            self.bot.last_activity = {
                "action": action,
                "user_id": interaction.user.id,
                "user_name": interaction.user.display_name,
                "timestamp": time.time(),
            }

            log_tree_branch(
                "user_activity", f"{interaction.user.display_name}: {action}"
            )

        except Exception as e:
            log_error_with_traceback("Error tracking user activity", e)

    def update_surah_select(self):
        """Update Surah select menu with new page"""
        try:
            # Remove old surah select
            for item in self.children[:]:
                if isinstance(item, SurahSelect):
                    self.remove_item(item)

            # Add new surah select with current page
            self.surah_select = SurahSelect(self.bot, self.current_page)
            self.add_item(self.surah_select)

        except Exception as e:
            log_error_with_traceback("Error updating Surah select", e)

    # Navigation buttons
    @discord.ui.button(
        label="◀️ Previous Page", style=discord.ButtonStyle.secondary, row=2
    )
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        """Go to previous page of Surahs"""
        try:
            if self.current_page > 0:
                self.current_page -= 1
                self.update_surah_select()
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.defer()

        except Exception as e:
            log_async_error("prev_page_button", e)
            await interaction.response.defer()

    @discord.ui.button(label="Next Page ▶️", style=discord.ButtonStyle.secondary, row=2)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Go to next page of Surahs"""
        try:
            max_pages = (114 + SURAHS_PER_PAGE - 1) // SURAHS_PER_PAGE
            if self.current_page < max_pages - 1:
                self.current_page += 1
                self.update_surah_select()
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.defer()

        except Exception as e:
            log_async_error("next_page_button", e)
            await interaction.response.defer()

    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.primary, row=2)
    async def search_button(self, interaction: discord.Interaction, button: Button):
        """Open search modal"""
        try:
            modal = SurahSearchModal(self.bot)
            await interaction.response.send_modal(modal)

        except Exception as e:
            log_async_error("search_button", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to open search: {str(e)}", discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # Playback control buttons
    @discord.ui.button(label="⏮️ Previous", style=discord.ButtonStyle.danger, row=3)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        """Play previous Surah"""
        try:
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if self.audio_manager:
                # Use AudioManager to skip to previous
                await self.audio_manager.skip_to_previous()

                # Get the new current surah
                status = self.audio_manager.get_playback_status()
                current_surah = status["current_surah"]

                # Track activity
                self._track_user_activity(interaction, f"Went to Previous Surah")

                # Send confirmation
                surah_info = get_surah_info(current_surah)
                embed = create_response_embed(
                    "✅ Previous Surah",
                    f"Now playing: **{surah_info.emoji} {surah_info.name_english}**",
                    discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Fallback to old method
                current_index = None
                if hasattr(self.bot, "state_manager"):
                    current_index = self.bot.state_manager.get_current_song_index()

                if current_index is None or current_index <= 0:
                    embed = create_response_embed(
                        "⚠️ Cannot Go Back",
                        "Already at the first Surah or no Surah selected!",
                        discord.Color.orange(),
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Update state and restart playback
                new_index = current_index - 1
                if hasattr(self.bot, "state_manager"):
                    self.bot.state_manager.set_current_song_index(new_index)

                # Track activity
                self._track_user_activity(interaction, f"Went to Previous Surah")

                await self._restart_playback()

                # Send confirmation
                surah_info = get_surah_info(new_index + 1)
                embed = create_response_embed(
                    "✅ Previous Surah",
                    f"Now playing: **{surah_info.emoji} {surah_info.name_english}**",
                    discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            log_async_error("previous_button", e)
            embed = create_response_embed(
                "❌ Error",
                f"Failed to go to previous Surah: {str(e)}",
                discord.Color.red(),
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.success, row=3)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        """Play next Surah"""
        try:
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if self.audio_manager:
                # Use AudioManager to skip to next
                await self.audio_manager.skip_to_next()

                # Get the new current surah
                status = self.audio_manager.get_playback_status()
                current_surah = status["current_surah"]

                # Track activity
                self._track_user_activity(interaction, f"Skipped to Next Surah")

                # Send confirmation
                surah_info = get_surah_info(current_surah)
                embed = create_response_embed(
                    "✅ Next Surah",
                    f"Now playing: **{surah_info.emoji} {surah_info.name_english}**",
                    discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Fallback to old method
                current_index = None
                if hasattr(self.bot, "state_manager"):
                    current_index = self.bot.state_manager.get_current_song_index()

                if current_index is None:
                    embed = create_response_embed(
                        "⚠️ No Surah Selected",
                        "Please select a Surah first!",
                        discord.Color.orange(),
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                # Update state and restart playback
                new_index = current_index + 1
                if new_index >= 114:  # Loop back to first Surah
                    new_index = 0

                if hasattr(self.bot, "state_manager"):
                    self.bot.state_manager.set_current_song_index(new_index)

                # Track activity
                self._track_user_activity(interaction, f"Skipped to Next Surah")

                await self._restart_playback()

                # Send confirmation
                surah_info = get_surah_info(new_index + 1)
                embed = create_response_embed(
                    "✅ Next Surah",
                    f"Now playing: **{surah_info.emoji} {surah_info.name_english}**",
                    discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            log_async_error("next_button", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to go to next Surah: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, row=3)
    async def loop_button(self, interaction: discord.Interaction, button: Button):
        """Toggle loop mode"""
        try:
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if self.audio_manager:
                # Use AudioManager to toggle loop
                self.audio_manager.toggle_loop()

                status = self.audio_manager.get_playback_status()
                loop_enabled = status["is_loop_enabled"]

                # Store user attribution for loop
                if loop_enabled:
                    self.bot.loop_enabled_by = interaction.user.id
                else:
                    self.bot.loop_enabled_by = None

                # Track activity
                action = "Enabled Loop" if loop_enabled else "Disabled Loop"
                self._track_user_activity(interaction, action)

                # Update button style
                button.style = (
                    discord.ButtonStyle.success
                    if loop_enabled
                    else discord.ButtonStyle.secondary
                )

                # Update control panel display
                await self.update_panel_status()

                # Send confirmation
                status_text = "enabled" if loop_enabled else "disabled"
                embed = create_response_embed(
                    "✅ Loop Updated", f"Loop mode {status_text}", discord.Color.green()
                )

                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Fallback to old method
                current_loop = getattr(self.bot, "loop_enabled", False)
                self.bot.loop_enabled = not current_loop

                # Store user attribution for loop
                if self.bot.loop_enabled:
                    self.bot.loop_enabled_by = interaction.user.id
                else:
                    self.bot.loop_enabled_by = None

                # Track activity
                action = "Enabled Loop" if self.bot.loop_enabled else "Disabled Loop"
                self._track_user_activity(interaction, action)

                # Update button style
                button.style = (
                    discord.ButtonStyle.success
                    if self.bot.loop_enabled
                    else discord.ButtonStyle.secondary
                )

                # Update control panel display
                await self.update_panel_status()

                # Send confirmation
                status = "enabled" if self.bot.loop_enabled else "disabled"
                embed = create_response_embed(
                    "✅ Loop Updated", f"Loop mode {status}", discord.Color.green()
                )

                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log_async_error("loop_button", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to toggle loop: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, row=3)
    async def shuffle_button(self, interaction: discord.Interaction, button: Button):
        """Toggle shuffle mode"""
        try:
            if not is_user_in_voice_channel(interaction):
                embed = create_response_embed(
                    "🚫 Access Denied",
                    "You must be in the same voice channel as the bot!",
                    discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if self.audio_manager:
                # Use AudioManager to toggle shuffle
                self.audio_manager.toggle_shuffle()

                status = self.audio_manager.get_playback_status()
                shuffle_enabled = status["is_shuffle_enabled"]

                # Store user attribution for shuffle
                if shuffle_enabled:
                    self.bot.shuffle_enabled_by = interaction.user.id
                else:
                    self.bot.shuffle_enabled_by = None

                # Track activity
                action = "Enabled Shuffle" if shuffle_enabled else "Disabled Shuffle"
                self._track_user_activity(interaction, action)

                # Update button style
                button.style = (
                    discord.ButtonStyle.success
                    if shuffle_enabled
                    else discord.ButtonStyle.secondary
                )

                # Update control panel display
                await self.update_panel_status()

                # Send confirmation
                status_text = "enabled" if shuffle_enabled else "disabled"
                embed = create_response_embed(
                    "✅ Shuffle Updated",
                    f"Shuffle mode {status_text}",
                    discord.Color.green(),
                )

                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Fallback to old method
                current_shuffle = getattr(self.bot, "shuffle_enabled", False)
                self.bot.shuffle_enabled = not current_shuffle

                # Store user attribution for shuffle
                if self.bot.shuffle_enabled:
                    self.bot.shuffle_enabled_by = interaction.user.id
                else:
                    self.bot.shuffle_enabled_by = None

                # Track activity
                action = (
                    "Enabled Shuffle"
                    if self.bot.shuffle_enabled
                    else "Disabled Shuffle"
                )
                self._track_user_activity(interaction, action)

                # Update button style
                button.style = (
                    discord.ButtonStyle.success
                    if self.bot.shuffle_enabled
                    else discord.ButtonStyle.secondary
                )

                # Update control panel display
                await self.update_panel_status()

                # Send confirmation
                status = "enabled" if self.bot.shuffle_enabled else "disabled"
                embed = create_response_embed(
                    "✅ Shuffle Updated",
                    f"Shuffle mode {status}",
                    discord.Color.green(),
                )

                await interaction.response.edit_message(view=self)
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            log_async_error("shuffle_button", e)
            embed = create_response_embed(
                "❌ Error", f"Failed to toggle shuffle: {str(e)}", discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    async def _restart_playback(self):
        """Restart playback with current settings"""
        try:
            log_tree_branch("playback_restart", "Stopping current playback")

            # Stop current playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = False

            await asyncio.sleep(2)

            # Find voice client
            voice_client = None
            for guild in self.bot.guilds:
                if guild.voice_client:
                    voice_client = guild.voice_client
                    break

            if not voice_client or not voice_client.is_connected():
                log_warning_with_context(
                    "No voice client available", "Playback restart cancelled"
                )
                return

            # Restart playback
            if hasattr(self.bot, "is_streaming"):
                self.bot.is_streaming = True

            if hasattr(self.bot, "play_quran_files"):
                log_tree_branch("playback_restart", "Starting new playback")
                asyncio.create_task(
                    self.bot.play_quran_files(voice_client, voice_client.channel)
                )

            log_tree_final("playback_restart", "✅ Completed")

        except Exception as e:
            log_async_error("restart_playback", e)
            raise

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, "_update_task") and not self._update_task.done():
                self._update_task.cancel()
        except Exception as e:
            log_error_with_traceback("Error cleaning up control panel", e)


# =============================================================================
# Panel Management Functions
# =============================================================================


async def create_control_panel(
    bot, channel: discord.TextChannel, audio_manager=None
) -> Optional[discord.Message]:
    """Create and send the control panel to specified channel"""
    try:
        log_section_start("Control Panel Creation", "🎛️")
        log_tree_branch("channel", f"{channel.name} ({channel.id})")

        # Create initial embed with beautiful design
        embed = discord.Embed(
            title="🕌 QuranBot Control Panel",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )

        # Add loading status in the same format as the dynamic updates
        loading_status = (
            "• **Now Playing:** *Loading...*  \n"
            "\n"
            "• **Reciter:** 🎤 *Loading...*  \n"
            "\n"
            "• **Status:** ⏸️ *Initializing...*  \n"
            "\n"
            "• **Loop:** 🔁 OFF  \n"
            "\n"
            "• **Shuffle:** 🔀 OFF  \n"
        )
        embed.add_field(name="\u200b", value=loading_status, inline=False)

        # Add bot thumbnail
        if bot.user and bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)

        # Create view with AudioManager
        view = ControlPanelView(bot, audio_manager)

        # Send panel message
        panel_message = await channel.send(embed=embed, view=view)

        # Set message reference
        view.set_panel_message(panel_message)

        # Update with current status
        await view.update_panel_status()

        log_tree_final("panel_created", f"Message ID: {panel_message.id}")
        return panel_message

    except Exception as e:
        log_error_with_traceback("Error creating control panel", e)
        return None


async def setup_control_panel(bot, channel_id: int, audio_manager=None) -> bool:
    """Set up control panel in specified channel"""
    try:
        log_section_start("Control Panel Setup", "⚙️")
        log_tree_branch("channel_id", channel_id)

        # Find channel
        channel = None
        for guild in bot.guilds:
            channel = guild.get_channel(channel_id)
            if channel:
                break

        if not channel:
            log_warning_with_context("Channel not found", f"ID: {channel_id}")
            return False

        # Clear channel
        try:
            deleted_count = 0
            async for message in channel.history(limit=100):
                await message.delete()
                deleted_count += 1

            log_tree_branch("channel_cleared", f"Deleted {deleted_count} messages")
        except Exception as e:
            log_warning_with_context("Could not clear channel", str(e))

        # Create panel with AudioManager
        panel_message = await create_control_panel(bot, channel, audio_manager)

        if panel_message:
            log_tree_final("setup_complete", "✅ Control panel ready")
            return True
        else:
            log_tree_final("setup_failed", "❌ Failed to create panel")
            return False

    except Exception as e:
        log_error_with_traceback("Error setting up control panel", e)
        return False
