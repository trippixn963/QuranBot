# =============================================================================
# QuranBot - Simple Control Panel
# =============================================================================
# Clean, simple Discord control panel for 24/7 QuranBot
# Updates every 5 seconds with current time display
# =============================================================================

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from discord.ui import Button, Select, View

from .surah_mapper import get_surah_info
from .tree_log import log_error_with_traceback, log_tree_branch, log_tree_final

# =============================================================================
# Configuration
# =============================================================================

SURAHS_PER_PAGE = 10
UPDATE_INTERVAL = 5  # seconds - for time display updates


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
        """Start the 5-second update task"""
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """Update the panel every 5 seconds"""
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

            # Update the message
            if self.panel_message:
                await self.panel_message.edit(embed=embed, view=self)

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
            async for message in channel.history(limit=None):
                try:
                    await message.delete()
                    deleted_count += 1
                except Exception as e:
                    # Skip messages that can't be deleted (too old, no permissions, etc.)
                    pass

            if deleted_count > 0:
                log_tree_branch(
                    "messages_deleted", f"Deleted {deleted_count} existing messages"
                )
            else:
                log_tree_branch("channel_status", "Channel was already empty")
        except Exception as e:
            log_error_with_traceback("Error clearing channel", e)

        # Create the view
        view = SimpleControlPanelView(bot, audio_manager)

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

        # Send the message
        message = await channel.send(embed=embed, view=view)
        view.set_panel_message(message)

        # Initial update
        await view.update_panel()

        log_tree_final("panel_created", "✅ Simple control panel created")
        return message

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
