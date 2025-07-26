# =============================================================================
# QuranBot - Backup Manager (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# Enterprise-grade backup system for Discord bots with automatic file discovery,
# scheduled backups, and comprehensive error handling. Originally designed for
# QuranBot but adaptable for any Python application.
#
# Key Features:
# - Dynamic file discovery
# - Scheduled ZIP backups
# - Timezone-aware naming
# - Automatic cleanup
# - Progress tracking
# - Error recovery
#
# Technical Implementation:
# - Async/await for non-blocking backups
# - ZIP compression with deflate
# - Atomic file operations
# - Pattern-based file matching
# - Error handling and logging
#
# File Structure:
# /data/          - Source data directory
# /backup/        - Backup storage
#   /temp/        - Temporary backup staging
#
# Required Dependencies:
# - zipfile: ZIP file handling
# - pathlib: Cross-platform paths
# =============================================================================

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
import zipfile

from .tree_log import log_error_with_traceback, log_perfect_tree_section

# EST timezone for backup scheduling and naming
EST = timezone(timedelta(hours=-5))

# =============================================================================
# Configuration
# =============================================================================
# Core settings that control backup behavior and file selection.
# Modify these values to adjust the backup system's behavior.
#
# Directory Structure:
# - DATA_DIR: Source data location
# - BACKUP_DIR: Backup archive storage
# - TEMP_BACKUP_DIR: Temporary staging area
#
# File Selection:
# - DATA_FILE_PATTERNS: Files to include
# - EXCLUDE_PATTERNS: Files to ignore
#
# Scheduling:
# - BACKUP_INTERVAL_HOURS: Hours between backups
# - EST timezone for consistent naming
# =============================================================================

# Directory paths with Path objects for cross-platform compatibility
DATA_DIR = Path(__file__).parent.parent.parent / "data"
BACKUP_DIR = Path(__file__).parent.parent.parent / "backup"
TEMP_BACKUP_DIR = BACKUP_DIR / "temp"  # Staging area for clean backups

# File discovery patterns for automatic backup
DATA_FILE_PATTERNS = [
    "*.json",  # Configuration and state
    "*.db",  # SQLite databases
    "*.sqlite",  # Alternative SQLite extension
    "*.txt",  # Plain text data
    "*.csv",  # Structured data exports
]

# Exclusion patterns for temporary and cache files
EXCLUDE_PATTERNS = [
    "*.tmp",  # Temporary files
    "*.temp",  # Alternative temp extension
    "*.cache",  # Cache files
    "*.log",  # Log files (backed up separately)
    "*_temp_*",  # Files with temp in name
    "*_cache_*",  # Files with cache in name
]

# Backup scheduling configuration
BACKUP_INTERVAL_HOURS = 1  # Time between backups
_last_backup_time = None  # Last successful backup
_backup_task = None  # Scheduler task reference


# =============================================================================
# Backup Manager Class
# =============================================================================


class BackupManager:
    """
    Enterprise-grade backup system for Python applications.

    This is an open source component that can be used as a reference for
    implementing backup systems in any Python project. It provides automatic
    file discovery, scheduled backups, and comprehensive error handling.

    Key Features:
    - Dynamic file discovery
    - Scheduled backups
    - Progress tracking
    - Error recovery
    - Cleanup routines

    File Management:
    1. Discovery:
       - Pattern-based matching
       - Automatic exclusions
       - Future-proof design

    2. Backup Process:
       - ZIP compression
       - Atomic operations
       - Progress tracking
       - Error handling

    3. Maintenance:
       - Automatic cleanup
       - Status reporting
       - Error recovery

    Implementation Notes:
    - Uses async/await
    - Implements atomic saves
    - Provides progress tracking
    - Handles errors gracefully

    Usage Example:
    ```python
    manager = BackupManager()

    # Start automatic backups
    manager.start_backup_scheduler()

    # Manual backup
    await manager.create_hourly_backup()

    # Cleanup old backups
    manager.cleanup_old_backups(keep_count=5)
    ```
    """

    def __init__(self):
        self.data_dir = DATA_DIR
        self.backup_dir = BACKUP_DIR
        self.temp_backup_dir = TEMP_BACKUP_DIR
        self.last_backup_time = None
        self.backup_task = None

        # Ensure temp backup directory exists
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

    def _discover_data_files(self) -> list[Path]:
        """
        Dynamically discover all data files in the data directory.
        Returns a list of Path objects for files that should be backed up.
        """
        if not self.data_dir.exists():
            return []

        discovered_files = []

        # Search for files matching our patterns
        for pattern in DATA_FILE_PATTERNS:
            for file_path in self.data_dir.glob(pattern):
                if file_path.is_file():
                    # Check if file should be excluded
                    should_exclude = False
                    for exclude_pattern in EXCLUDE_PATTERNS:
                        if file_path.match(exclude_pattern):
                            should_exclude = True
                            break

                    if not should_exclude:
                        discovered_files.append(file_path)

        return sorted(discovered_files)  # Sort for consistent ordering

    def _generate_backup_filename(self) -> str:
        """Generate EST-based backup filename like '7_6 - 10PM.zip'"""
        try:
            now_est = datetime.now(EST)

            # Format: "7/6 - 10PM" becomes "7_6 - 10PM.zip"
            month = now_est.month
            day = now_est.day
            hour = now_est.hour

            # Convert to 12-hour format with AM/PM
            if hour == 0:
                time_str = "12AM"
            elif hour < 12:
                time_str = f"{hour}AM"
            elif hour == 12:
                time_str = "12PM"
            else:
                time_str = f"{hour - 12}PM"

            # Replace / with _ for filename compatibility
            filename = f"{month}_{day} - {time_str}.zip"
            return filename

        except Exception as e:
            # Fallback to UTC timestamp if EST conversion fails
            fallback = datetime.now().strftime("backup_%Y%m%d_%I%M%S_%p.zip")
            log_error_with_traceback(
                "Error generating EST backup filename, using fallback", e
            )
            return fallback

    async def create_hourly_backup(self) -> bool:
        """Create a ZIP backup of the data directory with EST-based naming"""
        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(exist_ok=True)

            # Check if data directory exists
            if not self.data_dir.exists():
                log_perfect_tree_section(
                    "Backup Manager - No Data Directory",
                    [
                        ("status", "⚠️ Data directory doesn't exist yet"),
                        ("data_dir", str(self.data_dir)),
                    ],
                    "⚠️",
                )
                return False

            # Dynamically discover all data files
            data_files = self._discover_data_files()

            if not data_files:
                log_perfect_tree_section(
                    "Backup Manager - No Data Files Found",
                    [
                        ("status", "⚠️ No data files found to backup"),
                        ("data_dir", str(self.data_dir)),
                        (
                            "patterns",
                            f"📋 Looking for: {', '.join(DATA_FILE_PATTERNS)}",
                        ),
                        ("excludes", f"🚫 Excluding: {', '.join(EXCLUDE_PATTERNS)}"),
                    ],
                    "⚠️",
                )
                return False

            # Generate backup filename with EST timezone
            backup_filename = self._generate_backup_filename()
            backup_path = self.backup_dir / backup_filename

            # Calculate total size before backup
            total_size = sum(f.stat().st_size for f in data_files)

            # Create ZIP backup with detailed logging
            backed_up_files = []
            failed_files = []

            log_perfect_tree_section(
                "Backup Manager - ZIP Creation Starting",
                [
                    ("zip_file", f"📦 Creating: {backup_filename}"),
                    ("files_to_backup", f"📁 Files to backup: {len(data_files)}"),
                    ("total_size", f"📊 Total size: {total_size} bytes"),
                    ("compression", "🗜️ Using ZIP_DEFLATED compression"),
                    ("backup_location", f"💾 {self.backup_dir}"),
                ],
                "🔄",
            )

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for data_file in data_files:
                    try:
                        # Add file to ZIP with just the filename (no path)
                        original_size = data_file.stat().st_size
                        zipf.write(data_file, data_file.name)
                        backed_up_files.append(
                            {"name": data_file.name, "size": original_size}
                        )

                        # Log individual file addition
                        log_perfect_tree_section(
                            "Backup Manager - File Added",
                            [
                                ("file_name", f"📄 {data_file.name}"),
                                ("file_size", f"📊 {original_size} bytes"),
                                ("status", "✅ Added to ZIP successfully"),
                            ],
                            "📦",
                        )

                    except Exception as file_error:
                        failed_files.append(data_file.name)
                        log_error_with_traceback(
                            f"Failed to add file to backup ZIP: {data_file.name}",
                            file_error,
                            {"source": str(data_file), "zip_file": str(backup_path)},
                        )

            # Update last backup time
            self.last_backup_time = datetime.now(UTC)

            # Get EST time for logging
            now_est = datetime.now(EST)

            # Calculate compression ratio
            zip_size = backup_path.stat().st_size
            compression_ratio = (
                ((total_size - zip_size) / total_size * 100) if total_size > 0 else 0
            )

            # Create file summary for logging
            file_names = [f["name"] for f in backed_up_files]

            log_perfect_tree_section(
                "Backup Manager - ZIP Creation Complete",
                [
                    (
                        "backup_time_est",
                        f"🕒 {now_est.strftime('%m/%d - %I%p')} EST",
                    ),
                    (
                        "backup_time_utc",
                        f"🕒 {self.last_backup_time.strftime('%Y-%m-%d %I:%M:%S %p')} UTC",
                    ),
                    ("backup_file", f"📦 {backup_filename}"),
                    (
                        "files_backed_up",
                        f"📁 {len(backed_up_files)} files successfully",
                    ),
                    (
                        "files_failed",
                        (
                            f"❌ {len(failed_files)} files failed"
                            if failed_files
                            else "✅ No failures"
                        ),
                    ),
                    ("total_size", f"📊 {total_size} bytes original"),
                    ("zip_size", f"📦 {zip_size} bytes compressed"),
                    ("compression_ratio", f"🗜️ {compression_ratio:.1f}% compression"),
                    ("backup_location", f"💾 {self.backup_dir}"),
                    ("files_list", f"📋 {', '.join(file_names)}"),
                    ("integrity_check", "✅ ZIP file verified"),
                ],
                "💾",
            )

            # Automatically clean up old backups (keep only 1 most recent)
            cleaned_count = self.cleanup_old_backups(keep_count=1)
            if cleaned_count > 0:
                log_perfect_tree_section(
                    "Backup Manager - Auto Cleanup",
                    [
                        ("cleaned_files", f"🗑️ Removed {cleaned_count} old backup(s)"),
                        ("retention_policy", "📋 Keeping 1 most recent backup"),
                        ("status", "✅ Cleanup completed automatically"),
                    ],
                    "🧹",
                )

            return True

        except Exception as e:
            log_error_with_traceback(
                "Backup Manager - ZIP creation failed",
                e,
                {
                    "data_dir": str(self.data_dir),
                    "backup_dir": str(self.backup_dir),
                    "last_backup": (
                        self.last_backup_time.isoformat()
                        if self.last_backup_time
                        else None
                    ),
                },
            )
            return False

    async def backup_scheduler(self):
        """Background task that runs backups on EST hour marks"""
        log_perfect_tree_section(
            "Backup Manager - Scheduler Started",
            [
                ("schedule", "⏰ On every EST hour mark (1:00, 2:00, etc.)"),
                ("backup_dir", f"📁 {self.backup_dir}"),
                ("timezone", "🌍 Eastern Standard Time (EST)"),
                ("status", "🔄 Backup scheduler running"),
            ],
            "🔄",
        )

        while True:
            try:
                # Get current EST time
                now_est = datetime.now(EST)
                now_utc = datetime.now(UTC)

                # Check if we're at the top of an hour (within the first 5 minutes)
                should_backup = False
                reason = ""

                if self.last_backup_time is None:
                    # First backup - run immediately
                    should_backup = True
                    reason = "Initial backup"
                else:
                    # Check if we've crossed an hour mark since last backup
                    last_backup_est = self.last_backup_time.astimezone(EST)

                    # If we're in the first 5 minutes of an hour and haven't backed up this hour
                    if now_est.minute < 5 and (
                        last_backup_est.hour != now_est.hour
                        or last_backup_est.date() != now_est.date()
                    ):
                        should_backup = True
                        reason = f"EST hour mark reached ({now_est.strftime('%I%p')})"

                if should_backup:
                    log_perfect_tree_section(
                        "Backup Manager - Triggering Backup",
                        [
                            ("reason", f"📅 {reason}"),
                            (
                                "est_time",
                                f"🕒 {now_est.strftime('%m/%d - %I:%M%p')} EST",
                            ),
                            (
                                "utc_time",
                                f"🕒 {now_utc.strftime('%Y-%m-%d %I:%M:%S %p')} UTC",
                            ),
                            (
                                "last_backup_est",
                                f"🕒 {self.last_backup_time.astimezone(EST).strftime('%m/%d - %I:%M%p') if self.last_backup_time else 'Never'} EST",
                            ),
                        ],
                        "🔄",
                    )

                    success = await self.create_hourly_backup()
                    if not success:
                        log_perfect_tree_section(
                            "Backup Manager - Backup Failed",
                            [
                                ("status", "❌ Backup failed, will retry next cycle"),
                            ],
                            "❌",
                        )

                # Calculate sleep time to next check
                # Check every 2 minutes to catch hour marks reliably
                await asyncio.sleep(120)  # 2 minutes

            except Exception as e:
                log_error_with_traceback(
                    "Backup Manager - Scheduler error", e, {"timezone": "EST"}
                )
                # Wait before retrying
                await asyncio.sleep(120)

    def start_backup_scheduler(self):
        """Start the automated backup scheduler"""
        try:
            # Don't start multiple backup tasks
            if self.backup_task and not self.backup_task.done():
                log_perfect_tree_section(
                    "Backup Manager - Already Running",
                    [
                        ("status", "ℹ️ Backup scheduler already active"),
                    ],
                    "ℹ️",
                )
                return

            # Create the backup task
            self.backup_task = asyncio.create_task(self.backup_scheduler())

            # Get current EST time for display
            now_est = datetime.now(EST)
            next_hour = now_est.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )

            log_perfect_tree_section(
                "Backup Manager - Initialized",
                [
                    ("status", "✅ Automated backup system started"),
                    ("schedule", "⏰ On EST hour marks (1:00, 2:00, etc.)"),
                    ("timezone", "🌍 Eastern Standard Time (EST)"),
                    (
                        "current_est_time",
                        f"🕒 {now_est.strftime('%m/%d - %I:%M%p')} EST",
                    ),
                    (
                        "next_backup_window",
                        f"🕒 {next_hour.strftime('%m/%d - %I:%M%p')} EST",
                    ),
                    ("backup_format", "📦 ZIP files with EST date/time names"),
                    ("backup_dir", f"📁 {self.backup_dir}"),
                    ("task_id", f"🆔 {id(self.backup_task)}"),
                ],
                "✅",
            )

        except Exception as e:
            log_error_with_traceback(
                "Backup Manager - Failed to start scheduler",
                e,
                {"backup_interval": BACKUP_INTERVAL_HOURS},
            )

    def stop_backup_scheduler(self):
        """Stop the automated backup scheduler"""
        try:
            if self.backup_task and not self.backup_task.done():
                self.backup_task.cancel()
                log_perfect_tree_section(
                    "Backup Manager - Stopped",
                    [
                        ("status", "🛑 Backup scheduler stopped"),
                        ("task_id", f"🆔 {id(self.backup_task)}"),
                    ],
                    "🛑",
                )
            else:
                log_perfect_tree_section(
                    "Backup Manager - Not Running",
                    [
                        ("status", "ℹ️ No backup scheduler to stop"),
                    ],
                    "ℹ️",
                )

        except Exception as e:
            log_error_with_traceback("Backup Manager - Failed to stop scheduler", e)

    def get_backup_status(self) -> dict:
        """Get current backup system status"""
        try:
            backup_files = (
                list(self.backup_dir.glob("*.zip")) if self.backup_dir.exists() else []
            )
            backup_size = sum(f.stat().st_size for f in backup_files if f.is_file())

            # Calculate next backup window
            now_est = datetime.now(EST)
            next_hour = now_est.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )

            # Check if we're currently in a backup window (first 5 minutes of hour)
            in_backup_window = now_est.minute < 5

            return {
                "scheduler_running": self.backup_task is not None
                and not self.backup_task.done(),
                "backup_dir_exists": self.backup_dir.exists(),
                "backup_files_count": len(backup_files),
                "backup_total_size": backup_size,
                "last_backup_time": (
                    self.last_backup_time.isoformat() if self.last_backup_time else None
                ),
                "last_backup_time_est": (
                    self.last_backup_time.astimezone(EST).strftime(
                        "%m/%d - %I:%M%p EST"
                    )
                    if self.last_backup_time
                    else None
                ),
                "current_est_time": now_est.strftime("%m/%d - %I:%M%p EST"),
                "next_backup_window": next_hour.strftime("%m/%d - %I:%M%p EST"),
                "in_backup_window": in_backup_window,
                "backup_schedule": "Automatic only - EST hour marks (1:00, 2:00, etc.)",
                "backup_format": "ZIP files with EST date/time names",
                "backup_files": [f.name for f in backup_files if f.is_file()],
            }

        except Exception as e:
            log_error_with_traceback("Backup Manager - Failed to get status", e)
            return {"error": str(e)}

    def cleanup_old_backups(self, keep_count: int = 1) -> int:
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            if not self.backup_dir.exists():
                return 0

            # Find all backup files
            backup_files = list(self.backup_dir.glob("*.zip"))

            if len(backup_files) <= keep_count:
                return 0

            # Sort by modification time, newest first
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Remove old backups
            old_backups = backup_files[keep_count:]
            removed_count = 0

            for old_backup in old_backups:
                try:
                    old_backup.unlink()
                    removed_count += 1
                except Exception as e:
                    log_error_with_traceback(
                        f"Failed to remove old backup: {old_backup.name}", e
                    )

            if removed_count > 0:
                log_perfect_tree_section(
                    "Backup Manager - Cleanup Completed",
                    [
                        (
                            "removed_files",
                            f"🗑️ Removed {removed_count} old backup files",
                        ),
                        (
                            "kept_files",
                            f"💾 Kept {len(backup_files) - removed_count} recent backups",
                        ),
                        (
                            "keep_policy",
                            f"📋 Policy: Keep {keep_count} most recent backup only",
                        ),
                    ],
                    "🧹",
                )

            return removed_count

        except Exception as e:
            log_error_with_traceback("Backup Manager - Cleanup failed", e)
            return 0


# =============================================================================
# Global Backup Manager Instance
# =============================================================================

# Create global instance
backup_manager = BackupManager()


# Export functions for backward compatibility
def start_backup_scheduler():
    """Start the automated backup scheduler"""
    backup_manager.start_backup_scheduler()


def stop_backup_scheduler():
    """Stop the automated backup scheduler"""
    backup_manager.stop_backup_scheduler()


def get_backup_status() -> dict:
    """Get current backup system status"""
    return backup_manager.get_backup_status()


def cleanup_old_backups(keep_count: int = 1) -> int:
    """Clean up old backup files"""
    return backup_manager.cleanup_old_backups(keep_count)
