#!/usr/bin/env python3
# =============================================================================
# QuranBot - Daily Verses Manager
# =============================================================================
# Manages daily Quran verses and user interactions
# =============================================================================

import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import discord
import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# Global scheduler task
_verse_scheduler_task = None


class DailyVerseManager:
    """Manages daily Quran verses and user interactions"""

    def __init__(self, data_dir: Union[str, Path]):
        """Initialize the daily verse manager"""
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "daily_verse_state.json"
        self.verses_file = self.data_dir / "daily_verses_pool.json"
        self.verses_state_file = (
            self.data_dir / "daily_verses_state.json"
        )  # For interval config
        self.current_verse = None
        self.verse_pool = []
        self.last_sent_time = None

        # Recent verses tracking to avoid duplicates
        self.recent_verses: List[str] = []  # Store verse IDs (surah:verse format)
        self.max_recent_verses = 20  # Track last 20 verses

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state and verses
        self.load_state()
        self.load_verses()

    def get_interval_hours(self) -> float:
        """Get the current verse interval in hours from config"""
        try:
            if self.verses_state_file.exists():
                with open(self.verses_state_file, "r") as f:
                    data = json.load(f)
                    return data.get("schedule_config", {}).get(
                        "send_interval_hours", 3.0
                    )
            return 3.0  # Default 3 hours
        except Exception as e:
            log_error_with_traceback("Error loading verse interval config", e)
            return 3.0

    def should_send_verse(self) -> bool:
        """Check if it's time to send a verse based on custom interval"""
        try:
            interval_hours = self.get_interval_hours()

            if not self.last_sent_time:
                return True  # Send immediately if never sent

            current_time = datetime.now(pytz.UTC)
            time_diff = current_time - self.last_sent_time
            interval_seconds = interval_hours * 3600

            return time_diff.total_seconds() >= interval_seconds
        except Exception as e:
            log_error_with_traceback("Error checking verse send time", e)
            return True

    def update_last_sent_time(self):
        """Update the last sent time to now"""
        try:
            self.last_sent_time = datetime.now(pytz.UTC)
            self.save_state()
        except Exception as e:
            log_error_with_traceback("Error updating last sent time", e)

    def should_update_verse(self) -> bool:
        """Check if it's time to update the daily verse"""
        try:
            if not self.current_verse:
                return True

            current_time = datetime.now(pytz.UTC)
            verse_time = datetime.fromtimestamp(
                self.current_verse["timestamp"], tz=pytz.UTC
            )
            time_diff = current_time - verse_time

            return time_diff.days >= 1
        except Exception as e:
            log_error_with_traceback("Error checking verse update time", e)
            return True

    def get_time_until_next_verse(self) -> timedelta:
        """Get time remaining until next verse"""
        try:
            if not self.current_verse:
                return timedelta()

            current_time = datetime.now(pytz.UTC)
            verse_time = datetime.fromtimestamp(
                self.current_verse["timestamp"], tz=pytz.UTC
            )
            next_verse_time = verse_time + timedelta(days=1)

            return next_verse_time - current_time
        except Exception as e:
            log_error_with_traceback("Error calculating next verse time", e)
            return timedelta()

    def add_verse(
        self,
        surah: int,
        verse: int,
        text: str,
        translation: str,
        transliteration: str,
    ) -> bool:
        """Add a verse to the pool"""
        try:
            # Validate input
            if not (1 <= surah <= 114):
                log_error_with_traceback(
                    "Invalid surah number",
                    ValueError(f"Surah number must be 1-114, got {surah}"),
                )
                return False

            if verse < 1:
                log_error_with_traceback(
                    "Invalid verse number",
                    ValueError(f"Verse number must be positive, got {verse}"),
                )
                return False

            if not all([text, translation, transliteration]):
                log_error_with_traceback(
                    "Missing required fields",
                    ValueError("All verse fields must be non-empty"),
                )
                return False

            # Create verse entry
            verse_entry = {
                "surah": surah,
                "verse": verse,
                "text": text,
                "translation": translation,
                "transliteration": transliteration,
            }

            self.verse_pool.append(verse_entry)
            self.save_verses()

            log_perfect_tree_section(
                "Verse Added",
                [
                    ("surah", surah),
                    ("verse", verse),
                    ("status", "✅ Added successfully"),
                ],
                "📖",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error adding verse", e)
            return False

    def get_verse_by_number(self, surah: int, verse: int) -> Optional[Dict]:
        """Get a specific verse by number"""
        try:
            for verse_entry in self.verse_pool:
                if verse_entry["surah"] == surah and verse_entry["verse"] == verse:
                    return verse_entry
            return None
        except Exception as e:
            log_error_with_traceback("Error getting verse by number", e)
            return None

    def get_random_verse(self) -> Optional[Dict]:
        """Get a random verse from the pool, avoiding recently sent verses"""
        try:
            if not self.verse_pool:
                return None

            # Filter out recently sent verses
            available_verses = [
                v
                for v in self.verse_pool
                if f"{v['surah']}:{v['verse']}" not in self.recent_verses
            ]

            # If no verses available (all recent), reset recent list and use all
            if not available_verses:
                log_perfect_tree_section(
                    "Daily Verses - Recent Reset",
                    [
                        ("reason", "All verses recently sent"),
                        ("recent_count", len(self.recent_verses)),
                        ("action", "🔄 Resetting recent verses list"),
                        ("available_after_reset", len(self.verse_pool)),
                    ],
                    "🔄",
                )
                self.recent_verses = []
                available_verses = self.verse_pool

            # Select random verse
            verse = random.choice(available_verses)
            verse["timestamp"] = datetime.now(pytz.UTC).timestamp()
            self.current_verse = verse

            # Track this verse as recently sent
            verse_id = f"{verse['surah']}:{verse['verse']}"
            self.add_to_recent_verses(verse_id)

            self.save_state()

            log_perfect_tree_section(
                "Random Verse Selected",
                [
                    ("surah", verse["surah"]),
                    ("verse", verse["verse"]),
                    ("verse_id", verse_id),
                    ("recent_count", len(self.recent_verses)),
                    ("available_count", len(available_verses)),
                    ("status", "✅ Selected successfully"),
                ],
                "🎲",
            )
            return verse
        except Exception as e:
            log_error_with_traceback("Error getting random verse", e)
            return None

    def add_to_recent_verses(self, verse_id: str) -> None:
        """Add a verse ID to the recent verses list"""
        try:
            # Add to beginning of list
            if verse_id in self.recent_verses:
                self.recent_verses.remove(verse_id)

            self.recent_verses.insert(0, verse_id)

            # Keep only the most recent verses
            if len(self.recent_verses) > self.max_recent_verses:
                self.recent_verses = self.recent_verses[: self.max_recent_verses]

            # Save state to persist recent verses
            self.save_state()

        except Exception as e:
            log_error_with_traceback("Error adding to recent verses", e)

    def get_recent_verses_info(self) -> Dict:
        """Get information about recently sent verses"""
        try:
            return {
                "recent_count": len(self.recent_verses),
                "max_recent": self.max_recent_verses,
                "recent_ids": self.recent_verses.copy(),
                "total_verses": len(self.verse_pool),
                "available_verses": len(
                    [
                        v
                        for v in self.verse_pool
                        if f"{v['surah']}:{v['verse']}" not in self.recent_verses
                    ]
                ),
            }
        except Exception as e:
            log_error_with_traceback("Error getting recent verses info", e)
            return {}

    def save_state(self) -> bool:
        """Save current state to file"""
        try:
            state_data = {}
            if self.current_verse:
                state_data["current_verse"] = self.current_verse
            if self.last_sent_time:
                state_data["last_sent_time"] = self.last_sent_time.timestamp()

            # Add recent verses tracking
            state_data["recent_verses"] = self.recent_verses

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)

            log_perfect_tree_section(
                "Daily Verse State Saved",
                [
                    (
                        "surah",
                        self.current_verse["surah"] if self.current_verse else "None",
                    ),
                    (
                        "verse",
                        self.current_verse["verse"] if self.current_verse else "None",
                    ),
                    ("recent_verses", len(self.recent_verses)),
                    (
                        "last_sent",
                        (
                            self.last_sent_time.strftime("%H:%M:%S")
                            if self.last_sent_time
                            else "Never"
                        ),
                    ),
                    ("status", "✅ State saved successfully"),
                ],
                "💾",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error saving verse state", e)
            return False

    def load_state(self) -> bool:
        """Load state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle both old format (direct verse) and new format (with timestamps)
                if isinstance(data, dict) and "current_verse" in data:
                    # New format
                    self.current_verse = data.get("current_verse")
                    self.recent_verses = data.get("recent_verses", [])
                    if data.get("last_sent_time"):
                        self.last_sent_time = datetime.fromtimestamp(
                            data["last_sent_time"], tz=pytz.UTC
                        )
                else:
                    # Old format - data is the verse directly
                    self.current_verse = data
                    self.recent_verses = []
                    self.last_sent_time = None

                log_perfect_tree_section(
                    "Daily Verse State Loaded",
                    [
                        (
                            "surah",
                            (
                                self.current_verse["surah"]
                                if self.current_verse
                                else "None"
                            ),
                        ),
                        (
                            "verse",
                            (
                                self.current_verse["verse"]
                                if self.current_verse
                                else "None"
                            ),
                        ),
                        ("recent_verses", len(self.recent_verses)),
                        (
                            "last_sent",
                            (
                                self.last_sent_time.strftime("%H:%M:%S")
                                if self.last_sent_time
                                else "Never"
                            ),
                        ),
                        ("status", "✅ State loaded successfully"),
                    ],
                    "📥",
                )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading verse state", e)
            return False

    def save_verses(self) -> bool:
        """Save verses to file"""
        try:
            with open(self.verses_file, "w", encoding="utf-8") as f:
                json.dump(self.verse_pool, f, indent=2)

            log_perfect_tree_section(
                "Daily Verses Saved",
                [
                    ("total_verses", len(self.verse_pool)),
                    ("status", "✅ Verses saved successfully"),
                ],
                "💾",
            )
            return True
        except Exception as e:
            log_error_with_traceback("Error saving verses", e)
            return False

    def load_verses(self) -> bool:
        """Load verses from file"""
        try:
            if self.verses_file.exists():
                with open(self.verses_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle different file formats
                if isinstance(data, list):
                    # Old format - direct list of verses
                    self.verse_pool = data
                elif isinstance(data, dict) and "verses" in data:
                    # New format - verses under "verses" key
                    verses = data["verses"]
                    self.verse_pool = []

                    # Convert each verse to expected format
                    for verse_data in verses:
                        try:
                            # Map the fields to expected format
                            verse_entry = {
                                "surah": verse_data.get("surah"),
                                "verse": verse_data.get(
                                    "ayah", verse_data.get("verse")
                                ),  # Handle both field names
                                "text": verse_data.get(
                                    "arabic", verse_data.get("text", "")
                                ),
                                "translation": verse_data.get("translation", ""),
                                "transliteration": verse_data.get(
                                    "transliteration", ""
                                ),
                            }

                            # Only add if we have the required fields
                            if verse_entry["surah"] and verse_entry["verse"]:
                                self.verse_pool.append(verse_entry)

                        except Exception as e:
                            log_error_with_traceback(f"Error processing verse entry", e)
                            continue
                else:
                    # Unknown format - initialize empty
                    log_error_with_traceback(
                        "Unknown verses file format",
                        ValueError(
                            f"Expected list or dict with 'verses' key, got {type(data)}"
                        ),
                    )
                    self.verse_pool = []

                log_perfect_tree_section(
                    "Daily Verses Loaded",
                    [
                        ("total_verses", len(self.verse_pool)),
                        ("status", "✅ Verses loaded successfully"),
                    ],
                    "📥",
                )
            return True
        except Exception as e:
            log_error_with_traceback("Error loading verses", e)
            return False


# Global instance
daily_verse_manager = None


async def setup_daily_verses(bot, channel_id: int) -> None:
    """
    Set up the daily verse system.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for daily verse posts
    """
    global daily_verse_manager

    try:
        # Initialize manager if needed
        if daily_verse_manager is None:
            daily_verse_manager = DailyVerseManager(Path("data"))

        # Schedule initial verse check (legacy daily system)
        await check_and_post_verse(bot, channel_id)

        # Start the custom interval scheduler
        start_verse_scheduler(bot, channel_id)

        # Log successful setup
        interval_hours = daily_verse_manager.get_interval_hours()
        log_perfect_tree_section(
            "Daily Verse System Setup",
            [
                ("status", "✅ System initialized"),
                ("channel", str(channel_id)),
                ("verses_loaded", str(len(daily_verse_manager.verse_pool))),
                ("custom_interval", f"{interval_hours}h"),
                ("scheduler", "✅ Custom interval scheduler started"),
            ],
            "📅",
        )

    except Exception as e:
        log_error_with_traceback("Error setting up daily verse system", e)


async def check_and_post_verse(bot, channel_id: int) -> None:
    """
    Check if it's time for a new verse and post if needed.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for daily verse posts
    """
    try:
        if not daily_verse_manager:
            return

        if daily_verse_manager.should_update_verse():
            # Get new verse
            verse = daily_verse_manager.get_random_verse()
            if verse:
                # Get channel
                channel = bot.get_channel(channel_id)
                if channel:
                    # Get surah name and Arabic name from the verse data
                    surah_name = verse.get("surah_name", f"Surah {verse['surah']}")
                    arabic_name = verse.get("arabic_name", "")

                    # Format the title like in the screenshot
                    if arabic_name:
                        title = f"📖 Daily Verse - {surah_name} ({arabic_name})"
                    else:
                        title = f"📖 Daily Verse - {surah_name}"

                    # Create embed with green color like in screenshot
                    embed = discord.Embed(
                        title=title,
                        color=0x2ECC71,  # Green color matching screenshot
                    )

                    # Add Ayah number as description
                    embed.description = f"Ayah {verse.get('ayah', verse['verse'])}"

                    # Add bot's profile picture as thumbnail
                    if bot.user and bot.user.avatar:
                        embed.set_thumbnail(url=bot.user.avatar.url)
                    elif bot.user:
                        # Fallback to default avatar if no custom avatar
                        embed.set_thumbnail(url=bot.user.default_avatar.url)

                    # Add Arabic section with moon emoji and code block formatting
                    embed.add_field(
                        name="🌙 Arabic",
                        value=f"```\n{verse.get('arabic', verse['text'])}\n```",
                        inline=False,
                    )

                    # Add Translation section with scroll emoji and code block formatting
                    embed.add_field(
                        name="📝 Translation",
                        value=f"```\n{verse['translation']}\n```",
                        inline=False,
                    )

                    # Set footer with creator information like in screenshot
                    try:
                        # Get developer ID from environment
                        DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
                        if DEVELOPER_ID != 0:
                            admin_user = await bot.fetch_user(DEVELOPER_ID)
                            if admin_user and admin_user.avatar:
                                embed.set_footer(
                                    text="created by حَـــــنَّـــــا",
                                    icon_url=admin_user.avatar.url,
                                )
                            else:
                                embed.set_footer(text="created by حَـــــنَّـــــا")
                        else:
                            embed.set_footer(text="created by حَـــــنَّـــــا")
                    except Exception:
                        # Fallback to text-only footer if avatar fetch fails
                        embed.set_footer(text="created by حَـــــنَّـــــا")

                    # Send message
                    message = await channel.send(embed=embed)

                    # Add dua reaction
                    try:
                        await message.add_reaction("🤲")

                        # Monitor reactions to remove unwanted ones
                        def check_reaction(reaction, user):
                            return (
                                reaction.message.id == message.id
                                and str(reaction.emoji) != "🤲"
                                and not user.bot
                            )

                        # Set up reaction monitoring in background
                        async def monitor_reactions():
                            try:
                                while True:
                                    reaction, user = await bot.wait_for(
                                        "reaction_add",
                                        timeout=3600,  # Monitor for 1 hour
                                        check=check_reaction,
                                    )
                                    # Remove unwanted reaction
                                    await reaction.remove(user)
                            except asyncio.TimeoutError:
                                pass  # Stop monitoring after timeout
                            except Exception:
                                pass  # Ignore errors in monitoring

                        # Start monitoring task
                        asyncio.create_task(monitor_reactions())

                    except Exception:
                        pass  # Non-critical if reaction fails

                    log_perfect_tree_section(
                        "Daily Verse Posted",
                        [
                            ("surah", str(verse["surah"])),
                            ("verse", str(verse.get("ayah", verse["verse"]))),
                            ("channel", str(channel_id)),
                        ],
                        "📬",
                    )

    except Exception as e:
        log_error_with_traceback("Error checking and posting verse", e)


async def check_and_send_scheduled_verse(bot, channel_id: int) -> None:
    """
    Check if it's time for a scheduled verse based on custom interval and send if needed.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for verse posts
    """
    try:
        if not daily_verse_manager:
            return

        if daily_verse_manager.should_send_verse():
            # Get new verse
            verse = daily_verse_manager.get_random_verse()
            if verse:
                # Get channel
                channel = bot.get_channel(channel_id)
                if channel:
                    # Get surah name and Arabic name from the verse data
                    surah_name = verse.get("surah_name", f"Surah {verse['surah']}")
                    arabic_name = verse.get("arabic_name", "")

                    # Format the title like in the screenshot
                    if arabic_name:
                        title = f"📖 Daily Verse - {surah_name} ({arabic_name})"
                    else:
                        title = f"📖 Daily Verse - {surah_name}"

                    # Create embed with green color like in screenshot
                    embed = discord.Embed(
                        title=title,
                        color=0x2ECC71,  # Green color matching screenshot
                    )

                    # Add Ayah number as description
                    embed.description = f"Ayah {verse.get('ayah', verse['verse'])}"

                    # Add bot's profile picture as thumbnail
                    if bot.user and bot.user.avatar:
                        embed.set_thumbnail(url=bot.user.avatar.url)
                    elif bot.user:
                        # Fallback to default avatar if no custom avatar
                        embed.set_thumbnail(url=bot.user.default_avatar.url)

                    # Add Arabic section with moon emoji
                    embed.add_field(
                        name="🌙 Arabic",
                        value=f"```\n{verse.get('arabic', verse['text'])}\n```",
                        inline=False,
                    )

                    # Add Translation section with scroll emoji
                    embed.add_field(
                        name="📝 Translation",
                        value=f"```\n{verse['translation']}\n```",
                        inline=False,
                    )

                    # Set footer with creator information like in screenshot
                    try:
                        # Get developer ID from environment
                        DEVELOPER_ID = int(os.getenv("DEVELOPER_ID") or "0")
                        if DEVELOPER_ID != 0:
                            admin_user = await bot.fetch_user(DEVELOPER_ID)
                            if admin_user and admin_user.avatar:
                                embed.set_footer(
                                    text="created by حَـــــنَّـــــا",
                                    icon_url=admin_user.avatar.url,
                                )
                            else:
                                embed.set_footer(text="created by حَـــــنَّـــــا")
                        else:
                            embed.set_footer(text="created by حَـــــنَّـــــا")
                    except Exception:
                        # Fallback to text-only footer if avatar fetch fails
                        embed.set_footer(text="created by حَـــــنَّـــــا")

                    # Send message
                    message = await channel.send(embed=embed)

                    # Add dua reaction
                    try:
                        await message.add_reaction("🤲")

                        # Monitor reactions to remove unwanted ones
                        def check_reaction(reaction, user):
                            return (
                                reaction.message.id == message.id
                                and str(reaction.emoji) != "🤲"
                                and not user.bot
                            )

                        # Set up reaction monitoring in background
                        async def monitor_reactions():
                            try:
                                while True:
                                    reaction, user = await bot.wait_for(
                                        "reaction_add",
                                        timeout=3600,  # Monitor for 1 hour
                                        check=check_reaction,
                                    )
                                    # Remove unwanted reaction
                                    await reaction.remove(user)
                            except asyncio.TimeoutError:
                                pass  # Stop monitoring after timeout
                            except Exception:
                                pass  # Ignore errors in monitoring

                        # Start monitoring task
                        asyncio.create_task(monitor_reactions())

                    except Exception:
                        pass  # Non-critical if reaction fails

                    # Update last sent time
                    daily_verse_manager.update_last_sent_time()

                    log_perfect_tree_section(
                        "Scheduled Verse Posted",
                        [
                            ("surah", str(verse["surah"])),
                            ("verse", str(verse.get("ayah", verse["verse"]))),
                            ("channel", str(channel_id)),
                            (
                                "interval",
                                f"{daily_verse_manager.get_interval_hours()}h",
                            ),
                        ],
                        "📬",
                    )

    except Exception as e:
        log_error_with_traceback("Error checking and sending scheduled verse", e)


async def verse_scheduler_loop(bot, channel_id: int) -> None:
    """
    Background task that checks for scheduled verses every 30 seconds.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for verse posts
    """
    log_perfect_tree_section(
        "Verse Scheduler - Started",
        [
            ("status", "🔄 Verse scheduler running"),
            ("check_interval", "30 seconds"),
            ("channel_id", str(channel_id)),
        ],
        "⏰",
    )

    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            await check_and_send_scheduled_verse(bot, channel_id)
        except asyncio.CancelledError:
            log_perfect_tree_section(
                "Verse Scheduler - Stopped",
                [
                    ("status", "🛑 Verse scheduler stopped"),
                    ("reason", "Task cancelled"),
                ],
                "⏰",
            )
            break
        except Exception as e:
            log_error_with_traceback("Error in verse scheduler loop", e)
            await asyncio.sleep(30)  # Wait before retrying


def start_verse_scheduler(bot, channel_id: int) -> None:
    """
    Start the background verse scheduler.

    Args:
        bot: Discord bot instance
        channel_id: Channel ID for verse posts
    """
    global _verse_scheduler_task

    try:
        # Cancel existing task if running
        if _verse_scheduler_task and not _verse_scheduler_task.done():
            _verse_scheduler_task.cancel()

        # Start new scheduler task
        _verse_scheduler_task = asyncio.create_task(
            verse_scheduler_loop(bot, channel_id)
        )

        log_perfect_tree_section(
            "Verse Scheduler - Initialized",
            [
                ("status", "✅ Verse scheduler started"),
                ("channel_id", str(channel_id)),
                ("check_frequency", "Every 30 seconds"),
                ("task_id", f"🆔 {id(_verse_scheduler_task)}"),
            ],
            "⏰",
        )

    except Exception as e:
        log_error_with_traceback("Failed to start verse scheduler", e)
