# =============================================================================
# QuranBot - Islamic AI Mention Listener
# =============================================================================
# Islamic AI Mention Listener - Natural AI Interaction
# Listens for bot mentions and provides AI-powered Islamic guidance in English,
# understanding both English and Arabic input.
# =============================================================================

from datetime import datetime, timedelta
import re

import discord
from discord.ext import commands

from src.config import get_config_service
from src.core.di_container import DIContainer
from src.services.islamic_ai_service import get_enhanced_islamic_ai_service
from src.services.memory_service import get_conversation_memory_service
from src.services.translation_service import get_translation_service
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section


class TranslationView(discord.ui.View):
    """Discord UI View for translation buttons."""

    def __init__(
        self, ai_response: str, original_embed: discord.Embed, original_user_id: int
    ):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.ai_response = ai_response
        self.original_embed = original_embed
        self.original_user_id = original_user_id
        self.translation_service = get_translation_service()

        # Add language selection buttons with different colors
        language_buttons = [
            ("en", discord.ButtonStyle.success),  # Green for English (original)
            ("ar", discord.ButtonStyle.danger),  # Red for Arabic
            ("de", discord.ButtonStyle.secondary),  # Gray for Deutsch
            ("es", discord.ButtonStyle.primary),  # Blue for Spanish
            ("ru", discord.ButtonStyle.blurple),  # Purple for Russian
            ("fr", discord.ButtonStyle.red),  # Red for French
        ]

        for lang_code, button_style in language_buttons:
            if lang_code in self.translation_service.supported_languages:
                lang_info = self.translation_service.supported_languages[lang_code]
                button = discord.ui.Button(
                    label=f"{lang_info['flag']} {lang_info['name']}",
                    custom_id=f"translate_{lang_code}",
                    style=button_style,
                )
                button.callback = self.create_translation_callback(lang_code)
                self.add_item(button)

    def create_translation_callback(self, language_code: str):
        """Create callback function for translation button."""

        async def translation_callback(interaction: discord.Interaction):
            # Check if the user is authorized to use this translation
            if interaction.user.id != self.original_user_id:
                await interaction.response.send_message(
                    "❌ **Translation Not Available**\n"
                    "You can only translate responses that were directed to you. "
                    "Try mentioning the bot yourself to get your own response! 🤖",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            try:
                (
                    success,
                    translated_text,
                ) = await self.translation_service.translate_ai_response(
                    self.ai_response, language_code
                )

                if success:
                    # Update embed description with translated text
                    new_embed = self.original_embed.copy()
                    new_embed.description = f"```{translated_text}```"

                    # Add translation indicator
                    lang_display = self.translation_service.get_language_display_name(
                        language_code
                    )
                    if language_code == "en":
                        # Special case for English (original language)
                        new_embed.set_footer(
                            text=f"{self.original_embed.footer.text} • Original",
                            icon_url=self.original_embed.footer.icon_url,
                        )
                    else:
                        new_embed.set_footer(
                            text=f"{self.original_embed.footer.text} • Translated to {lang_display}",
                            icon_url=self.original_embed.footer.icon_url,
                        )

                    await interaction.edit_original_response(embed=new_embed, view=self)

                    log_perfect_tree_section(
                        "AI Translation - Success",
                        [
                            ("language", language_code),
                            ("user", str(interaction.user.id)),
                            ("length", str(len(translated_text))),
                        ],
                        "🌍",
                    )
                else:
                    await interaction.edit_original_response(
                        content=f"❌ Translation failed: {translated_text}", view=None
                    )

            except Exception as e:
                log_error_with_traceback("Translation callback error", e)
                await interaction.edit_original_response(
                    content="❌ Translation failed", view=None
                )

        return translation_callback


class IslamicAIMentionListener(commands.Cog):
    """Event listener for bot mentions with Islamic questions"""

    def __init__(self, bot: commands.Bot, container: DIContainer):
        self.bot = bot
        self.container = container
        self.config = get_config_service().config

        # Keywords that indicate an Islamic question (English and Arabic)
        self.islamic_keywords = {
            # English keywords
            "english": [
                "islam",
                "muslim",
                "allah",
                "prophet",
                "muhammad",
                "quran",
                "koran",
                "prayer",
                "salah",
                "salat",
                "wudu",
                "ablution",
                "mosque",
                "masjid",
                "ramadan",
                "fasting",
                "sawm",
                "zakat",
                "charity",
                "hajj",
                "pilgrimage",
                "shahada",
                "faith",
                "belief",
                "hadith",
                "sunnah",
                "imam",
                "scholar",
                "halal",
                "haram",
                "makruh",
                "mustahab",
                "fiqh",
                "sharia",
                "tawhid",
                "iman",
                "dua",
                "dhikr",
                "recitation",
                "surah",
                "ayah",
                "verse",
                "mecca",
                "medina",
                "kaaba",
                "qibla",
                "eid",
                "jummah",
                "friday",
            ],
            # Arabic keywords (common Islamic terms)
            "arabic": [
                "الله",
                "إسلام",
                "مسلم",
                "محمد",
                "قرآن",
                "صلاة",
                "وضوء",
                "مسجد",
                "رمضان",
                "صوم",
                "زكاة",
                "حج",
                "شهادة",
                "حديث",
                "سنة",
                "إمام",
                "حلال",
                "حرام",
                "فقه",
                "شريعة",
                "توحيد",
                "إيمان",
                "دعاء",
                "ذكر",
                "سورة",
                "آية",
                "مكة",
                "المدينة",
                "الكعبة",
                "قبلة",
                "عيد",
                "جمعة",
            ],
        }

        # Keywords that indicate questions about other religions (should be declined)
        self.non_islamic_keywords = [
            "christianity",
            "christian",
            "jesus",
            "christ",
            "bible",
            "church",
            "pope",
            "judaism",
            "jewish",
            "jew",
            "torah",
            "synagogue",
            "rabbi",
            "hinduism",
            "hindu",
            "buddha",
            "buddhism",
            "buddhist",
            "atheism",
            "atheist",
            "agnostic",
            "secular",
            "compare",
            "comparison",
            "versus",
            "vs",
            "better than",
            "different from",
            "why not",
            "debunk",
            "prove",
            "disprove",
            "wrong",
            "false",
        ]

        # Question indicators (English and Arabic)
        self.question_patterns = [
            # English question patterns
            r"\b(what|how|when|where|why|who|can|should|is|are|do|does|will|would)\b",
            r"\?",  # Question mark
            # Arabic question patterns
            r"\b(ما|كيف|متى|أين|لماذا|من|هل|أين|كم)\b",
            r"؟",  # Arabic question mark
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for bot mentions with Islamic questions"""

        # Ignore bot's own messages
        if message.author == self.bot.user:
            return

        # Check if bot is mentioned
        if self.bot.user not in message.mentions:
            return

        # Ignore replies to bot's own embeds/messages
        if message.reference and message.reference.resolved:
            referenced_message = message.reference.resolved
            # If replying to the bot's message, ignore it
            if referenced_message.author == self.bot.user:
                return

        # Get message content without the mention
        content = self._clean_mention_from_message(message)

        # Check if this looks like an Islamic question
        if not self._is_islamic_question(content):
            return

        # Log the interaction
        log_perfect_tree_section(
            "Islamic AI - Mention Detected",
            [
                ("user", f"{message.author.display_name} ({message.author.id})"),
                (
                    "channel",
                    (
                        f"#{message.channel.name}"
                        if hasattr(message.channel, "name")
                        else "DM"
                    ),
                ),
                ("content_length", str(len(content))),
                (
                    "content_preview",
                    content[:50] + "..." if len(content) > 50 else content,
                ),
                ("has_arabic", str(self._contains_arabic(content))),
            ],
            "🤖",
        )

        try:
            # Show typing indicator
            async with message.channel.typing():
                # Get Enhanced AI service instead of basic one
                enhanced_ai_service = await get_enhanced_islamic_ai_service()

                if enhanced_ai_service.client is None:
                    await message.reply(
                        "🚫 Sorry, the Enhanced Islamic AI assistant is currently unavailable. Please try again later.",
                        mention_author=False,
                    )
                    return

                # Check rate limit
                rate_status = enhanced_ai_service.get_rate_limit_status(
                    message.author.id
                )

                # Handle admin case where requests_remaining is "∞" (string)
                requests_remaining = rate_status["requests_remaining"]
                if isinstance(requests_remaining, str) or requests_remaining > 0:
                    # Admin user (∞) or user has remaining requests
                    pass  # Continue to process the question
                else:
                    # Regular user has no requests remaining
                    reset_time = rate_status.get("reset_time", 0)
                    minutes = reset_time // 60
                    seconds = reset_time % 60
                    hours = minutes // 60
                    remaining_minutes = minutes % 60

                    # Calculate the exact time when they can ask again
                    now = datetime.now()
                    reset_datetime = now + timedelta(seconds=reset_time)
                    reset_time_str = reset_datetime.strftime(
                        "%I:%M %p"
                    )  # 12-hour format with AM/PM

                    if hours > 0:
                        time_str = f"**{hours}h {remaining_minutes}m**"
                    else:
                        time_str = f"**{minutes}m {seconds}s**"

                    embed = discord.Embed(
                        title="⏰ Rate Limit Reached",
                        description=f"To protect API costs, each user can ask **1 question per hour**.\n"
                        f"You can ask your next question at **{reset_time_str}** (in {time_str}).",
                        color=0xFFA500,
                    )
                    embed.add_field(
                        name="💡 Why This Limit?",
                        value="```• Helps manage AI API costs\n"
                        "• Ensures fair access for all users\n"
                        "• Encourages thoughtful questions```",
                        inline=False,
                    )

                    # Set footer with admin profile picture
                    try:
                        admin_user = await self.bot.fetch_user(self.config.developer_id)
                        if admin_user and admin_user.avatar:
                            embed.set_footer(
                                text="Created by حَـــــنَّـــــا",
                                icon_url=admin_user.avatar.url,
                            )
                        else:
                            embed.set_footer(text="Created by حَـــــنَّـــــا")
                    except (discord.HTTPException, discord.NotFound, AttributeError):
                        embed.set_footer(text="Created by حَـــــنَّـــــا")

                    await message.reply(embed=embed, mention_author=False)
                    return

                # Process question through Enhanced AI
                (
                    success,
                    ai_response,
                    error_message,
                ) = await enhanced_ai_service.ask_question(message.author.id, content)

                if not success:
                    await message.reply(
                        f"❌ {error_message or 'An error occurred while processing your question. Please try again.'}",
                        mention_author=False,
                    )
                    return

                # Get conversation memory service
                memory_service = get_conversation_memory_service()

                # Classify question topics for learning
                topics = memory_service.classify_question_topics(content)

                # Get user context for personalization
                user_context = memory_service.get_user_context(message.author.id)

                # Add conversation to memory
                memory_service.add_conversation(
                    message.author.id, content, ai_response, topics
                )

                # Create response embed
                embed = discord.Embed(
                    title="Quran Knowledge Assistant",
                    description=f"```{ai_response}```",
                    color=0x1ABC9C,
                )

                # Set bot profile picture as thumbnail
                if self.bot.user and self.bot.user.avatar:
                    embed.set_thumbnail(url=self.bot.user.avatar.url)

                # Add user's question (truncated if too long)
                question_display = (
                    content if len(content) <= 100 else content[:97] + "..."
                )
                embed.add_field(
                    name="❓ Your Question",
                    value=f"```{question_display}```",
                    inline=False,
                )

                # Note: User learning tracking happens silently in the background
                # The memory service still learns about user preferences, but we don't display it
                # to maintain privacy and avoid making users feel tracked

                # Add rate limit status
                updated_rate_status = enhanced_ai_service.get_rate_limit_status(
                    message.author.id
                )

                if updated_rate_status.get("is_admin"):
                    embed.add_field(
                        name="👑 Admin Access",
                        value="```Unlimited questions```",
                        inline=True,
                    )
                else:
                    embed.add_field(
                        name="⏰ Questions Remaining",
                        value="```1 (resets hourly)```",
                        inline=True,
                    )

                # Set footer with admin profile picture
                try:
                    admin_user = await self.bot.fetch_user(self.config.developer_id)
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="Created by حَـــــنَّـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="Created by حَـــــنَّـــــا")
                except (discord.HTTPException, discord.NotFound, AttributeError):
                    embed.set_footer(text="Created by حَـــــنَّـــــا")

                # Create translation view
                translation_view = TranslationView(
                    ai_response, embed, message.author.id
                )

                # Send response with translation buttons
                await message.reply(
                    embed=embed, view=translation_view, mention_author=False
                )

                # Log successful response
                log_perfect_tree_section(
                    "Islamic AI - Response Sent",
                    [
                        (
                            "user",
                            f"{message.author.display_name} ({message.author.id})",
                        ),
                        ("response_length", str(len(ai_response))),
                        (
                            "questions_remaining",
                            str(updated_rate_status["requests_remaining"]),
                        ),
                        ("method", "mention-based"),
                        ("status", "✅ AI response delivered"),
                    ],
                    "✅",
                )

        except Exception as e:
            log_error_with_traceback("Islamic AI mention listener error", e)

            try:
                await message.reply(
                    "❌ An unexpected error occurred while processing your question. Please try again later.",
                    mention_author=False,
                )
            except:
                # If even error handling fails, log it
                log_error_with_traceback(
                    "Failed to send error message in AI mention listener", e
                )

    def _clean_mention_from_message(self, message: discord.Message) -> str:
        """Remove bot mention from message content"""
        content = message.content

        # Remove @BotName mentions
        if self.bot.user:
            content = content.replace(f"<@{self.bot.user.id}>", "")
            content = content.replace(f"<@!{self.bot.user.id}>", "")

        # Clean up extra whitespace
        content = " ".join(content.split())

        return content.strip()

    def _is_islamic_question(self, content: str) -> bool:
        """Allow all questions - let AI handle Islamic vs non-Islamic content with personality"""
        if not content or len(content.strip()) < 3:
            return False

        content_lower = content.lower()

        # Check for question patterns (any question gets through)
        has_question_pattern = False
        for pattern in self.question_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                has_question_pattern = True
                break

        # Allow any mention that looks like a question, greeting, or direct address
        # This includes: questions, greetings like "hello", direct statements to the bot
        is_direct_address = any(
            word in content_lower
            for word in [
                "hello",
                "hi",
                "hey",
                "how are you",
                "what are you",
                "who are you",
                "tell me",
                "can you",
                "are you",
                "do you",
                "what do you",
            ]
        )

        # Allow if it's a question, direct address, or has some content to respond to
        return has_question_pattern or is_direct_address or len(content.strip()) >= 5

    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        arabic_pattern = (
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
        )
        return bool(re.search(arabic_pattern, text))


async def setup_islamic_ai_listener(bot: commands.Bot, container: DIContainer):
    """Set up the Islamic AI mention listener"""
    try:
        cog = IslamicAIMentionListener(bot, container)
        await bot.add_cog(cog)

        log_perfect_tree_section(
            "Islamic AI Listener - Loaded",
            [
                ("trigger", "Bot mentions"),
                ("languages", "English + Arabic input"),
                ("response", "English only"),
                ("ai_model", "GPT-3.5 Turbo"),
                ("rate_limit", "1 question/hour per user"),
                ("admin_access", "✅ Unlimited for admin"),
                ("status", "🤖 Ready for natural AI interaction"),
            ],
            "👂",
        )

    except Exception as e:
        log_error_with_traceback("Failed to load Islamic AI listener", e)
