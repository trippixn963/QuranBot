# =============================================================================
# QuranBot - Centralized Timezone Configuration
# =============================================================================
# Single source of truth for timezone configuration across the entire project.
# All modules should import from here to ensure consistency.
# =============================================================================

from datetime import datetime
from zoneinfo import ZoneInfo

# =============================================================================
# Timezone Configuration
# =============================================================================

# Primary timezone for the entire application
APP_TIMEZONE = ZoneInfo("America/New_York")

# Convenience aliases for backward compatibility
EST = APP_TIMEZONE
TIMEZONE = "America/New_York"  # String version for legacy code

# =============================================================================
# Utility Functions
# =============================================================================


def now() -> datetime:
    """Get current datetime in application timezone."""
    return datetime.now(APP_TIMEZONE)


def now_iso() -> str:
    """Get current datetime as ISO string in application timezone."""
    return now().isoformat()


def format_timestamp(dt: datetime = None) -> str:
    """Format datetime for logging display."""
    if dt is None:
        dt = now()
    return dt.strftime("[%m/%d %I:%M:%S %p EST]")


def to_app_timezone(dt: datetime) -> datetime:
    """Convert any datetime to application timezone."""
    return dt.astimezone(APP_TIMEZONE)
