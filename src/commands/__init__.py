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

# =============================================================================
# Command Loading Function
# =============================================================================


async def load_commands(bot, container):
    """Load all command cogs with dependency injection"""
    try:
        from src.core.webhook_logger import LogLevel
        
        # Log command loading start
        webhook_router = container.get("webhook_router")
        if webhook_router:
            await webhook_router.log_bot_event(
                event_type="commands_loading",
                title="🔧 Loading Commands",
                description="Loading Discord slash commands",
                level=LogLevel.INFO,
                context={
                    "commands_to_load": ["credits", "interval", "leaderboard", "question", "verse"],
                },
            )
        
        # Load commands
        await setup_credits(bot, container)
        await setup_interval(bot, container)
        await setup_leaderboard(bot, container)
        await setup_question(bot, container)
        await setup_verse(bot, container)
        
        # Log successful command loading
        if webhook_router:
            await webhook_router.log_bot_event(
                event_type="commands_loaded",
                title="✅ Commands Loaded",
                description="All Discord slash commands loaded successfully",
                level=LogLevel.INFO,
                context={
                    "commands_loaded": ["credits", "interval", "leaderboard", "question", "verse"],
                    "total_commands": 5,
                },
            )
            
    except Exception as e:
        # Log command loading error
        if webhook_router:
            await webhook_router.log_error_event(
                event_type="command_loading_error",
                title="❌ Command Loading Error",
                description="Failed to load Discord commands",
                level=LogLevel.ERROR,
                context={
                    "error": str(e),
                    "commands_attempted": ["credits", "interval", "leaderboard", "question", "verse"],
                },
            )
        raise


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
    # Command loading
    "load_commands",
]
