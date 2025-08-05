# =============================================================================
# QuranBot - Language Toggle View
# =============================================================================
# View for language switching in AI responses
# =============================================================================


import discord

from ...core.logger import TreeLogger


class LanguageToggleView(discord.ui.View):
    """View with language toggle button for AI responses."""

    def __init__(
        self,
        english_response: str,
        arabic_response: str,
        original_question: str,
        user: discord.User,
        remaining_questions: int = 1,
        bot=None,
    ):
        super().__init__(timeout=None)  # No timeout
        self.english_response = english_response
        self.arabic_response = arabic_response
        self.original_question = original_question
        self.user = user
        self.remaining_questions = remaining_questions
        self.bot = bot
        self.current_language = "english"

        # Add the initial button (Arabic)
        self.add_language_button()

    def add_language_button(self):
        """Add the appropriate language button based on current state."""
        # Clear existing buttons
        self.clear_items()

        if self.current_language == "english":
            # Show Arabic button (green)
            button = discord.ui.Button(
                label="Arabic",
                emoji="🇸🇦",
                style=discord.ButtonStyle.success,  # Green
                custom_id="switch_to_arabic",
            )
            button.callback = self.switch_to_arabic
        else:
            # Show English button (red)
            button = discord.ui.Button(
                label="English",
                emoji="🇺🇸",
                style=discord.ButtonStyle.danger,  # Red
                custom_id="switch_to_english",
            )
            button.callback = self.switch_to_english

        self.add_item(button)

    async def switch_to_arabic(self, interaction: discord.Interaction):
        """Switch to Arabic response."""
        try:
            # Only allow the original user to switch
            if interaction.user.id != self.user.id:
                from .response_embeds import create_error_embed_with_pfp

                embed = create_error_embed_with_pfp(
                    title="❌ Permission Denied",
                    description="Only the person who asked can switch languages.",
                    bot=self.bot,
                    color=0xFF0000,  # Red
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            self.current_language = "arabic"
            self.add_language_button()

            # Create Arabic embed
            from .response_embeds import create_ai_response_embed

            embed = create_ai_response_embed(
                question=self.original_question,
                response=self.arabic_response,
                user=self.user,
                bot=self.bot,
                remaining_questions=self.remaining_questions,
            )

            await interaction.response.edit_message(embed=embed, view=self)

            TreeLogger.debug("Switched to Arabic", {"user_id": interaction.user.id})

        except Exception as e:
            TreeLogger.error("Error switching to Arabic", e)
            from .response_embeds import create_error_embed_with_pfp

            embed = create_error_embed_with_pfp(
                title="❌ Error",
                description="Error switching language.",
                bot=self.bot,
                color=0xFF0000,  # Red
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def switch_to_english(self, interaction: discord.Interaction):
        """Switch to English response."""
        try:
            # Only allow the original user to switch
            if interaction.user.id != self.user.id:
                from .response_embeds import create_error_embed_with_pfp

                embed = create_error_embed_with_pfp(
                    title="❌ Permission Denied",
                    description="Only the person who asked can switch languages.",
                    bot=self.bot,
                    color=0xFF0000,  # Red
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            self.current_language = "english"
            self.add_language_button()

            # Create English embed
            from .response_embeds import create_ai_response_embed

            embed = create_ai_response_embed(
                question=self.original_question,
                response=self.english_response,
                user=self.user,
                bot=self.bot,
                remaining_questions=self.remaining_questions,
            )

            await interaction.response.edit_message(embed=embed, view=self)

            TreeLogger.debug("Switched to English", {"user_id": interaction.user.id})

        except Exception as e:
            TreeLogger.error("Error switching to English", e)
            from .response_embeds import create_error_embed_with_pfp

            embed = create_error_embed_with_pfp(
                title="❌ Error",
                description="Error switching language.",
                bot=self.bot,
                color=0xFF0000,  # Red
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
