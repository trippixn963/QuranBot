# =============================================================================
# QuranBot - Search Modal
# =============================================================================
# Interactive modal for Surah search functionality with intelligent search
# capabilities and result handling.
# =============================================================================


import discord
from discord.ui import Modal, TextInput

from ...core.logger import TreeLogger
from ...data.surahs_data import search_surahs
from ..base.components import LoggingMixin, create_developer_footer
from ..base.interaction_logging import InteractionLoggingMixin


class SurahSearchModal(Modal, LoggingMixin, InteractionLoggingMixin):
    """
    Interactive modal for Surah search.

    Provides search input interface with support for multiple search formats:
    - Numeric search (1-114 for direct Surah numbers)
    - English transliterated names (Al-Fatiha, Ya-Sin, An-Nur)
    - Arabic names (الفاتحة, يس, النور)
    - English meanings (Light, Cave, Elephant)
    - Partial matching with fuzzy search capabilities
    """

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
        """Process search submission."""
        try:
            query = self.search_input.value.strip()

            if not query:
                embed = discord.Embed(
                    title="❌ Empty Search Query",
                    description="Please enter a search term!",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Create developer footer
                footer_text, developer_icon_url = create_developer_footer(interaction.client)

                embed.set_footer(
                    text=footer_text, icon_url=developer_icon_url
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Track activity
            if self.control_panel_view and hasattr(
                self.control_panel_view, "_update_last_activity"
            ):
                self.control_panel_view._update_last_activity(
                    interaction.user, f"searched for '{query}'"
                )

            # Execute intelligent search using the proper search service
            results = search_surahs(query)

            TreeLogger.info(
                "Search query processed",
                {
                    "user_id": interaction.user.id,
                    "username": interaction.user.display_name,
                    "query": query,
                    "results_count": len(results),
                },
                service="SearchModal",
            )

            if not results:
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

                # Add bot thumbnail
                if interaction.client.user and interaction.client.user.avatar:
                    try:
                        embed.set_thumbnail(url=interaction.client.user.avatar.url)
                    except:
                        pass

                # Get developer avatar
                from ...config import get_config

                config = get_config()
                developer_icon_url = None
                if config.developer_id:
                    try:
                        developer = interaction.client.get_user(config.developer_id)
                        if developer and developer.avatar:
                            developer_icon_url = developer.avatar.url
                    except:
                        pass

                embed.set_footer(
                    text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Single result optimization - direct confirmation
            if len(results) == 1:
                surah = results[0]

                TreeLogger.info(
                    "Single search result found",
                    {
                        "user_id": interaction.user.id,
                        "query": query,
                        "result": f"{surah['name_english']} (#{surah['number']})",
                    },
                    service="SearchModal",
                )

                # Show confirmation embed
                await self._show_confirmation_embed(interaction, surah, query)
            else:
                # Multiple results - show selection dropdown
                await self._handle_multiple_results(interaction, results, query)

        except Exception as e:
            TreeLogger.error(
                f"Search error: {e}",
                e,
                {
                    "user_id": interaction.user.id,
                    "query": getattr(self.search_input, "value", "unknown"),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                service="SearchModal",
            )

            embed = discord.Embed(
                title="❌ Search Error",
                description="An error occurred while searching. Please try again.",
                color=0xFF6B6B,
            )

            # Add bot thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                try:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                except:
                    pass

            # Get developer avatar
            from ...config import get_config

            config = get_config()
            developer_icon_url = None
            if config.developer_id:
                try:
                    developer = interaction.client.get_user(config.developer_id)
                    if developer and developer.avatar:
                        developer_icon_url = developer.avatar.url
                except:
                    pass

            embed.set_footer(
                text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
            )

            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

    async def _show_confirmation_embed(
        self, interaction: discord.Interaction, surah, query: str
    ):
        """Show confirmation embed with surah details."""
        # Create confirmation view
        from .confirmation import SurahConfirmationView

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

        # Add surah field with emoji and details
        embed.add_field(
            name=f"{surah['emoji']} {surah['name_english']}",
            value=f"*{surah['name_arabic']}*\n📖 Surah {surah['number']} • {surah['verses']} verses",
            inline=False,
        )

        # Add meaning if available (not currently in data)
        if surah.get("meaning"):
            embed.add_field(name="💫 Meaning", value=surah["meaning"], inline=True)

        # Get developer avatar
        from ...config import get_config

        config = get_config()
        developer_icon_url = None
        if config.developer_id:
            try:
                developer = interaction.client.get_user(config.developer_id)
                if developer and developer.avatar:
                    developer_icon_url = developer.avatar.url
            except:
                pass

        embed.set_footer(text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url)

        await interaction.response.send_message(
            embed=embed, view=confirmation_view, ephemeral=True
        )

        TreeLogger.info(
            "Search confirmation sent",
            {
                "user_id": interaction.user.id,
                "surah_number": surah["number"],
                "surah_name": surah["name_english"],
                "query": query,
            },
            service="SearchModal",
        )

    async def _handle_multiple_results(
        self, interaction: discord.Interaction, results: list, query: str
    ):
        """Handle multiple search results with selection."""
        from .results import SearchResultsView

        results_view = SearchResultsView(
            results=results,
            query=query,
            audio_manager=self.audio_manager,
            control_panel_view=self.control_panel_view,
        )

        embed = discord.Embed(
            title=f"🔍 Search Results for '{query}'",
            description=f"Found {len(results)} matching surahs:",
            color=0x3498DB,
        )

        # Add bot thumbnail
        if interaction.client.user and interaction.client.user.avatar:
            try:
                embed.set_thumbnail(url=interaction.client.user.avatar.url)
            except:
                pass

        # Show first few results in embed
        result_text = []
        for i, result in enumerate(results[:5], 1):
            result_text.append(
                f"{i}. **{result['name_english']}** ({result['name_arabic']})"
            )

        embed.add_field(name="📋 Results", value="\n".join(result_text), inline=False)

        if len(results) > 5:
            embed.add_field(
                name="📊 Total Results",
                value=f"Showing 5 of {len(results)} results",
                inline=False,
            )

        # Get developer avatar
        from ...config import get_config

        config = get_config()
        developer_icon_url = None
        if config.developer_id:
            try:
                developer = interaction.client.get_user(config.developer_id)
                if developer and developer.avatar:
                    developer_icon_url = developer.avatar.url
            except:
                pass

        embed.set_footer(text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url)
        await interaction.followup.send(embed=embed, view=results_view, ephemeral=True)
