# =============================================================================
# QuranBot - Mention Handler
# =============================================================================
# Handles bot mentions for Islamic AI companion functionality
# =============================================================================

import re

import discord

from ..config import get_config
from ..core.errors import ErrorHandler
from ..core.logger import TreeLogger
from ..ui.islamic.response_embeds import (
    create_ai_response_embed,
    create_rate_limit_embed,
)


class MentionHandler:
    """
    Handles @QuranBot mentions for AI-powered Islamic companion.

    Features:
    - Detects bot mentions in messages
    - Extracts messages from mentions
    - Manages AI service interaction
    - Handles rate limiting
    - Creates beautiful response embeds
    """

    def __init__(self, bot):
        """Initialize mention handler."""
        self.bot = bot
        self.config = get_config()
        self.error_handler = ErrorHandler()

        TreeLogger.debug("Mention handler instance created")

        # Services (will be loaded when ready)
        self.ai_service = None
        self.islamic_service = None
        self.rate_limiter = None
        self.token_tracker = None

        # Message extraction patterns
        self.mention_pattern = re.compile(r"<@!?\d+>")

        TreeLogger.debug("Mention patterns compiled")

    async def setup(self) -> None:
        """Setup mention handler by getting required services."""
        try:
            TreeLogger.info("Setting up mention handler")

            # Get required services
            self.ai_service = self.bot.services.get("ai")
            self.islamic_service = self.bot.services.get("islamic_ai")
            self.rate_limiter = self.bot.services.get("rate_limiter")
            self.token_tracker = self.bot.services.get("token_tracker")

            TreeLogger.debug(
                "Services retrieved",
                {
                    "ai_service": bool(self.ai_service),
                    "islamic_service": bool(self.islamic_service),
                    "rate_limiter": bool(self.rate_limiter),
                    "token_tracker": bool(self.token_tracker),
                },
            )

            if not all([self.ai_service, self.islamic_service, self.rate_limiter]):
                TreeLogger.warning(
                    "Some AI services not available - mention handler limited",
                    {
                        "ai_service": bool(self.ai_service),
                        "islamic_service": bool(self.islamic_service),
                        "rate_limiter": bool(self.rate_limiter),
                        "token_tracker": bool(self.token_tracker),
                    },
                )

            TreeLogger.info(
                "Mention handler setup complete",
                {
                    "services_available": sum(
                        [
                            bool(self.ai_service),
                            bool(self.islamic_service),
                            bool(self.rate_limiter),
                            bool(self.token_tracker),
                        ]
                    )
                },
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to setup mention handler", e, {"error_type": type(e).__name__}
            )
            await self.error_handler.handle_error(
                e, {"operation": "mention_handler_setup"}
            )

    async def handle_message(self, message: discord.Message) -> None:
        """
        Handle a message that might contain a bot mention.

        Args:
            message: Discord message to process
        """
        # Skip if not a mention or from a bot
        if message.author.bot:
            TreeLogger.debug("Skipping bot message")
            return

        if self.bot.user not in message.mentions:
            return

        # Skip if this is a reply to a bot message
        if message.reference and message.reference.message_id:
            try:
                # Try to get the referenced message
                referenced_msg = await message.channel.fetch_message(
                    message.reference.message_id
                )
                if referenced_msg.author.id == self.bot.user.id:
                    TreeLogger.debug(
                        "Skipping reply to bot message",
                        {
                            "user_id": message.author.id,
                            "referenced_message_id": message.reference.message_id,
                        },
                    )
                    return
            except:
                # If we can't fetch the message, continue processing
                pass

        TreeLogger.debug(
            "Bot mention detected",
            {
                "user_id": message.author.id,
                "guild_id": message.guild.id if message.guild else None,
                "channel_id": message.channel.id,
            },
        )

        # Check if AI services are available
        if not self.ai_service or not self.config.openai_api_key:
            TreeLogger.warning(
                "AI services not available for mention",
                {
                    "has_ai_service": bool(self.ai_service),
                    "has_api_key": bool(self.config.openai_api_key),
                },
            )
            return

        try:
            # Extract message content
            message_text = self._extract_question(message.content)
            if not message_text.strip():
                TreeLogger.debug("Empty message after extraction")
                return

            # Check for special developer commands
            if message.author.id == self.config.developer_id:
                if message_text.lower() in [
                    "usage",
                    "ai usage",
                    "openai usage",
                    "budget",
                ]:
                    await self._handle_usage_command(message)
                    return

            # Log mention
            TreeLogger.info(
                "Bot mentioned for AI interaction",
                {
                    "user": message.author.name,
                    "user_id": message.author.id,
                    "guild": message.guild.name if message.guild else "DM",
                    "message_length": len(message_text),
                },
            )

            # Check rate limit
            if self.rate_limiter:
                TreeLogger.debug("Checking rate limit", {"user_id": message.author.id})

                allowed, time_remaining = await self.rate_limiter.check_user(
                    message.author.id
                )

                if not allowed:
                    TreeLogger.info(
                        "Rate limit hit for user",
                        {
                            "user_id": message.author.id,
                            "time_remaining": str(time_remaining),
                        },
                    )

                    # Send rate limit message
                    cooldown_message = self.rate_limiter.format_cooldown_message(
                        time_remaining
                    )
                    embed = create_rate_limit_embed(
                        cooldown_message, time_remaining, message.author, self.bot
                    )
                    await message.reply(embed=embed, ephemeral=True)
                    return

            # Check budget limit
            if self.token_tracker and self.token_tracker.is_budget_exceeded():
                TreeLogger.warning(
                    "AI budget exceeded, blocking request",
                    {"user_id": message.author.id},
                )

                embed = discord.Embed(
                    title="💰 AI Budget Exceeded",
                    description="The monthly AI budget has been reached. The AI feature will be available again next month, InshaAllah.",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if self.bot and self.bot.user and self.bot.user.avatar:
                    try:
                        embed.set_thumbnail(url=self.bot.user.avatar.url)
                    except:
                        pass

                # Get developer avatar
                developer_icon_url = None
                if self.config.developer_id:
                    try:
                        developer = self.bot.get_user(self.config.developer_id)
                        if developer and developer.avatar:
                            developer_icon_url = developer.avatar.url
                    except:
                        pass

                embed.set_footer(
                    text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                )
                await message.reply(embed=embed)
                return

            # Send typing indicator
            async with message.channel.typing():
                # Check for greeting first
                greeting_response = None
                if self.islamic_service:
                    greeting_response = self.islamic_service.detect_greeting(
                        message_text
                    )
                    if greeting_response:
                        TreeLogger.debug(
                            "Greeting detected",
                            {
                                "greeting_type": (
                                    "islamic"
                                    if "Assalam" in greeting_response
                                    else "regular"
                                )
                            },
                        )

                # Get current playing context
                context = {}
                if self.islamic_service:
                    context = self.islamic_service.get_current_playing_context()
                    context["user_name"] = message.author.display_name

                    TreeLogger.debug(
                        "Context prepared",
                        {
                            "has_playing_context": bool(context.get("current_surah")),
                            "user_name": message.author.display_name,
                        },
                    )

                # Add user_id to context and check if user is developer
                context["user_id"] = message.author.id
                context["is_developer"] = message.author.id == self.config.developer_id
                
                # Log developer interaction if detected
                if context["is_developer"]:
                    TreeLogger.info(
                        "Developer interaction detected",
                        {
                            "user_id": message.author.id,
                            "username": message.author.name,
                            "display_name": message.author.display_name,
                            "developer_id": self.config.developer_id,
                        },
                    )

                # Generate AI response
                TreeLogger.debug(
                    "Generating AI response",
                    {
                        "message_length": len(message_text),
                        "has_context": bool(context),
                        "user_id": message.author.id,
                    },
                )

                success, response, metadata = await self.ai_service.generate_response(
                    message_text, context, user_id=message.author.id
                )

                if not success:
                    TreeLogger.warning(
                        "AI response generation failed",
                        {"error_message": response, "user_id": message.author.id},
                    )

                    # Send error message
                    embed = discord.Embed(
                        title="❌ Unable to Process Message",
                        description=response,
                        color=0xFF6B6B,
                    )

                    # Add bot thumbnail
                    if self.bot and self.bot.user and self.bot.user.avatar:
                        try:
                            embed.set_thumbnail(url=self.bot.user.avatar.url)
                        except:
                            pass

                    # Get developer avatar
                    developer_icon_url = None
                    if self.config.developer_id:
                        try:
                            developer = self.bot.get_user(self.config.developer_id)
                            if developer and developer.avatar:
                                developer_icon_url = developer.avatar.url
                        except:
                            pass

                    embed.set_footer(
                        text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                    )
                    await message.reply(embed=embed)
                    return

                # Enhance response with Islamic formatting
                if self.islamic_service:
                    original_length = len(response)
                    response = self.islamic_service.enhance_response(response)

                    if len(response) != original_length:
                        TreeLogger.debug(
                            "Response enhanced",
                            {
                                "original_length": original_length,
                                "enhanced_length": len(response),
                            },
                        )

                # Combine greeting with response if applicable
                if greeting_response:
                    response = f"{greeting_response}\n\n{response}"

                # Get remaining questions for user
                remaining_questions = 1  # Default
                if self.rate_limiter:
                    is_limited, _, _ = await self.rate_limiter.check_mention_rate_limit(
                        message.author.id, message.author.name
                    )
                    # If not limited, they have 1 question available
                    remaining_questions = 0 if is_limited else 1

                # Generate Arabic translation
                arabic_response = response  # Default to same
                if self.ai_service:
                    try:
                        # Ask AI to translate to Arabic
                        arabic_prompt = f"Translate this to Arabic (keep the same tone and style): {response}"
                        (
                            success,
                            arabic_resp,
                            _,
                        ) = await self.ai_service.generate_response(arabic_prompt)
                        if success:
                            arabic_response = arabic_resp
                    except:
                        arabic_response = response  # Fallback to English

                # Create response embed with language toggle
                embed = create_ai_response_embed(
                    question=message_text,
                    response=response,
                    user=message.author,
                    context=context,
                    metadata=metadata,
                    bot=self.bot,
                    remaining_questions=remaining_questions,
                )

                # Create language toggle view
                from ..ui.islamic.language_toggle import LanguageToggleView

                view = LanguageToggleView(
                    english_response=response,
                    arabic_response=arabic_response,
                    original_question=message_text,
                    user=message.author,
                    remaining_questions=remaining_questions,
                    bot=self.bot,
                )

                # Send response with view
                await message.reply(embed=embed, view=view)

                TreeLogger.info(
                    "AI response sent successfully",
                    {
                        "user_id": message.author.id,
                        "response_length": len(response),
                        "tokens_used": (
                            metadata.get("total_tokens", 0) if metadata else 0
                        ),
                    },
                )

                # Record successful mention for rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.record_mention(
                        message.author.id, message.author.name
                    )

                # Track token usage
                if self.token_tracker and metadata:
                    TreeLogger.debug(
                        "Tracking token usage",
                        {
                            "total_tokens": metadata.get("total_tokens", 0),
                            "cost": metadata.get("cost", 0.0),
                        },
                    )

                    await self.token_tracker.track_usage(
                        user_id=message.author.id,
                        username=message.author.name,
                        question=message_text,
                        response=response,
                        input_tokens=metadata.get("input_tokens", 0),
                        output_tokens=metadata.get("output_tokens", 0),
                        model=metadata.get("model", self.config.openai_model),
                        cost=metadata.get("cost", 0.0),
                    )

        except Exception as e:
            TreeLogger.error(
                "Error handling mention",
                e,
                {
                    "user_id": message.author.id,
                    "guild_id": message.guild.id if message.guild else None,
                    "error_type": type(e).__name__,
                    "channel_id": message.channel.id,
                },
            )

            await self.error_handler.handle_error(
                e,
                {
                    "operation": "handle_mention",
                    "user_id": message.author.id,
                    "message_content_length": len(message.content),
                },
            )

            # Send generic error message
            try:
                embed = discord.Embed(
                    title="❌ Error",
                    description="I encountered an error while processing your message. Please try again.",
                    color=0xFF6B6B,
                )

                # Add bot thumbnail
                if self.bot and self.bot.user and self.bot.user.avatar:
                    try:
                        embed.set_thumbnail(url=self.bot.user.avatar.url)
                    except:
                        pass

                # Get developer avatar
                developer_icon_url = None
                if self.config.developer_id:
                    try:
                        developer = self.bot.get_user(self.config.developer_id)
                        if developer and developer.avatar:
                            developer_icon_url = developer.avatar.url
                    except:
                        pass

                embed.set_footer(
                    text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                )
                await message.reply(embed=embed)
            except:
                pass

    def _extract_question(self, content: str) -> str:
        """
        Extract the message content from a message containing a bot mention.

        Args:
            content: Message content with mention

        Returns:
            Cleaned message text
        """
        TreeLogger.debug(
            "Extracting message content",
            {
                "original_length": len(content),
                "has_mentions": bool(self.mention_pattern.search(content)),
            },
        )

        # Remove all mentions
        message_text = self.mention_pattern.sub("", content).strip()

        # Clean up extra whitespace
        message_text = " ".join(message_text.split())

        TreeLogger.debug(
            "Message extracted",
            {
                "extracted_length": len(message_text),
                "is_empty": not message_text.strip(),
            },
        )

        return message_text

    async def _handle_usage_command(self, message: discord.Message) -> None:
        """Handle special usage command for developer."""
        try:
            # Send typing indicator
            async with message.channel.typing():
                # Get OpenAI usage tracker
                usage_tracker = self.bot.services.get("openai_usage")
                if not usage_tracker:
                    embed = discord.Embed(
                        title="❌ Service Unavailable",
                        description="OpenAI usage tracking service is not available.",
                        color=0xFF6B6B,
                    )

                    # Add bot thumbnail
                    if self.bot and self.bot.user and self.bot.user.avatar:
                        try:
                            embed.set_thumbnail(url=self.bot.user.avatar.url)
                        except:
                            pass

                    # Get developer avatar
                    developer_icon_url = None
                    if self.config.developer_id:
                        try:
                            developer = self.bot.get_user(self.config.developer_id)
                            if developer and developer.avatar:
                                developer_icon_url = developer.avatar.url
                        except:
                            pass

                    embed.set_footer(
                        text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                    )
                    await message.reply(embed=embed)
                    return

                # Get usage summary
                summary = await usage_tracker.get_usage_summary()

                if summary["status"] != "available":
                    embed = discord.Embed(
                        title="❌ Unable to Fetch Usage",
                        description=summary.get("message", "Unknown error"),
                        color=0xFF6B6B,
                    )

                    # Add bot thumbnail
                    if self.bot and self.bot.user and self.bot.user.avatar:
                        try:
                            embed.set_thumbnail(url=self.bot.user.avatar.url)
                        except:
                            pass

                    # Get developer avatar
                    developer_icon_url = None
                    if self.config.developer_id:
                        try:
                            developer = self.bot.get_user(self.config.developer_id)
                            if developer and developer.avatar:
                                developer_icon_url = developer.avatar.url
                        except:
                            pass

                    embed.set_footer(
                        text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                    )
                    await message.reply(embed=embed)
                    return

                # Create usage embed
                embed = discord.Embed(
                    title="📊 OpenAI API Usage (Real-time)",
                    description="Live data from OpenAI API dashboard",
                    color=0x00D4AA,
                )

                # Add bot thumbnail
                if self.bot and self.bot.user and self.bot.user.avatar:
                    try:
                        embed.set_thumbnail(url=self.bot.user.avatar.url)
                    except:
                        pass

                # Add current usage
                embed.add_field(
                    name="💰 Current Month Usage",
                    value=f"**Used:** {summary['current_cost']} / {summary['budget']}\n"
                    f"**Remaining:** {summary['remaining']}\n"
                    f"**Percentage:** {summary['percentage_used']}",
                    inline=False,
                )

                # Add usage statistics
                embed.add_field(
                    name="📈 Usage Statistics",
                    value=f"**Total Requests:** {summary['total_requests']}\n"
                    f"**Total Tokens:** {summary['total_tokens']}\n"
                    f"**Daily Burn Rate:** {summary['daily_burn_rate']}",
                    inline=True,
                )

                # Add projections
                status_emoji = "⚠️" if summary["will_exceed_budget"] else "✅"
                embed.add_field(
                    name="📅 Monthly Projection",
                    value=f"**Projected Cost:** {summary['projected_monthly']}\n"
                    f"**Days Remaining:** {summary['days_remaining']}\n"
                    f"**Status:** {status_emoji} {'Will exceed budget!' if summary['will_exceed_budget'] else 'Within budget'}",
                    inline=True,
                )

                # Compare with local tracking
                if self.token_tracker:
                    local_usage = await self.token_tracker.get_current_month_usage()
                    local_cost = local_usage.get("total_cost", 0)

                    embed.add_field(
                        name="🔄 Tracking Comparison",
                        value=f"**Local Tracking:** ${local_cost:.2f}\n"
                        f"**OpenAI Actual:** {summary['current_cost']}\n"
                        f"**Accuracy:** {'✅ Accurate' if abs(float(summary['current_cost'][1:]) - local_cost) < 0.01 else '⚠️ Discrepancy detected'}",
                        inline=False,
                    )

                # Add developer footer
                developer_icon_url = None
                if self.config.developer_id:
                    try:
                        developer = self.bot.get_user(self.config.developer_id)
                        if developer and developer.avatar:
                            developer_icon_url = developer.avatar.url
                    except:
                        pass

                embed.set_footer(
                    text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
                )

                # Add refresh tip
                embed.add_field(
                    name="💡 Tip",
                    value="This data is fetched directly from OpenAI's API and cached for 5 minutes.",
                    inline=False,
                )

                await message.reply(embed=embed)

                TreeLogger.info(
                    "Usage command executed via mention",
                    {
                        "user": message.author.name,
                        "current_cost": summary["current_cost"],
                    },
                )

        except Exception as e:
            TreeLogger.error("Error handling usage command", e)

            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching usage data.",
                color=0xFF6B6B,
            )

            # Add bot thumbnail
            if self.bot and self.bot.user and self.bot.user.avatar:
                try:
                    embed.set_thumbnail(url=self.bot.user.avatar.url)
                except:
                    pass

            # Get developer avatar
            developer_icon_url = None
            if self.config.developer_id:
                try:
                    developer = self.bot.get_user(self.config.developer_id)
                    if developer and developer.avatar:
                        developer_icon_url = developer.avatar.url
                except:
                    pass

            embed.set_footer(
                text="Developed by حَـــــنَّـــــا", icon_url=developer_icon_url
            )

            await message.reply(embed=embed)
