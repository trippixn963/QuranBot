#!/usr/bin/env python3
"""
Test script to manually create a control panel and test the AudioServiceAdapter
"""

import asyncio
from pathlib import Path
import sys

import discord
from discord.ext import commands

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our modules
from main import AudioServiceAdapter
from src.utils.control_panel import setup_control_panel


class TestBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        print(f"🤖 Test bot logged in as {self.user}")
        print("Ready to test control panel!")

    @commands.command(name="testpanel")
    async def test_panel(self, ctx):
        """Test command to create a control panel"""
        try:
            print("🎯 Testing control panel creation...")

            # Create a mock AudioServiceAdapter for testing
            class MockAudioService:
                def __init__(self):
                    self._current_state = type(
                        "MockState",
                        (),
                        {
                            "is_playing": True,
                            "is_paused": False,
                            "is_connected": True,
                            "current_reciter": "Saad Al Ghamdi",
                            "current_position": type(
                                "MockPosition",
                                (),
                                {
                                    "surah_number": 2,
                                    "position_seconds": 150.5,
                                    "total_duration": 7054.331125,
                                },
                            )(),
                            "mode": "normal",
                            "volume": 1.0,
                            "voice_channel_id": ctx.channel.id,
                            "guild_id": ctx.guild.id,
                        },
                    )()
                    self._available_reciters = [
                        type("Reciter", (), {"name": "Saad Al Ghamdi"})()
                    ]

            mock_audio_service = MockAudioService()
            adapter = AudioServiceAdapter(mock_audio_service)

            # Test the adapter
            print("🔍 Testing AudioServiceAdapter...")
            status = adapter.get_playback_status()
            print(f"📊 Adapter status: {status}")

            # Create control panel
            print("🎛️ Creating control panel...")
            success = await setup_control_panel(self, ctx.channel.id, adapter)

            if success:
                await ctx.send(
                    "✅ **Control panel created successfully!**\n📊 **Status from adapter:**\n```json\n"
                    + str(status)
                    + "\n```"
                )
            else:
                await ctx.send("❌ **Failed to create control panel**")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()
            await ctx.send(f"❌ **Error**: {e!s}")


async def main():
    """Main test function"""
    try:
        # Load environment variables
        from dotenv import load_dotenv

        load_dotenv()

        import os

        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("❌ No DISCORD_BOT_TOKEN found in environment")
            return

        bot = TestBot()

        print("🚀 Starting test bot...")
        print("Commands:")
        print("  !testpanel - Create a test control panel")
        print("  Ctrl+C to stop")

        await bot.start(token)

    except KeyboardInterrupt:
        print("\n🛑 Test bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
