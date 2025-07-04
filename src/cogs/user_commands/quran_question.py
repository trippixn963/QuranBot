import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
import asyncio
from typing import Optional, Dict, Any, List

QUESTIONS_FILE = "data/quran_questions.json"
SCORES_FILE = "data/quran_question_scores.json"

# Persistent score storage
class QuranScoreManager:
    def __init__(self, file_path=SCORES_FILE):
        self.file_path = file_path
        self.scores = self.load_scores()
    def load_scores(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    def save_scores(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.scores, f, indent=2, ensure_ascii=False)
    def add_point(self, user_id):
        user_id = str(user_id)
        self.scores[user_id] = self.scores.get(user_id, 0) + 1
        self.save_scores()
    def get_leaderboard(self, limit=10):
        return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)[:limit]

class QuranMCQView(discord.ui.View):
    def __init__(self, question: Dict[str, Any], bot_user: discord.User, score_manager: QuranScoreManager, original_message: Optional[discord.Message] = None):
        super().__init__(timeout=60)  # 1 minute timer
        self.question = question
        self.choices_en = question["choices_en"]
        self.choices_ar = question["choices_ar"]
        self.answer_en = question["answer_en"]
        self.answer_ar = question["answer_ar"]
        self.bot_user = bot_user
        self.original_message = original_message
        self.answers = {}  # user_id -> idx
        self.score_manager = score_manager
        self.timer_seconds = 60
        self.timer_task: Optional[asyncio.Task] = None
        for idx, label in enumerate(["A", "B", "C", "D"]):
            self.add_item(QuranMCQButton(label, idx, self))

    async def on_timeout(self):
        if self.timer_task:
            self.timer_task.cancel()
        if self.original_message:
            await self.reveal_results()

    async def start_timer_update(self):
        while self.timer_seconds > 0:
            await asyncio.sleep(10)
            self.timer_seconds -= 10
            if self.original_message:
                await self.update_embed_timer()
        # Final update at 0
        if self.original_message:
            await self.update_embed_timer()

    async def update_embed_timer(self):
        if not self.original_message:
            return
        embed = self.build_embed(timer_override=self.timer_seconds)
        await self.original_message.edit(embed=embed, view=self)

    def build_embed(self, timer_override=None):
        timer = timer_override if timer_override is not None else self.timer_seconds
        minutes = timer // 60
        seconds = timer % 60
        timer_str = f"⏳ Time Left: {minutes}:{seconds:02d} / 1:00"
        
        embed = discord.Embed(
            color=discord.Color.dark_embed()
        )
        if self.bot_user and self.bot_user.avatar:
            embed.set_thumbnail(url=self.bot_user.avatar.url)
        
        # Use daily verse emojis for question fields
        embed.add_field(
            name="📝 Question (English)",
            value=f"```{self.question['question_en']}```",
            inline=False
        )
        embed.add_field(
            name="🌙 Question (Arabic)",
            value=f"```{self.question['question_ar']}```",
            inline=False
        )
        
        # Add choices in separate black code block
        choices_text = ""
        for idx, (en, ar) in enumerate(zip(self.choices_en, self.choices_ar)):
            label = chr(65 + idx)
            choices_text += f"{label}. {en} / {ar}\n"
        
        embed.add_field(name="📝 Options", value=f"```{choices_text}```", inline=False)
        embed.add_field(name="Answered", value=self.get_answered_list(), inline=False)
        embed.add_field(name="Timer", value=timer_str, inline=False)
        return embed

    def get_answered_list(self):
        if not self.answers:
            return "No one yet."
        ids = list(self.answers.keys())
        mentions = [f"<@{uid}>" for uid in ids]
        return " | ".join(mentions)

    async def reveal_results(self):
        if not self.original_message:
            return
        results = []
        for user_id, idx in self.answers.items():
            guild = self.original_message.guild if self.original_message and getattr(self.original_message, 'guild', None) is not None else None
            user = guild.get_member(user_id) if guild is not None else None
            name = user.display_name if user else f"<@{user_id}>"
            selected_en = self.choices_en[idx]
            selected_ar = self.choices_ar[idx]
            correct = selected_en == self.answer_en
            emoji = "✅" if correct else "❌"
            results.append(f"{emoji} {name}: {selected_en} / {selected_ar}")
            if correct:
                self.score_manager.add_point(user_id)
        if not results:
            results_text = "No one answered in time."
        else:
            results_text = "\n".join(results)
        embed = self.build_embed(timer_override=0)
        embed.add_field(name="Correct Answer", value=f"{self.answer_en} / {self.answer_ar}", inline=False)
        embed.add_field(name="Results", value=results_text, inline=False)
        await self.original_message.edit(embed=embed, view=None)

        # Send a new embed with a jump link and the correct answer
        try:
            guild = self.original_message.guild if self.original_message and getattr(self.original_message, 'guild', None) is not None else None
            channel = self.original_message.channel if self.original_message and getattr(self.original_message, 'channel', None) is not None else None
            if guild and channel:
                jump_url = f"https://discord.com/channels/{guild.id}/{channel.id}/{self.original_message.id}"
                answer_embed = discord.Embed(
                    title="Quran Question Answer Revealed",
                    description=f"The answer to the previous question has been revealed!\n[Jump to question]({jump_url})",
                    color=discord.Color.green()
                )
                answer_embed.add_field(name="Correct Answer", value=f"{self.answer_en} / {self.answer_ar}", inline=False)
                if self.bot_user and self.bot_user.avatar:
                    answer_embed.set_thumbnail(url=self.bot_user.avatar.url)
                await channel.send(embed=answer_embed)

                # Send the leaderboard embed after the answer reveal
                leaderboard = self.score_manager.get_leaderboard()
                leaderboard_embed = discord.Embed(
                    title="Quran Question Leaderboard",
                    color=discord.Color.gold()
                )
                if self.bot_user and self.bot_user.avatar:
                    leaderboard_embed.set_thumbnail(url=self.bot_user.avatar.url)
                if not leaderboard:
                    leaderboard_embed.description = "No one has answered any questions yet!"
                else:
                    medals = ["🥇", "🥈", "🥉"]
                    lines = []
                    for i, (user_id, score) in enumerate(leaderboard):
                        medal = medals[i] if i < len(medals) else f"{i+1}."
                        lines.append(f"{medal} <@{user_id}> — **{score}** point{'s' if score != 1 else ''}")
                    leaderboard_embed.add_field(name="Top Scorers", value="\n".join(lines), inline=False)
                await channel.send(embed=leaderboard_embed)
        except Exception as e:
            pass

    async def update_answered_list(self):
        if not self.original_message:
            return
        embed = self.build_embed()
        await self.original_message.edit(embed=embed, view=self)

class QuranMCQButton(discord.ui.Button):
    def __init__(self, label: str, idx: int, view: QuranMCQView):
        # Assign a different color to each button
        style_map = [
            discord.ButtonStyle.primary,   # A - blurple
            discord.ButtonStyle.success,   # B - green
            discord.ButtonStyle.danger,    # C - red
            discord.ButtonStyle.secondary  # D - grey
        ]
        super().__init__(label=label, style=style_map[idx], custom_id=f"mcq_{label}")
        self.idx = idx
        self.mcq_view = view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in self.mcq_view.answers:
            await interaction.response.send_message(embed=self.make_feedback_embed(interaction.user, already_answered=True), ephemeral=True)
            return
        self.mcq_view.answers[user_id] = self.idx
        await interaction.response.send_message(embed=self.make_feedback_embed(interaction.user), ephemeral=True)
        await self.mcq_view.update_answered_list()

    def make_feedback_embed(self, user, already_answered=False):
        embed = discord.Embed(color=discord.Color.blurple())
        if self.mcq_view.bot_user and self.mcq_view.bot_user.avatar:
            embed.set_author(name=self.mcq_view.bot_user.display_name, icon_url=self.mcq_view.bot_user.avatar.url)
        if already_answered:
            embed.title = "You already answered!"
            embed.description = "You can only answer once."
        else:
            embed.title = "Answer Recorded!"
            embed.description = "Your answer has been recorded. The correct answer will be revealed soon!"
        return embed

class QuranQuestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.questions = self.load_questions()
        self.score_manager = QuranScoreManager()

    def load_questions(self) -> List[Dict[str, Any]]:
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def get_random_question(self) -> Optional[Dict[str, Any]]:
        if not self.questions:
            return None
        return random.choice(self.questions)

    @commands.hybrid_command(name="askquranquestion", description="Ask a random Quran multiple choice question.", with_app_command_only=True)
    async def ask_quran_question(self, ctx):
        # Restrict to owner only
        if (hasattr(ctx, 'user') and ctx.user.id != 259725211664908288) or (hasattr(ctx, 'author') and ctx.author.id != 259725211664908288):
            await ctx.send("❌ Only the bot owner can use this command.", ephemeral=True)
            return
        question = self.get_random_question()
        if not question:
            await ctx.send("❌ No questions available.")
            return
        choices_text = ""
        for idx, (en, ar) in enumerate(zip(question["choices_en"], question["choices_ar"])):
            label = chr(65 + idx)
            choices_text += f"**{label}.** {en} / {ar}\n"
        embed = discord.Embed(
            title="❓ Quran Question (MCQ)",
            description=f"**EN:** {question['question_en']}\n**AR:** {question['question_ar']}\n\n{choices_text}",
            color=discord.Color.dark_embed()
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar.url)
        embed.set_footer(text="Choose the correct answer below. You have 1 minute.")
        view = QuranMCQView(question, self.bot.user, self.score_manager)
        sent_msg = await ctx.send(embed=embed, view=view)
        view.original_message = sent_msg
        view.timer_task = asyncio.create_task(view.start_timer_update())
        await view.update_answered_list()

    @commands.hybrid_command(name="leaderboard", description="Show the Quran question leaderboard.", with_app_command_only=True)
    async def leaderboard(self, ctx):
        leaderboard = self.score_manager.get_leaderboard()
        if not leaderboard:
            await ctx.send("No scores yet!")
            return
        embed = discord.Embed(
            title="🏆 Quran Question Leaderboard",
            color=discord.Color.gold()
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        medals = ["🥇", "🥈", "🥉"]
        for idx, (user_id, score) in enumerate(leaderboard, 1):
            member = ctx.guild.get_member(int(user_id)) if ctx.guild else None
            mention = member.mention if member else f"<@{user_id}>"
            medal = medals[idx-1] if idx <= 3 else f"{idx}."
            if idx <= 3:
                entry = f"**{medal} {mention}**\nPoints: {score}"
            else:
                entry = f"{medal} {mention}\nPoints: {score}"
            embed.add_field(name="\u200b", value=entry, inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(QuranQuestionCog(bot)) 