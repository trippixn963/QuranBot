#!/usr/bin/env python3
# =============================================================================
# QuranBot - Daily Verses Manager
# =============================================================================
# Manages daily Quran verses and user interactions
# =============================================================================

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import discord
import pytz

from .tree_log import log_error_with_traceback, log_perfect_tree_section


class DailyVerseManager:
    """Manages daily Quran verses and user interactions"""

    def __init__(self, data_dir: Union[str, Path]):
        """Initialize the daily verse manager"""
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "daily_verse_state.json"
        self.verses_file = self.data_dir / "daily_verses_pool.json"
        self.current_verse = None
        self.verse_pool = []

        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing state and verses
        self.load_state()
        self.load_verses()

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
        """Get a random verse from the pool"""
        try:
            if not self.verse_pool:
                return None

            verse = random.choice(self.verse_pool)
            verse["timestamp"] = datetime.now(pytz.UTC).timestamp()
            self.current_verse = verse
            self.save_state()

            log_perfect_tree_section(
                "Random Verse Selected",
                [
                    ("surah", verse["surah"]),
                    ("verse", verse["verse"]),
                    ("status", "✅ Selected successfully"),
                ],
                "🎲",
            )
            return verse
        except Exception as e:
            log_error_with_traceback("Error getting random verse", e)
            return None

    def save_state(self) -> bool:
        """Save current state to file"""
        try:
            if self.current_verse:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self.current_verse, f, indent=2)

                log_perfect_tree_section(
                    "Daily Verse State Saved",
                    [
                        ("surah", self.current_verse["surah"]),
                        ("verse", self.current_verse["verse"]),
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
                    self.current_verse = json.load(f)

                log_perfect_tree_section(
                    "Daily Verse State Loaded",
                    [
                        ("surah", self.current_verse["surah"]),
                        ("verse", self.current_verse["verse"]),
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

        # Schedule initial verse check
        await check_and_post_verse(bot, channel_id)

        # Log successful setup
        log_perfect_tree_section(
            "Daily Verse System Setup",
            [
                ("status", "✅ System initialized"),
                ("channel", str(channel_id)),
                ("verses_loaded", str(len(daily_verse_manager.verse_pool))),
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
                    # Create embed
                    embed = discord.Embed(
                        title=f"Daily Verse - Surah {verse['surah']}, Verse {verse['verse']}",
                        description=verse["text"],
                        color=0x2ECC71,
                    )
                    embed.add_field(
                        name="Translation",
                        value=verse["translation"],
                        inline=False,
                    )
                    embed.add_field(
                        name="Transliteration",
                        value=verse["transliteration"],
                        inline=False,
                    )

                    # Add footer with next verse time
                    next_verse = daily_verse_manager.get_time_until_next_verse()
                    embed.set_footer(
                        text=f"Next verse in: {next_verse.days}d {next_verse.seconds//3600}h {(next_verse.seconds//60)%60}m"
                    )

                    # Send message
                    await channel.send(embed=embed)

                    log_perfect_tree_section(
                        "Daily Verse Posted",
                        [
                            ("surah", str(verse["surah"])),
                            ("verse", str(verse["verse"])),
                            ("channel", str(channel_id)),
                        ],
                        "📬",
                    )

    except Exception as e:
        log_error_with_traceback("Error checking and posting verse", e)
