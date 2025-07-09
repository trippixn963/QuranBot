# =============================================================================
# QuranBot - Commands Package
# =============================================================================
# Contains slash commands and user interaction commands for QuranBot
#
# This package provides Discord slash commands including:
# - /credits: Shows bot information, developer credits, and GitHub repository
# - /leaderboard: Displays listening time leaderboard for Quran voice channel users
# - /verse: Manually sends a daily verse and resets the 3-hour timer
# - /question: Manually sends an Islamic knowledge quiz and resets the timer
#
# Key Features:
# - Professional slash command implementation
# - Consistent error handling with tree logging
# - Beautiful embed styling with thumbnails and links
# - User-friendly information display
# - Proper Discord API integration
# =============================================================================

# Import all command modules for easy access
from .credits import *
from .interval import setup_interval_command
from .leaderboard import *
from .question import *
from .verse import *

# Export main command functions
__all__ = [
    # Credits Command
    "setup_credits_command",
    "credits_command",
    # Leaderboard Command
    "setup_leaderboard_command",
    "leaderboard_command",
    # Verse Command
    "setup_verse_command",
    "verse_slash_command",
    # Question Command
    "setup_question_command",
    "question_slash_command",
    # Interval Command
    "setup_interval_command",
]
