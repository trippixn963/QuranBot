# =============================================================================
# QuranBot - Surah Mapping and Metadata
# =============================================================================
# Comprehensive Surah information management with perfect tree logging
# =============================================================================

import json
import os
import random
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import discord

# Import tree logging functions
try:
    from .tree_log import (
        log_error_with_traceback,
        log_perfect_tree_section,
        log_warning_with_context,
    )
except ImportError:
    # Fallback imports for different contexts
    try:
        from tree_log import (
            log_error_with_traceback,
            log_perfect_tree_section,
            log_warning_with_context,
        )
    except ImportError:
        # Minimal fallback functions
        def log_error_with_traceback(msg, e):
            print(f"ERROR: {msg} - {e}")

        def log_perfect_tree_section(title, items, emoji=""):
            print(f"{emoji} {title}")
            for key, value in items:
                print(f"  {key}: {value}")

        def log_warning_with_context(msg, context=""):
            print(f"WARNING: {msg} - {context}")


# =============================================================================
# Surah Data Classes and Enums
# =============================================================================


class RevelationType(Enum):
    """Type of revelation location"""

    MECCAN = "Meccan"
    MEDINAN = "Medinan"


@dataclass
class SurahInfo:
    """Complete information about a Surah"""

    number: int
    name_arabic: str
    name_english: str
    name_transliteration: str
    emoji: str
    verses: int
    revelation_type: RevelationType
    meaning: str
    description: str


# =============================================================================
# JSON Data Loading
# =============================================================================


def load_surah_database() -> Dict[int, SurahInfo]:
    """Load Surah database from JSON file with comprehensive error handling"""
    try:
        json_path = Path(__file__).parent / "surahs.json"

        log_perfect_tree_section(
            "Loading Surah Database",
            [
                ("source", "surahs.json"),
                ("status", "📖 Loading from JSON file"),
            ],
            "📖",
        )

        try:
            if not json_path.exists():
                log_warning_with_context(
                    "surahs.json file not found",
                    f"Expected path: {json_path}",
                )
                return {}

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            log_perfect_tree_section(
                "Database Load Success",
                [
                    ("surahs_loaded", f"{len(data)} Surahs from JSON"),
                    ("status", "✅ Data loaded successfully"),
                ],
                "📊",
            )

            database = {}
            # Handle JSON format with string keys (e.g., {"1": {...}, "2": {...}})
            for number_str, surah_data in data.items():
                try:
                    surah_number = int(number_str)
                    database[surah_number] = SurahInfo(
                        number=surah_data["number"],
                        name_arabic=surah_data["name_arabic"],
                        name_transliteration=surah_data["name_transliteration"],
                        name_english=surah_data["name_english"],
                        verses=surah_data["verses"],
                        revelation_type=RevelationType(surah_data["revelation_type"]),
                        emoji=surah_data.get("emoji", "📖"),
                        meaning=surah_data.get("meaning", surah_data["name_english"]),
                        description=surah_data.get("description", ""),
                    )
                except (KeyError, ValueError, TypeError) as e:
                    log_warning_with_context(
                        f"Error processing Surah {number_str}",
                        f"Skipping due to: {str(e)}",
                    )
                    continue

            if len(database) == 114:
                log_perfect_tree_section(
                    "Database Validation",
                    [
                        ("total_surahs", "114"),
                        ("status", "✅ All Surahs loaded successfully"),
                    ],
                    "✅",
                )
            else:
                log_warning_with_context(
                    f"Incomplete database: {len(database)}/114 Surahs loaded",
                    "Some Surahs may be missing or corrupted",
                )

            return database

        except FileNotFoundError as e:
            log_error_with_traceback("Surah database file not found", e)
            return {}

        except json.JSONDecodeError as e:
            log_error_with_traceback("Invalid JSON format in Surah database", e)
            return {}

        except Exception as e:
            log_error_with_traceback("Unexpected error loading Surah database", e)
            return {}

    except Exception as e:
        log_error_with_traceback("Critical error in load_surah_database", e)
        return {}


# Load the database once when module is imported
SURAH_DATABASE = load_surah_database()

# =============================================================================
# Utility Functions
# =============================================================================


def get_surah_info(surah_number: int) -> Optional[SurahInfo]:
    """Get complete information about a Surah by number"""
    try:
        if not validate_surah_number(surah_number):
            log_warning_with_context(
                f"Invalid Surah number: {surah_number}", "Valid range is 1-114"
            )
            return None

        if not SURAH_DATABASE:
            log_error_with_traceback(
                "Surah database not loaded", "Cannot retrieve Surah information"
            )
            return None

        return SURAH_DATABASE.get(surah_number)

    except Exception as e:
        log_error_with_traceback(
            f"Error getting Surah info for number {surah_number}", e
        )
        return None


def get_surah_name(surah_number: int) -> str:
    """Get the transliterated name of a Surah by number"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback(
                "Surah database not loaded", "Cannot retrieve Surah information"
            )
            return f"Surah {surah_number}"

        if surah_number in SURAH_DATABASE:
            surah = SURAH_DATABASE[surah_number]
            return surah.name_transliteration
        else:
            log_perfect_tree_section(
                "Surah Not Found",
                [
                    ("surah_number", surah_number),
                    ("status", "⚠️ Using fallback name"),
                ],
                "⚠️",
            )
            return f"Surah {surah_number}"
    except Exception as e:
        log_error_with_traceback(f"Error getting Surah name for {surah_number}", e)
        return f"Surah {surah_number}"


def get_surah_display(surah_number: int) -> str:
    """Get a display-friendly Surah name with number"""
    try:
        surah = get_surah_info(surah_number)
        if not surah:
            log_perfect_tree_section(
                "Surah Display Fallback",
                [
                    ("surah_number", surah_number),
                    ("status", "⚠️ Using fallback display"),
                ],
                "⚠️",
            )
            return f"Surah {surah_number}"

        return f"{surah.number}. {surah.name_transliteration}"
    except Exception as e:
        log_error_with_traceback(f"Error getting Surah display for {surah_number}", e)
        return f"Surah {surah_number}"


def get_random_surah() -> Optional[SurahInfo]:
    """Get a random Surah from the database"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback("Cannot get random Surah", "Database not loaded")
            return None

        surah_number = random.randint(1, 114)
        surah = get_surah_info(surah_number)
        if surah:
            log_perfect_tree_section(
                "Random Surah Selected",
                [
                    ("surah_number", surah_number),
                    ("surah_name", surah.name_transliteration),
                    ("status", "🎲 Random selection complete"),
                ],
                "🎲",
            )
            return surah
        else:
            log_error_with_traceback(
                f"Random Surah {surah_number} not found", "Database issue"
            )
            return None
    except Exception as e:
        log_error_with_traceback("Error getting random Surah", e)
        return None


def search_surahs(query: str) -> List[SurahInfo]:
    """Search for Surahs by name or number"""
    try:
        results = []
        query_lower = query.lower().strip()

        # Try exact number match first
        if query_lower.isdigit():
            surah_number = int(query_lower)
            if validate_surah_number(surah_number):
                surah = get_surah_info(surah_number)
                if surah:
                    results.append(surah)
                    return results

        # Search by name (prioritize transliteration)
        for i in range(1, 115):
            surah = get_surah_info(i)
            if not surah:
                continue

            # Check transliteration first
            if (
                query_lower in surah.name_transliteration.lower()
                or query_lower in surah.name_arabic
                or query_lower in surah.name_english.lower()
            ):
                results.append(surah)

        return results[:10]  # Limit to 10 results

    except Exception as e:
        log_error_with_traceback("Error searching Surahs", e)
        return []


def get_meccan_surahs() -> List[SurahInfo]:
    """Get all Meccan Surahs"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback("Cannot get Meccan Surahs", "Database not loaded")
            return []

        meccan = [
            s
            for s in SURAH_DATABASE.values()
            if s.revelation_type == RevelationType.MECCAN
        ]
        log_perfect_tree_section(
            "Meccan Surahs Retrieved",
            [
                ("count", len(meccan)),
                ("status", "🕌 Meccan Surahs found"),
            ],
            "🕌",
        )
        return meccan

    except Exception as e:
        log_error_with_traceback("Error getting Meccan Surahs", e)
        return []


def get_medinan_surahs() -> List[SurahInfo]:
    """Get all Medinan Surahs"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback("Cannot get Medinan Surahs", "Database not loaded")
            return []

        medinan = [
            s
            for s in SURAH_DATABASE.values()
            if s.revelation_type == RevelationType.MEDINAN
        ]
        log_perfect_tree_section(
            "Medinan Surahs Retrieved",
            [
                ("count", len(medinan)),
                ("status", "🏛️ Medinan Surahs found"),
            ],
            "🏛️",
        )
        return medinan

    except Exception as e:
        log_error_with_traceback("Error getting Medinan Surahs", e)
        return []


def get_short_surahs(max_verses: int = 20) -> List[SurahInfo]:
    """Get Surahs with verses count less than or equal to max_verses"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback("Cannot get short Surahs", "Database not loaded")
            return []

        short = [s for s in SURAH_DATABASE.values() if s.verses <= max_verses]
        log_perfect_tree_section(
            "Short Surahs Retrieved",
            [
                ("count", len(short)),
                ("max_verses", max_verses),
                ("status", f"📜 Surahs with ≤{max_verses} verses"),
            ],
            "📜",
        )
        return short

    except Exception as e:
        log_error_with_traceback("Error getting short Surahs", e)
        return []


def get_long_surahs(min_verses: int = 100) -> List[SurahInfo]:
    """Get Surahs with verses count greater than or equal to min_verses"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback("Cannot get long Surahs", "Database not loaded")
            return []

        long = [s for s in SURAH_DATABASE.values() if s.verses >= min_verses]
        log_perfect_tree_section(
            "Long Surahs Retrieved",
            [
                ("count", len(long)),
                ("min_verses", min_verses),
                ("status", f"📚 Surahs with ≥{min_verses} verses"),
            ],
            "📚",
        )
        return long

    except Exception as e:
        log_error_with_traceback("Error getting long Surahs", e)
        return []


def validate_surah_number(surah_number: int) -> bool:
    """Validate that a Surah number is within valid range (1-114)"""
    try:
        is_valid = 1 <= surah_number <= 114
        if not is_valid:
            log_perfect_tree_section(
                "Invalid Surah Number",
                [
                    ("surah_number", surah_number),
                    ("valid_range", "1-114"),
                    ("status", "❌ Invalid number"),
                ],
                "❌",
            )
        return is_valid

    except Exception as e:
        log_error_with_traceback(f"Error validating Surah number {surah_number}", e)
        return False


def get_quran_statistics() -> Dict[str, int]:
    """Get statistics about the Quran"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback(
                "Cannot get Surah statistics", "Database not loaded"
            )
            return {}

        meccan_count = len(get_meccan_surahs())
        medinan_count = len(get_medinan_surahs())
        total_verses = sum(s.verses for s in SURAH_DATABASE.values())

        stats = {
            "total_surahs": len(SURAH_DATABASE),
            "meccan_surahs": meccan_count,
            "medinan_surahs": medinan_count,
            "total_verses": total_verses,
            "shortest_surah": min(
                SURAH_DATABASE.values(), key=lambda s: s.verses
            ).verses,
            "longest_surah": max(
                SURAH_DATABASE.values(), key=lambda s: s.verses
            ).verses,
        }

        log_perfect_tree_section(
            "Quran Statistics Generated",
            [
                ("total_metrics", len(stats)),
                ("status", "📊 Statistics compiled successfully"),
            ],
            "📊",
        )
        return stats

    except Exception as e:
        log_error_with_traceback("Error generating Surah statistics", e)
        return {}


# =============================================================================
# Discord Formatting Functions
# =============================================================================


def format_now_playing(
    surah_info: Optional[SurahInfo], reciter: str = "Unknown"
) -> str:
    """Format a now playing message for Discord"""
    try:
        if not surah_info:
            log_perfect_tree_section(
                "Now Playing Format Warning",
                [
                    ("surah_info", "None provided"),
                    ("status", "⚠️ Using fallback message"),
                ],
                "⚠️",
            )
            return "🎵 **Now Playing** • *Unknown*"

        message = (
            f"🎵 **Now Playing** • "
            f"{surah_info.emoji} **{surah_info.name_transliteration}** "
            f"({surah_info.name_arabic}) • "
            f"*{surah_info.verses} verses* • "
            f"**{reciter}**"
        )

        log_perfect_tree_section(
            "Now Playing Message Formatted",
            [
                ("surah", surah_info.name_transliteration),
                ("reciter", reciter),
                ("status", "🎵 Message formatted"),
            ],
            "🎵",
        )
        return message

    except Exception as e:
        log_error_with_traceback("Error formatting now playing message", e)
        return "🎵 **Now Playing** • *Error*"


def format_surah_embed(surah_info: Optional[SurahInfo]) -> Optional[discord.Embed]:
    """Format a Discord embed for Surah information"""
    try:
        if not discord:
            log_perfect_tree_section(
                "Discord Embed Warning",
                [
                    ("discord_available", "False"),
                    ("status", "⚠️ Discord not available"),
                ],
                "⚠️",
            )
            return None

        if not surah_info:
            log_perfect_tree_section(
                "Embed Format Warning",
                [
                    ("surah_info", "None provided"),
                    ("status", "⚠️ Using error embed"),
                ],
                "⚠️",
            )
            return discord.Embed(
                title="❌ Error",
                description="No Surah information provided",
                color=0xFF0000,
            )

        embed = discord.Embed(
            title=f"{surah_info.emoji} {surah_info.name_transliteration}",
            description=f"**{surah_info.name_arabic}** • *{surah_info.name_english}*",
            color=0x00D4AA,
        )
        embed.add_field(name="📖 Surah", value=f"#{surah_info.number}", inline=True)
        embed.add_field(name="📜 Verses", value=f"{surah_info.verses}", inline=True)
        embed.add_field(
            name="🏛️ Revelation",
            value=f"{surah_info.revelation_type.value.title()}",
            inline=True,
        )

        log_perfect_tree_section(
            "Discord Embed Formatted",
            [
                ("surah", surah_info.name_transliteration),
                ("status", "📋 Embed created"),
            ],
            "📋",
        )
        return embed

    except Exception as e:
        log_error_with_traceback("Error formatting Surah embed", e)
        return None


# =============================================================================
# Example Usage and Testing
# =============================================================================

if __name__ == "__main__":
    # Test the mapper
    log_perfect_tree_section(
        "QuranBot Surah Mapper Test",
        [
            ("status", "🕌 Starting test suite"),
        ],
        "🕌",
    )
    print("=" * 50)

    # Check if database loaded successfully
    if not SURAH_DATABASE:
        log_error_with_traceback(
            "Failed to load Surah database!", "Cannot proceed with tests"
        )
        exit(1)

    # Test various functions
    print("\n1. Testing get_surah_info:")
    fatiha = get_surah_info(1)
    if fatiha:
        print(f"   Surah 1: {fatiha.name_transliteration} ({fatiha.name_arabic})")
    else:
        print("   ❌ Failed to get Surah 1")

    print("\n2. Testing get_surah_name:")
    print(f"   Surah 2: {get_surah_name(2)}")

    print("\n3. Testing get_surah_display:")
    print(f"   Display: {get_surah_display(3)}")

    print("\n4. Testing get_random_surah:")
    random_surah = get_random_surah()
    if random_surah:
        print(f"   Random: {random_surah.name_transliteration}")

    print("\n5. Testing validation:")
    print(f"   Valid (1): {validate_surah_number(1)}")
    print(f"   Invalid (115): {validate_surah_number(115)}")

    print("\n6. Testing statistics:")
    stats = get_quran_statistics()
    print(f"   Total Surahs: {stats.get('total_surahs', 0)}")
    print(f"   Total Verses: {stats.get('total_verses', 0)}")

    print("\n7. Testing formatting:")
    print(format_now_playing(get_surah_info(36), "Saad Al Ghamdi"))

    log_perfect_tree_section(
        "Test Suite Complete",
        [
            ("status", "✅ All tests completed"),
        ],
        "✅",
    )
