#!/usr/bin/env python3
"""
Test script to send a Mecca prayer notification
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys

import discord
from discord.ext import commands

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def send_test_prayer_notification():
    """Send a test Mecca prayer notification"""

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv("config/.env")

    token = os.getenv("DISCORD_TOKEN")
    channel_id = int(os.getenv("DAILY_VERSE_CHANNEL_ID", "0"))
    developer_id = int(os.getenv("DEVELOPER_ID", "0"))

    if not token or not channel_id:
        print("❌ Missing Discord token or channel ID in config/.env")
        return

    # Create bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"✅ Bot connected as {bot.user}")

        try:
            # Get the channel
            channel = bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Could not find channel with ID: {channel_id}")
                await bot.close()
                return

            print(f"📍 Found channel: {channel.name}")

            # Load appropriate dua for Maghrib (evening prayer)
            try:
                with open("data/time_based_duas.json", encoding='utf-8') as f:
                    time_based_duas = json.load(f)

                # For Maghrib (evening prayer), use evening duas
                if 'evening_duas' in time_based_duas and time_based_duas['evening_duas']:
                    import random
                    selected_dua = random.choice(time_based_duas['evening_duas'])
                    print(f"✅ Selected evening dua: {selected_dua.get('name', 'Unknown')}")
                else:
                    # Fallback to any available category
                    available_categories = [cat for cat in time_based_duas.values() if cat]
                    if available_categories:
                        selected_dua = random.choice(random.choice(available_categories))
                        print("✅ Selected fallback dua from available categories")
                    else:
                        raise Exception("No duas available")

            except Exception as e:
                print(f"⚠️ Error loading time-based duas: {e}")
                # Final fallback dua
                selected_dua = {
                    'arabic': 'رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ',
                    'english': 'Our Lord, give us good in this world and good in the Hereafter, and save us from the punishment of the Fire.',
                    'source': 'Quran 2:201',
                    'name': 'Dua for Good in Both Worlds'
                }
                print("✅ Using fallback dua")

            # Create beautiful prayer notification embed
            embed = discord.Embed(
                title="🕌 Maghrib Time in the Holy City",
                description="*The sunset prayer in the Holy City - a blessed time for dua*\n\n\n"
                           f"📿 **Dua from {selected_dua.get('source', 'Islamic Tradition')}:**\n\n"
                           f"```{selected_dua['arabic']}```\n\n"
                           f"```{selected_dua['english']}```",
                color=0x1ABC9C,  # Beautiful teal color
                timestamp=datetime.now()
            )

            # Add prayer time field
            embed.add_field(
                name="🕐 Prayer Time in Mecca",
                value="```6:15 PM AST (Arabia Standard Time)```",
                inline=False
            )

            # Add spiritual reminder
            embed.add_field(
                name="🤲 Blessed Moments",
                value="```Wherever you are in the world, this is a blessed time for dua```",
                inline=False
            )

            # Set bot thumbnail
            if bot.user and bot.user.avatar:
                embed.set_thumbnail(url=bot.user.avatar.url)

            # Set footer with admin profile picture
            try:
                admin_user = await bot.fetch_user(developer_id)
                if admin_user and admin_user.avatar:
                    embed.set_footer(
                        text="Created by حَـــــنَـــــا",
                        icon_url=admin_user.avatar.url
                    )
                else:
                    embed.set_footer(text="Created by حَـــــنَـــــا")
            except:
                embed.set_footer(text="Created by حَـــــنَـــــا")

            # Send the embed
            message = await channel.send(embed=embed)
            print("✅ Prayer notification sent successfully!")

            # Add dua emoji reaction
            dua_emoji = "🤲"
            await message.add_reaction(dua_emoji)
            print(f"✅ Added {dua_emoji} reaction")

            # Set up reaction monitoring task
            asyncio.create_task(monitor_reactions(bot, message, dua_emoji))
            print("✅ Reaction monitoring started")

            print("🕌 Test prayer notification complete!")
            print("📋 Features demonstrated:")
            print("   • Beautiful embed with bot thumbnail")
            print("   • Admin footer with profile picture")
            print("   • Automatic dua emoji reaction")
            print("   • Automatic removal of other reactions")

            # Keep bot running for a few minutes to monitor reactions
            await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await bot.close()

    # Start the bot
    await bot.start(token)

async def monitor_reactions(bot, message, allowed_emoji):
    """Monitor and clean up unwanted reactions"""
    print(f"🔍 Monitoring reactions on message {message.id}...")

    def check(reaction, user):
        return (reaction.message.id == message.id and
                not user.bot and
                str(reaction.emoji) != allowed_emoji)

    try:
        # Monitor for 5 minutes (for testing)
        end_time = asyncio.get_event_loop().time() + 300

        while asyncio.get_event_loop().time() < end_time:
            try:
                reaction, user = await bot.wait_for('reaction_add', check=check, timeout=30)

                # Remove the unwanted reaction
                await reaction.remove(user)
                print(f"🧹 Removed {reaction.emoji} reaction from {user.display_name}")

            except TimeoutError:
                continue

    except Exception as e:
        print(f"⚠️ Reaction monitoring error: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_prayer_notification())
