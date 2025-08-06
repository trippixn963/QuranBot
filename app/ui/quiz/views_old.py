"""Quiz view components for QuranBot."""

import asyncio
from datetime import datetime
from typing import Optional

import discord

from ...core.logger import TreeLogger
from ...services.quiz import QuizQuestion, QuizService
from .embeds import create_quiz_result_embed, create_quiz_timeout_embed


class QuizView(discord.ui.View):
    """
    Interactive view for quiz questions.

    Provides buttons for answering quiz questions with timer
    functionality and result tracking.
    """

    def __init__(
        self,
        question: QuizQuestion,
        quiz_service: QuizService,
        timeout_seconds: int = 60,
    ):
        """
        Initialize quiz view.

        Args
        ----
            question: Quiz question object.
            quiz_service: Quiz service instance.
            timeout_seconds: Time limit for answering.

        """
        super().__init__(timeout=timeout_seconds)
        self.question = question
        self.quiz_service = quiz_service
        self.timeout_seconds = timeout_seconds
        self.message: discord.Message | None = None
        self.original_embed: discord.Embed | None = None
        self.answered = False
        self.start_time = datetime.utcnow()
        self.timer_task: asyncio.Task | None = None

        # Create answer buttons with different colors
        button_styles = {
            "A": discord.ButtonStyle.primary,    # Blue
            "B": discord.ButtonStyle.success,    # Green
            "C": discord.ButtonStyle.danger,     # Red
            "D": discord.ButtonStyle.secondary,  # Gray
        }
        
        for letter in ["A", "B", "C", "D"]:
            button = QuizAnswerButton(
                letter=letter,
                style=button_styles[letter],
                is_correct=(letter == self.question.correct_answer),
            )
            self.add_item(button)

    async def start_timer(self) -> None:
        """Start the countdown timer."""
        self.timer_task = asyncio.create_task(self._update_timer())

    async def _update_timer(self) -> None:
        """Update timer display every second."""
        try:
            while not self.answered and self.timeout_seconds > 0:
                elapsed = (datetime.utcnow() - self.start_time).seconds
                remaining = max(0, self.timeout_seconds - elapsed)

                if remaining <= 0:
                    break

                # Update timer field in embed
                if self.original_embed and self.message:
                    for i, field in enumerate(self.original_embed.fields):
                        if field.name == "⏰ Timer":
                            self.original_embed.set_field_at(
                                i,
                                name="⏰ Timer",
                                value=f"{remaining} seconds",
                                inline=True,
                            )
                            break

                    try:
                        await self.message.edit(embed=self.original_embed, view=self)
                    except discord.NotFound:
                        break
                    except Exception as e:
                        TreeLogger.warning(
                            "Failed to update timer",
                            {"error": str(e)},
                            service="QuizView",
                        )
                        break

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            TreeLogger.error(
                "Timer update error", {"error": str(e)}, service="QuizView"
            )

    async def on_timeout(self) -> None:
        """Handle view timeout."""
        if not self.answered:
            await self._handle_timeout()

    async def _handle_timeout(self) -> None:
        """Handle quiz timeout."""
        try:
            if self.timer_task:
                self.timer_task.cancel()

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            # Create timeout embed
            timeout_embed = create_quiz_timeout_embed(
                self.question, 
                bot=self.message.guild.me if self.message else None,
                guild=self.message.guild if self.message else None
            )

            # Update message
            if self.message:
                await self.message.edit(embed=timeout_embed, view=self)

            TreeLogger.info(
                "Quiz timed out", {"question_id": self.question.id}, service="QuizView"
            )
            
            # Clean up quiz data
            if self.quiz_service:
                await self.quiz_service.cleanup_finished_quiz(self.question.id)

        except Exception as e:
            TreeLogger.error(
                "Failed to handle timeout", {"error": str(e)}, service="QuizView"
            )

    async def handle_answer(
        self, interaction: discord.Interaction, answer: str, is_correct: bool
    ) -> None:
        """
        Handle user answer.

        Args
        ----
            interaction: Discord interaction.
            answer: User's answer letter.
            is_correct: Whether answer is correct.

        """
        try:
            if self.answered:
                await interaction.response.send_message(
                    "This quiz has already been answered!", ephemeral=True
                )
                return

            self.answered = True

            # Cancel timer
            if self.timer_task:
                self.timer_task.cancel()

            # Calculate response time
            response_time = (datetime.utcnow() - self.start_time).total_seconds()

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            # Record answer
            reward_given, reward_amount = await self.quiz_service.record_answer(
                user_id=str(interaction.user.id),
                question_id=self.question.id,
                answer=answer,
                is_correct=is_correct,
                response_time=response_time,
            )

            # Create result embed
            result_embed = create_quiz_result_embed(
                self.question,
                user_answer=answer,
                is_correct=is_correct,
                bot=interaction.client,
                guild=interaction.guild,
                response_time=response_time,
                reward_amount=reward_amount if reward_given else None,
            )

            # Update message
            await interaction.response.edit_message(embed=result_embed, view=self)

            TreeLogger.info(
                "Quiz answered",
                {
                    "user_id": interaction.user.id,
                    "question_id": self.question.id,
                    "answer": answer,
                    "correct": is_correct,
                    "response_time": response_time,
                    "reward_amount": reward_amount,
                },
                service="QuizView",
            )

        except Exception as e:
            TreeLogger.error(
                "Failed to handle answer",
                {
                    "user_id": interaction.user.id,
                    "error": str(e),
                    "traceback": True,
                    "question_id": self.question.id,
                    "answer": answer,
                },
                service="QuizView",
            )

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred processing your answer.", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "An error occurred processing your answer.", ephemeral=True
                    )
            except Exception:
                pass


class QuizAnswerButton(discord.ui.Button):
    """Button for quiz answer selection."""

    def __init__(self, letter: str, style: discord.ButtonStyle, is_correct: bool):
        """
        Initialize answer button.

        Args
        ----
            letter: Answer letter (A, B, C, D).
            style: Button style/color.
            is_correct: Whether this is the correct answer.

        """
        super().__init__(
            style=style,
            label=letter,  # Just the letter
            custom_id=f"quiz_answer_{letter}",
        )
        self.letter = letter
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction) -> None:
        """Handle button click."""
        await self.view.handle_answer(interaction, self.letter, self.is_correct)
