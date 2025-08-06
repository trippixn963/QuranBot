"""Quiz view components for QuranBot with multi-answer support."""

import asyncio
from datetime import datetime
from typing import Dict, Set, Optional

import discord

from ...core.logger import TreeLogger
from ...services.quiz import QuizQuestion, QuizService
from .embeds import create_quiz_embed, create_quiz_result_embed, create_quiz_timeout_embed


class QuizView(discord.ui.View):
    """
    Interactive view for quiz questions with multi-answer support.

    Allows multiple users to answer, shows results in real-time,
    and runs for the full duration.
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
        super().__init__(timeout=None)  # Disable Discord's auto-timeout, we'll handle it manually
        self.question = question
        self.quiz_service = quiz_service
        self.timeout_seconds = timeout_seconds
        self.message: discord.Message | None = None
        self.original_embed: discord.Embed | None = None
        self.start_time = datetime.utcnow()
        self.timer_task: asyncio.Task | None = None
        
        # Track answers from all users
        self.user_answers: Dict[int, Dict] = {}  # user_id -> {answer, is_correct, response_time, reward}
        self.quiz_ended = False

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
            while not self.quiz_ended:
                elapsed = (datetime.utcnow() - self.start_time).total_seconds()
                remaining = max(0, self.timeout_seconds - int(elapsed))

                # Update timer field in embed
                if self.message:
                    # Create updated embed with current answers
                    updated_embed = self._create_updated_embed(remaining)
                    
                    try:
                        await self.message.edit(embed=updated_embed, view=self)
                    except discord.NotFound:
                        break
                    except Exception as e:
                        TreeLogger.warning(
                            "Failed to update timer",
                            {"error": str(e)},
                            service="QuizView",
                        )
                        break

                # Check if time is up
                if elapsed >= self.timeout_seconds:
                    TreeLogger.info(
                        "⏰ Quiz timer expired",
                        {
                            "question_id": self.question.id,
                            "elapsed": elapsed,
                            "timeout_seconds": self.timeout_seconds,
                            "quiz_ended": self.quiz_ended
                        },
                        service="QuizView"
                    )
                    
                    # Show 0 seconds first
                    if self.message and remaining != 0:
                        try:
                            zero_embed = self._create_updated_embed(0)
                            await self.message.edit(embed=zero_embed, view=self)
                            await asyncio.sleep(0.5)  # Brief pause to show 0
                        except Exception as zero_error:
                            TreeLogger.warning(
                                "Failed to show 0 seconds",
                                {"error": str(zero_error)},
                                service="QuizView"
                            )
                    
                    TreeLogger.debug(
                        "Timer reached 0, calling _handle_timeout",
                        {"question_id": self.question.id, "elapsed": elapsed},
                        service="QuizView"
                    )
                    # Trigger timeout
                    await self._handle_timeout()
                    TreeLogger.debug(
                        "_handle_timeout completed",
                        {"question_id": self.question.id},
                        service="QuizView"
                    )
                    break

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            TreeLogger.error(
                "Timer update error", {"error": str(e)}, service="QuizView"
            )

    def _create_updated_embed(self, remaining_seconds: int) -> discord.Embed:
        """Create an updated embed showing current quiz state."""
        embed = discord.Embed(color=0x00D4AA)

        # Add question text (Arabic first if available)
        arabic_text = self.question.get_question_text("arabic")
        english_text = self.question.get_question_text("english")

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
        embed.add_field(name="📚 Category", value=self.question.category, inline=True)

        # Convert difficulty number to stars
        difficulty_stars = "⭐" * self.question.difficulty
        embed.add_field(name="⭐ Difficulty", value=difficulty_stars, inline=True)

        # Timer
        embed.add_field(name="⏰ Timer", value=f"{remaining_seconds} seconds", inline=True)

        # Add current answers if any
        if self.user_answers:
            # Add spacing
            embed.add_field(name="\u200b", value="", inline=False)
            
            # Create list of users who answered
            answered_users = []
            for user_id in self.user_answers.keys():
                answered_users.append(f"<@{user_id}>")
            
            # Show who has answered (without revealing their answers)
            if answered_users:
                # Display users in a compact format
                answered_text = " | ".join(answered_users[:10])  # Show first 10 users
                if len(answered_users) > 10:
                    answered_text += f" | *+{len(answered_users) - 10} more*"
                
                embed.add_field(
                    name=f"📝 **Answered ({len(answered_users)}):**",
                    value=answered_text,
                    inline=False
                )
        
        # Add spacing
        embed.add_field(name="\u200b", value="", inline=False)

        # Add choices
        choice_text = ""
        for letter in ["A", "B", "C", "D"]:
            english_choice = self.question.get_choice_text(letter, "english")
            arabic_choice = self.question.get_choice_text(letter, "arabic")

            if english_choice and english_choice != "Choice not available":
                choice_text += f"**{letter}.** {english_choice}"

            if arabic_choice and arabic_choice != "Choice not available":
                choice_text += f"\n```\n{arabic_choice}\n```"

            choice_text += "\n\n"

        if choice_text:
            embed.add_field(name="**Answers:**", value=choice_text.strip(), inline=False)

        # Set bot thumbnail
        if self.message and self.message.guild and self.message.guild.me:
            bot = self.message.guild.me
            if bot.avatar:
                try:
                    embed.set_thumbnail(url=bot.avatar.url)
                except Exception:
                    pass

        # Set developer footer
        from ..base.components import create_developer_footer
        footer_text, developer_icon_url = create_developer_footer(
            self.message.guild.me if self.message and self.message.guild else None,
            self.message.guild if self.message else None
        )
        embed.set_footer(text=footer_text, icon_url=developer_icon_url)

        return embed

    async def on_timeout(self) -> None:
        """Handle view timeout."""
        if not self.quiz_ended:
            await self._handle_timeout()

    async def _handle_timeout(self) -> None:
        """Handle quiz timeout."""
        TreeLogger.info(
            "🚨 HANDLE TIMEOUT CALLED",
            {
                "question_id": self.question.id,
                "quiz_ended": self.quiz_ended,
                "has_message": bool(self.message),
                "total_answers": len(self.user_answers)
            },
            service="QuizView"
        )
        try:
            TreeLogger.debug(
                "Handle timeout called",
                {"question_id": self.question.id},
                service="QuizView"
            )
            self.quiz_ended = True
            
            if self.timer_task:
                self.timer_task.cancel()

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            # Create final results embed
            TreeLogger.debug(
                "Creating final results embed",
                {"question_id": self.question.id},
                service="QuizView"
            )
            try:
                final_embed = self._create_final_results_embed()
                TreeLogger.debug(
                    "Final results embed created",
                    {
                        "embed_title": final_embed.title,
                        "fields_count": len(final_embed.fields),
                        "has_footer": bool(final_embed.footer)
                    },
                    service="QuizView"
                )
            except Exception as embed_error:
                import traceback
                TreeLogger.error(
                    "Failed to create final results embed",
                    {
                        "error": str(embed_error),
                        "error_type": type(embed_error).__name__,
                        "traceback": traceback.format_exc()
                    },
                    service="QuizView"
                )
                raise

            TreeLogger.info(
                "📍 Checkpoint: Embed created, about to update message",
                {"question_id": self.question.id},
                service="QuizView"
            )

            # Skip updating original message - it's causing issues
            TreeLogger.info(
                "Skipping original message update to prevent hanging",
                {"message_id": self.message.id if self.message else None},
                service="QuizView"
            )
                
            # Send results as a new message
            results_message = None
            
            # Force send results no matter what
            TreeLogger.info(
                "🎯 FORCING RESULTS SEND",
                {
                    "has_message": bool(self.message),
                    "has_channel": bool(self.message.channel) if self.message else False,
                    "message_id": self.message.id if self.message else None,
                    "channel_id": self.message.channel.id if self.message and self.message.channel else None,
                },
                service="QuizView"
            )
            
            if self.message and self.message.channel:
                TreeLogger.debug(
                    "Attempting to send results message",
                    {
                        "channel_id": self.message.channel.id,
                        "channel_name": self.message.channel.name,
                        "embed_title": final_embed.title,
                        "embed_color": final_embed.color,
                        "fields_count": len(final_embed.fields)
                    },
                    service="QuizView"
                )
                try:
                    # Try multiple times
                    for attempt in range(3):
                        try:
                            TreeLogger.info(
                                f"📤 Sending results message (attempt {attempt + 1})",
                                {"channel_id": self.message.channel.id},
                                service="QuizView"
                            )
                            results_message = await self.message.channel.send(embed=final_embed)
                            TreeLogger.success(
                                "✅ Results message sent successfully",
                                {
                                    "message_id": results_message.id,
                                    "channel_id": self.message.channel.id,
                                    "attempt": attempt + 1
                                },
                                service="QuizView"
                            )
                            break
                        except Exception as e:
                            TreeLogger.error(
                                f"❌ Attempt {attempt + 1} failed",
                                {"error": str(e)},
                                service="QuizView"
                            )
                            if attempt == 2:  # Last attempt
                                raise
                            await asyncio.sleep(0.5)
                except Exception as send_error:
                    import traceback
                    TreeLogger.error(
                        "Failed to send results message after all attempts",
                        {
                            "error": str(send_error),
                            "error_type": type(send_error).__name__,
                            "traceback": traceback.format_exc(),
                            "channel_id": self.message.channel.id
                        },
                        service="QuizView"
                    )
                    # Don't raise, just log
            else:
                TreeLogger.error(
                    "❌ CRITICAL: Cannot send results - no message or channel",
                    {
                        "has_message": bool(self.message),
                        "has_channel": bool(self.message.channel) if self.message else False,
                        "message_type": type(self.message).__name__ if self.message else None
                    },
                    service="QuizView"
                )

            TreeLogger.info(
                "Quiz timed out",
                {
                    "question_id": self.question.id,
                    "total_answers": len(self.user_answers),
                    "correct_answers": sum(1 for a in self.user_answers.values() if a["is_correct"])
                },
                service="QuizView"
            )
            
            # Clean up quiz data
            if self.quiz_service:
                await self.quiz_service.cleanup_finished_quiz(self.question.id)
                
            # Schedule deletion of both messages after 60 seconds
            if self.message or results_message:
                TreeLogger.info(
                    "📅 Scheduling message deletion in 60 seconds",
                    {
                        "quiz_message_id": self.message.id if self.message else None,
                        "results_message_id": results_message.id if results_message else None
                    },
                    service="QuizView"
                )
                asyncio.create_task(self._schedule_message_deletion(self.message, results_message))
            else:
                TreeLogger.warning(
                    "No messages to schedule for deletion",
                    service="QuizView"
                )

        except Exception as e:
            import traceback
            TreeLogger.error(
                "Failed to handle timeout", 
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "question_id": self.question.id if self.question else None,
                    "message_exists": bool(self.message),
                    "channel_exists": bool(self.message.channel) if self.message else False,
                    "stage": "handle_timeout"
                }, 
                service="QuizView"
            )
            # Try to send error message to channel
            try:
                if self.message and self.message.channel:
                    error_embed = discord.Embed(
                        title="❌ Quiz Error",
                        description="An error occurred while processing quiz results.",
                        color=0xFF0000
                    )
                    await self.message.channel.send(embed=error_embed)
            except:
                pass

    def _create_final_results_embed(self) -> discord.Embed:
        """Create final results embed showing all answers and correct answer."""
        # Determine color based on results
        if not self.user_answers:
            color = 0xF39C12  # Orange for no answers
            title = "⏰ Quiz Ended - No Answers"
        else:
            correct_count = sum(1 for a in self.user_answers.values() if a["is_correct"])
            if correct_count > 0:
                color = 0x2ECC71  # Green if anyone got it right
                title = f"✅ Quiz Ended - {correct_count} Correct Answer{'s' if correct_count != 1 else ''}"
            else:
                color = 0xE74C3C  # Red if all wrong
                title = "❌ Quiz Ended - No Correct Answers"

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.utcnow()
        )

        # Show correct answer in a code block
        correct_choice_text = self.question.get_choice_text(self.question.correct_answer, "english")
        embed.add_field(
            name="Correct Answer",
            value=f"```\n{self.question.correct_answer}. {correct_choice_text}\n```",
            inline=False,
        )

        # Add spacing
        embed.add_field(name="\u200b", value="", inline=False)

        # Show explanation in a code block if available
        explanation_text = self.question.get_explanation_text("english")
        if explanation_text:
            embed.add_field(
                name="📚 Explanation", 
                value=f"```\n{explanation_text}\n```", 
                inline=False
            )
            # Add spacing
            embed.add_field(name="\u200b", value="", inline=False)

        # Show reference in a code block if available
        if self.question.reference:
            embed.add_field(
                name="📖 Reference", 
                value=f"```\n{self.question.reference}\n```", 
                inline=False
            )
            # Add spacing
            embed.add_field(name="\u200b", value="", inline=False)

        # Show all participants
        if self.user_answers:
            # Sort by response time
            sorted_answers = sorted(
                self.user_answers.items(),
                key=lambda x: x[1]["response_time"]
            )
            
            results_text = ""
            for i, (user_id, answer_data) in enumerate(sorted_answers[:10]):  # Show top 10
                emoji = "✅" if answer_data["is_correct"] else "❌"
                answer_letter = f"**{answer_data['answer']}**"
                time_str = f"{answer_data['response_time']:.1f}s"
                reward_str = ""
                if answer_data.get("reward"):
                    reward_str = f" (+{answer_data['reward']} coins)" if answer_data["reward"] > 0 else f" ({answer_data['reward']} coins)"
                
                results_text += f"{i+1}. {emoji} <@{user_id}> - {answer_letter} ({time_str}){reward_str}\n"
            
            if len(self.user_answers) > 10:
                results_text += f"\n*and {len(self.user_answers) - 10} more participants...*"
            
            embed.add_field(
                name=f"**Participants ({len(self.user_answers)}):**",
                value=results_text,
                inline=False
            )

        # Set bot thumbnail
        if self.message and self.message.guild and self.message.guild.me:
            bot = self.message.guild.me
            if bot.avatar:
                try:
                    embed.set_thumbnail(url=bot.avatar.url)
                except Exception:
                    pass

        # Set developer footer
        from ..base.components import create_developer_footer
        footer_text, developer_icon_url = create_developer_footer(
            self.message.guild.me if self.message and self.message.guild else None,
            self.message.guild if self.message else None
        )
        embed.set_footer(text=footer_text, icon_url=developer_icon_url)

        return embed

    async def _schedule_message_deletion(self, quiz_message: discord.Message, results_message: discord.Message) -> None:
        """Schedule deletion of quiz and results messages after 60 seconds."""
        TreeLogger.info(
            "⏳ Starting 60-second deletion timer",
            {
                "quiz_message_id": quiz_message.id if quiz_message else None,
                "results_message_id": results_message.id if results_message else None
            },
            service="QuizView"
        )
        
        await asyncio.sleep(60)
        
        TreeLogger.info(
            "🗑️ Deletion timer expired, deleting messages",
            {
                "quiz_message_id": quiz_message.id if quiz_message else None,
                "results_message_id": results_message.id if results_message else None
            },
            service="QuizView"
        )
        
        try:
            # Delete quiz message
            if quiz_message:
                try:
                    await quiz_message.delete()
                    TreeLogger.success(
                        "✅ Quiz message deleted successfully",
                        {"message_id": quiz_message.id},
                        service="QuizView"
                    )
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    TreeLogger.warning(
                        "No permission to delete quiz message",
                        {"message_id": quiz_message.id},
                        service="QuizView"
                    )
            
            # Delete results message
            if results_message:
                try:
                    await results_message.delete()
                    TreeLogger.success(
                        "✅ Results message deleted successfully",
                        {"message_id": results_message.id},
                        service="QuizView"
                    )
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    TreeLogger.warning(
                        "No permission to delete results message",
                        {"message_id": results_message.id},
                        service="QuizView"
                    )
                    
        except Exception as e:
            TreeLogger.error(
                "Failed to delete quiz messages",
                {"error": str(e)},
                service="QuizView"
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
            # Check if quiz has ended
            if self.quiz_ended:
                await interaction.response.send_message(
                    "This quiz has already ended!", ephemeral=True
                )
                return

            # Check if user already answered
            if interaction.user.id in self.user_answers:
                await interaction.response.send_message(
                    f"You already answered **{self.user_answers[interaction.user.id]['answer']}**!",
                    ephemeral=True
                )
                return

            # Calculate response time
            response_time = (datetime.utcnow() - self.start_time).total_seconds()

            # Record answer
            reward_given, reward_amount = await self.quiz_service.record_answer(
                user_id=str(interaction.user.id),
                question_id=self.question.id,
                answer=answer,
                is_correct=is_correct,
                response_time=response_time,
            )

            # Store answer
            self.user_answers[interaction.user.id] = {
                "answer": answer,
                "is_correct": is_correct,
                "response_time": response_time,
                "reward": reward_amount if reward_given else 0
            }

            # Don't send any response - users will see their name in the embed
            # This prevents cheating and keeps the suspense
            await interaction.response.defer(ephemeral=True)

            # Update the main embed (the timer task will handle this)
            
            TreeLogger.info(
                "Quiz answer recorded",
                {
                    "user_id": interaction.user.id,
                    "question_id": self.question.id,
                    "answer": answer,
                    "correct": is_correct,
                    "response_time": response_time,
                    "reward_amount": reward_amount,
                    "total_answers": len(self.user_answers)
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