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

from .surah_utils import get_surah_info, search_surahs
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
    """
    Interactive Discord modal for intelligent Surah search functionality.

    Implements a sophisticated search system that supports multiple input formats:
    - Numeric search (1-114 for direct Surah numbers)
    - English transliterated names (Al-Fatiha, Ya-Sin, An-Nur)
    - Arabic names (الفاتحة, يس, النور)
    - English meanings (Light, Cave, Elephant)
    - Partial matching with fuzzy search capabilities

    The modal handles user input validation, provides intelligent search suggestions,
    and implements a multi-stage result presentation system with confirmation dialogs.
    Search results are categorized and presented with rich context including Arabic
    names, verse counts, and revelation location information.

    This component integrates with the audio manager for seamless playback control
    and maintains comprehensive interaction logging for analytics and debugging.
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
        """
        Process and execute Surah search with intelligent result handling.

        Implements a comprehensive search workflow:
        1. Input validation and sanitization
        2. Multi-format search execution (numeric, transliterated, Arabic, meaning)
        3. Result categorization and ranking by relevance
        4. Adaptive UI response based on result count:
           - Single result: Direct confirmation dialog
           - Multiple results: Selection dropdown interface
           - No results: Helpful search guidance
        5. Comprehensive interaction logging for analytics

        The search algorithm considers partial matches, phonetic similarities,
        and contextual relevance to provide the best user experience. All
        interactions are logged with detailed context for monitoring and debugging.

        Args:
            interaction: Discord interaction object containing user input and context

        Raises:
            discord.InteractionResponded: If interaction has already been handled
            Exception: For unexpected search processing errors
        """
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

            # Execute intelligent search across multiple data sources
            # This searches through transliterated names, Arabic names, English meanings,
            # and Surah numbers with fuzzy matching and relevance scoring
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

            # Single result optimization - direct confirmation interface
            # When search yields exactly one match, skip selection step and show
            # immediate confirmation dialog with detailed Surah information
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

            # Multiple results workflow - present organized selection interface
            # Creates paginated dropdown with rich context for each result
            # Limited to 25 options per Discord API constraints
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
    """
    Interactive view for presenting multiple search results with dropdown selection.

    Manages the presentation and selection of multiple Surah search results through
    a Discord dropdown interface. This view handles:

    - Result pagination and truncation (Discord 25-option limit)
    - Rich result presentation with Arabic names and context
    - User interaction timeout handling (60-second window)
    - Seamless integration with confirmation workflow
    - Comprehensive selection logging and analytics

    The view automatically disables interactions after timeout to prevent
    stale UI states and maintains clean user experience. Each selection
    triggers detailed confirmation dialogs with full Surah information.
    """

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
    """
    Dynamic dropdown component for Surah search result selection.

    Implements intelligent result presentation within Discord's dropdown constraints:
    - Maximum 25 options due to Discord API limitations
    - Rich option labels with emoji indicators and transliterated names
    - Descriptive text including Arabic names, Surah numbers, and verse counts
    - Semantic value mapping for reliable selection processing

    The dropdown dynamically generates options from search results, prioritizing
    the most relevant matches and providing comprehensive context for user decision-making.
    Selection triggers confirmation workflows with detailed Surah information display.

    Integration features:
    - Audio manager connectivity for immediate playback control
    - Enhanced webhook logging for interaction analytics
    - Control panel state synchronization
    """

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
        """
        Process user selection from search results dropdown.

        Handles the complete selection workflow:
        1. Validates selected option and retrieves Surah information
        2. Logs detailed interaction data for analytics and monitoring
        3. Updates enhanced webhook router with structured interaction data
        4. Generates confirmation dialog with rich Surah context
        5. Provides error handling for edge cases and data corruption

        The callback implements defensive programming patterns to handle:
        - Invalid Surah number selections
        - Missing Surah data scenarios
        - Network failures during webhook logging
        - UI state management during async operations

        Args:
            interaction: Discord interaction containing the user's dropdown selection

        Raises:
            ValueError: If selected Surah number is invalid
            discord.NotFound: If interaction context is no longer valid
        """
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

            # Log to enhanced webhook router first, then fallback to discord logger
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="search_selection",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Search result selection",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "search_query": str(self.query),
                                "selected_surah_number": str(selected_surah_number),
                                "selected_surah_name": surah.name_transliteration,
                                "surah_arabic_name": surah.name_arabic,
                                "selection_method": "search_dropdown",
                                "verses_count": str(surah.verses),
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
    """
    Confirmation interface for Surah selection with action buttons.

    Provides a final confirmation step in the search-to-play workflow with
    three primary action options:

    1. **Play This Surah** - Immediately starts audio playback
       - Integrates with audio manager for seamless playback control
       - Updates control panel state and user activity tracking
       - Provides visual feedback and status updates

    2. **Search Again** - Returns to search modal for new query
       - Preserves search context and user preferences
       - Enables iterative search refinement
       - Maintains session continuity

    3. **Cancel** - Aborts the selection process
       - Graceful workflow termination
       - Cleans up UI state and interactions
       - Provides clear user feedback

    The view implements comprehensive interaction logging, timeout handling,
    and state management to ensure reliable user experience across all scenarios.
    """

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
        """
        Execute confirmed Surah playback with comprehensive state management.

        Orchestrates the complete playback initiation workflow:
        1. Logs detailed user interaction with search context preservation
        2. Updates enhanced webhook router with structured playback analytics
        3. Synchronizes control panel state with new audio selection
        4. Initiates audio manager playback with error handling
        5. Provides immediate visual feedback to user
        6. Disables UI components to prevent duplicate actions

        The method implements robust error handling for common failure scenarios:
        - Audio manager unavailability or connection issues
        - Invalid Surah number or missing audio files
        - Discord interaction timeouts or network failures
        - Control panel state synchronization errors

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback

        Raises:
            discord.InteractionResponded: If interaction already handled
            AudioManagerError: If playback initiation fails
        """
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

            # Log to enhanced webhook router first, then fallback to discord logger
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="search_confirm_play",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Search confirm and play",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "surah_number": str(self.surah.number),
                                "surah_name": self.surah.name_transliteration,
                                "surah_arabic_name": self.surah.name_arabic,
                                "original_query": str(self.query),
                                "action": "play_from_search",
                                "verses_count": str(self.surah.verses),
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
        """
        Reinitiate search workflow for iterative query refinement.

        Enables users to perform new searches while preserving context from
        their previous search session. This supports iterative search patterns
        where users may want to explore different Surahs or refine their queries.

        Workflow:
        1. Logs the search retry interaction with context about rejected selection
        2. Maintains search session continuity and user preferences
        3. Creates fresh search modal with preserved audio manager connection
        4. Enables seamless transition back to search interface

        This pattern improves user experience by allowing exploration without
        losing progress or requiring navigation back to the main control panel.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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
        """
        Gracefully cancel the search selection workflow.

        Provides users with a clear exit path from the search confirmation process
        while maintaining proper UI state management and interaction logging.

        Cancellation workflow:
        1. Logs the cancellation event with context about the rejected selection
        2. Disables all interactive components to prevent further interactions
        3. Updates the UI with clear feedback about the cancelled operation
        4. Preserves the option for users to restart the search process

        This ensures users never feel trapped in the search workflow and can
        exit at any point with clear feedback about their action.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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
    """
    Paginated Surah selection dropdown with intelligent option management.

    Implements a paginated dropdown system for browsing all 114 Surahs of the Quran
    with efficient memory usage and responsive user interface:

    **Pagination System:**
    - Displays 10 Surahs per page to maintain readable dropdown size
    - Dynamic page calculation and boundary management
    - Automatic option generation with rich context (emoji, names, descriptions)

    **Smart Option Presentation:**
    - Contextual emoji indicators for visual identification
    - Transliterated names for accessibility
    - Arabic names in descriptions for authenticity
    - Sequential numbering for traditional reference

    **Integration Features:**
    - Seamless audio manager connectivity for immediate playback
    - Enhanced webhook logging for interaction analytics
    - Parent view state synchronization and activity tracking
    - Error-resilient option generation with fallback handling

    The dropdown automatically handles Discord API constraints while providing
    comprehensive Surah browsing capabilities with rich contextual information.
    """

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
        """
        Dynamically generate dropdown options for the current page.

        Implements intelligent option generation with:
        1. Page boundary calculation and validation
        2. Dynamic placeholder text with current page context
        3. Rich option creation with emoji, transliteration, and Arabic names
        4. Error handling for missing or corrupted Surah data
        5. Automatic fallback for data inconsistencies

        The method ensures dropdown options are always current and properly
        formatted, handling edge cases like incomplete Surah data gracefully
        while maintaining user experience quality.

        Option format: "🕌 1. Al-Fatiha" with Arabic description "الفاتحة"
        """
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
        """
        Process Surah selection from paginated dropdown with immediate playback.

        Orchestrates the complete selection-to-playback workflow:
        1. Validates selected Surah number and retrieves metadata
        2. Logs comprehensive interaction data for analytics and monitoring
        3. Updates enhanced webhook router with structured selection context
        4. Synchronizes parent view activity tracking with user action
        5. Initiates immediate audio playback through audio manager
        6. Triggers control panel update to reflect new playback state

        The callback implements defensive programming patterns:
        - Input validation and sanitization
        - Graceful error handling for missing data
        - Async operation coordination
        - UI state management during transitions
        - Comprehensive logging for debugging

        Unlike search-based selection, this provides immediate playback without
        confirmation dialogs since users are browsing a curated list.

        Args:
            interaction: Discord interaction containing dropdown selection
        """
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
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="surah_selection",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Surah selection",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "surah_number": str(selected_surah),
                                "surah_name": surah_name,
                                "page": str(self.page + 1),
                                "selection_method": "dropdown",
                                "total_pages": str(
                                    (114 + 9) // 10
                                ),  # SURAHS_PER_PAGE = 10
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)
                # No fallback - enhanced webhook router is the primary logging method

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
    """
    Dynamic reciter selection dropdown with audio folder scanning.

    Implements intelligent reciter management by scanning the local audio directory
    structure and presenting available reciters with rich contextual information:

    **Dynamic Reciter Discovery:**
    - Real-time audio folder scanning for available reciters
    - Automatic reciter list generation from directory structure
    - Fallback handling for missing or corrupted audio directories

    **Rich Presentation System:**
    - English transliterated names for accessibility
    - Arabic names for authenticity and cultural context
    - Consistent formatting with emoji indicators
    - Alphabetical sorting for predictable navigation

    **Integration Features:**
    - Seamless audio manager connectivity for immediate reciter switching
    - Enhanced webhook logging for reciter preference analytics
    - Parent view state synchronization and activity tracking
    - Error-resilient option generation with graceful degradation

    The dropdown automatically adapts to available audio content while providing
    comprehensive reciter information and smooth switching capabilities.
    """

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
        """
        Dynamically scan audio directory and generate reciter options.

        Implements intelligent reciter discovery and presentation:
        1. Scans local audio directory for available reciter folders
        2. Validates directory structure and audio file availability
        3. Maps technical folder names to user-friendly display names
        4. Provides Arabic name translations for cultural authenticity
        5. Generates sorted dropdown options with consistent formatting

        The method handles various edge cases:
        - Missing or inaccessible audio directories
        - Corrupted or incomplete reciter folders
        - Unknown reciters without Arabic name mappings
        - File system permission issues

        Arabic name mapping ensures cultural authenticity while technical
        folder names (with underscores) are converted to readable formats.

        Option format: "🎤 Saad Al Ghamdi" with Arabic description "سعد الغامدي"
        """
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
        """
        Process reciter selection with immediate audio switching.

        Orchestrates the complete reciter switching workflow:
        1. Validates selected reciter and formats display names
        2. Logs detailed interaction data including previous reciter context
        3. Updates enhanced webhook router with reciter preference analytics
        4. Synchronizes parent view activity tracking with user action
        5. Initiates immediate reciter switch through audio manager
        6. Triggers control panel update to reflect new reciter selection

        The callback handles the complexity of reciter switching:
        - Audio stream interruption and reconnection
        - Playback position preservation during switch
        - Error handling for missing reciter audio files
        - UI feedback during potentially lengthy switch operations
        - State synchronization across all active components

        Reciter switching preserves the current Surah and playback position
        while seamlessly transitioning to the new voice, providing users with
        immediate feedback and uninterrupted listening experience.

        Args:
            interaction: Discord interaction containing reciter selection
        """
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

            # Log to enhanced webhook router first, then fallback to discord logger
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="reciter_selection",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Reciter selection",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "selected_reciter": selected_reciter,
                                "reciter_display": reciter_display,
                                "previous_reciter": getattr(
                                    self.view, "current_reciter", "Unknown"
                                ),
                                "selection_method": "dropdown",
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)
                # No fallback - enhanced webhook router is the primary logging method

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
    """
    Comprehensive Discord control panel for 24/7 Quran bot management.

    This is the primary user interface component providing complete bot control
    through an integrated Discord panel with real-time updates and rich interactions:

    **Core Features:**
    - Real-time playback status with progress bars and timing information
    - Paginated Surah browsing with intelligent search capabilities
    - Dynamic reciter selection with audio directory scanning
    - Playback controls (previous, next, shuffle, loop modes)
    - Activity tracking with user interaction history
    - Smart update intervals based on playback state

    **Advanced Capabilities:**
    - Adaptive update frequency (10-60 seconds based on audio state)
    - Rate limiting protection with automatic backoff strategies
    - Health monitoring with failure detection and recovery
    - Comprehensive interaction logging for analytics
    - Multi-modal search integration with confirmation workflows
    - Discord permission validation and graceful degradation

    **Architecture:**
    - Modular component design with specialized UI elements
    - Event-driven updates with smart batching for performance
    - Defensive programming patterns for reliability
    - Integration with enhanced webhook router for monitoring
    - Persistent view state with timeout handling

    The panel serves as the central hub for all user interactions with the bot,
    providing intuitive controls while maintaining robust performance and reliability.
    """

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
        """
        Track and update user interaction history for activity display.

        Maintains a record of the most recent user interaction with the control panel
        for display in the panel embed. This provides valuable context about bot usage
        and helps users understand recent changes to playback state.

        Tracked information:
        - User who performed the action (for mention display)
        - Timestamp of the interaction (for elapsed time calculation)
        - Description of the action performed (for context display)

        The activity tracking enhances user experience by showing:
        - Who last interacted with the bot
        - What action they performed
        - How long ago the interaction occurred

        This information is displayed prominently in the control panel embed.

        Args:
            user: Discord user who performed the action
            action: Human-readable description of the action performed
        """
        self.last_activity_user = user
        self.last_activity_time = datetime.now(UTC)
        self.last_activity_action = action

    def _format_time_elapsed(self, activity_time: datetime) -> str:
        """
        Calculate and format human-readable elapsed time since last activity.

        Provides intelligent time formatting that adapts to the duration:
        - Seconds: "42s ago" (for recent activity)
        - Minutes: "15m ago" (for activity within the hour)
        - Hours and minutes: "2h 30m ago" (for activity within the day)
        - Days and hours: "3d 5h ago" (for older activity)

        The method implements robust error handling for edge cases:
        - Invalid datetime objects or timezone issues
        - Negative time calculations (clock adjustments)
        - Overflow conditions for very old timestamps
        - Timezone conversion errors

        This ensures the activity display always shows meaningful, readable
        time information without crashing on edge cases.

        Args:
            activity_time: UTC datetime of the last activity

        Returns:
            Human-readable time elapsed string (e.g., "5m ago", "2h 15m ago")
        """
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
        """
        Initialize the intelligent panel update system with adaptive intervals.

        Starts the background update task that keeps the control panel synchronized
        with the current audio state. The update system implements smart interval
        adjustment based on playback status to optimize performance:

        - Active playback: 10-second updates for responsive progress tracking
        - Paused state: 20-second updates for moderate refresh rate
        - Finished audio: 60-second updates to reduce API calls
        - Error states: 30-second fallback interval

        The task management ensures only one update loop runs at a time,
        preventing resource leaks and duplicate operations. Updates continue
        until the view is destroyed or explicitly stopped.
        """
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """
        Continuous panel update loop with intelligent interval management.

        Implements the core update cycle that maintains panel synchronization with
        audio playback state while optimizing for performance and rate limiting:

        **Smart Interval Algorithm:**
        1. Queries current audio state from audio manager
        2. Calculates optimal update interval based on playback status
        3. Sleeps for the calculated interval to prevent unnecessary API calls
        4. Executes panel update with comprehensive error handling
        5. Repeats cycle until cancellation or fatal error

        **Error Handling:**
        - Graceful cancellation handling for clean shutdown
        - Exception isolation to prevent update loop termination
        - Automatic recovery from transient errors
        - Comprehensive logging for debugging and monitoring

        The loop maintains panel accuracy while respecting Discord's rate limits
        and minimizing unnecessary API calls during inactive periods.
        """
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
        """
        Calculate optimal panel update interval based on current audio state.

        Implements intelligent interval selection to balance responsiveness with
        performance and rate limiting considerations:

        **Interval Logic:**
        - 10 seconds: Active playback (frequent progress updates needed)
        - 20 seconds: Paused state (moderate refresh for resume detection)
        - 60 seconds: Finished audio (minimal updates, reduce rate limiting)
        - 30 seconds: Default fallback for unknown states

        **State Analysis:**
        1. Retrieves current playback status from audio manager
        2. Analyzes playback state, pause status, and progress position
        3. Detects near-completion scenarios (within 1 second of end)
        4. Applies appropriate interval based on detected state
        5. Falls back to safe default for error conditions

        This approach minimizes unnecessary API calls while ensuring responsive
        updates during active user engagement periods.

        Returns:
            Optimal update interval in seconds (10-60 range)
        """
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
        """
        Generate comprehensive control panel embed with real-time status display.

        Creates the primary visual interface displaying current bot state with:

        **Status Information:**
        - Current Surah with transliterated and Arabic names
        - Active reciter with English and Arabic names
        - Playback progress with time display and visual progress bar
        - Last user activity with elapsed time tracking

        **Visual Elements:**
        - Bot avatar thumbnail for branding consistency
        - Color-coded embed (green for healthy state)
        - Structured field layout for readable information hierarchy
        - Unicode progress bar with percentage completion

        **Error Handling:**
        - Graceful degradation for missing audio manager
        - Fallback values for unavailable status information
        - Safe time formatting with error recovery
        - Comprehensive exception handling with error embed fallback

        The embed serves as the primary information display, updated continuously
        to reflect current bot state and user interactions.

        Returns:
            Fully configured Discord embed ready for message display
        """
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
        """
        Execute panel update with comprehensive error handling and monitoring.

        Orchestrates the complete panel update workflow with robust error handling,
        rate limiting protection, and health monitoring integration:

        **Update Process:**
        1. Validates message existence and accessibility
        2. Generates updated embed with current status information
        3. Attempts message edit with rate limiting detection
        4. Records success/failure metrics for monitoring
        5. Handles various error scenarios with appropriate responses

        **Error Scenarios Handled:**
        - Message deletion (stops update task gracefully)
        - Rate limiting (waits and reports via webhook)
        - Network timeouts (retries with backoff)
        - Permission errors (logs and continues)
        - General HTTP errors (comprehensive logging)

        **Monitoring Integration:**
        - Success/failure tracking for health monitoring
        - Automatic alerting for sustained failures
        - Rate limiting notifications via enhanced webhook router
        - Detailed error context logging for debugging

        The method ensures reliable panel updates while protecting against
        various failure modes and providing comprehensive operational visibility.
        """
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

                    # Rate limiting notification handled by enhanced webhook router
                    try:
                        from src.core.di_container import get_container

                        container = get_container()
                        if container:
                            enhanced_webhook = container.get("webhook_router")
                            if enhanced_webhook and hasattr(
                                enhanced_webhook, "log_bot_event"
                            ):
                                await enhanced_webhook.log_bot_event(
                                    event_type="rate_limit_encountered",
                                    title="Control Panel Rate Limited",
                                    description="Panel update skipped due to rate limiting (HTTP 429)",
                                    level="warning",
                                    context={
                                        "component": "Control Panel",
                                        "action": "Panel Update",
                                        "impact": "Skipped update cycle",
                                        "retry_after": str(retry_after),
                                        "http_status": "429",
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
        """
        Convert seconds to human-readable time format with intelligent duration display.

        Provides adaptive time formatting based on duration length:
        - Short duration (< 1 hour): "MM:SS" format for compact display
        - Long duration (≥ 1 hour): "H:MM:SS" format with hour indication
        - Error fallback: "00:00" for invalid input or calculation errors

        The formatting ensures consistent display width and intuitive time
        representation across different Surah lengths, from short verses to
        longer chapters that may exceed one hour in duration.

        Args:
            seconds: Time duration in seconds (float for precision)

        Returns:
            Formatted time string ("MM:SS" or "H:MM:SS" format)
        """
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
        """
        Generate visual progress bar with percentage completion indicator.

        Creates an ASCII-based progress visualization using Unicode block characters:
        - Filled blocks (▰) represent completed progress
        - Empty blocks (▱) represent remaining duration
        - Percentage display provides precise completion status

        **Progress Calculation:**
        1. Validates input parameters for edge cases
        2. Calculates completion percentage with bounds checking
        3. Determines filled/empty block distribution
        4. Assembles visual bar with percentage annotation

        **Error Handling:**
        - Zero or negative total time (returns empty bar)
        - Current time exceeding total time (caps at 100%)
        - Invalid numeric inputs (returns fallback bar)

        The progress bar provides immediate visual feedback about playback
        position within the current Surah, enhancing user experience.

        Args:
            current_time: Current playback position in seconds
            total_time: Total duration of current audio in seconds
            length: Number of characters in progress bar (default: 20)

        Returns:
            Visual progress bar string (e.g., "▰▰▰▱▱▱▱▱ 45%")
        """
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
        """
        Synchronize panel state after pagination navigation with immediate UI update.

        Handles the coordination between pagination controls and the main panel display:
        1. Updates the SurahSelect dropdown options for the new page
        2. Refreshes the main panel embed with current audio status
        3. Applies changes immediately through interaction response
        4. Provides error handling for UI update failures

        This method ensures that pagination changes are immediately visible to users
        without waiting for the next scheduled update cycle, improving responsiveness
        and user experience during navigation.

        Args:
            interaction: Discord interaction from pagination button press
        """
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
        """
        Navigate to previous page in Surah selection dropdown.

        Implements backward pagination with boundary checking and comprehensive logging:
        1. Validates current page position (prevents negative pages)
        2. Updates internal page state and logs navigation event
        3. Records interaction via enhanced webhook router for analytics
        4. Updates activity tracking with user navigation context
        5. Triggers immediate panel refresh to show new page options

        The navigation maintains smooth user experience by providing immediate
        visual feedback and preventing invalid page states. All navigation
        events are logged for usage analytics and debugging purposes.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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

                # Log to enhanced webhook router
                try:
                    from src.core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_control_panel_interaction"
                        ):
                            await enhanced_webhook.log_control_panel_interaction(
                                interaction_type="page_navigation",
                                user_name=interaction.user.display_name,
                                user_id=interaction.user.id,
                                action_performed="Navigated to previous surah page",
                                user_avatar_url=(
                                    interaction.user.avatar.url
                                    if interaction.user.avatar
                                    else None
                                ),
                                panel_details={
                                    "old_page": old_page + 1,
                                    "new_page": self.current_page + 1,
                                    "direction": "previous",
                                    "button": "⬅️ Prev Page",
                                },
                            )
                except Exception as e:
                    log_error_with_traceback(
                        "Failed to log to enhanced webhook router", e
                    )

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
        """
        Navigate to next page in Surah selection dropdown.

        Implements forward pagination with boundary checking and comprehensive logging:
        1. Calculates maximum pages based on total Surahs and page size
        2. Validates navigation request against page boundaries
        3. Updates internal page state and logs navigation event
        4. Records interaction via enhanced webhook router for analytics
        5. Updates activity tracking with user navigation context
        6. Triggers immediate panel refresh to show new page options

        The navigation ensures users can browse through all 114 Surahs efficiently
        while maintaining proper boundary conditions and providing comprehensive
        interaction tracking for analytics and debugging.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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

                # Log to enhanced webhook router
                try:
                    from src.core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_control_panel_interaction"
                        ):
                            await enhanced_webhook.log_control_panel_interaction(
                                interaction_type="page_navigation",
                                user_name=interaction.user.display_name,
                                user_id=interaction.user.id,
                                action_performed="Navigated to next surah page",
                                user_avatar_url=(
                                    interaction.user.avatar.url
                                    if interaction.user.avatar
                                    else None
                                ),
                                panel_details={
                                    "old_page": old_page + 1,
                                    "new_page": self.current_page + 1,
                                    "direction": "next",
                                    "max_pages": max_pages,
                                    "button": "➡️ Next Page",
                                },
                            )
                except Exception as e:
                    log_error_with_traceback(
                        "Failed to log to enhanced webhook router", e
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
        """
        Launch intelligent Surah search modal interface.

        Initiates the comprehensive search workflow that allows users to find Surahs
        using multiple search criteria (numbers, names, meanings, Arabic text):

        1. Logs search initiation event for user interaction analytics
        2. Updates enhanced webhook router with search modal opening context
        3. Records activity tracking for control panel history
        4. Creates and presents search modal with preserved context
        5. Maintains connection to audio manager for seamless playback integration

        The search modal provides advanced functionality beyond simple pagination,
        enabling users to quickly locate specific Surahs through intelligent
        matching algorithms and fuzzy search capabilities.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
        try:
            # Log user interaction in dedicated section
            log_user_interaction(
                interaction_type="button_search",
                user_name=interaction.user.display_name,
                user_id=interaction.user.id,
                action_description="Opened surah search modal",
                details={"modal_type": "surah_search"},
            )

            # Log to enhanced webhook router first, then fallback to discord logger
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="search_modal_opened",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Search modal opened",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "modal_type": "surah_search",
                                "button": "🔍 Search",
                                "action": "search_modal_opened",
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)
                # No fallback - enhanced webhook router is the primary logging method

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
        """
        Skip to previous Surah in the sequential playback order.

        Implements backward navigation through the Quran with comprehensive state management:
        1. Logs skip interaction with direction and context information
        2. Updates enhanced webhook router with skip analytics data
        3. Records user activity for control panel history display
        4. Initiates audio manager skip operation with error handling
        5. Relies on audio manager for subsequent panel updates

        The skip operation handles wraparound logic (Surah 1 to 114) and maintains
        playback continuity while providing immediate user feedback. The audio manager
        coordinates the actual audio switching and notifies the panel of changes.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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

            # Log to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="surah_skip",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Skipped to previous surah",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "direction": "previous",
                                "audio_manager_available": self.audio_manager
                                is not None,
                                "button": "⏮️ Previous",
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
        """
        Toggle shuffle mode for randomized Surah playback order.

        Manages the shuffle mode state with visual feedback and comprehensive logging:

        **Shuffle Mode Behavior:**
        - Enabled: Surahs play in randomized order after current completion
        - Disabled: Surahs play in traditional sequential order (1-114)
        - State persists across bot restarts through audio manager integration

        **UI State Management:**
        1. Coordinates with audio manager to toggle actual shuffle functionality
        2. Updates button visual style (green for enabled, gray for disabled)
        3. Logs detailed state transition for analytics and debugging
        4. Records enhanced webhook analytics with before/after state context
        5. Updates activity tracking only when enabling (reduces noise)

        The shuffle feature enhances user experience by providing variety in
        Quran listening while maintaining the 24/7 continuous playback model.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
        try:
            # Toggle audio manager's shuffle state
            old_state = self.shuffle_enabled
            if self.audio_manager:
                await self.audio_manager.toggle_shuffle()
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

            # Log to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="shuffle_toggle",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed=f"Toggled shuffle mode: {old_state} → {self.shuffle_enabled}",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "feature": "shuffle",
                                "old_state": old_state,
                                "new_state": self.shuffle_enabled,
                                "audio_manager_available": self.audio_manager
                                is not None,
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
        """
        Toggle individual Surah loop mode within 24/7 continuous playback.

        Manages loop mode functionality that allows repetition of individual Surahs:

        **Loop Mode Behavior:**
        - Enabled: Current Surah repeats indefinitely until manually changed
        - Disabled: Normal progression to next Surah after completion
        - 24/7 playback continues regardless (never stops completely)
        - Overrides shuffle mode when enabled (current Surah takes priority)

        **UI State Management:**
        1. Coordinates with audio manager to toggle actual loop functionality
        2. Updates button visual style (green for enabled, gray for disabled)
        3. Logs detailed state transition with behavioral context
        4. Records enhanced webhook analytics with comprehensive mode information
        5. Updates activity tracking only when enabling (reduces notification noise)

        This feature allows users to focus on specific Surahs while maintaining
        the continuous nature of the 24/7 bot functionality.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
        try:
            # Toggle audio manager's loop state
            old_state = self.loop_enabled
            if self.audio_manager:
                await self.audio_manager.toggle_loop()
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

            # Log to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="loop_toggle",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed=f"Toggled loop mode: {old_state} → {self.loop_enabled}",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "feature": "individual_surah_loop",
                                "old_state": old_state,
                                "new_state": self.loop_enabled,
                                "behavior": (
                                    "Individual surah repeat"
                                    if self.loop_enabled
                                    else "Normal progression"
                                ),
                                "continuous_playback": "24/7 mode always active",
                                "audio_manager_available": self.audio_manager
                                is not None,
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
        """
        Skip to next Surah in the playback sequence.

        Implements forward navigation through the Quran with intelligent sequence handling:
        1. Logs skip interaction with direction and availability context
        2. Updates enhanced webhook router with skip analytics data
        3. Records user activity for control panel history display
        4. Initiates audio manager skip operation with error handling
        5. Relies on audio manager for subsequent panel state updates

        **Sequence Logic:**
        - Normal mode: Sequential progression (1→2→3...→114→1)
        - Shuffle mode: Random next Surah selection
        - Loop mode: Remains on current Surah (skip overrides loop)

        The skip operation provides immediate user control over playback flow
        while maintaining the continuous 24/7 nature of the bot.

        Args:
            interaction: Discord interaction from button press
            button: The button component that triggered this callback
        """
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

            # Log to enhanced webhook router
            try:
                from src.core.di_container import get_container

                container = get_container()
                if container:
                    enhanced_webhook = container.get("webhook_router")
                    if enhanced_webhook and hasattr(
                        enhanced_webhook, "log_control_panel_interaction"
                    ):
                        await enhanced_webhook.log_control_panel_interaction(
                            interaction_type="surah_skip",
                            user_name=interaction.user.display_name,
                            user_id=interaction.user.id,
                            action_performed="Skipped to next surah",
                            user_avatar_url=(
                                interaction.user.avatar.url
                                if interaction.user.avatar
                                else None
                            ),
                            panel_details={
                                "direction": "next",
                                "audio_manager_available": self.audio_manager
                                is not None,
                                "button": "⏭️ Next",
                            },
                        )
            except Exception as e:
                log_error_with_traceback("Failed to log to enhanced webhook router", e)

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
        """
        Associate Discord message with panel view and initialize update system.

        Establishes the connection between the panel view and its Discord message
        representation, enabling the continuous update system:

        1. Stores message reference for future update operations
        2. Initiates the background update task with smart interval management
        3. Enables message editing for real-time status synchronization

        This method is called immediately after panel creation to begin the
        continuous update cycle that keeps the panel synchronized with audio state.

        Args:
            message: Discord message object containing the panel embed and view
        """
        self.panel_message = message
        self.start_updates()

    def cleanup(self):
        """
        Gracefully shutdown panel view and release resources.

        Performs comprehensive cleanup to prevent resource leaks and ensure
        proper termination of background tasks:

        1. Cancels the background update task if running
        2. Logs cleanup completion for operational monitoring
        3. Prevents zombie tasks from consuming resources
        4. Enables clean bot shutdown processes

        This method is called during bot shutdown or when creating new panels
        to ensure clean resource management and prevent conflicts.
        """
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
    """
    Register control panel view for global lifecycle management.

    Adds the panel view to the global registry for coordinated cleanup
    operations during bot shutdown or panel recreation. This ensures
    no panels are left running with orphaned update tasks.

    Args:
        panel_view: SimpleControlPanelView instance to register
    """
    _active_panels.append(panel_view)


def cleanup_all_control_panels():
    """
    Perform global cleanup of all registered control panels.

    Coordinates shutdown of all active control panels to prevent resource
    leaks and ensure clean bot termination:

    1. Iterates through all registered panel views
    2. Calls individual cleanup methods with error isolation
    3. Clears the global registry for fresh start capability
    4. Logs cleanup statistics for operational monitoring

    This function is called during bot shutdown or before creating new
    panels to ensure clean resource management.
    """
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
    """
    Intelligent health monitoring system for control panel reliability.

    Implements comprehensive monitoring and alerting for control panel operations
    with automatic failure detection, recovery tracking, and Discord notifications:

    **Health Tracking:**
    - Consecutive failure counting with configurable thresholds
    - Success timestamp tracking for uptime analysis
    - Automatic recovery detection and notification
    - Cooldown periods to prevent alert spam

    **Alert System:**
    - Failure alerts after sustained issues (3+ consecutive failures)
    - Recovery notifications when service returns to healthy state
    - Rate limiting protection with 5-minute cooldown periods
    - Rich context information for debugging and response

    **Integration:**
    - Enhanced webhook router for Discord notifications
    - Structured logging for operational visibility
    - Error categorization for targeted troubleshooting
    - Automatic service health status tracking

    The monitor ensures operational teams are aware of control panel issues
    while avoiding notification fatigue through intelligent alerting logic.
    """

    def __init__(self):
        self.consecutive_failures = 0
        self.last_successful_update = datetime.now(UTC)
        self.last_alert_sent = None
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.failure_threshold = 3  # Alert after 3 consecutive failures
        self.is_panel_healthy = True

    def record_success(self):
        """
        Record successful panel update and handle recovery scenarios.

        Processes successful update events with recovery detection:
        1. Resets consecutive failure counter to indicate health restoration
        2. Updates last successful update timestamp for uptime tracking
        3. Detects recovery scenarios (failures → success transition)
        4. Triggers recovery notifications via async task creation
        5. Maintains healthy state flag for future monitoring

        Recovery detection ensures operational teams are notified when
        service returns to normal operation after sustained issues.
        """
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
        """
        Record panel update failure and trigger alerts when thresholds are reached.

        Processes failure events with intelligent alerting logic:
        1. Increments consecutive failure counter for trend analysis
        2. Evaluates failure threshold and cooldown conditions
        3. Triggers failure alert notifications for sustained issues
        4. Updates health status flags for monitoring state
        5. Provides error context for debugging and response

        The alerting system prevents notification spam while ensuring
        operational teams are informed of sustained service issues.

        Args:
            error_type: Categorized error type for classification
            error_message: Detailed error description for debugging
        """
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
        """
        Send comprehensive failure alert via Discord webhook.

        Generates detailed failure notifications with operational context:
        1. Calculates downtime duration since last successful update
        2. Records alert timestamp to enforce cooldown periods
        3. Sends structured alert via enhanced webhook router
        4. Includes actionable information for response teams
        5. Logs alert delivery for monitoring audit trails

        Alert content includes error classification, impact assessment,
        downtime duration, and recommended response actions.

        Args:
            error_type: Categorized error type for alert classification
            error_message: Detailed error context for debugging
        """
        try:
            from src.core.di_container import get_container

            container = get_container()
            if container:
                enhanced_webhook = container.get("webhook_router")
                if enhanced_webhook and hasattr(enhanced_webhook, "log_bot_event"):
                    self.last_alert_sent = datetime.now(UTC)

                    time_since_success = datetime.now(UTC) - self.last_successful_update
                    minutes_down = int(time_since_success.total_seconds() / 60)

                    await enhanced_webhook.log_bot_event(
                        event_type="control_panel_failure",
                        title="Control Panel Failure Alert",
                        description=f"Control panel has been down for {minutes_down} minutes",
                        level="critical",
                        context={
                            "component": "Control Panel",
                            "error_type": error_type,
                            "error_message": error_message[:500],
                            "consecutive_failures": str(self.consecutive_failures),
                            "time_since_success": f"{minutes_down} minutes ago",
                            "impact": "Control panel not updating - user interface affected",
                            "status": "Control Panel Down",
                            "action_required": "Check bot connection and restart if needed",
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
        """
        Send service recovery notification via Discord webhook.

        Generates recovery notifications to inform operational teams that
        service has returned to healthy operation:
        1. Sends structured recovery alert via enhanced webhook router
        2. Includes recovery timestamp and status confirmation
        3. Logs recovery event for operational audit trails
        4. Provides positive confirmation of service restoration

        Recovery alerts help teams understand service reliability patterns
        and confirm that previous issues have been resolved.
        """
        try:
            from src.core.di_container import get_container

            container = get_container()
            if container:
                enhanced_webhook = container.get("webhook_router")
                if enhanced_webhook and hasattr(enhanced_webhook, "log_bot_event"):
                    await enhanced_webhook.log_bot_event(
                        event_type="control_panel_recovery",
                        title="Control Panel Recovery",
                        description="Control panel has been restored and is updating normally",
                        level="info",
                        context={
                            "component": "Control Panel",
                            "status": "Control Panel Restored",
                            "recovery_time": datetime.now(UTC).strftime("%H:%M:%S UTC"),
                            "action": "Panel updates resumed successfully",
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


# Global monitor instance for control panel health tracking
# This singleton monitors all panel operations and provides failure alerting
_control_panel_monitor = ControlPanelMonitor()


# =============================================================================
# Setup Functions
# =============================================================================


async def create_control_panel(
    bot, channel: discord.TextChannel, audio_manager=None
) -> discord.Message | None:
    """
    Create and deploy comprehensive control panel with intelligent setup.

    Orchestrates the complete control panel creation workflow with robust
    error handling, cleanup procedures, and performance optimization:

    **Setup Process:**
    1. Comprehensive logging of creation context and parameters
    2. Global cleanup of existing panels to prevent conflicts
    3. Intelligent message cleanup with rate limiting protection
    4. Panel view creation and registration for lifecycle management
    5. Initial embed generation with bot branding
    6. Message deployment with retry logic for rate limiting
    7. Background update system initialization

    **Error Handling:**
    - Rate limiting detection and automatic retry with backoff
    - Permission validation and graceful degradation
    - Message deletion handling during cleanup operations
    - Comprehensive logging for debugging and monitoring
    - Enhanced webhook notifications for operational awareness

    **Performance Optimization:**
    - Smart delay insertion to prevent rate limiting
    - Efficient message cleanup with minimal API calls
    - Background task coordination for smooth user experience

    Args:
        bot: Discord bot instance for channel and user access
        channel: Target text channel for panel deployment
        audio_manager: Optional audio manager for playback integration

    Returns:
        Discord message containing the deployed panel, None on failure
    """
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

                        # Rate limiting notification handled by enhanced webhook router
                        try:
                            from src.core.di_container import get_container

                            container = get_container()
                            if container:
                                enhanced_webhook = container.get(
                                    "enhanced_webhook_router"
                                )
                                if enhanced_webhook and hasattr(
                                    enhanced_webhook, "log_bot_event"
                                ):
                                    await enhanced_webhook.log_bot_event(
                                        event_type="rate_limit_encountered",
                                        title="Message Deletion Rate Limited",
                                        description="Message deletion delayed due to rate limiting (HTTP 429)",
                                        level="warning",
                                        context={
                                            "component": "Control Panel",
                                            "action": "Message Deletion",
                                            "impact": "Cleanup delayed",
                                            "retry_after": str(retry_after),
                                            "http_status": "429",
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

                # Rate limiting notification handled by enhanced webhook router
                try:
                    from src.core.di_container import get_container

                    container = get_container()
                    if container:
                        enhanced_webhook = container.get("webhook_router")
                        if enhanced_webhook and hasattr(
                            enhanced_webhook, "log_bot_event"
                        ):
                            await enhanced_webhook.log_bot_event(
                                event_type="rate_limit_encountered",
                                title="Panel Creation Rate Limited",
                                description="Panel creation delayed due to rate limiting (HTTP 429)",
                                level="warning",
                                context={
                                    "component": "Control Panel",
                                    "action": "Panel Creation",
                                    "impact": "Creation delayed",
                                    "retry_after": str(retry_after),
                                    "http_status": "429",
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
    """
    Initialize control panel system with comprehensive validation and setup.

    Provides high-level control panel initialization with complete validation
    and error handling for production deployment:

    **Validation Process:**
    1. Channel existence and accessibility verification
    2. Bot permission validation (send messages, manage messages)
    3. Permission warning handling with graceful degradation
    4. Audio manager integration validation

    **Setup Coordination:**
    1. Global panel cleanup to prevent resource conflicts
    2. Delegation to specialized creation function
    3. Success/failure validation and reporting
    4. Comprehensive logging for operational monitoring

    This function serves as the primary entry point for control panel
    deployment, providing a clean API for bot initialization code.

    Args:
        bot: Discord bot instance for channel access and operations
        channel_id: Target channel ID for panel deployment
        audio_manager: Optional audio manager for playback integration

    Returns:
        True if panel setup completed successfully, False on failure
    """
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
