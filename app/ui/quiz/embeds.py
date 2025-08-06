"""Quiz embed creators for QuranBot."""

from datetime import datetime
from typing import Any, Dict, Optional

import discord

from ...services.quiz import QuizQuestion
from ..base.components import create_developer_footer


def create_quiz_embed(
    question: QuizQuestion,
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
    show_timer: bool = True,
) -> discord.Embed:
    """
    Create a quiz question embed.

    Args
    ----
        question: Quiz question object.
        bot: Discord bot instance for footer.
        guild: Discord guild for member-specific avatar.
        show_timer: Whether to show timer field.

    Returns
    -------
        Discord embed for the quiz question.

    """
    embed = discord.Embed(color=0x00D4AA)

    # Add question text (Arabic first if available)
    arabic_text = question.get_question_text("arabic")
    english_text = question.get_question_text("english")

    if arabic_text and arabic_text != "Question not available":
        embed.add_field(
            name="🕌 **Question**", value=f"```\n{arabic_text}\n```", inline=False
        )

    if english_text and english_text != "Question not available":
        embed.add_field(
            name="📖 **Translation**", value=f"```\n{english_text}\n```", inline=False
        )

    # Add spacing
    embed.add_field(name="\u200b", value="", inline=False)

    # Add metadata
    embed.add_field(name="📚 Category", value=question.category, inline=True)

    # Convert difficulty number to stars
    difficulty_stars = "⭐" * question.difficulty
    embed.add_field(name="⭐ Difficulty", value=difficulty_stars, inline=True)

    if show_timer:
        embed.add_field(name="⏰ Timer", value="Starting...", inline=True)

    # Add spacing
    embed.add_field(name="\u200b", value="", inline=False)

    # Add choices
    choice_text = ""
    for letter in ["A", "B", "C", "D"]:
        english_choice = question.get_choice_text(letter, "english")
        arabic_choice = question.get_choice_text(letter, "arabic")

        if english_choice and english_choice != "Choice not available":
            choice_text += f"**{letter}.** {english_choice}"

        if arabic_choice and arabic_choice != "Choice not available":
            choice_text += f"\n```\n{arabic_choice}\n```"

        choice_text += "\n\n"

    if choice_text:
        embed.add_field(name="**Answers:**", value=choice_text.strip(), inline=False)

    # Add spacing
    embed.add_field(name="\u200b", value="", inline=False)

    # Set bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except Exception:
            pass

    # Set developer footer
    footer_text, developer_icon_url = create_developer_footer(bot, guild)
    embed.set_footer(text=footer_text, icon_url=developer_icon_url)

    return embed


def create_quiz_result_embed(
    question: QuizQuestion,
    user_answer: str,
    is_correct: bool,
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
    response_time: float | None = None,
    reward_amount: int | None = None,
) -> discord.Embed:
    """
    Create a quiz result embed.

    Args
    ----
        question: Quiz question object.
        user_answer: User's answer letter.
        is_correct: Whether answer was correct.
        bot: Discord bot instance for footer.
        guild: Discord guild for member-specific avatar.
        response_time: Time taken to answer in seconds.
        reward_amount: UnbelievaBoat reward amount if given.

    Returns
    -------
        Discord embed for the quiz result.

    """
    # Color based on result
    color = 0x2ECC71 if is_correct else 0xE74C3C

    # Title based on result
    title = "✅ Correct!" if is_correct else "❌ Incorrect"

    embed = discord.Embed(title=title, color=color, timestamp=datetime.utcnow())

    # Show user answer
    user_choice_text = question.get_choice_text(user_answer, "english")
    embed.add_field(
        name="Your Answer", value=f"**{user_answer}.** {user_choice_text}", inline=False
    )

    # Show correct answer if wrong
    if not is_correct:
        correct_choice_text = question.get_choice_text(
            question.correct_answer, "english"
        )
        embed.add_field(
            name="Correct Answer",
            value=f"**{question.correct_answer}.** {correct_choice_text}",
            inline=False,
        )

    # Show explanation if available
    explanation_text = question.get_explanation_text("english")
    if explanation_text:
        embed.add_field(name="📚 Explanation", value=explanation_text, inline=False)

    # Show reference if available
    if question.reference:
        embed.add_field(name="📖 Reference", value=question.reference, inline=False)

    # Show response time if provided
    if response_time:
        embed.add_field(
            name="⏱️ Response Time", value=f"{response_time:.1f} seconds", inline=True
        )
    
    # Show reward or penalty if provided
    if reward_amount:
        if reward_amount > 0:
            # Calculate base reward for comparison
            base_rewards = {"easy": 100, "medium": 250, "hard": 500}
            difficulty_name = "easy" if question.difficulty <= 2 else "medium" if question.difficulty == 3 else "hard"
            base_reward = base_rewards.get(difficulty_name, 100)
            
            # Create detailed reward text
            reward_text = f"**+{reward_amount} coins**"
            
            # Add bonus indicators if applicable
            if reward_amount > base_reward * 1.5:
                reward_text += "\n🥇 First answer bonus!"
            if response_time and response_time <= 5:
                reward_text += "\n⚡ Lightning fast bonus!"
            elif response_time and response_time <= 10:
                reward_text += "\n🏃 Quick answer bonus!"
                
            embed.add_field(
                name="💰 Reward Earned", value=reward_text, inline=True
            )
        else:
            # Show penalty details
            penalty_text = f"**{reward_amount} coins**"
            if response_time and response_time > 20:
                penalty_text += "\n🐌 Slow response penalty"
                
            embed.add_field(
                name="💸 Penalty Applied", value=penalty_text, inline=True
            )

    # Set bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except Exception:
            pass

    # Set developer footer
    footer_text, developer_icon_url = create_developer_footer(bot, guild)
    embed.set_footer(text=footer_text, icon_url=developer_icon_url)

    return embed


def create_quiz_timeout_embed(
    question: QuizQuestion, 
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
) -> discord.Embed:
    """
    Create a quiz timeout embed.

    Args
    ----
        question: Quiz question object.
        bot: Discord bot instance for footer.
        guild: Discord guild for member-specific avatar.

    Returns
    -------
        Discord embed for quiz timeout.

    """
    embed = discord.Embed(
        title="⏰ Time's Up!",
        description="The quiz has ended due to timeout.",
        color=0xF39C12,
        timestamp=datetime.utcnow(),
    )

    # Show correct answer
    correct_choice_text = question.get_choice_text(question.correct_answer, "english")
    embed.add_field(
        name="Correct Answer",
        value=f"**{question.correct_answer}.** {correct_choice_text}",
        inline=False,
    )

    # Show explanation if available
    explanation_text = question.get_explanation_text("english")
    if explanation_text:
        embed.add_field(name="📚 Explanation", value=explanation_text, inline=False)

    # Set bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except Exception:
            pass

    # Set developer footer
    footer_text, developer_icon_url = create_developer_footer(bot, guild)
    embed.set_footer(text=footer_text, icon_url=developer_icon_url)

    return embed


def create_quiz_stats_embed(
    stats: dict[str, Any], 
    username: str, 
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
) -> discord.Embed:
    """
    Create a user quiz stats embed.

    Args
    ----
        stats: User statistics dictionary.
        username: User's display name.
        bot: Discord bot instance for footer.
        guild: Discord guild for member-specific avatar.

    Returns
    -------
        Discord embed for user stats.

    """
    embed = discord.Embed(
        title=f"📊 Quiz Statistics for {username}",
        color=0x3498DB,
        timestamp=datetime.utcnow(),
    )

    # Overall stats
    embed.add_field(
        name="📈 Overall Performance",
        value=(
            f"**Total Questions:** {stats['total_questions']}\n"
            f"**Correct Answers:** {stats['correct_answers']}\n"
            f"**Accuracy:** {stats['accuracy_percentage']}%\n"
            f"**Total Points:** {stats['total_points']:,}"
        ),
        inline=True,
    )

    # Streak stats
    embed.add_field(
        name="🔥 Streak Stats",
        value=(
            f"**Current Streak:** {stats['current_streak']}\n"
            f"**Best Streak:** {stats['best_streak']}"
        ),
        inline=True,
    )

    # Rank if available
    if stats.get("rank"):
        embed.add_field(
            name="🏆 Leaderboard Rank", value=f"**#{stats['rank']}**", inline=True
        )

    # Category performance
    category_perf = stats.get("category_performance", {})
    if category_perf:
        perf_text = ""
        for category, data in sorted(category_perf.items()):
            perf_text += f"**{category}:** {data['accuracy']}% ({data['correct']}/{data['total']})\n"

        if perf_text:
            embed.add_field(
                name="📚 Category Performance", value=perf_text.strip(), inline=False
            )

    # Set bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except Exception:
            pass

    # Set developer footer
    footer_text, developer_icon_url = create_developer_footer(bot, guild)
    embed.set_footer(text=footer_text, icon_url=developer_icon_url)

    return embed


def create_quiz_leaderboard_embed(
    leaderboard: list, 
    bot: discord.Client | None = None,
    guild: discord.Guild | None = None,
) -> discord.Embed:
    """
    Create a quiz leaderboard embed.

    Args
    ----
        leaderboard: List of leaderboard entries.
        bot: Discord bot instance for footer.
        guild: Discord guild for member-specific avatar.

    Returns
    -------
        Discord embed for leaderboard.

    """
    embed = discord.Embed(
        title="🏆 Quiz Leaderboard",
        description="Top performers in the Islamic Knowledge Quiz",
        color=0xFFD700,
        timestamp=datetime.utcnow(),
    )

    if not leaderboard:
        embed.add_field(
            name="No Data", value="No quiz statistics available yet.", inline=False
        )
    else:
        # Format leaderboard entries
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]

        for entry in leaderboard:
            rank = entry["rank"]
            medal = medals[rank - 1] if rank <= 3 else f"**#{rank}**"

            leaderboard_text += (
                f"{medal} <@{entry['user_id']}>\n"
                f"   📊 **{entry['total_points']:,} points** | "
                f"✅ {entry['accuracy_percentage']}% | "
                f"📝 {entry['total_questions']} questions\n\n"
            )

        embed.add_field(name="Rankings", value=leaderboard_text.strip(), inline=False)

    # Set bot thumbnail
    if bot and bot.user and bot.user.avatar:
        try:
            embed.set_thumbnail(url=bot.user.avatar.url)
        except Exception:
            pass

    # Set developer footer
    footer_text, developer_icon_url = create_developer_footer(bot, guild)
    embed.set_footer(text=footer_text, icon_url=developer_icon_url)

    return embed
