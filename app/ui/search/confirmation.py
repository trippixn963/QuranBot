# =============================================================================
# QuranBot - Search Confirmation
# =============================================================================
# Confirmation dialog for surah selection with action buttons for play,
# search again, or cancel operations.
# =============================================================================

from typing import Any

import discord
from discord.ui import Button, View

from ...core.logger import TreeLogger
from ..base.components import LoggingMixin, create_developer_footer


class SurahConfirmationView(View, LoggingMixin):
    """
    Confirmation view for surah selection with action buttons.

    Provides final confirmation step in the search-to-play workflow with
    three primary action options: Play, Search Again, or Cancel.
    """

    def __init__(
        self,
        surah: dict[str, Any],
        query: str,
        audio_manager=None,
        control_panel_view=None,
        **kwargs,
    ):
        super().__init__(timeout=60, **kwargs)
        self.surah = surah
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view

    async def on_timeout(self):
        """Handle timeout by disabling all buttons."""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(
        label="🎵 Play This Surah", style=discord.ButtonStyle.primary, row=0
    )
    async def play_surah(self, interaction: discord.Interaction, button: Button):
        """Execute confirmed surah playbook with state management."""
        try:
            self.log_interaction(interaction, "confirm_play_surah")

            await interaction.response.defer(ephemeral=True)

            # Track activity
            if self.control_panel_view and hasattr(
                self.control_panel_view, "_update_last_activity"
            ):
                surah_name = self.surah.get(
                    "name_english", f"Surah {self.surah.get('number', 'Unknown')}"
                )
                self.control_panel_view._update_last_activity(
                    interaction.user, f"searched for '{self.query}' → `{surah_name}`"
                )

            if not self.audio_manager:
                embed = discord.Embed(
                    title="❌ Audio Error",
                    description="Audio manager not available.",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Create developer footer
                footer_text, developer_icon_url = create_developer_footer(
                    interaction.client, interaction.guild
                )

                embed.set_footer(text=footer_text, icon_url=developer_icon_url)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Change to selected surah (handle both dict and object format)
            surah_number = (
                self.surah.get("number")
                if hasattr(self.surah, "get")
                else getattr(self.surah, "number", None)
            )
            if not surah_number:
                embed = discord.Embed(
                    title="❌ Invalid Surah",
                    description="Unable to determine surah number.",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Create developer footer
                footer_text, developer_icon_url = create_developer_footer(
                    interaction.client, interaction.guild
                )

                embed.set_footer(text=footer_text, icon_url=developer_icon_url)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            success = await self.audio_manager.change_surah(surah_number)

            if success:
                # Get surah name (handle both dict and object format)
                surah_name = (
                    self.surah.get("name_english")
                    if hasattr(self.surah, "get")
                    else getattr(self.surah, "name_english", f"Surah {surah_number}")
                )

                embed = discord.Embed(
                    title="✅ Now Playing",
                    description=f"Started playing **{surah_name}**",
                    color=0x2ECC71,
                )

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Create developer footer
                footer_text, developer_icon_url = create_developer_footer(
                    interaction.client, interaction.guild
                )

                embed.set_footer(text=footer_text, icon_url=developer_icon_url)

                TreeLogger.info(
                    "Surah playback started via search",
                    {
                        "user_id": interaction.user.id,
                        "username": interaction.user.display_name,
                        "surah_number": surah_number,
                        "surah_name": surah_name,
                        "search_query": self.query,
                    },
                    service="SearchConfirmation",
                )

                # Update control panel if available
                if self.control_panel_view and hasattr(
                    self.control_panel_view, "update_display"
                ):
                    await self.control_panel_view.update_display()

            else:
                embed = discord.Embed(
                    title="❌ Playback Error",
                    description=f"Could not start playing **{surah_name}**",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Create developer footer
                footer_text, developer_icon_url = create_developer_footer(
                    interaction.client, interaction.guild
                )

                embed.set_footer(text=footer_text, icon_url=developer_icon_url)

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.followup.send(embed=embed, ephemeral=True)
            await interaction.edit_original_response(view=self)

        except Exception as e:
            self.log_error(
                e,
                {
                    "surah_number": self.surah.get("number"),
                    "user_id": interaction.user.id,
                },
            )

            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while starting playback.",
                color=0xFF6B6B,
            )

            # Add bot thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                try:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                except:
                    pass

            # Create developer footer
            footer_text, developer_icon_url = create_developer_footer(
                interaction.client, interaction.guild
            )

            embed.set_footer(text=footer_text, icon_url=developer_icon_url)
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass

    @discord.ui.button(
        label="🔍 Search Again", style=discord.ButtonStyle.secondary, row=0
    )
    async def search_again(self, interaction: discord.Interaction, button: Button):
        """Open search modal again for new query."""
        try:
            self.log_interaction(interaction, "search_again")

            # Track activity
            if self.control_panel_view and hasattr(
                self.control_panel_view, "_update_last_activity"
            ):
                self.control_panel_view._update_last_activity(
                    interaction.user, "opened search modal"
                )

            # Import here to avoid circular imports
            from .modal import SurahSearchModal

            # Create new search modal
            search_modal = SurahSearchModal(
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view,
            )

            await interaction.response.send_modal(search_modal)

            TreeLogger.info(
                "New search initiated",
                {"user_id": interaction.user.id, "previous_query": self.query},
                service="Search",
            )

        except Exception as e:
            self.log_error(e, {"user_id": interaction.user.id})

            embed = discord.Embed(
                title="❌ Error",
                description="Could not open search dialog.",
                color=0xFF6B6B,
            )

            # Add bot thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                try:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                except:
                    pass

            # Create developer footer
            footer_text, developer_icon_url = create_developer_footer(
                interaction.client, interaction.guild
            )

            embed.set_footer(text=footer_text, icon_url=developer_icon_url)
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=0)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        """Cancel the selection process."""
        try:
            self.log_interaction(interaction, "cancel_selection")

            # Track activity - no tracking for cancel to reduce noise

            embed = discord.Embed(
                title="❌ Cancelled",
                description="Surah selection cancelled.",
                color=0x95A5A6,
            )

            # Add bot thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                try:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                except:
                    pass

            # Create developer footer
            footer_text, developer_icon_url = create_developer_footer(
                interaction.client, interaction.guild
            )

            embed.set_footer(text=footer_text, icon_url=developer_icon_url)

            # Disable buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.edit_original_response(view=self)

            TreeLogger.info(
                "Surah selection cancelled",
                {
                    "user_id": interaction.user.id,
                    "cancelled_surah": self.surah.get("number"),
                    "search_query": self.query,
                },
                service="Search",
            )

        except Exception as e:
            self.log_error(e, {"user_id": interaction.user.id})

            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Error cancelling selection.",
                    color=0xFF6B6B,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass
