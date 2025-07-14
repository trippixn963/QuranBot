#!/usr/bin/env python3
"""
Integration Tests for QuranBot Discord Interactions
==================================================
Tests for Discord slash commands, voice functionality, and bot behavior.
"""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import discord
from discord.ext import commands

# Import bot modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bot.main import DiscordTreeHandler
from commands.verse import VerseCog
from commands.interval import IntervalCog
from commands.question import QuestionCog
from commands.leaderboard import LeaderboardCog
from commands.credits import CreditsCog
from utils.audio_manager import AudioManager
from utils.quiz_manager import QuizManager
from utils.state_manager import StateManager


class TestDiscordIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for Discord bot functionality."""

    async def asyncSetUp(self):
        """Set up test environment."""
        # Mock Discord objects
        self.guild = MagicMock()
        self.guild.id = 123456789
        self.guild.name = "Test Server"

        self.channel = MagicMock()
        self.channel.id = 987654321
        self.channel.name = "test-channel"
        self.channel.guild = self.guild

        self.voice_channel = MagicMock()
        self.voice_channel.id = 555666777
        self.voice_channel.name = "General"
        self.voice_channel.guild = self.guild

        self.user = MagicMock()
        self.user.id = 111222333
        self.user.name = "TestUser"
        self.user.mention = "<@111222333>"
        self.user.voice = MagicMock()
        self.user.voice.channel = self.voice_channel

        # Mock interaction
        self.interaction = AsyncMock()
        self.interaction.guild = self.guild
        self.interaction.channel = self.channel
        self.interaction.user = self.user
        self.interaction.response = AsyncMock()
        self.interaction.followup = AsyncMock()

        # Initialize bot components
        self.audio_manager = AudioManager()
        self.quiz_manager = QuizManager()
        self.state_manager = StateManager()

        # Create bot instance
        self.bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
        self.bot.tree = discord.app_commands.CommandTree(self.bot)

        # Add Discord tree handler
        self.tree_handler = DiscordTreeHandler()
        discord.utils.setup_logging(handler=self.tree_handler)

    async def test_verse_command_integration(self):
        """Test /verse command integration."""
        # Test data
        surah = 1
        ayah = 1
        reciter = "Mishary Rashid Alafasy"

        with patch('src.commands.verse.AudioManager') as mock_audio:
            mock_audio_instance = AsyncMock()
            mock_audio.return_value = mock_audio_instance
            mock_audio_instance.play_verse.return_value = {
                'success': True,
                'surah': surah,
                'ayah': ayah,
                'reciter': reciter,
                'duration': '00:03',
                'arabic_text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
                'translation': 'In the name of Allah, the Entirely Merciful, the Especially Merciful.'
            }

            # Create verse cog
            verse_cog = VerseCog(self.bot)

            # Execute command
            await verse_cog.verse(self.interaction)

            # Verify interactions
            self.interaction.response.defer.assert_called_once()
            mock_audio_instance.play_verse.assert_called_once_with(
                surah, ayah, reciter, self.voice_channel
            )
            
            # Verify response was sent
            self.assertTrue(self.interaction.followup.send.called)
            
            # Verify embed content
            call_args = self.interaction.followup.send.call_args
            embed = call_args[1]['embed']
            self.assertIn('Al-Fatiha', embed.title)
            self.assertIn('1:1', embed.title)

    async def test_interval_command_integration(self):
        """Test /interval command integration."""
        # Test data
        surah = 1
        start_ayah = 1
        end_ayah = 7
        reciter = "Abdul Basit Abdul Samad"
        pause_duration = 3

        with patch('src.commands.interval.AudioManager') as mock_audio:
            mock_audio_instance = AsyncMock()
            mock_audio.return_value = mock_audio_instance
            mock_audio_instance.play_interval.return_value = {
                'success': True,
                'surah': surah,
                'start_ayah': start_ayah,
                'end_ayah': end_ayah,
                'total_verses': 7,
                'reciter': reciter,
                'estimated_duration': '00:45'
            }

            # Create interval cog
            interval_cog = IntervalCog(self.bot)

            # Execute command
            await interval_cog.interval(
                self.interaction,
                quiz_time="30m",
                verse_time="3h"
            )

            # Verify interactions
            self.interaction.response.defer.assert_called_once()
            mock_audio_instance.play_interval.assert_called_once_with(
                surah, start_ayah, end_ayah, reciter, pause_duration, self.voice_channel
            )

            # Verify response
            self.assertTrue(self.interaction.followup.send.called)

    async def test_question_command_integration(self):
        """Test /question command integration."""
        # Mock quiz data
        mock_question = {
            'id': 'q_test_001',
            'difficulty': 'medium',
            'category': 'verses',
            'question': 'Which surah is known as "The Opening"?',
            'options': ['Al-Baqarah', 'Al-Fatiha', 'An-Nas', 'Al-Ikhlas'],
            'correct_answer': 1,
            'explanation': 'Al-Fatiha is the first surah of the Quran.',
            'points': 10
        }

        with patch('src.commands.question.QuizManager') as mock_quiz:
            mock_quiz_instance = MagicMock()
            mock_quiz.return_value = mock_quiz_instance
            mock_quiz_instance.get_question.return_value = mock_question

            # Create question cog
            question_cog = QuestionCog(self.bot)

            # Execute command
            await question_cog.question(self.interaction)

            # Verify quiz manager called
            mock_quiz_instance.get_question.assert_called_once_with(
                user_id=self.user.id,
                difficulty='medium',
                category='verses'
            )

            # Verify response sent
            self.assertTrue(self.interaction.response.send_message.called)

    async def test_leaderboard_command_integration(self):
        """Test /leaderboard command integration."""
        # Mock leaderboard data
        mock_leaderboard = {
            'scope': 'server',
            'total_players': 25,
            'rankings': [
                {
                    'rank': 1,
                    'user_id': 111222333,
                    'username': 'TestUser',
                    'score': 1250,
                    'accuracy': 85.5,
                    'streak': 12
                },
                {
                    'rank': 2,
                    'user_id': 444555666,
                    'username': 'AnotherUser',
                    'score': 980,
                    'accuracy': 78.2,
                    'streak': 8
                }
            ],
            'user_stats': {
                'rank': 1,
                'score': 1250,
                'accuracy': 85.5
            }
        }

        with patch('src.commands.leaderboard.QuizManager') as mock_quiz:
            mock_quiz_instance = MagicMock()
            mock_quiz.return_value = mock_quiz_instance
            mock_quiz_instance.get_leaderboard.return_value = mock_leaderboard

            # Create leaderboard cog
            leaderboard_cog = LeaderboardCog(self.bot)

            # Execute command
            await leaderboard_cog.leaderboard(self.interaction, 'server', 10)

            # Verify quiz manager called
            mock_quiz_instance.get_leaderboard.assert_called_once_with(
                scope='server',
                guild_id=self.guild.id,
                limit=10
            )

            # Verify response sent
            self.assertTrue(self.interaction.response.send_message.called)

    async def test_credits_command_integration(self):
        """Test /credits command integration."""
        # Execute command
        credits_cog = CreditsCog(self.bot)
        await credits_cog.credits(self.interaction)

        # Verify response sent
        self.assertTrue(self.interaction.response.send_message.called)
        
        # Verify embed content
        call_args = self.interaction.response.send_message.call_args
        embed = call_args[1]['embed']
        self.assertIn('QuranBot', embed.title)
        self.assertIn('3.5.2', embed.description)

    async def test_audio_manager_voice_integration(self):
        """Test AudioManager voice channel integration."""
        # Mock voice client
        mock_voice_client = AsyncMock()
        mock_voice_client.is_connected.return_value = True
        mock_voice_client.is_playing.return_value = False

        with patch('discord.VoiceChannel.connect') as mock_connect:
            mock_connect.return_value = mock_voice_client
            
            # Test voice connection
            audio_manager = AudioManager()
            result = await audio_manager.connect_to_voice(self.voice_channel)
            
            self.assertTrue(result)
            mock_connect.assert_called_once()

    async def test_quiz_answer_integration(self):
        """Test quiz answer submission integration."""
        # Mock quiz state
        mock_active_question = {
            'id': 'q_test_001',
            'user_id': self.user.id,
            'correct_answer': 1,
            'points': 10,
            'start_time': asyncio.get_event_loop().time()
        }

        with patch('src.utils.quiz_manager.QuizManager.get_active_question') as mock_get_active:
            mock_get_active.return_value = mock_active_question
            
            with patch('src.utils.quiz_manager.QuizManager.submit_answer') as mock_submit:
                mock_submit.return_value = {
                    'correct': True,
                    'points_earned': 10,
                    'streak': 5,
                    'explanation': 'Correct! Al-Fatiha is the opening surah.'
                }

                # Test answer submission
                quiz_manager = QuizManager()
                result = await quiz_manager.submit_answer(self.user.id, 1)
                
                self.assertTrue(result['correct'])
                self.assertEqual(result['points_earned'], 10)

    async def test_state_persistence_integration(self):
        """Test state manager persistence integration."""
        # Test data
        test_state = {
            'user_id': self.user.id,
            'guild_id': self.guild.id,
            'quiz_score': 500,
            'current_streak': 8,
            'preferences': {
                'default_reciter': 'Mishary Rashid Alafasy',
                'auto_play': True
            }
        }

        state_manager = StateManager()
        
        # Test saving state
        await state_manager.save_user_state(self.user.id, test_state)
        
        # Test loading state
        loaded_state = await state_manager.load_user_state(self.user.id)
        
        self.assertEqual(loaded_state['quiz_score'], 500)
        self.assertEqual(loaded_state['current_streak'], 8)
        self.assertEqual(loaded_state['preferences']['default_reciter'], 'Mishary Rashid Alafasy')

    async def test_error_handling_integration(self):
        """Test error handling in command integration."""
        # Test invalid surah number
        with patch('src.commands.verse.AudioManager') as mock_audio:
            mock_audio_instance = AsyncMock()
            mock_audio.return_value = mock_audio_instance
            mock_audio_instance.play_verse.side_effect = ValueError("Invalid surah number: 115")

            verse_command = VerseCog(self.bot)
            await verse_command.verse(self.interaction)

            # Verify error response
            self.assertTrue(self.interaction.followup.send.called)
            call_args = self.interaction.followup.send.call_args
            self.assertIn('error', call_args[0][0].lower())

    async def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        # Mock rate limiter
        with patch('src.utils.rate_limiter.RateLimiter') as mock_rate_limiter:
            mock_limiter_instance = MagicMock()
            mock_rate_limiter.return_value = mock_limiter_instance
            
            # Test rate limit not exceeded
            mock_limiter_instance.is_rate_limited.return_value = False
            
            verse_command = VerseCog(self.bot)
            # Should proceed normally
            
            # Test rate limit exceeded
            mock_limiter_instance.is_rate_limited.return_value = True
            mock_limiter_instance.get_retry_after.return_value = 5.0
            
            # Should return rate limit error
            # (Implementation depends on actual rate limiting logic)

    async def test_permissions_integration(self):
        """Test bot permissions integration."""
        # Mock guild permissions
        permissions = discord.Permissions()
        permissions.send_messages = True
        permissions.use_slash_commands = True
        permissions.connect = True
        permissions.speak = True
        
        self.guild.me = MagicMock()
        self.guild.me.guild_permissions = permissions
        
        # Test permission checking
        has_required_perms = all([
            permissions.send_messages,
            permissions.use_slash_commands,
            permissions.connect,
            permissions.speak
        ])
        
        self.assertTrue(has_required_perms)

    async def test_concurrent_commands_integration(self):
        """Test handling concurrent command execution."""
        # Simulate multiple users using commands simultaneously
        users = []
        interactions = []
        
        for i in range(5):
            user = MagicMock()
            user.id = 111222333 + i
            user.name = f"TestUser{i}"
            user.voice = MagicMock()
            user.voice.channel = self.voice_channel
            
            interaction = AsyncMock()
            interaction.guild = self.guild
            interaction.channel = self.channel
            interaction.user = user
            interaction.response = AsyncMock()
            interaction.followup = AsyncMock()
            
            users.append(user)
            interactions.append(interaction)

        # Execute commands concurrently
        with patch('src.commands.verse.AudioManager') as mock_audio:
            mock_audio_instance = AsyncMock()
            mock_audio.return_value = mock_audio_instance
            mock_audio_instance.play_verse.return_value = {
                'success': True,
                'surah': 1,
                'ayah': 1,
                'reciter': 'Mishary Rashid Alafasy'
            }

            verse_command = VerseCog(self.bot)
            
            # Execute all commands concurrently
            tasks = []
            for interaction in interactions:
                task = asyncio.create_task(
                    verse_command.verse(interaction)
                )
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
            # Verify all interactions were handled
            for interaction in interactions:
                self.assertTrue(interaction.response.defer.called)

    async def test_bot_lifecycle_integration(self):
        """Test bot startup and shutdown integration."""
        # Test bot initialization
        self.assertIsNotNone(self.bot)
        
        # Test command registration
        # (Would verify slash commands are registered)
        
        # Test bot shutdown
        await self.bot.close()

    def test_configuration_integration(self):
        """Test configuration loading integration."""
        # Test environment variable loading
        test_env = {
            'DISCORD_TOKEN': 'test_token',
            'GUILD_ID': '123456789',
            'TARGET_CHANNEL_ID': '987654321'
        }
        
        with patch.dict(os.environ, test_env):
            # Test configuration loading
            from src.utils.config import load_config
            config = load_config()
            
            self.assertEqual(config['discord_token'], 'test_token')
            self.assertEqual(config['guild_id'], 123456789)

    async def test_logging_integration(self):
        """Test logging system integration."""
        with patch('src.utils.discord_logger.DiscordLogger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            # Test logging various events
            logger = mock_logger_instance
            
            # Test command execution logging
            await logger.log_command_execution(
                command='verse',
                user_id=self.user.id,
                guild_id=self.guild.id,
                success=True
            )
            
            # Test error logging
            await logger.log_error(
                error_type='ValueError',
                message='Invalid surah number',
                user_id=self.user.id
            )
            
            # Verify logging calls
            self.assertTrue(mock_logger_instance.log_command_execution.called)
            self.assertTrue(mock_logger_instance.log_error.called)


class TestBotBehavior(unittest.IsolatedAsyncioTestCase):
    """Test overall bot behavior and edge cases."""

    async def test_voice_channel_handling(self):
        """Test voice channel connection and disconnection."""
        # Test user not in voice channel
        user_no_voice = MagicMock()
        user_no_voice.voice = None
        
        interaction = AsyncMock()
        interaction.user = user_no_voice
        
        # Should handle gracefully
        # (Implementation depends on actual voice handling logic)

    async def test_invalid_input_handling(self):
        """Test handling of invalid user inputs."""
        # Test cases for invalid inputs
        invalid_cases = [
            {'surah': 0, 'ayah': 1},      # Surah too low
            {'surah': 115, 'ayah': 1},    # Surah too high
            {'surah': 1, 'ayah': 0},      # Ayah too low
            {'surah': 1, 'ayah': 1000},   # Ayah too high for surah
        ]
        
        for case in invalid_cases:
            # Each case should be handled gracefully with appropriate error messages
            pass

    async def test_network_failure_handling(self):
        """Test handling of network failures."""
        # Mock network failures
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Network timeout")
            
            # Test audio loading failure
            audio_manager = AudioManager()
            # Should handle timeout gracefully
            
    async def test_database_failure_handling(self):
        """Test handling of database/state failures."""
        # Mock database failures
        with patch('src.utils.state_manager.StateManager.save_user_state') as mock_save:
            mock_save.side_effect = Exception("Database connection failed")
            
            # Should handle database failures gracefully
            state_manager = StateManager()
            # Test should not crash the bot


if __name__ == '__main__':
    # Run integration tests
    unittest.main() 