"""Quiz UI module for QuranBot."""

from .embeds import (
    create_quiz_embed,
    create_quiz_leaderboard_embed,
    create_quiz_result_embed,
    create_quiz_stats_embed,
    create_quiz_timeout_embed,
)
from .views import QuizView


__all__ = [
    "QuizView",
    "create_quiz_embed",
    "create_quiz_result_embed",
    "create_quiz_timeout_embed",
    "create_quiz_stats_embed",
    "create_quiz_leaderboard_embed",
]
