# QuranBot API Usage Examples

This document provides practical examples of how to interact with the QuranBot API using various programming languages and tools.

## Table of Contents

- [Authentication](#authentication)
- [Audio Control Examples](#audio-control-examples)
- [Quiz System Examples](#quiz-system-examples)
- [AI Assistant Examples](#ai-assistant-examples)
- [Analytics Examples](#analytics-examples)
- [Error Handling Examples](#error-handling-examples)
- [SDK Examples](#sdk-examples)

## Authentication

All API requests require proper Discord bot authentication. The bot uses Discord's standard authentication mechanisms.

### Discord.py Example
```python
import discord
from discord.ext import commands

# Initialize bot with proper intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
```

### HTTP Request Headers
```http
Authorization: Bot paste_your_bot_token_here
Content-Type: application/json
User-Agent: QuranBot/4.0.1
```

## Audio Control Examples

### Start Audio Playback

#### Python (discord.py)
```python
@bot.slash_command(name="play", description="Start Quran audio playback")
async def play_audio(ctx, surah: int = None, reciter: str = None):
    """Start audio playbook with optional surah and reciter selection."""

    # Validate surah number
    if surah and not (1 <= surah <= 114):
        await ctx.respond("❌ Surah number must be between 1 and 114")
        return

    # Get audio service
    audio_service = bot.get_cog('AudioService')

    try:
        # Start playback
        result = await audio_service.start_playback(
            surah_number=surah,
            reciter=reciter,
            resume_position=True
        )

        if result['success']:
            embed = discord.Embed(
                title="🎵 Audio Playback Started",
                description=f"Now playing: **Surah {result['current_surah']}**",
                color=0x00ff00
            )
            embed.add_field(
                name="Reciter",
                value=result['current_reciter'],
                inline=True
            )
            embed.add_field(
                name="Position",
                value=f"{result['position_seconds']:.1f}s",
                inline=True
            )
            await ctx.respond(embed=embed)
        else:
            await ctx.respond("❌ Failed to start audio playback")

    except Exception as e:
        await ctx.respond(f"❌ Error: {str(e)}")
```

#### JavaScript (Node.js with discord.js)
```javascript
const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('play')
        .setDescription('Start Quran audio playback')
        .addIntegerOption(option =>
            option.setName('surah')
                .setDescription('Surah number (1-114)')
                .setMinValue(1)
                .setMaxValue(114)
                .setRequired(false))
        .addStringOption(option =>
            option.setName('reciter')
                .setDescription('Reciter name')
                .addChoices(
                    { name: 'Saad Al Ghamdi', value: 'Saad Al Ghamdi' },
                    { name: 'Abdul Basit', value: 'Abdul Basit Abdul Samad' },
                    { name: 'Maher Al Muaiqly', value: 'Maher Al Muaiqly' }
                )
                .setRequired(false)),

    async execute(interaction) {
        const surah = interaction.options.getInteger('surah');
        const reciter = interaction.options.getString('reciter');

        try {
            const audioService = interaction.client.audioService;
            const result = await audioService.startPlayback({
                surah_number: surah,
                reciter: reciter,
                resume_position: true
            });

            if (result.success) {
                const embed = {
                    title: '🎵 Audio Playback Started',
                    description: `Now playing: **Surah ${result.current_surah}**`,
                    color: 0x00ff00,
                    fields: [
                        {
                            name: 'Reciter',
                            value: result.current_reciter,
                            inline: true
                        },
                        {
                            name: 'Position',
                            value: `${result.position_seconds.toFixed(1)}s`,
                            inline: true
                        }
                    ]
                };

                await interaction.reply({ embeds: [embed] });
            } else {
                await interaction.reply('❌ Failed to start audio playback');
            }
        } catch (error) {
            console.error('Audio playback error:', error);
            await interaction.reply(`❌ Error: ${error.message}`);
        }
    }
};
```

#### cURL Example
```bash
# Start audio playback
curl -X POST "https://api.quranbot.example.com/audio/play" \
  -H "Authorization: Bot paste_your_bot_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "surah_number": 1,
    "reciter": "Saad Al Ghamdi",
    "resume_position": true
  }'
```

### Get Audio Status

#### Python Example
```python
@bot.slash_command(name="status", description="Get current audio status")
async def audio_status(ctx):
    """Get current audio playback status."""

    audio_service = bot.get_cog('AudioService')

    try:
        status = await audio_service.get_status()

        # Create status embed
        embed = discord.Embed(
            title="🎵 Audio Status",
            color=0x0099ff if status['is_playing'] else 0x999999
        )

        # Add status fields
        embed.add_field(
            name="Status",
            value="▶️ Playing" if status['is_playing'] else "⏸️ Stopped",
            inline=True
        )

        if status['is_playing']:
            embed.add_field(
                name="Current Surah",
                value=f"Surah {status['current_surah']}",
                inline=True
            )
            embed.add_field(
                name="Reciter",
                value=status['current_reciter'],
                inline=True
            )
            embed.add_field(
                name="Progress",
                value=f"{status['position_seconds']:.1f}s / {status['total_duration']:.1f}s",
                inline=False
            )
            embed.add_field(
                name="Listeners",
                value=f"{status['listeners_count']} active",
                inline=True
            )

            # Add progress bar
            progress = status['position_seconds'] / status['total_duration']
            progress_bar = create_progress_bar(progress, 20)
            embed.add_field(
                name="Progress Bar",
                value=f"`{progress_bar}` {progress*100:.1f}%",
                inline=False
            )

        await ctx.respond(embed=embed)

    except Exception as e:
        await ctx.respond(f"❌ Error getting status: {str(e)}")

def create_progress_bar(progress, length=20):
    """Create a text-based progress bar."""
    filled = int(progress * length)
    bar = "█" * filled + "░" * (length - filled)
    return bar
```

### Jump to Specific Surah

#### Python Example
```python
@bot.slash_command(name="jump", description="Jump to a specific surah")
async def jump_to_surah(ctx, surah_number: int):
    """Jump to a specific surah during playback."""

    # Validate surah number
    if not (1 <= surah_number <= 114):
        await ctx.respond("❌ Surah number must be between 1 and 114")
        return

    audio_service = bot.get_cog('AudioService')

    try:
        result = await audio_service.jump_to_surah(surah_number)

        if result['success']:
            # Get surah info
            surah_info = get_surah_info(surah_number)

            embed = discord.Embed(
                title="⏭️ Jumped to Surah",
                description=f"Now playing: **{surah_info['name_english']}** (Surah {surah_number})",
                color=0x00ff00
            )
            embed.add_field(
                name="Arabic Name",
                value=surah_info['name_arabic'],
                inline=True
            )
            embed.add_field(
                name="Verses",
                value=f"{surah_info['verses_count']} verses",
                inline=True
            )
            embed.add_field(
                name="Revelation",
                value=surah_info['revelation_place'],
                inline=True
            )

            await ctx.respond(embed=embed)
        else:
            await ctx.respond(f"❌ Failed to jump to Surah {surah_number}")

    except Exception as e:
        await ctx.respond(f"❌ Error: {str(e)}")
```

## Quiz System Examples

### Start a Quiz

#### Python Example
```python
@bot.slash_command(name="quiz", description="Start an Islamic knowledge quiz")
async def start_quiz(ctx, category: str = None, difficulty: str = None):
    """Start a new Islamic knowledge quiz."""

    quiz_service = bot.get_cog('QuizService')

    try:
        # Start quiz session
        session = await quiz_service.start_quiz(
            user_id=ctx.author.id,
            category=category,
            difficulty=difficulty,
            question_count=5
        )

        # Create quiz embed
        embed = discord.Embed(
            title="🧠 Islamic Knowledge Quiz",
            description="Test your Islamic knowledge!",
            color=0x9932cc
        )

        # Add current question
        question = session['current_question']
        embed.add_field(
            name=f"Question {session['question_number']}/{session['total_questions']}",
            value=question['question'],
            inline=False
        )

        # Add choices
        choices_text = ""
        for i, choice in enumerate(question['choices']):
            choices_text += f"{chr(65+i)}. {choice}\n"

        embed.add_field(
            name="Choices",
            value=choices_text,
            inline=False
        )

        embed.add_field(
            name="Category",
            value=question['category'].title(),
            inline=True
        )
        embed.add_field(
            name="Difficulty",
            value=question['difficulty'].title(),
            inline=True
        )
        embed.add_field(
            name="Time Limit",
            value=f"{session['time_limit_seconds']}s",
            inline=True
        )

        # Create answer buttons
        view = QuizView(session['session_id'], question['choices'])

        await ctx.respond(embed=embed, view=view)

    except Exception as e:
        await ctx.respond(f"❌ Error starting quiz: {str(e)}")

class QuizView(discord.ui.View):
    """Interactive quiz answer buttons."""

    def __init__(self, session_id, choices):
        super().__init__(timeout=30)
        self.session_id = session_id

        # Create buttons for each choice
        for i, choice in enumerate(choices):
            button = discord.ui.Button(
                label=f"{chr(65+i)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"quiz_answer_{i}"
            )
            button.callback = self.create_answer_callback(i)
            self.add_item(button)

    def create_answer_callback(self, answer_index):
        async def answer_callback(interaction):
            await self.handle_answer(interaction, answer_index)
        return answer_callback

    async def handle_answer(self, interaction, answer_index):
        """Handle quiz answer submission."""
        quiz_service = interaction.client.get_cog('QuizService')

        try:
            result = await quiz_service.submit_answer(
                session_id=self.session_id,
                answer_index=answer_index,
                user_id=interaction.user.id
            )

            # Create result embed
            embed = discord.Embed(
                title="✅ Correct!" if result['correct'] else "❌ Incorrect",
                color=0x00ff00 if result['correct'] else 0xff0000
            )

            embed.add_field(
                name="Explanation",
                value=result['explanation'],
                inline=False
            )

            embed.add_field(
                name="Points Earned",
                value=f"+{result['points_earned']} points",
                inline=True
            )
            embed.add_field(
                name="Total Score",
                value=f"{result['total_score']} points",
                inline=True
            )

            if not result['session_complete']:
                embed.add_field(
                    name="Next Question",
                    value="Loading next question...",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Quiz Complete!",
                    value=f"Final Score: {result['total_score']} points",
                    inline=False
                )

            await interaction.response.edit_message(embed=embed, view=None)

            # Show next question if quiz continues
            if not result['session_complete'] and 'next_question' in result:
                await self.show_next_question(interaction, result)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    async def show_next_question(self, interaction, result):
        """Show the next quiz question."""
        # Implementation for next question...
        pass
```

### Get Quiz Leaderboard

#### Python Example
```python
@bot.slash_command(name="leaderboard", description="Show quiz leaderboard")
async def quiz_leaderboard(ctx, limit: int = 10):
    """Show the quiz leaderboard."""

    if not (1 <= limit <= 50):
        await ctx.respond("❌ Limit must be between 1 and 50")
        return

    quiz_service = bot.get_cog('QuizService')

    try:
        leaderboard = await quiz_service.get_leaderboard(limit=limit)

        embed = discord.Embed(
            title="🏆 Quiz Leaderboard",
            description=f"Top {len(leaderboard['leaderboard'])} performers",
            color=0xffd700
        )

        leaderboard_text = ""
        for entry in leaderboard['leaderboard']:
            rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(entry['rank'], "🏅")
            leaderboard_text += (
                f"{rank_emoji} **{entry['rank']}.** {entry['username']}\n"
                f"   📊 {entry['total_score']} points | "
                f"✅ {entry['accuracy_rate']:.1f}% accuracy | "
                f"🔥 {entry['current_streak']} streak\n\n"
            )

        embed.add_field(
            name="Rankings",
            value=leaderboard_text or "No participants yet",
            inline=False
        )

        embed.add_field(
            name="Total Participants",
            value=str(leaderboard['total_participants']),
            inline=True
        )

        embed.set_footer(
            text=f"Last updated: {leaderboard['last_updated']}"
        )

        await ctx.respond(embed=embed)

    except Exception as e:
        await ctx.respond(f"❌ Error getting leaderboard: {str(e)}")
```

## AI Assistant Examples

### Ask Islamic Question

#### Python Example
```python
@bot.slash_command(name="ask", description="Ask the Islamic AI assistant")
async def ask_ai(ctx, question: str, language: str = "en"):
    """Ask a question to the Islamic AI assistant."""

    # Validate question length
    if len(question) < 10:
        await ctx.respond("❌ Question must be at least 10 characters long")
        return

    if len(question) > 500:
        await ctx.respond("❌ Question must be less than 500 characters")
        return

    ai_service = bot.get_cog('AIService')

    # Defer response as AI might take time
    await ctx.defer()

    try:
        response = await ai_service.ask_question(
            question=question,
            user_id=ctx.author.id,
            language=language
        )

        embed = discord.Embed(
            title="🤖 Islamic AI Assistant",
            color=0x00bfff
        )

        embed.add_field(
            name="❓ Question",
            value=f"*{question}*",
            inline=False
        )

        embed.add_field(
            name="💡 Answer",
            value=response['answer'],
            inline=False
        )

        if response.get('sources'):
            sources_text = "\n".join([f"• {source}" for source in response['sources']])
            embed.add_field(
                name="📚 Sources",
                value=sources_text,
                inline=False
            )

        embed.add_field(
            name="🎯 Confidence",
            value=f"{response['confidence_score']*100:.1f}%",
            inline=True
        )

        embed.add_field(
            name="⏱️ Response Time",
            value=f"{response['response_time_ms']}ms",
            inline=True
        )

        embed.set_footer(
            text="Rate limit: 1 question per hour per user"
        )

        await ctx.followup.send(embed=embed)

    except Exception as e:
        error_messages = {
            'AI_RATE_LIMITED': "⏰ You can ask one question per hour. Please try again later.",
            'AI_QUESTION_TOO_LONG': "❌ Your question is too long. Please keep it under 500 characters.",
            'AI_INAPPROPRIATE_CONTENT': "❌ Please ask questions related to Islamic topics only.",
            'AI_SERVICE_UNAVAILABLE': "🔧 AI service is temporarily unavailable. Please try again later."
        }

        error_code = getattr(e, 'code', 'UNKNOWN_ERROR')
        message = error_messages.get(error_code, f"❌ Error: {str(e)}")

        await ctx.followup.send(message)
```

#### JavaScript Example
```javascript
const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('ask')
        .setDescription('Ask the Islamic AI assistant')
        .addStringOption(option =>
            option.setName('question')
                .setDescription('Your Islamic question')
                .setRequired(true)
                .setMinLength(10)
                .setMaxLength(500))
        .addStringOption(option =>
            option.setName('language')
                .setDescription('Response language')
                .addChoices(
                    { name: 'English', value: 'en' },
                    { name: 'Arabic', value: 'ar' }
                )
                .setRequired(false)),

    async execute(interaction) {
        const question = interaction.options.getString('question');
        const language = interaction.options.getString('language') || 'en';

        // Defer reply as AI processing takes time
        await interaction.deferReply();

        try {
            const aiService = interaction.client.aiService;
            const response = await aiService.askQuestion({
                question: question,
                user_id: interaction.user.id,
                language: language
            });

            const embed = {
                title: '🤖 Islamic AI Assistant',
                color: 0x00bfff,
                fields: [
                    {
                        name: '❓ Question',
                        value: `*${question}*`,
                        inline: false
                    },
                    {
                        name: '💡 Answer',
                        value: response.answer,
                        inline: false
                    }
                ],
                footer: {
                    text: 'Rate limit: 1 question per hour per user'
                }
            };

            if (response.sources && response.sources.length > 0) {
                const sourcesText = response.sources.map(source => `• ${source}`).join('\n');
                embed.fields.push({
                    name: '📚 Sources',
                    value: sourcesText,
                    inline: false
                });
            }

            embed.fields.push(
                {
                    name: '🎯 Confidence',
                    value: `${(response.confidence_score * 100).toFixed(1)}%`,
                    inline: true
                },
                {
                    name: '⏱️ Response Time',
                    value: `${response.response_time_ms}ms`,
                    inline: true
                }
            );

            await interaction.editReply({ embeds: [embed] });

        } catch (error) {
            const errorMessages = {
                'AI_RATE_LIMITED': '⏰ You can ask one question per hour. Please try again later.',
                'AI_QUESTION_TOO_LONG': '❌ Your question is too long. Please keep it under 500 characters.',
                'AI_INAPPROPRIATE_CONTENT': '❌ Please ask questions related to Islamic topics only.',
                'AI_SERVICE_UNAVAILABLE': '🔧 AI service is temporarily unavailable. Please try again later.'
            };

            const message = errorMessages[error.code] || `❌ Error: ${error.message}`;
            await interaction.editReply(message);
        }
    }
};
```

## Analytics Examples

### Get User Statistics

#### Python Example
```python
@bot.slash_command(name="stats", description="View your listening and quiz statistics")
async def user_stats(ctx, user: discord.Member = None):
    """Get user statistics."""

    target_user = user or ctx.author
    analytics_service = bot.get_cog('AnalyticsService')

    try:
        stats = await analytics_service.get_user_analytics(target_user.id)

        embed = discord.Embed(
            title=f"📊 Statistics for {target_user.display_name}",
            color=0x9932cc
        )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        # Listening statistics
        embed.add_field(
            name="🎵 Listening Stats",
            value=(
                f"**Total Time:** {stats['total_listening_time_hours']:.1f} hours\n"
                f"**Favorite Reciters:** {', '.join(stats['favorite_reciters'][:3])}\n"
                f"**Favorite Surahs:** {', '.join(map(str, stats['favorite_surahs'][:5]))}"
            ),
            inline=False
        )

        # Quiz statistics
        quiz_stats = stats['quiz_statistics']
        embed.add_field(
            name="🧠 Quiz Stats",
            value=(
                f"**Questions Answered:** {quiz_stats['total_questions']}\n"
                f"**Correct Answers:** {quiz_stats['correct_answers']}\n"
                f"**Accuracy Rate:** {quiz_stats['accuracy_rate']:.1f}%\n"
                f"**Current Streak:** {quiz_stats['current_streak']}"
            ),
            inline=False
        )

        # Recent activity
        if stats['daily_activity']:
            recent_activity = stats['daily_activity'][-7:]  # Last 7 days
            activity_text = ""
            for day in recent_activity:
                activity_text += (
                    f"**{day['date']}:** {day['listening_minutes']}min listening, "
                    f"{day['quiz_questions']} quiz questions\n"
                )

            embed.add_field(
                name="📅 Recent Activity (Last 7 Days)",
                value=activity_text or "No recent activity",
                inline=False
            )

        await ctx.respond(embed=embed)

    except Exception as e:
        await ctx.respond(f"❌ Error getting statistics: {str(e)}")
```

## Error Handling Examples

### Comprehensive Error Handler

#### Python Example
```python
class QuranBotErrorHandler:
    """Centralized error handling for QuranBot commands."""

    @staticmethod
    async def handle_command_error(ctx, error):
        """Handle command errors with user-friendly messages."""

        error_responses = {
            # Audio errors
            'AUDIO_PLAYBACK_FAILED': {
                'message': '🎵 Unable to start audio playback. Please try again.',
                'color': 0xff6b6b
            },
            'AUDIO_INVALID_SURAH': {
                'message': '📖 Please enter a valid surah number (1-114).',
                'color': 0xffa500
            },
            'AUDIO_VOICE_CHANNEL_ERROR': {
                'message': '🔊 Cannot connect to voice channel. Check bot permissions.',
                'color': 0xff6b6b
            },

            # Quiz errors
            'QUIZ_RATE_LIMITED': {
                'message': '⏰ Please wait a few minutes before starting another quiz.',
                'color': 0xffa500
            },
            'QUIZ_SESSION_NOT_FOUND': {
                'message': '🧠 Quiz session expired. Please start a new quiz.',
                'color': 0xffa500
            },

            # AI errors
            'AI_RATE_LIMITED': {
                'message': '🤖 You can ask one AI question per hour. Please try again later.',
                'color': 0xffa500
            },
            'AI_SERVICE_UNAVAILABLE': {
                'message': '🔧 AI service is temporarily unavailable. Please try again later.',
                'color': 0xff6b6b
            },

            # Auth errors
            'AUTH_INSUFFICIENT_PERMISSIONS': {
                'message': '🔒 You don\'t have permission to use this command.',
                'color': 0xff6b6b
            },

            # Rate limiting
            'RATE_LIMIT_EXCEEDED': {
                'message': '⏱️ You\'re sending commands too quickly. Please slow down.',
                'color': 0xffa500
            }
        }

        # Get error code
        error_code = getattr(error, 'code', 'UNKNOWN_ERROR')

        # Get error response or use default
        error_info = error_responses.get(error_code, {
            'message': f'❌ An unexpected error occurred: {str(error)}',
            'color': 0xff6b6b
        })

        # Create error embed
        embed = discord.Embed(
            title="Error",
            description=error_info['message'],
            color=error_info['color']
        )

        # Add additional details if available
        if hasattr(error, 'details') and error.details:
            details_text = ""
            for key, value in error.details.items():
                details_text += f"**{key.title()}:** {value}\n"

            embed.add_field(
                name="Details",
                value=details_text,
                inline=False
            )

        # Add retry information if available
        if hasattr(error, 'retry_after'):
            embed.add_field(
                name="Retry After",
                value=f"{error.retry_after} seconds",
                inline=True
            )

        embed.set_footer(text="If this error persists, please contact support.")

        try:
            if ctx.response.is_done():
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.respond(embed=embed, ephemeral=True)
        except:
            # Fallback to simple message if embed fails
            await ctx.send(error_info['message'])

# Register error handler
@bot.event
async def on_application_command_error(ctx, error):
    await QuranBotErrorHandler.handle_command_error(ctx, error)
```

### Retry Logic Example

#### Python Example
```python
import asyncio
from typing import Callable, Any

class RetryHandler:
    """Handle retries for transient errors."""

    RETRYABLE_ERRORS = [
        'SYSTEM_OVERLOADED',
        'SYSTEM_MAINTENANCE',
        'AI_SERVICE_UNAVAILABLE',
        'AUDIO_PLAYBACK_FAILED'
    ]

    @staticmethod
    async def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        *args,
        **kwargs
    ) -> Any:
        """Retry function with exponential backoff."""

        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                error_code = getattr(e, 'code', 'UNKNOWN_ERROR')

                # Don't retry non-retryable errors
                if error_code not in RetryHandler.RETRYABLE_ERRORS:
                    raise e

                # Don't retry on last attempt
                if attempt == max_retries:
                    raise e

                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)

                # Add jitter to prevent thundering herd
                jitter = delay * 0.1 * (0.5 - random.random())
                delay += jitter

                print(f"Attempt {attempt + 1} failed: {error_code}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # This should never be reached
        raise Exception("Max retries exceeded")

# Usage example
async def start_audio_with_retry(surah_number: int, reciter: str):
    """Start audio with automatic retry on transient failures."""

    async def _start_audio():
        audio_service = bot.get_cog('AudioService')
        return await audio_service.start_playback(
            surah_number=surah_number,
            reciter=reciter
        )

    return await RetryHandler.retry_with_backoff(
        _start_audio,
        max_retries=3,
        base_delay=2.0
    )
```

## SDK Examples

### Python SDK Usage

```python
# Example Python SDK for QuranBot API
import aiohttp
import asyncio
from typing import Optional, Dict, Any

class QuranBotSDK:
    """Python SDK for QuranBot API."""

    def __init__(self, bot_token: str, base_url: str = "https://api.quranbot.example.com"):
        self.bot_token = bot_token
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'QuranBot-SDK/1.0.0'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def start_audio(self, surah_number: Optional[int] = None,
                         reciter: Optional[str] = None) -> Dict[str, Any]:
        """Start audio playback."""
        data = {}
        if surah_number:
            data['surah_number'] = surah_number
        if reciter:
            data['reciter'] = reciter

        async with self.session.post(f'{self.base_url}/audio/play', json=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.json()
                raise QuranBotAPIError(error['error'])

    async def get_audio_status(self) -> Dict[str, Any]:
        """Get current audio status."""
        async with self.session.get(f'{self.base_url}/audio/status') as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.json()
                raise QuranBotAPIError(error['error'])

    async def start_quiz(self, category: Optional[str] = None,
                        difficulty: Optional[str] = None) -> Dict[str, Any]:
        """Start a new quiz."""
        data = {}
        if category:
            data['category'] = category
        if difficulty:
            data['difficulty'] = difficulty

        async with self.session.post(f'{self.base_url}/quiz/start', json=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error = await resp.json()
                raise QuranBotAPIError(error['error'])

class QuranBotAPIError(Exception):
    """QuranBot API error."""

    def __init__(self, error_data: Dict[str, Any]):
        self.code = error_data.get('code', 'UNKNOWN_ERROR')
        self.message = error_data.get('message', 'Unknown error')
        self.details = error_data.get('details', {})
        super().__init__(self.message)

# Usage example
async def main():
    async with QuranBotSDK('paste_your_bot_token_here') as sdk:
        try:
            # Start audio playback
            result = await sdk.start_audio(surah_number=1, reciter='Saad Al Ghamdi')
            print(f"Audio started: {result}")

            # Get status
            status = await sdk.get_audio_status()
            print(f"Current status: {status}")

            # Start quiz
            quiz = await sdk.start_quiz(category='quran', difficulty='intermediate')
            print(f"Quiz started: {quiz}")

        except QuranBotAPIError as e:
            print(f"API Error: {e.code} - {e.message}")

if __name__ == "__main__":
    asyncio.run(main())
```

This comprehensive documentation provides practical examples for all major QuranBot API features, complete with error handling, retry logic, and SDK usage patterns. Developers can use these examples as starting points for their own implementations.
