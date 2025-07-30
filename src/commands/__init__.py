# =============================================================================
# QuranBot Commands Package
# =============================================================================
# Command cogs for Discord slash commands using Discord.py Cogs architecture
# =============================================================================

# Import all command cogs

from .credits import CreditsCog
from .credits import setup as setup_credits
from .interval import IntervalCog
from .interval import setup as setup_interval
from .leaderboard import LeaderboardCog
from .leaderboard import setup as setup_leaderboard
from .question import QuestionCog
from .question import setup as setup_question

from .verse import VerseCog
from .verse import setup as setup_verse
from .quiz_editor import QuizEditorCog
from .quiz_editor import setup as setup_quiz_editor
from .backup_manager import BackupManagerCog
from .backup_manager import setup as setup_backup_manager

# =============================================================================
# Command Loading Function
# =============================================================================


async def load_commands(bot, container):
    """Load all command cogs with dependency injection"""
    await setup_credits(bot, container)
    await setup_interval(bot, container)
    await setup_leaderboard(bot, container)
    await setup_question(bot, container)

    await setup_verse(bot, container)
    await setup_quiz_editor(bot, container)
    await setup_backup_manager(bot, container)


# Export all cogs and setup functions
__all__ = [
    # Cog classes
    "CreditsCog",
    "IntervalCog",
    "LeaderboardCog",
    "QuestionCog",
    "VerseCog",
    "QuizEditorCog",
    "BackupManagerCog",
    # Setup functions
    "setup_credits",
    "setup_interval",
    "setup_leaderboard",
    "setup_question",
    "setup_verse",
    "setup_quiz_editor",
    "setup_backup_manager",
    # Command loading
    "load_commands",
]
