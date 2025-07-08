# =============================================================================
# QuranBot - Daily Verses Manager
# =============================================================================
# Sends beautiful Quran verse embeds to general chat every 3 hours
# =============================================================================

import asyncio
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import discord

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# =============================================================================
# Configuration
# =============================================================================

# Path to daily verses data files
DATA_DIR = Path(__file__).parent.parent.parent / "data"
VERSES_STATE_FILE = DATA_DIR / "daily_verses_state.json"
VERSES_QUEUE_FILE = DATA_DIR / "daily_verses_queue.json"
VERSES_POOL_FILE = DATA_DIR / "daily_verses_pool.json"

# Send interval (3 hours in seconds)
VERSE_SEND_INTERVAL = 3 * 60 * 60  # 3 hours

# =============================================================================
# Daily Verses Manager
# =============================================================================


class DailyVersesManager:
    """Manages automated daily Quran verse sending to general chat"""

    def __init__(self):
        """Initialize the Daily Verses Manager with enhanced metadata support"""
        self.verses_pool = []
        self.verses_queue = []
        self.pool_metadata = {}
        self.queue_metadata = {}
        self.system_stats = {"verses_from_queue": 0, "verses_from_pool": 0}
        self.schedule_config = {"send_interval_hours": 3, "timezone": "UTC"}
        self.last_sent_verse = None
        self.last_sent_time = None
        self.bot = None
        self.daily_verse_channel_id = None
        self.developer_user_id = None
        self.verse_task = None
        self.load_verses_data()

    def load_verses_data(self):
        """Load verses data from JSON files with enhanced structure support"""
        try:
            # Load verses pool (enhanced structure)
            if VERSES_POOL_FILE.exists():
                with open(VERSES_POOL_FILE, "r", encoding="utf-8") as f:
                    pool_data = json.load(f)
                    # Handle enhanced structure with metadata
                    if isinstance(pool_data, dict) and "verses" in pool_data:
                        self.verses_pool = pool_data["verses"]
                        self.pool_metadata = pool_data.get("pool_metadata", {})
                    else:
                        # Fallback for old structure
                        self.verses_pool = (
                            pool_data if isinstance(pool_data, list) else []
                        )
                        self.pool_metadata = {}

            # Load verses queue (enhanced structure)
            if VERSES_QUEUE_FILE.exists():
                with open(VERSES_QUEUE_FILE, "r", encoding="utf-8") as f:
                    queue_data = json.load(f)
                    # Handle enhanced structure with metadata
                    if isinstance(queue_data, dict) and "queue" in queue_data:
                        self.verses_queue = queue_data["queue"]
                        self.queue_metadata = queue_data.get("queue_metadata", {})
                    else:
                        # Fallback for old structure
                        self.verses_queue = (
                            queue_data if isinstance(queue_data, list) else []
                        )
                        self.queue_metadata = {}

            # Load state (enhanced structure)
            if VERSES_STATE_FILE.exists():
                with open(VERSES_STATE_FILE, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                    self.last_sent_verse = state_data.get("last_sent_verse")
                    self.last_sent_time = state_data.get("last_sent_time")
                    self.system_stats = state_data.get("system_stats", {})
                    self.schedule_config = state_data.get("schedule_config", {})

            # Log enhanced data loading
            pool_categories = self.pool_metadata.get("categories", {})
            queue_themes = {}
            if self.verses_queue:
                for verse in self.verses_queue:
                    theme = verse.get("theme", "unknown")
                    queue_themes[theme] = queue_themes.get(theme, 0) + 1

            log_perfect_tree_section(
                "Daily Verses - Enhanced Data Loaded",
                [
                    ("verses_pool", f"{len(self.verses_pool)} verses in pool"),
                    ("pool_categories", f"{len(pool_categories)} categories"),
                    ("verses_queue", f"{len(self.verses_queue)} verses in queue"),
                    ("queue_themes", f"{len(queue_themes)} themes"),
                    (
                        "last_sent_verse",
                        (
                            f"Surah {self.last_sent_verse['surah']}:{self.last_sent_verse['ayah']}"
                            if self.last_sent_verse
                            else "None"
                        ),
                    ),
                    ("last_sent_time", self.last_sent_time or "Never"),
                    ("enhanced_features", "✅ Metadata, categories, themes loaded"),
                ],
                "📖",
            )

        except Exception as e:
            log_error_with_traceback("Error loading verses data", e)
            # Initialize with empty data if loading fails
            self.verses_pool = []
            self.verses_queue = []
            self.last_sent_verse = None
            self.last_sent_time = None

    def save_state(self):
        """Save current state to JSON file with enhanced structure"""
        try:
            # Update system stats
            if not hasattr(self, "system_stats"):
                self.system_stats = {}

            self.system_stats.update(
                {
                    "verses_from_queue": self.system_stats.get("verses_from_queue", 0),
                    "verses_from_pool": self.system_stats.get("verses_from_pool", 0),
                    "duplicate_prevention": True,
                    "auto_refill_enabled": True,
                }
            )

            # Update schedule config
            if not hasattr(self, "schedule_config"):
                self.schedule_config = {}

            self.schedule_config.update({"send_interval_hours": 3, "timezone": "UTC"})

            state_data = {
                "last_sent_verse": self.last_sent_verse,
                "last_sent_time": self.last_sent_time,
                "queue_position": (
                    len(self.verses_queue) if hasattr(self, "verses_queue") else 0
                ),
                "pool_size": (
                    len(self.verses_pool) if hasattr(self, "verses_pool") else 0
                ),
                "total_verses_sent": self.system_stats.get("verses_from_queue", 0)
                + self.system_stats.get("verses_from_pool", 0),
                "system_stats": self.system_stats,
                "schedule_config": self.schedule_config,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "version": "2.3.2",
            }

            with open(VERSES_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            log_error_with_traceback("Error saving verses state", e)

    def get_next_verse(self) -> Optional[Dict]:
        """Get the next verse to send from queue or pool with enhanced tracking"""
        try:
            # Initialize system stats if not present
            if not hasattr(self, "system_stats"):
                self.system_stats = {"verses_from_queue": 0, "verses_from_pool": 0}

            # Use queue first if available
            if self.verses_queue:
                verse = self.verses_queue.pop(0)

                # Update statistics
                self.system_stats["verses_from_queue"] = (
                    self.system_stats.get("verses_from_queue", 0) + 1
                )

                # Save updated queue with enhanced structure
                queue_data = {
                    "queue_metadata": getattr(self, "queue_metadata", {}),
                    "queue": self.verses_queue,
                }
                queue_data["queue_metadata"]["last_modified"] = datetime.now(
                    timezone.utc
                ).isoformat()
                queue_data["queue_metadata"]["total_verses"] = len(self.verses_queue)

                with open(VERSES_QUEUE_FILE, "w", encoding="utf-8") as f:
                    json.dump(queue_data, f, ensure_ascii=False, indent=2)

                log_perfect_tree_section(
                    "Daily Verses - Queue Verse Selected",
                    [
                        ("source", "📋 Queue (ordered)"),
                        ("verse_id", verse.get("id", "unknown")),
                        ("theme", verse.get("theme", "unknown")),
                        (
                            "surah",
                            f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                        ),
                        ("queue_remaining", len(self.verses_queue)),
                        ("priority", verse.get("priority", "N/A")),
                        ("coordination", "✅ Removed from queue to prevent duplicates"),
                    ],
                    "📋",
                )

                return verse

            # If queue is empty, pick random from pool
            elif self.verses_pool:
                verse = random.choice(self.verses_pool)

                # Remove from pool to prevent sending the same verse again
                self.verses_pool.remove(verse)

                # Update statistics
                self.system_stats["verses_from_pool"] = (
                    self.system_stats.get("verses_from_pool", 0) + 1
                )

                # Save updated pool with enhanced structure
                pool_data = {
                    "pool_metadata": getattr(self, "pool_metadata", {}),
                    "verses": self.verses_pool,
                }
                pool_data["pool_metadata"]["last_modified"] = datetime.now(
                    timezone.utc
                ).isoformat()
                pool_data["pool_metadata"]["total_verses"] = len(self.verses_pool)

                with open(VERSES_POOL_FILE, "w", encoding="utf-8") as f:
                    json.dump(pool_data, f, ensure_ascii=False, indent=2)

                log_perfect_tree_section(
                    "Daily Verses - Pool Verse Selected",
                    [
                        ("source", "🎲 Pool (random)"),
                        ("verse_id", verse.get("id", "unknown")),
                        ("category", verse.get("category", "unknown")),
                        (
                            "surah",
                            f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                        ),
                        ("pool_remaining", len(self.verses_pool)),
                        ("themes", ", ".join(verse.get("themes", []))),
                        ("coordination", "✅ Removed from pool to prevent duplicates"),
                    ],
                    "🎲",
                )

                return verse

            # No verses available
            else:
                log_perfect_tree_section(
                    "Daily Verses - No Verses Available",
                    [
                        ("status", "⚠️ No verses in queue or pool"),
                        ("queue_empty", "✅ All queue verses sent"),
                        ("pool_empty", "✅ All pool verses sent"),
                        (
                            "total_sent",
                            f"{self.system_stats.get('verses_from_queue', 0) + self.system_stats.get('verses_from_pool', 0)} verses",
                        ),
                        ("action", "Cannot send verse - all verses used"),
                    ],
                    "⚠️",
                )
                return None

        except Exception as e:
            log_error_with_traceback("Error getting next verse", e)
            return None

    async def create_verse_embed(self, verse: Dict) -> discord.Embed:
        """Create a beautiful embed for the verse with enhanced metadata"""
        try:
            # Get enhanced metadata
            theme = verse.get("theme", "")
            category = verse.get("category", "")
            themes_list = verse.get("themes", [])

            # Create description with enhanced info
            description_parts = [f"Ayah {verse['ayah']}"]
            if theme:
                description_parts.append(f"Theme: {theme.title()}")
            if category and category != theme:
                description_parts.append(f"Category: {category.title()}")

            description = " • ".join(description_parts)

            # Create embed with verse content
            embed = discord.Embed(
                title=f"📖 Daily Verse - {verse['surah_name']} ({verse['arabic_name']})",
                description=description,
                color=0x00D4AA,
            )

            # Add Arabic text field with black box background
            embed.add_field(
                name="🌙 Arabic",
                value=f"```\n{verse['arabic']}\n```",
                inline=False,
            )

            # Add English translation field with black box background
            embed.add_field(
                name="📝 Translation",
                value=f"```\n{verse['translation']}\n```",
                inline=False,
            )

            # Add themes as footer if available
            if themes_list and len(themes_list) > 1:
                themes_text = f"Related themes: {', '.join(themes_list)}"
                embed.add_field(
                    name="🏷️ Tags",
                    value=themes_text,
                    inline=False,
                )

            # Set footer with admin profile picture
            if self.bot and self.developer_user_id:
                try:
                    admin_user = await self.bot.fetch_user(self.developer_user_id)
                    if admin_user and admin_user.avatar:
                        embed.set_footer(
                            text="created by حَـــــنَـــــا",
                            icon_url=admin_user.avatar.url,
                        )
                    else:
                        embed.set_footer(text="created by حَـــــنَـــــا")
                except Exception as avatar_error:
                    log_error_with_traceback(
                        "Failed to fetch admin avatar for verse embed", avatar_error
                    )
                    embed.set_footer(text="created by حَـــــنَـــــا")
            else:
                embed.set_footer(text="created by حَـــــنَـــــا")

            return embed

        except Exception as e:
            log_error_with_traceback("Error creating verse embed", e)
            # Return fallback embed
            fallback_embed = discord.Embed(
                title="📖 Daily Verse",
                description="*Error loading verse content*",
                color=0x00D4AA,
            )
            fallback_embed.set_footer(text="created by حَـــــنَـــــا")
            return fallback_embed

    async def send_daily_verse(self):
        """Send a daily verse to the general chat"""
        try:
            if not self.bot or not self.daily_verse_channel_id:
                return

            channel = self.bot.get_channel(self.daily_verse_channel_id)
            if not channel:
                log_perfect_tree_section(
                    "Daily Verses - Channel Not Found",
                    [
                        ("channel_id", str(self.daily_verse_channel_id)),
                        ("status", "❌ Channel not accessible"),
                    ],
                    "❌",
                )
                return

            # Get next verse
            verse = self.get_next_verse()
            if not verse:
                return

            # Create embed
            embed = await self.create_verse_embed(verse)

            # Send the verse
            message = await channel.send(embed=embed)

            # Add dua reaction automatically
            try:
                await message.add_reaction("🤲")
            except Exception as reaction_error:
                log_error_with_traceback("Error adding dua reaction", reaction_error)

            # Update state
            self.last_sent_verse = verse
            self.last_sent_time = datetime.now(timezone.utc).isoformat()
            self.save_state()

            log_perfect_tree_section(
                "Daily Verses - Verse Sent",
                [
                    ("channel", channel.name),
                    (
                        "surah",
                        f"{verse['surah_name']} ({verse['surah']}:{verse['ayah']})",
                    ),
                    ("message_id", str(message.id)),
                    ("reaction_added", "🤲 Dua"),
                    ("queue_remaining", len(self.verses_queue)),
                ],
                "📖",
            )

        except Exception as e:
            log_error_with_traceback("Error sending daily verse", e)

    def setup(self, bot, daily_verse_channel_id: int, developer_user_id: int):
        """Set up the daily verses system"""
        try:
            self.bot = bot
            self.daily_verse_channel_id = daily_verse_channel_id
            self.developer_user_id = developer_user_id

            # Start the verse sending task
            self.start_verse_scheduler()

            # Calculate next verse time for display
            next_verse_info = "Will send immediately (first verse)"
            if self.last_sent_time:
                try:
                    # Handle different datetime string formats
                    if self.last_sent_time.endswith("Z"):
                        # ISO format with Z suffix
                        last_time = datetime.fromisoformat(
                            self.last_sent_time.replace("Z", "+00:00")
                        )
                    elif "+" in self.last_sent_time or self.last_sent_time.endswith(
                        "00:00"
                    ):
                        # ISO format with timezone
                        last_time = datetime.fromisoformat(self.last_sent_time)
                    else:
                        # ISO format without timezone - assume UTC
                        last_time = datetime.fromisoformat(self.last_sent_time).replace(
                            tzinfo=timezone.utc
                        )

                    now = datetime.now(timezone.utc)
                    time_diff = (now - last_time).total_seconds()
                    time_remaining = VERSE_SEND_INTERVAL - time_diff

                    if time_remaining > 0:
                        hours_remaining = time_remaining / 3600
                        minutes_remaining = (time_remaining % 3600) / 60
                        next_verse_info = f"Next verse in {hours_remaining:.1f}h ({minutes_remaining:.0f}m)"
                    else:
                        next_verse_info = "Will send immediately (overdue)"
                except Exception:
                    next_verse_info = "Will send immediately (time calculation error)"

            log_perfect_tree_section(
                "Daily Verses - Setup Complete",
                [
                    ("channel_id", str(daily_verse_channel_id)),
                    ("developer_id", str(developer_user_id)),
                    ("send_interval", f"{VERSE_SEND_INTERVAL // 3600} hours"),
                    (
                        "verses_available",
                        len(self.verses_pool) + len(self.verses_queue),
                    ),
                    ("next_verse", next_verse_info),
                    ("status", "✅ Daily verses system initialized"),
                ],
                "📖",
            )

        except Exception as e:
            log_error_with_traceback("Failed to setup daily verses system", e)

    def start_verse_scheduler(self):
        """Start the automatic verse sending task"""
        try:
            # Cancel existing task if running
            if self.verse_task and not self.verse_task.done():
                self.verse_task.cancel()

            # Start new verse task
            self.verse_task = asyncio.create_task(self._verse_scheduler_loop())

            log_perfect_tree_section(
                "Daily Verses - Scheduler Started",
                [
                    ("status", "✅ Verse scheduler started"),
                    ("interval", f"Every {VERSE_SEND_INTERVAL // 3600} hours"),
                    ("next_verse", "Will send soon if due"),
                ],
                "⏰",
            )

        except Exception as e:
            log_error_with_traceback("Failed to start verse scheduler", e)

    async def _verse_scheduler_loop(self):
        """Background task that sends verses every 3 hours"""
        while True:
            try:
                # Check if it's time to send a verse
                should_send = False
                sleep_duration = 600  # Default 10 minutes

                if self.last_sent_time is None:
                    # Never sent before, send immediately
                    should_send = True
                    reason = "First verse - never sent before"
                else:
                    # Check if 3 hours have passed since last verse
                    try:
                        # Handle different datetime string formats
                        if self.last_sent_time.endswith("Z"):
                            # ISO format with Z suffix
                            last_time = datetime.fromisoformat(
                                self.last_sent_time.replace("Z", "+00:00")
                            )
                        elif "+" in self.last_sent_time or self.last_sent_time.endswith(
                            "00:00"
                        ):
                            # ISO format with timezone
                            last_time = datetime.fromisoformat(self.last_sent_time)
                        else:
                            # ISO format without timezone - assume UTC
                            last_time = datetime.fromisoformat(
                                self.last_sent_time
                            ).replace(tzinfo=timezone.utc)

                        now = datetime.now(timezone.utc)
                        time_diff = (now - last_time).total_seconds()
                    except (ValueError, TypeError) as e:
                        # If datetime parsing fails, send immediately
                        log_perfect_tree_section(
                            "Daily Verses - Datetime Parse Error",
                            [
                                ("last_sent_time", str(self.last_sent_time)),
                                ("error", str(e)),
                                ("action", "Sending verse immediately"),
                            ],
                            "⚠️",
                        )
                        should_send = True
                        reason = "Datetime parsing error - sending immediately"
                        continue

                    time_remaining = VERSE_SEND_INTERVAL - time_diff

                    if time_diff >= VERSE_SEND_INTERVAL:
                        should_send = True
                        reason = f"3 hours elapsed ({time_diff // 3600:.1f}h ago)"
                    else:
                        # Calculate how long to wait until next verse
                        hours_remaining = time_remaining / 3600
                        minutes_remaining = (time_remaining % 3600) / 60

                        # Log the remaining time (only on first check or every hour)
                        if (
                            not hasattr(self, "_last_remaining_log")
                            or time_diff - getattr(self, "_last_remaining_log", 0)
                            >= 3600
                        ):
                            log_perfect_tree_section(
                                "Daily Verses - Schedule Status",
                                [
                                    ("status", "⏳ Waiting for next verse time"),
                                    ("last_sent", f"{time_diff // 3600:.1f}h ago"),
                                    (
                                        "time_remaining",
                                        f"{hours_remaining:.1f}h ({minutes_remaining:.0f}m)",
                                    ),
                                    ("next_check", "10 minutes"),
                                ],
                                "⏰",
                            )
                            self._last_remaining_log = time_diff

                        # If less than 15 minutes remaining, check more frequently
                        if time_remaining < 900:  # 15 minutes
                            sleep_duration = 60  # Check every minute when close

                if should_send:
                    log_perfect_tree_section(
                        "Daily Verses - Sending Scheduled Verse",
                        [
                            ("reason", reason),
                            ("status", "📖 Sending daily verse"),
                        ],
                        "📖",
                    )
                    await self.send_daily_verse()
                    # Reset the remaining time log after sending
                    if hasattr(self, "_last_remaining_log"):
                        delattr(self, "_last_remaining_log")

                # Wait before checking again
                await asyncio.sleep(sleep_duration)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in verse scheduler loop", e)
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes

    def reset_timer(self):
        """Reset the 3-hour timer (used by manual verse command)"""
        try:
            # Update the last sent time to now
            self.last_sent_time = datetime.now(timezone.utc).isoformat()
            self.save_state()

            # Restart the scheduler to pick up the new timing
            if self.verse_task and not self.verse_task.done():
                self.verse_task.cancel()

            # Start the scheduler again with the new timing
            if self.bot:
                self.start_verse_scheduler()

            log_perfect_tree_section(
                "Daily Verses - Timer Reset",
                [
                    ("status", "✅ Timer reset to 3 hours"),
                    ("last_sent_time", self.last_sent_time),
                    ("scheduler_restarted", "Yes"),
                ],
                "🔄",
            )

        except Exception as e:
            log_error_with_traceback("Error resetting verse timer", e)

    def stop_verse_scheduler(self):
        """Stop the verse scheduler"""
        try:
            if self.verse_task and not self.verse_task.done():
                self.verse_task.cancel()

            log_perfect_tree_section(
                "Daily Verses - Scheduler Stopped",
                [
                    ("status", "🛑 Verse scheduler stopped"),
                ],
                "🛑",
            )

        except Exception as e:
            log_error_with_traceback("Error stopping verse scheduler", e)


# =============================================================================
# Global Instance
# =============================================================================

# Global daily verses manager instance
daily_verses_manager = DailyVersesManager()


# =============================================================================
# Utility Functions
# =============================================================================


def setup_daily_verses(bot, daily_verse_channel_id: int, developer_user_id: int):
    """Set up the daily verses system"""
    daily_verses_manager.setup(bot, daily_verse_channel_id, developer_user_id)


def stop_daily_verses():
    """Stop the daily verses system"""
    daily_verses_manager.stop_verse_scheduler()


# =============================================================================
# Export Functions
# =============================================================================

__all__ = [
    "DailyVersesManager",
    "daily_verses_manager",
    "setup_daily_verses",
    "stop_daily_verses",
]
