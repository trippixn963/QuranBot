# =============================================================================
# QuranBot - Search Results
# =============================================================================
# Search results display components for multiple search results with
# selection dropdown interface.
# =============================================================================

from typing import List, Dict, Any, Optional

import discord
from discord.ui import View, Select

from ..base.components import LoggingMixin
from ...core.logger import TreeLogger


class SearchResultsView(View, LoggingMixin):
    """View for displaying and selecting from multiple search results."""
    
    def __init__(self, results: List[Dict[str, Any]], query: str, 
                 audio_manager=None, control_panel_view=None, **kwargs):
        super().__init__(timeout=60, **kwargs)
        self.results = results
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view
        
        # Add results selection dropdown
        self.add_item(SearchResultsSelect(
            results=results,
            query=query,
            audio_manager=audio_manager,
            control_panel_view=control_panel_view
        ))
    
    async def on_timeout(self):
        """Handle view timeout."""
        for item in self.children:
            item.disabled = True


class SearchResultsSelect(Select, LoggingMixin):
    """Dropdown for selecting from search results."""
    
    def __init__(self, results: List[Dict[str, Any]], query: str,
                 audio_manager=None, control_panel_view=None):
        self.results = results
        self.query = query
        self.audio_manager = audio_manager
        self.control_panel_view = control_panel_view
        
        # Create options from results
        options = []
        for i, result in enumerate(results[:25]):  # Discord limit
            label = f"{result['number']}. {result['name_english']}"
            if len(label) > 100:
                label = label[:97] + "..."
            
            description = f"{result['name_arabic']} • {result['verses']} verses"
            if len(description) > 100:
                description = description[:97] + "..."
            
            options.append(discord.SelectOption(
                label=label,
                description=description,
                value=str(i),
                emoji="📖"
            ))
        
        super().__init__(
            placeholder="Select a surah from the search results...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle result selection."""
        try:
            self.log_interaction(interaction, "search_result_selection")
            
            result_index = int(self.values[0])
            selected_surah = self.results[result_index]
            
            # Import here to avoid circular imports
            from .confirmation import SurahConfirmationView
            
            # Create confirmation dialog
            confirmation_view = SurahConfirmationView(
                surah=selected_surah,
                query=self.query,
                audio_manager=self.audio_manager,
                control_panel_view=self.control_panel_view
            )
            
            embed = discord.Embed(
                title="✅ Surah Selected!",
                description=f"You selected from your search results for '{self.query}':",
                color=0x2ECC71
            )
            
            # Add bot thumbnail
            if interaction.client.user and interaction.client.user.avatar:
                try:
                    embed.set_thumbnail(url=interaction.client.user.avatar.url)
                except:
                    pass
            
            embed.add_field(
                name=f"📖 {selected_surah['name_english']}",
                value=f"*{selected_surah['name_arabic']}*\nSurah {selected_surah['number']} • {selected_surah['verses']} verses",
                inline=False
            )
            
            if selected_surah.get("meaning"):
                embed.add_field(
                    name="💫 Meaning",
                    value=selected_surah["meaning"],
                    inline=True
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
            
            embed.set_footer(
                text="Developed by حَـــــنَّـــــا",
                icon_url=developer_icon_url
            )
            
            await interaction.response.send_message(
                embed=embed, view=confirmation_view, ephemeral=True
            )
            
        except Exception as e:
            self.log_error(e, {
                "selected_value": self.values[0] if self.values else None,
                "user_id": interaction.user.id
            })
            
            embed = discord.Embed(
                title="❌ Selection Error",
                description="An error occurred while selecting the surah.",
                color=0xFF6B6B
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
                text="Developed by حَـــــنَّـــــا",
                icon_url=developer_icon_url
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)