"""QuranBot - Quiz Editor Command.

Provides Discord slash commands for managing quiz questions easily.
Allows adding, editing, and viewing quiz questions without manual JSON editing.

This module provides user-friendly commands for:
- Adding new quiz questions
- Viewing existing questions
- Editing question details
- Managing question categories
- Bulk question operations

Commands:
    /quiz add - Add a new quiz question
    /quiz list - List questions by category
    /quiz edit - Edit an existing question
    /quiz delete - Delete a question
    /quiz export - Export questions to JSON
"""

import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from ..core.logger import StructuredLogger
from ..services.data_manager import HybridDataManager


class QuizEditorCog(commands.Cog):
    """Quiz question management commands."""

    def __init__(
        self,
        bot: commands.Bot,
        data_manager: HybridDataManager,
        logger: StructuredLogger,
    ):
        self.bot = bot
        self.data_manager = data_manager
        self.logger = logger

        # Quiz categories
        self.categories = [
            "General Knowledge",
            "Surah Names",
            "Prophet Stories",
            "Islamic History",
            "Quranic Verses",
            "Islamic Practices",
            "Arabic Language",
            "Islamic Scholars",
        ]

        # Difficulty levels
        self.difficulties = ["Easy", "Medium", "Hard", "Expert"]

    @app_commands.command(name="quiz", description="Manage quiz questions")
    @app_commands.describe(
        action="Action to perform (add, list, edit, delete, export)",
        category="Question category",
        difficulty="Question difficulty level",
        question="The question text",
        correct_answer="The correct answer",
        options="Comma-separated answer options",
    )
    async def quiz_command(
        self,
        interaction: discord.Interaction,
        action: str,
        category: str | None = None,
        difficulty: str | None = None,
        question: str | None = None,
        correct_answer: str | None = None,
        options: str | None = None,
    ):
        """Main quiz management command."""

        # Check permissions (only bot owner can manage questions)
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message(
                "❌ Only the bot owner can manage quiz questions.", ephemeral=True
            )
            return

        try:
            if action.lower() == "add":
                await self._add_question(
                    interaction, category, difficulty, question, correct_answer, options
                )
            elif action.lower() == "list":
                await self._list_questions(interaction, category)
            elif action.lower() == "edit":
                await self._edit_question(
                    interaction, category, difficulty, question, correct_answer, options
                )
            elif action.lower() == "delete":
                await self._delete_question(interaction, question)
            elif action.lower() == "export":
                await self._export_questions(interaction)
            else:
                await interaction.response.send_message(
                    f"❌ Unknown action: {action}. Use: add, list, edit, delete, export",
                    ephemeral=True,
                )

        except Exception as e:
            await self.logger.error(
                "Quiz command error", {"error": str(e), "action": action}
            )
            await interaction.response.send_message(f"❌ Error: {e!s}", ephemeral=True)

    async def _add_question(
        self,
        interaction: discord.Interaction,
        category: str,
        difficulty: str,
        question: str,
        correct_answer: str,
        options: str,
    ):
        """Add a new quiz question."""

        # Validate inputs
        if not all([category, difficulty, question, correct_answer, options]):
            await interaction.response.send_message(
                "❌ All fields are required: category, difficulty, question, correct_answer, options",
                ephemeral=True,
            )
            return

        if category not in self.categories:
            await interaction.response.send_message(
                f"❌ Invalid category. Use one of: {', '.join(self.categories)}",
                ephemeral=True,
            )
            return

        if difficulty not in self.difficulties:
            await interaction.response.send_message(
                f"❌ Invalid difficulty. Use one of: {', '.join(self.difficulties)}",
                ephemeral=True,
            )
            return

        # Parse options
        option_list = [opt.strip() for opt in options.split(",")]
        if correct_answer not in option_list:
            await interaction.response.send_message(
                "❌ Correct answer must be one of the options", ephemeral=True
            )
            return

        # Create new question
        new_question = {
            "id": self._generate_question_id(),
            "category": category,
            "difficulty": difficulty,
            "question": question,
            "correct_answer": correct_answer,
            "options": option_list,
            "created_by": interaction.user.display_name,
            "created_at": interaction.created_at.isoformat(),
        }

        # Load existing questions
        questions_data = await self.data_manager.get_content("quiz_questions")
        if not questions_data:
            questions_data = {"questions": []}

        # Add new question
        questions_data["questions"].append(new_question)

        # Save to JSON
        success = await self.data_manager.update_content(
            "quiz_questions", questions_data
        )

        if success:
            embed = discord.Embed(
                title="✅ Question Added Successfully",
                description=f"**Question:** {question}",
                color=0x00FF00,
            )
            embed.add_field(name="Category", value=category, inline=True)
            embed.add_field(name="Difficulty", value=difficulty, inline=True)
            embed.add_field(name="Correct Answer", value=correct_answer, inline=True)
            embed.add_field(name="Options", value=", ".join(option_list), inline=False)
            embed.add_field(name="Question ID", value=new_question["id"], inline=True)

            await interaction.response.send_message(embed=embed)

            await self.logger.info(
                "Quiz question added",
                {
                    "question_id": new_question["id"],
                    "category": category,
                    "difficulty": difficulty,
                    "added_by": interaction.user.display_name,
                },
            )
        else:
            await interaction.response.send_message(
                "❌ Failed to save question", ephemeral=True
            )

    async def _list_questions(
        self, interaction: discord.Interaction, category: str | None = None
    ):
        """List quiz questions."""

        questions_data = await self.data_manager.get_content("quiz_questions")
        if not questions_data or "questions" not in questions_data:
            await interaction.response.send_message(
                "No questions found.", ephemeral=True
            )
            return

        questions = questions_data["questions"]

        # Filter by category if specified
        if category:
            questions = [q for q in questions if q.get("category") == category]

        if not questions:
            await interaction.response.send_message(
                f"No questions found{f' in category: {category}' if category else ''}.",
                ephemeral=True,
            )
            return

        # Create embed with question list
        embed = discord.Embed(
            title=f"📝 Quiz Questions ({len(questions)} total)",
            description=f"Showing questions{f' in category: {category}' if category else ''}",
            color=0x0099FF,
        )

        # Group by category
        categories = {}
        for q in questions:
            cat = q.get("category", "Unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(q)

        for cat, cat_questions in categories.items():
            question_list = []
            for q in cat_questions[:10]:  # Limit to 10 per category
                difficulty_emoji = {
                    "Easy": "🟢",
                    "Medium": "🟡",
                    "Hard": "🟠",
                    "Expert": "🔴",
                }.get(q.get("difficulty", "Medium"), "🟡")
                question_list.append(
                    f"{difficulty_emoji} **{q.get('question', 'No question')[:50]}...**"
                )

            if len(cat_questions) > 10:
                question_list.append(f"... and {len(cat_questions) - 10} more")

            embed.add_field(
                name=f"{cat} ({len(cat_questions)})",
                value="\n".join(question_list) if question_list else "No questions",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    async def _edit_question(
        self,
        interaction: discord.Interaction,
        category: str,
        difficulty: str,
        question: str,
        correct_answer: str,
        options: str,
    ):
        """Edit an existing question."""
        await interaction.response.send_message(
            "🔄 Question editing feature coming soon!", ephemeral=True
        )

    async def _delete_question(self, interaction: discord.Interaction, question: str):
        """Delete a question."""
        await interaction.response.send_message(
            "🔄 Question deletion feature coming soon!", ephemeral=True
        )

    async def _export_questions(self, interaction: discord.Interaction):
        """Export questions to JSON file."""
        questions_data = await self.data_manager.get_content("quiz_questions")
        if not questions_data:
            await interaction.response.send_message(
                "No questions to export.", ephemeral=True
            )
            return

        # Create export file
        export_path = Path("data/exports")
        export_path.mkdir(exist_ok=True)

        timestamp = interaction.created_at.strftime("%Y%m%d_%H%M%S")
        export_file = export_path / f"quiz_questions_export_{timestamp}.json"

        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)

        # Send file
        await interaction.response.send_message(
            f"📁 Questions exported to: `{export_file}`",
            file=discord.File(export_file),
            ephemeral=True,
        )

    def _generate_question_id(self) -> str:
        """Generate a unique question ID."""
        import uuid

        return str(uuid.uuid4())[:8]


async def setup(
    bot: commands.Bot, data_manager: HybridDataManager, logger: StructuredLogger
):
    """Setup the quiz editor cog."""
    await bot.add_cog(QuizEditorCog(bot, data_manager, logger))
