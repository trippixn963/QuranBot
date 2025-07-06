# =============================================================================
# QuranBot - Surah Mapping Module
# =============================================================================
# Maps Surah numbers (1-114) to names, emojis, and metadata
# Provides beautiful display formatting for Discord and logging
# =============================================================================

import json
import os
import random
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import discord

    DISCORD_AVAILABLE = True
except ImportError:
    discord = None
    DISCORD_AVAILABLE = False

try:
    from .tree_log import (
        log_critical_error,
        log_error_with_traceback,
        log_tree,
        log_warning_with_context,
    )
except ImportError:
    # Fallback for direct execution
    import sys

    sys.path.append(os.path.dirname(__file__))
    from tree_log import (
        log_critical_error,
        log_error_with_traceback,
        log_tree,
        log_warning_with_context,
    )

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
    """Load Surah database from JSON file"""
    json_path = Path(__file__).parent / "surahs.json"

    log_tree("📖 Loading Surah database from JSON")

    try:
        if not json_path.exists():
            log_critical_error(
                "surahs.json file not found",
                f"Expected path: {json_path}",
                "surah_mapper",
            )
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        log_tree(f"📊 Loaded {len(data)} Surahs from JSON")

        database = {}
        for number_str, surah_data in data.items():
            try:
                number = int(number_str)

                # Validate required fields
                required_fields = [
                    "number",
                    "name_arabic",
                    "name_english",
                    "name_transliteration",
                    "emoji",
                    "verses",
                    "revelation_type",
                    "meaning",
                    "description",
                ]

                missing_fields = [
                    field for field in required_fields if field not in surah_data
                ]
                if missing_fields:
                    log_warning_with_context(
                        f"Surah {number} missing fields: {missing_fields}",
                        f"Skipping Surah {number}",
                        "surah_mapper",
                    )
                    continue

                database[number] = SurahInfo(
                    number=surah_data["number"],
                    name_arabic=surah_data["name_arabic"],
                    name_english=surah_data["name_english"],
                    name_transliteration=surah_data["name_transliteration"],
                    emoji=surah_data["emoji"],
                    verses=surah_data["verses"],
                    revelation_type=RevelationType(surah_data["revelation_type"]),
                    meaning=surah_data["meaning"],
                    description=surah_data["description"],
                )

            except (ValueError, KeyError, TypeError) as e:
                log_error_with_traceback(f"Error processing Surah {number_str}", e)
                continue

        if len(database) == 114:
            log_tree(f"✅ Successfully loaded all 114 Surahs")
        else:
            log_warning_with_context(
                f"Only loaded {len(database)}/114 Surahs",
                "Some Surahs may be missing or invalid",
                "surah_mapper",
            )

        return database

    except json.JSONDecodeError as e:
        log_error_with_traceback(
            "Invalid JSON format in surahs.json",
            f"JSON decode error: {str(e)}",
            "surah_mapper",
        )
        return {}

    except FileNotFoundError as e:
        log_critical_error("Surah database file not found", f"File path: {json_path}")
        return {}

    except PermissionError as e:
        log_error_with_traceback("Permission denied reading surahs.json", e)
        return {}

    except Exception as e:
        log_critical_error(
            "Unexpected error loading Surah database",
            f"Error: {str(e)}\nTraceback: {traceback.format_exc()}",
            "surah_mapper",
        )
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
            log_critical_error(
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
    """Get the transliterated name of a Surah"""
    try:
        surah = get_surah_info(surah_number)
        if surah:
            return surah.name_transliteration
        else:
            log_tree(f"⚠️ Surah {surah_number} not found, using fallback")
            return f"Surah {surah_number}"
    except Exception as e:
        log_error_with_traceback(f"Error getting Surah name for {surah_number}", e)
        return f"Surah {surah_number}"


def get_surah_display(surah_number: int, format_type: str = "full") -> str:
    """Get formatted display string for a Surah"""
    try:
        surah = get_surah_info(surah_number)
        if not surah:
            log_tree(f"⚠️ Surah {surah_number} not found, using fallback")
            return f"Surah {surah_number}"

        if format_type == "short":
            return f"{surah.emoji} {surah.name_transliteration}"
        elif format_type == "number":
            return f"{surah_number:03d}. {surah.emoji} {surah.name_transliteration}"
        elif format_type == "detailed":
            return (
                f"{surah_number:03d}. {surah.emoji} {surah.name_transliteration} "
                f"({surah.name_arabic}) - {surah.verses} verses"
            )
        else:  # full
            return (
                f"{surah_number:03d}. {surah.emoji} {surah.name_transliteration} "
                f"({surah.name_arabic})"
            )

    except Exception as e:
        log_error_with_traceback(
            f"Error formatting Surah display for {surah_number}", e
        )
        return f"Surah {surah_number}"


def get_random_surah() -> SurahInfo:
    """Get a random Surah"""
    try:
        surah_number = random.randint(1, 114)
        surah = get_surah_info(surah_number)
        if surah:
            log_tree(f"🎲 Selected random Surah: {surah.name_transliteration}")
            return surah
        else:
            # Fallback to Al-Fatiha if random selection fails
            return get_surah_info(1)
    except Exception as e:
        log_error_with_traceback("Error getting random Surah", e)
        return get_surah_info(1)


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
            log_critical_error("Cannot get Meccan Surahs", "Database not loaded")
            return []

        meccan = [
            s
            for s in SURAH_DATABASE.values()
            if s.revelation_type == RevelationType.MECCAN
        ]
        log_tree(f"🕌 Found {len(meccan)} Meccan Surahs")
        return meccan

    except Exception as e:
        log_error_with_traceback("Error getting Meccan Surahs", e)
        return []


def get_medinan_surahs() -> List[SurahInfo]:
    """Get all Medinan Surahs"""
    try:
        if not SURAH_DATABASE:
            log_critical_error("Cannot get Medinan Surahs", "Database not loaded")
            return []

        medinan = [
            s
            for s in SURAH_DATABASE.values()
            if s.revelation_type == RevelationType.MEDINAN
        ]
        log_tree(f"🏛️ Found {len(medinan)} Medinan Surahs")
        return medinan

    except Exception as e:
        log_error_with_traceback("Error getting Medinan Surahs", e)
        return []


def get_short_surahs(max_verses: int = 20) -> List[SurahInfo]:
    """Get Surahs with fewer than specified verses"""
    try:
        if not SURAH_DATABASE:
            log_critical_error("Cannot get short Surahs", "Database not loaded")
            return []

        short = [s for s in SURAH_DATABASE.values() if s.verses <= max_verses]
        log_tree(f"📜 Found {len(short)} Surahs with ≤{max_verses} verses")
        return short

    except Exception as e:
        log_error_with_traceback(
            f"Error getting short Surahs (max_verses={max_verses})", e
        )
        return []


def get_long_surahs(min_verses: int = 100) -> List[SurahInfo]:
    """Get Surahs with more than specified verses"""
    try:
        if not SURAH_DATABASE:
            log_critical_error("Cannot get long Surahs", "Database not loaded")
            return []

        long = [s for s in SURAH_DATABASE.values() if s.verses >= min_verses]
        log_tree(f"📚 Found {len(long)} Surahs with ≥{min_verses} verses")
        return long

    except Exception as e:
        log_error_with_traceback(
            f"Error getting long Surahs (min_verses={min_verses})", e
        )
        return []


def validate_surah_number(surah_number: int) -> bool:
    """Validate if a Surah number is valid (1-114)"""
    try:
        is_valid = 1 <= surah_number <= 114
        if not is_valid:
            log_tree(f"❌ Invalid Surah number: {surah_number} (valid: 1-114)")
        return is_valid

    except Exception as e:
        log_error_with_traceback(f"Error validating Surah number {surah_number}", e)
        return False


def get_surah_stats() -> Dict[str, int]:
    """Get statistics about the Quran"""
    try:
        if not SURAH_DATABASE:
            log_critical_error("Cannot get Surah statistics", "Database not loaded")
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

        log_tree(f"📊 Generated Quran statistics: {len(stats)} metrics")
        return stats

    except Exception as e:
        log_error_with_traceback("Error generating Surah statistics", e)
        return {}


# =============================================================================
# Discord Formatting Functions
# =============================================================================


def format_now_playing(surah_info: SurahInfo, reciter: str = "Unknown") -> str:
    """Format a 'now playing' message for Discord"""
    try:
        if not surah_info:
            log_tree("⚠️ No Surah info provided for now playing message")
            return "🎵 **Now Playing** • *Unknown*"

        # Create beautiful now playing message with transliterated name
        message = (
            f"🎵 **Now Playing**\n\n"
            f"{surah_info.emoji} **{surah_info.name_transliteration}** ({surah_info.name_arabic})\n"
            f"📖 *Surah {surah_info.number:03d} • {surah_info.verses} verses*\n"
            f"🎤 *Reciter: {reciter}*"
        )

        log_tree(f"🎵 Formatted Discord message for {surah_info.name_transliteration}")
        return message

    except Exception as e:
        log_error_with_traceback("Error formatting now playing message", e)
        return "🎵 **Now Playing** • *Error loading Surah info*"


def format_surah_embed(
    surah_info: SurahInfo, reciter: str = "Unknown", color: int = 0x00D4AA
):
    """Format a Discord embed for Surah information"""
    try:
        if not DISCORD_AVAILABLE or not discord:
            log_tree("⚠️ Discord not available for embed formatting")
            return None

        if not surah_info:
            log_tree("⚠️ No Surah info provided for embed")
            return discord.Embed(
                title="❌ Error",
                description="*Surah information not available*",
                color=0xFF0000,
            )

        # Create beautiful embed with transliterated name
        embed = discord.Embed(
            title=f"{surah_info.emoji} {surah_info.name_transliteration} ({surah_info.name_arabic})",
            color=color,
        )

        embed.add_field(
            name="📖 Surah Number", value=f"{surah_info.number:03d}", inline=True
        )
        embed.add_field(name="📜 Verses", value=f"{surah_info.verses}", inline=True)
        embed.add_field(
            name="🏛️ Type", value=f"{surah_info.revelation_type}", inline=True
        )
        embed.add_field(name="🎤 Reciter", value=f"{reciter}", inline=False)

        if surah_info.description:
            embed.add_field(
                name="📝 Description", value=surah_info.description, inline=False
            )

        log_tree(f"📋 Formatted Discord embed for {surah_info.name_transliteration}")
        return embed

    except Exception as e:
        log_error_with_traceback("Error formatting Surah embed", e)
        if discord:
            return discord.Embed(
                title="❌ Error",
                description="*Error loading Surah information*",
                color=0xFF0000,
            )
        return None


# =============================================================================
# Example Usage and Testing
# =============================================================================

if __name__ == "__main__":
    # Test the mapper
    log_tree(f"🕌 QuranBot Surah Mapper Test")
    print("=" * 50)

    # Check if database loaded successfully
    if not SURAH_DATABASE:
        log_critical_error(
            "Failed to load Surah database!", "Cannot proceed with tests"
        )
        exit(1)

    # Test specific Surahs
    test_surahs = [1, 2, 36, 55, 112, 114]

    for num in test_surahs:
        info = get_surah_info(num)
        if info:
            print(f"\n{get_surah_display(num, 'detailed')}")
            print(f"   Meaning: {info.meaning}")
            print(f"   Type: {info.revelation_type.value}")

    # Test search
    print(f"\n\nSearch Results for 'light':")
    results = search_surahs("light")
    for surah in results:
        print(f"  {get_surah_display(surah.number)}")

    # Test stats
    stats = get_surah_stats()
    print(f"\n\nQuran Statistics:")
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    # Test formatting
    print(f"\n\nNow Playing Format:")
    print(format_now_playing(get_surah_info(36), "Saad Al Ghamdi"))

    log_tree(f"✅ All tests completed successfully")
