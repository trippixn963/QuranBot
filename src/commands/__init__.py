# =============================================================================
# QuranBot Commands Package
# =============================================================================
# Command cogs for Discord slash commands using Discord.py Cogs architecture
# =============================================================================

# Import all command cogs
from .credits import CreditsCog, setup as setup_credits
from .interval import IntervalCog, setup as setup_interval
from .leaderboard import LeaderboardCog, setup as setup_leaderboard
from .question import QuestionCog, setup as setup_question
from .verse import VerseCog, setup as setup_verse

# Export all cogs and setup functions
__all__ = [
    # Cog classes
    "CreditsCog",
    "IntervalCog",
    "LeaderboardCog",
    "QuestionCog",
    "VerseCog",
    # Setup functions
    "setup_credits",
    "setup_interval",
    "setup_leaderboard",
    "setup_question",
    "setup_verse",
]
