# =============================================================================
# QuranBot - Mecca Prayer Times Module
# =============================================================================
# Handles prayer time notifications for the Holy City of Mecca, providing
# gentle reminders to the global community when it's prayer time in the
# Sacred Mosque (Masjid al-Haram).
# =============================================================================

import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path
import random

import discord
import pytz
import requests

from src.config import get_config
from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Mecca timezone (Arabia Standard Time)
MECCA_TZ = pytz.timezone("Asia/Riyadh")

# Prayer names in Arabic and English
PRAYER_NAMES = {
    "fajr": {"arabic": "الفجر", "english": "Fajr", "emoji": "🌅"},
    "dhuhr": {"arabic": "الظهر", "english": "Dhuhr", "emoji": "☀️"},
    "asr": {"arabic": "العصر", "english": "Asr", "emoji": "🌤️"},
    "maghrib": {"arabic": "المغرب", "english": "Maghrib", "emoji": "🌆"},
    "isha": {"arabic": "العشاء", "english": "Isha", "emoji": "🌙"},
}

# Map prayer times to appropriate dua categories
PRAYER_DUA_MAPPING = {
    "fajr": "morning_duas",  # Morning duas for Fajr
    "dhuhr": "friday_duas",  # Friday duas for Dhuhr (if Friday), otherwise morning
    "asr": "friday_duas",  # Friday duas for Asr (if Friday), otherwise general
    "maghrib": "evening_duas",  # Evening duas for Maghrib
    "isha": "evening_duas",  # Evening duas for Isha
}

# Spiritual messages for each prayer
PRAYER_MESSAGES = {
    "fajr": {
        "message": "The dawn prayer in the Holy City - a blessed start to the day",
        "dua_tip": "A beautiful time for morning remembrance and seeking Allah's guidance",
    },
    "dhuhr": {
        "message": "The midday prayer in the Sacred Mosque - a moment of peace",
        "dua_tip": "A perfect time to pause and remember Allah in the midst of daily life",
    },
    "asr": {
        "message": "The afternoon prayer in Mecca - blessed moments in the Holy City",
        "dua_tip": "A time of reflection and seeking Allah's protection for the rest of the day",
    },
    "maghrib": {
        "message": "The sunset prayer in the Holy City - a blessed time for dua",
        "dua_tip": "The time when duas are especially accepted - a gift from Allah",
    },
    "isha": {
        "message": "The night prayer in the Sacred Mosque - tranquil moments with Allah",
        "dua_tip": "A peaceful time for contemplation and seeking forgiveness",
    },
}


class MeccaPrayerNotifier:
    """Handles prayer time notifications for Mecca"""

    def __init__(self, bot):
        self.bot = bot
        self.config = get_config()
        self.prayer_cache_file = Path("data/prayer_cache.json")
        self.last_notification_file = Path("data/last_mecca_notification.json")
        self.time_based_duas_file = Path("data/time_based_duas.json")
        self.daily_prayers: dict[str, str] = {}
        self.time_based_duas: dict = {}
        self._scheduler_task: asyncio.Task | None = None

        # Load time-based duas
        self._load_time_based_duas()

    def _load_time_based_duas(self):
        """Load time-based duas from JSON file"""
        try:
            if self.time_based_duas_file.exists():
                with open(self.time_based_duas_file, encoding="utf-8") as f:
                    self.time_based_duas = json.load(f)

                log_perfect_tree_section(
                    "Mecca Prayer - Time-Based Duas Loaded",
                    [
                        ("file", str(self.time_based_duas_file)),
                        ("categories", str(len(self.time_based_duas))),
                        (
                            "total_duas",
                            str(
                                sum(
                                    len(category)
                                    for category in self.time_based_duas.values()
                                )
                            ),
                        ),
                        ("status", "✅ Time-based duas integrated"),
                    ],
                    "🕌",
                )
            else:
                log_perfect_tree_section(
                    "Mecca Prayer - Time-Based Duas Not Found",
                    [
                        ("file", str(self.time_based_duas_file)),
                        ("status", "⚠️ Using fallback dua system"),
                        (
                            "action",
                            "Create time_based_duas.json for enhanced experience",
                        ),
                    ],
                    "⚠️",
                )
                # Fallback: empty dict will cause fallback to prayer duas
                self.time_based_duas = {}
        except Exception as e:
            log_error_with_traceback(
                "Error loading time-based duas for Mecca prayers", e
            )
            self.time_based_duas = {}

    def _get_prayer_appropriate_dua(self, prayer_name: str) -> dict:
        """Get the most appropriate dua for the specific prayer time"""
        try:
            # Check if it's Friday for special Friday duas
            is_friday = datetime.now(MECCA_TZ).weekday() == 4  # Friday

            # Determine the appropriate dua category
            if prayer_name in PRAYER_DUA_MAPPING:
                primary_category = PRAYER_DUA_MAPPING[prayer_name]

                # For Dhuhr and Asr on Friday, prefer Friday duas
                if (
                    prayer_name in ["dhuhr", "asr"]
                    and is_friday
                    and "friday_duas" in self.time_based_duas
                    and self.time_based_duas["friday_duas"]
                ):
                    category = "friday_duas"
                else:
                    category = primary_category
            else:
                category = "morning_duas"  # Default fallback

            # Get duas from the determined category
            if self.time_based_duas.get(category):
                duas = self.time_based_duas[category]
                selected_dua = random.choice(duas)

                log_perfect_tree_section(
                    "Mecca Prayer - Dua Selection",
                    [
                        ("prayer", prayer_name),
                        ("category", category),
                        ("is_friday", str(is_friday)),
                        ("dua_name", selected_dua.get("name", "Unknown")),
                        ("source", selected_dua.get("source", "Unknown")),
                    ],
                    "🤲",
                )

                return selected_dua

            # Fallback to any available category
            for fallback_category in ["morning_duas", "evening_duas", "friday_duas"]:
                if self.time_based_duas.get(fallback_category):
                    selected_dua = random.choice(
                        self.time_based_duas[fallback_category]
                    )

                    log_perfect_tree_section(
                        "Mecca Prayer - Fallback Dua",
                        [
                            ("prayer", prayer_name),
                            ("fallback_category", fallback_category),
                            ("dua_name", selected_dua.get("name", "Unknown")),
                        ],
                        "⚠️",
                    )

                    return selected_dua

            # Final fallback to prayer duas system
            return self._get_fallback_prayer_dua()

        except Exception as e:
            log_error_with_traceback("Error selecting prayer-appropriate dua", e)
            return self._get_fallback_prayer_dua()

    def _get_fallback_prayer_dua(self) -> dict:
        """Fallback to prayer duas if time-based system fails"""
        return {
            "arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
            "english": "Our Lord, give us good in this world and good in the Hereafter, and save us from the punishment of the Fire.",
            "source": "Quran 2:201",
            "name": "Dua for Good in Both Worlds",
        }

    async def get_mecca_prayer_times(self, date: datetime = None) -> dict[str, str]:
        """Get prayer times for Mecca for a specific date"""
        if date is None:
            date = datetime.now(MECCA_TZ)

        date_str = date.strftime("%Y-%m-%d")

        # Check cache first
        if self.prayer_cache_file.exists():
            try:
                with open(self.prayer_cache_file) as f:
                    cache = json.load(f)
                    if date_str in cache:
                        log_perfect_tree_section(
                            "Mecca Prayer Times - Cache Hit",
                            [
                                ("date", date_str),
                                ("status", "✅ Using cached prayer times"),
                                ("prayers", str(list(cache[date_str].keys()))),
                            ],
                            "🕌",
                        )
                        return cache[date_str]
            except Exception as e:
                log_error_with_traceback("Error reading prayer cache", e)

        # Fetch from API (using Islamic Network API)
        try:
            # Mecca coordinates: 21.4225, 39.8262
            url = f"http://api.aladhan.com/v1/timings/{date_str}"
            params = {
                "latitude": 21.4225,
                "longitude": 39.8262,
                "method": 4,  # Umm Al-Qura method (used in Saudi Arabia)
                "timezone": "Asia/Riyadh",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data["code"] == 200:
                timings = data["data"]["timings"]
                prayer_times = {
                    "fajr": timings["Fajr"],
                    "dhuhr": timings["Dhuhr"],
                    "asr": timings["Asr"],
                    "maghrib": timings["Maghrib"],
                    "isha": timings["Isha"],
                }

                # Cache the result
                cache = {}
                if self.prayer_cache_file.exists():
                    try:
                        with open(self.prayer_cache_file) as f:
                            cache = json.load(f)
                    except:
                        pass

                cache[date_str] = prayer_times

                # Keep only last 7 days in cache
                cutoff = (date - timedelta(days=7)).strftime("%Y-%m-%d")
                cache = {k: v for k, v in cache.items() if k >= cutoff}

                with open(self.prayer_cache_file, "w") as f:
                    json.dump(cache, f, indent=2)

                log_perfect_tree_section(
                    "Mecca Prayer Times - API Success",
                    [
                        ("date", date_str),
                        ("status", "✅ Fetched from Islamic Network API"),
                        ("method", "Umm Al-Qura (Saudi Arabia)"),
                        ("cached", "✅ Saved to cache"),
                    ],
                    "🕌",
                )

                return prayer_times
            else:
                raise Exception(f"API returned code {data['code']}")

        except Exception as e:
            log_error_with_traceback("Error fetching Mecca prayer times", e)

            # Return default times as fallback (approximate Mecca times)
            default_times = {
                "fajr": "05:30",
                "dhuhr": "12:30",
                "asr": "15:45",
                "maghrib": "18:15",
                "isha": "19:45",
            }

            log_perfect_tree_section(
                "Mecca Prayer Times - Fallback",
                [
                    ("date", date_str),
                    ("status", "⚠️ Using default approximate times"),
                    ("reason", "API unavailable"),
                ],
                "⚠️",
            )

            return default_times

    async def create_prayer_notification_embed(
        self, prayer_name: str, prayer_time: str
    ) -> discord.Embed:
        """Create a beautiful embed for prayer time notification"""
        prayer_info = PRAYER_NAMES[prayer_name]
        messages = PRAYER_MESSAGES[prayer_name]

        # Convert 24-hour time to 12-hour AM/PM format
        try:
            from datetime import datetime

            time_obj = datetime.strptime(prayer_time, "%H:%M")
            formatted_time = time_obj.strftime("%I:%M %p").lstrip("0")
        except:
            # Fallback if parsing fails
            formatted_time = f"{prayer_time} AST"

        # Get appropriate dua for the prayer time
        selected_dua = self._get_prayer_appropriate_dua(prayer_name)

        # Create embed with single mosque emoji in title
        embed = discord.Embed(
            title=f"🕌 {prayer_info['english']} Time in the Holy City",
            description=f"*{messages['message']}*\n\n\n"
            f"📿 **Dua from {selected_dua.get('source', 'Quran')}:**\n\n"
            f"```{selected_dua['arabic']}```\n\n"
            f"```{selected_dua['english']}```",
            color=0x1ABC9C,  # Beautiful teal color
            timestamp=datetime.now(),
        )

        # Add prayer time field with black box formatting
        embed.add_field(
            name="🕐 Prayer Time in Mecca",
            value=f"```{formatted_time} AST (Arabia Standard Time)```",
            inline=False,
        )

        # Add spiritual reminder with black box formatting
        embed.add_field(
            name="🤲 Blessed Moments",
            value="```Wherever you are in the world, this is a blessed time for dua```",
            inline=False,
        )

        # Set bot thumbnail
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # Set footer with admin profile picture
        try:
            admin_user = await self.bot.fetch_user(self.config.DEVELOPER_ID)
            if admin_user and admin_user.avatar:
                embed.set_footer(
                    text="Created by حَـــــنَـــــا", icon_url=admin_user.avatar.url
                )
            else:
                embed.set_footer(text="Created by حَـــــنَـــــا")
        except (discord.HTTPException, discord.NotFound, AttributeError):
            embed.set_footer(text="Created by حَـــــنَـــــا")

        return embed

    def has_notification_been_sent(self, prayer_name: str, date_str: str) -> bool:
        """Check if notification for this prayer has already been sent today"""
        if not self.last_notification_file.exists():
            return False

        try:
            with open(self.last_notification_file) as f:
                data = json.load(f)
                return data.get(date_str, {}).get(prayer_name, False)
        except:
            return False

    def mark_notification_sent(self, prayer_name: str, date_str: str):
        """Mark that notification for this prayer has been sent"""
        data = {}
        if self.last_notification_file.exists():
            try:
                with open(self.last_notification_file) as f:
                    data = json.load(f)
            except:
                pass

        if date_str not in data:
            data[date_str] = {}
        data[date_str][prayer_name] = True

        # Keep only last 7 days
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        data = {k: v for k, v in data.items() if k >= cutoff}

        with open(self.last_notification_file, "w") as f:
            json.dump(data, f, indent=2)

    async def check_and_send_prayer_notification(self):
        """Check if it's prayer time in Mecca and send notification if needed"""
        try:
            mecca_now = datetime.now(MECCA_TZ)
            current_time = mecca_now.strftime("%H:%M")
            date_str = mecca_now.strftime("%Y-%m-%d")

            # Get today's prayer times
            prayer_times = await self.get_mecca_prayer_times(mecca_now)

            # Check each prayer time
            for prayer_name, prayer_time in prayer_times.items():
                # Check if current time matches prayer time (within 1 minute window)
                prayer_dt = datetime.strptime(
                    f"{date_str} {prayer_time}", "%Y-%m-%d %H:%M"
                )
                prayer_dt = MECCA_TZ.localize(prayer_dt)

                time_diff = abs((mecca_now - prayer_dt).total_seconds())

                # If within 30 seconds of prayer time and not already sent
                if time_diff <= 30 and not self.has_notification_been_sent(
                    prayer_name, date_str
                ):
                    await self.send_prayer_notification(prayer_name, prayer_time)
                    self.mark_notification_sent(prayer_name, date_str)

        except Exception as e:
            log_error_with_traceback("Error in prayer notification check", e)

    async def send_prayer_notification(self, prayer_name: str, prayer_time: str):
        """Send prayer notification to the daily verse channel"""
        try:
            channel_id = self.config.daily_verse_channel_id
            if not channel_id:
                log_perfect_tree_section(
                    "Mecca Prayer Notification - No Channel",
                    [
                        ("prayer", prayer_name),
                        ("status", "⚠️ No daily verse channel configured"),
                        ("action", "Skipping notification"),
                    ],
                    "⚠️",
                )
                return

            channel = self.bot.get_channel(channel_id)
            if not channel:
                log_perfect_tree_section(
                    "Mecca Prayer Notification - Channel Not Found",
                    [
                        ("prayer", prayer_name),
                        ("channel_id", str(channel_id)),
                        ("status", "❌ Channel not accessible"),
                    ],
                    "❌",
                )
                return

            # Create and send embed
            embed = await self.create_prayer_notification_embed(
                prayer_name, prayer_time
            )
            message = await channel.send(embed=embed)

            # Add dua emoji reaction
            dua_emoji = "🤲"
            await message.add_reaction(dua_emoji)

            # Set up reaction monitoring
            asyncio.create_task(self._monitor_prayer_reactions(message, dua_emoji))

            log_perfect_tree_section(
                "Mecca Prayer Notification - Sent",
                [
                    (
                        "prayer",
                        f"{PRAYER_NAMES[prayer_name]['emoji']} {PRAYER_NAMES[prayer_name]['english']}",
                    ),
                    ("time", prayer_time),
                    ("channel", channel.name),
                    ("status", "✅ Notification sent successfully"),
                    ("reaction_added", f"{dua_emoji} Dua emoji added"),
                ],
                "🕌",
            )

        except Exception as e:
            log_error_with_traceback("Error sending prayer notification", e)

    async def _monitor_prayer_reactions(
        self, message: discord.Message, allowed_emoji: str
    ):
        """Monitor prayer notification reactions and remove unwanted ones"""
        try:

            def check(reaction, user):
                return (
                    reaction.message.id == message.id
                    and not user.bot
                    and str(reaction.emoji) != allowed_emoji
                )

            # Monitor for 24 hours
            timeout = 24 * 60 * 60  # 24 hours in seconds
            end_time = asyncio.get_event_loop().time() + timeout

            while asyncio.get_event_loop().time() < end_time:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", check=check, timeout=300
                    )  # Check every 5 minutes

                    # Remove the unwanted reaction
                    await reaction.remove(user)

                    log_perfect_tree_section(
                        "Prayer Reaction - Cleaned",
                        [
                            ("user", user.display_name),
                            ("removed_emoji", str(reaction.emoji)),
                            ("allowed_emoji", allowed_emoji),
                            ("action", "🧹 Unwanted reaction removed"),
                        ],
                        "🕌",
                    )

                except TimeoutError:
                    # Continue monitoring
                    continue

        except Exception as e:
            log_error_with_traceback("Error monitoring prayer reactions", e)

    async def start_prayer_scheduler(self):
        """Start the prayer time monitoring scheduler"""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()

        self._scheduler_task = asyncio.create_task(self._prayer_scheduler_loop())

        log_perfect_tree_section(
            "Mecca Prayer Scheduler - Started",
            [
                ("status", "✅ Prayer time monitoring active"),
                ("check_interval", "60 seconds"),
                ("timezone", "Asia/Riyadh (Mecca)"),
                ("prayers_monitored", "5 daily prayers"),
            ],
            "🕌",
        )

    async def _prayer_scheduler_loop(self):
        """Main scheduler loop for prayer time monitoring"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.check_and_send_prayer_notification()
            except asyncio.CancelledError:
                log_perfect_tree_section(
                    "Mecca Prayer Scheduler - Stopped",
                    [
                        ("status", "🛑 Prayer scheduler stopped"),
                        ("reason", "Task cancelled"),
                    ],
                    "🕌",
                )
                break
            except Exception as e:
                log_error_with_traceback("Error in prayer scheduler loop", e)
                await asyncio.sleep(60)  # Wait before retrying


# Global instance
mecca_prayer_notifier: MeccaPrayerNotifier | None = None


async def setup_mecca_prayer_notifications(bot) -> None:
    """Set up the Mecca prayer time notification system"""
    global mecca_prayer_notifier

    try:
        mecca_prayer_notifier = MeccaPrayerNotifier(bot)
        await mecca_prayer_notifier.start_prayer_scheduler()

        log_perfect_tree_section(
            "Mecca Prayer System Setup",
            [
                ("status", "✅ System initialized"),
                ("monitoring", "5 daily prayers in Mecca"),
                ("scheduler", "✅ Prayer time scheduler started"),
                ("notifications", "✅ Beautiful embeds with bot thumbnail"),
                ("spiritual_connection", "🕌 Connecting global ummah to Holy City"),
            ],
            "🕌",
        )

    except Exception as e:
        log_error_with_traceback("Error setting up Mecca prayer notifications", e)


def get_mecca_prayer_notifier() -> MeccaPrayerNotifier | None:
    """Get the global Mecca prayer notifier instance"""
    return mecca_prayer_notifier
