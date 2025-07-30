# =============================================================================
# QuranBot - Surah Mapper (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Enterprise-grade Surah (Quranic chapter) information management system with
# comprehensive metadata, search capabilities, and Discord integration.
# Originally designed for QuranBot but adaptable for any Islamic app.
#
# Key Features:
# - Complete Surah metadata
# - Smart search functionality
# - Rich Discord embeds
# - Data validation
# - Error handling
# - Perfect tree logging
#
# Technical Implementation:
# - JSON-based data storage
# - Type-safe dataclasses
# - Enum-based categorization
# - Comprehensive validation
# - Error recovery
#
# File Structure:
# /utils/
#   surahs.json - Complete Surah database
#
# Required Dependencies:
# - discord.py: Discord integration
# =============================================================================

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import random

import discord

# Import tree logging with fallback support
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
        # Minimal fallback logging functions for standalone use
        def log_error_with_traceback(msg, e):
            print(f"ERROR: {msg} - {e}")

        def log_perfect_tree_section(title, items, emoji=""):
            print(f"{emoji} {title}")
            for key, value in items:
                print(f"  {key}: {value}")

        def log_warning_with_context(msg, context=""):
            print(f"WARNING: {msg} - {context}")


# Import custom exceptions
from src.core.exceptions import ValidationError

# =============================================================================
# Surah Data Classes and Enums
# =============================================================================
# Core data structures for Surah information management.
# These classes provide type safety and data validation.
#
# RevelationType:
# - Categorizes Surahs by revelation location
# - Used for filtering and organization
#
# SurahInfo:
# - Complete Surah metadata container
# - Provides rich functionality
# - Ensures data consistency
# =============================================================================


class RevelationType(Enum):
    """
    Surah revelation location classifier.

    This enum provides type-safe categorization of Surahs based on their
    revelation location (Mecca or Medina).

    Values:
        MECCAN: Revealed in Mecca
        MEDINAN: Revealed in Medina
    """

    MECCAN = "Meccan"
    MEDINAN = "Medinan"


@dataclass
class SurahInfo:
    """
    Enterprise-grade Surah metadata container.

    This class provides a complete and validated representation of
    Quranic chapter (Surah) information with rich functionality.

    Attributes:
        number (int): Surah number (1-114)
        name_arabic (str): Original Arabic name
        name_english (str): English translation
        name_transliteration (str): Latin script
        emoji (str): Visual identifier
        verses (int): Total verse count
        revelation_type (RevelationType): Mecca/Medina
        meaning (str): Name translation
        description (str): Brief overview

    Implementation Notes:
    - Uses dataclass for clean representation
    - Provides dict-like access
    - Implements iteration
    - Validates data types
    - Ensures consistency

    Usage Example:
    ```python
    # Create Surah info
    surah = SurahInfo(
        number=1,
        name_arabic="الفاتحة",
        name_english="The Opening",
        name_transliteration="Al-Fatihah",
        emoji="📖",
        verses=7,
        revelation_type=RevelationType.MECCAN,
        meaning="The Opening",
        description="The first chapter of the Quran"
    )

    # Access attributes
    print(surah.name_english)      # Direct access
    print(surah["name_english"])   # Dict-style

    # Iterate over fields
    for field in surah:
        print(field)
    ```
    """

    number: int
    name_arabic: str
    name_english: str
    name_transliteration: str
    emoji: str
    verses: int
    revelation_type: RevelationType
    meaning: str
    description: str

    def __getitem__(self, key: str) -> str:
        """
        Enable dictionary-style access to attributes.

        Args:
            key: Attribute name to access

        Returns:
            str: Attribute value

        Raises:
            KeyError: If key doesn't exist
        """
        mapping = {
            "name": self.name_transliteration,
            "name_arabic": self.name_arabic,
            "name_english": self.name_english,
            "name_transliteration": self.name_transliteration,
            "emoji": self.emoji,
            "verses": self.verses,
            "revelation_type": self.revelation_type.value,
            "meaning": self.meaning,
            "description": self.description,
        }
        if key not in mapping:
            raise ValidationError(
                f"Key {key} not found",
                field_name="key",
                field_value=key,
                validation_rule="must be valid mapping key",
            )
        return mapping[key]

    def __iter__(self):
        """
        Enable iteration over attribute names.

        Yields:
            str: Attribute names in order
        """
        yield from [
            "name",
            "name_arabic",
            "name_english",
            "name_transliteration",
            "emoji",
            "verses",
            "revelation_type",
            "meaning",
            "description",
        ]

    def __eq__(self, other):
        """
        Enable equality comparison between Surahs.

        Args:
            other: Another SurahInfo to compare

        Returns:
            bool: True if all attributes match
        """
        if not isinstance(other, SurahInfo):
            return False
        return (
            self.number == other.number
            and self.name_arabic == other.name_arabic
            and self.name_english == other.name_english
            and self.name_transliteration == other.name_transliteration
            and self.emoji == other.emoji
            and self.verses == other.verses
            and self.revelation_type == other.revelation_type
            and self.meaning == other.meaning
            and self.description == other.description
        )


# =============================================================================
# JSON Data Loading
# =============================================================================
# Core functionality for loading and validating the Surah database.
# Provides comprehensive error handling and data validation.
#
# Key Features:
# - Automatic file discovery
# - JSON validation
# - Error recovery
# - Detailed logging
# - Data integrity checks
#
# File Structure:
# surahs.json:
# {
#   "1": {
#     "number": 1,
#     "name_arabic": "الفاتحة",
#     "name_english": "The Opening",
#     "name_transliteration": "Al-Fatihah",
#     "verses": 7,
#     "revelation_type": "Meccan",
#     "emoji": "📖",
#     "meaning": "The Opening",
#     "description": "..."
#   },
#   "2": { ... }
# }
# =============================================================================


def load_surah_database() -> dict[int, SurahInfo]:
    """
    Load and validate the complete Surah database from JSON.

    This function provides enterprise-grade loading of Surah data with
    comprehensive error handling, validation, and recovery mechanisms.

    Returns:
        Dict[int, SurahInfo]: Mapping of Surah numbers to their info

    Implementation Notes:
    - Validates JSON structure
    - Handles missing files
    - Recovers from corruption
    - Provides detailed logging
    - Ensures data integrity

    Error Handling:
    1. File Access:
       - Handles missing files
       - Reports path issues
       - Provides context

    2. Data Validation:
       - Checks completeness
       - Validates types
       - Ensures consistency

    3. Recovery:
       - Skips invalid entries
       - Continues processing
       - Reports issues

    Usage Example:
    ```python
    # Load database
    database = load_surah_database()

    # Access Surah info
    if 1 in database:
        surah = database[1]
        print(f"Loaded: {surah.name_english}")
    ```
    """
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

            with open(json_path, encoding="utf-8") as f:
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
            # Process JSON data with validation
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
                        emoji=surah_data.get("emoji", "📖"),  # Default emoji
                        meaning=surah_data.get(
                            "meaning", surah_data["name_english"]
                        ),  # Fallback to English name
                        description=surah_data.get("description", ""),  # Optional field
                    )
                except (KeyError, ValueError, TypeError) as e:
                    log_warning_with_context(
                        f"Error processing Surah {number_str}",
                        f"Skipping due to: {e!s}",
                    )
                    continue

            # Validate database completeness
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


def get_surah_info(surah_number: int) -> SurahInfo | None:
    """Get complete Surah information by number"""
    if not validate_surah_number(surah_number):
        return None

    try:
        surah_data = load_surah_database().get(surah_number)
        if not surah_data:
            return None

        return SurahInfo(
            number=surah_number,
            name_arabic=surah_data["name_arabic"],
            name_english=surah_data["name_english"],
            name_transliteration=(
                "Al-Fatihah"
                if surah_number == 1
                else surah_data["name_transliteration"]
            ),
            emoji=surah_data["emoji"],
            verses=surah_data["verses"],
            revelation_type=RevelationType(surah_data["revelation_type"]),
            meaning=surah_data["meaning"],
            description=surah_data["description"],
        )
    except Exception as e:
        log_error_with_traceback("Error getting Surah info", e)
        return None


def get_surah_name(surah_number: int) -> str:
    """Get Surah name in English transliteration"""
    surah = get_surah_info(surah_number)
    if not surah:
        return f"Surah {surah_number}"
    return surah.name_transliteration


def get_surah_display(surah_number: int) -> str:
    """Get formatted Surah display name"""
    surah = get_surah_info(surah_number)
    if not surah:
        return f"Surah {surah_number}"
    return f"{surah.name_transliteration} ({surah.name_arabic})"


def get_random_surah() -> SurahInfo | None:
    """Get a random Surah from the database"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback(
                "Surah database not loaded", "Cannot retrieve random Surah"
            )
            return None

        surah_number = random.randint(1, 114)
        return get_surah_info(surah_number)
    except Exception as e:
        log_error_with_traceback("Error getting random Surah", e)
        return None


def get_all_surahs() -> dict[int, SurahInfo]:
    """Get all Surahs from the database"""
    try:
        if not SURAH_DATABASE:
            log_error_with_traceback(
                "Surah database not loaded", "Cannot retrieve Surahs"
            )
            return {}

        return SURAH_DATABASE.copy()
    except Exception as e:
        log_error_with_traceback("Error getting all Surahs", e)
        return {}


def search_surahs(query: str) -> list[SurahInfo]:
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


def get_meccan_surahs() -> list[SurahInfo]:
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


def get_medinan_surahs() -> list[SurahInfo]:
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


def get_short_surahs(max_verses: int = 20) -> list[SurahInfo]:
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


def get_long_surahs(min_verses: int = 100) -> list[SurahInfo]:
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


def get_quran_statistics() -> dict[str, int]:
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


def format_now_playing(surah_info: SurahInfo | None, reciter: str = "Unknown") -> str:
    """Format a Discord message for currently playing Surah"""
    if not surah_info:
        return "❌ No Surah information available"

    # Log the formatting operation
    log_perfect_tree_section(
        "Now Playing Message Formatted",
        [
            ("surah", surah_info.name_transliteration),
            ("reciter", reciter),
            ("status", "🎵 Message formatted"),
        ],
        "🎵",
    )

    # Format the message with consistent naming
    return (
        f"🎵 **Now Playing** • 🕌 **{surah_info.name_transliteration}** "
        f"({surah_info.name_arabic}) • *{surah_info.verses} verses* • "
        f"**{reciter}**"
    )


def format_surah_embed(surah_info: SurahInfo | None) -> discord.Embed | None:
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
