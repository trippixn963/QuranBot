# =============================================================================
# QuranBot - User Cache Utility
# =============================================================================
# Utility for caching Discord user information for analytics and statistics
# =============================================================================

from datetime import UTC, datetime
import json
from pathlib import Path

from src.core.exceptions import StateError, ValidationError

# Data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_CACHE_FILE = DATA_DIR / "user_cache.json"


def update_user_cache(user_id: int, display_name: str, avatar_url: str | None = None):
    """
    Update the user cache with Discord user information.

    Args:
        user_id: Discord user ID
        display_name: User's display name
        avatar_url: User's avatar URL (optional)

    Raises:
        ValidationError: If invalid user data is provided
        StateError: If cache file operations fail
    """
    try:
        # Validate inputs
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError(
                "Invalid user ID provided",
                field_name="user_id",
                field_value=user_id,
                validation_rule="positive_integer",
            )

        if not display_name or not isinstance(display_name, str):
            raise ValidationError(
                "Invalid display name provided",
                field_name="display_name",
                field_value=display_name,
                validation_rule="non_empty_string",
            )

        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)

        # Load existing cache
        cache_data = {
            "users": {},
            "last_updated": datetime.now(UTC).isoformat(),
            "total_cached_users": 0,
        }

        if USER_CACHE_FILE.exists():
            try:
                with open(USER_CACHE_FILE, encoding="utf-8") as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Log corruption but continue with default data
                raise StateError(
                    "User cache file corrupted, reinitializing",
                    state_type="user_cache",
                    state_file=str(USER_CACHE_FILE),
                    operation="load",
                    original_error=e,
                )

        # Update user info
        user_id_str = str(user_id)
        cache_data["users"][user_id_str] = {
            "display_name": display_name,
            "avatar_url": avatar_url,
            "last_seen": datetime.now(UTC).isoformat(),
        }

        # Update metadata
        cache_data["last_updated"] = datetime.now(UTC).isoformat()
        cache_data["total_cached_users"] = len(cache_data["users"])

        # Save to file
        try:
            with open(USER_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except (OSError, PermissionError) as e:
            raise StateError(
                "Failed to save user cache",
                state_type="user_cache",
                state_file=str(USER_CACHE_FILE),
                operation="save",
                original_error=e,
            )

    except (ValidationError, StateError):
        # Re-raise QuranBot exceptions
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise StateError(
            "Unexpected error updating user cache",
            state_type="user_cache",
            operation="update",
            context={"user_id": user_id, "display_name": display_name},
            original_error=e,
        )


def get_cached_user_info(user_id: int) -> dict[str, str] | None:
    """
    Get cached user information by user ID.

    Args:
        user_id: Discord user ID

    Returns:
        User information dict or None if not found

    Raises:
        ValidationError: If invalid user ID is provided
        StateError: If cache file operations fail
    """
    try:
        # Validate input
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValidationError(
                "Invalid user ID provided",
                field_name="user_id",
                field_value=user_id,
                validation_rule="positive_integer",
            )

        if not USER_CACHE_FILE.exists():
            return None

        try:
            with open(USER_CACHE_FILE, encoding="utf-8") as f:
                cache_data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise StateError(
                "Failed to read user cache file",
                state_type="user_cache",
                state_file=str(USER_CACHE_FILE),
                operation="read",
                original_error=e,
            )

        return cache_data.get("users", {}).get(str(user_id))

    except (ValidationError, StateError):
        # Re-raise QuranBot exceptions
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise StateError(
            "Unexpected error reading user cache",
            state_type="user_cache",
            operation="read",
            context={"user_id": user_id},
            original_error=e,
        )


def cache_user_from_interaction(interaction):
    """
    Cache user information from a Discord interaction.

    Args:
        interaction: Discord interaction object

    Raises:
        ValidationError: If interaction data is invalid
        StateError: If cache operations fail
    """
    try:
        if not interaction or not hasattr(interaction, "user"):
            raise ValidationError(
                "Invalid interaction object provided",
                field_name="interaction",
                field_value=str(type(interaction)),
                validation_rule="valid_discord_interaction",
            )

        user = interaction.user
        if not user:
            raise ValidationError(
                "No user found in interaction",
                field_name="interaction.user",
                field_value=None,
                validation_rule="user_required",
            )

        avatar_url = None
        if user.avatar:
            avatar_url = user.avatar.url

        update_user_cache(
            user_id=user.id,
            display_name=user.display_name,
            avatar_url=avatar_url,
        )

    except (ValidationError, StateError):
        # Re-raise QuranBot exceptions
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise StateError(
            "Unexpected error caching user from interaction",
            state_type="user_cache",
            operation="cache_from_interaction",
            context={
                "user_id": (
                    getattr(interaction.user, "id", None) if interaction.user else None
                )
            },
            original_error=e,
        )
