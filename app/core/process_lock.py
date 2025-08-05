# =============================================================================
# QuranBot - Process Lock Manager
# =============================================================================
# Singleton pattern implementation with file-based process locking to ensure
# only one bot instance can run at a time. Includes automatic cleanup and
# process termination for existing instances.
# =============================================================================

import atexit
from datetime import datetime
import fcntl
import os
from pathlib import Path
import time
from typing import Any

import psutil

from ..config.timezone import APP_TIMEZONE
from .logger import TreeLogger


class ProcessLockManager:
    """
    Manages process locking to ensure only one bot instance runs at a time.

    Features:
    - File-based locking with fcntl for Unix systems
    - Automatic detection and termination of existing instances
    - Process information tracking and validation
    - Graceful cleanup on shutdown
    - Comprehensive logging of all operations
    """

    def __init__(self, lock_file_path: str | None = None):
        """
        Initialize process lock manager.

        Args:
            lock_file_path: Custom path for lock file (defaults to data/runtime/bot.lock)
        """
        # Default lock file path
        if lock_file_path is None:
            project_root = Path(__file__).parent.parent.parent
            lock_dir = project_root / "data" / "runtime"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_file_path = str(lock_dir / "quranbot.lock")

        self.lock_file_path = lock_file_path
        self.lock_file: int | None = None
        self.current_pid = os.getpid()
        self.lock_acquired = False

        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)

        TreeLogger.info(
            "Process lock manager initialized",
            {"lock_file_path": self.lock_file_path, "current_pid": self.current_pid},
            service="ProcessLockManager",
        )

    def acquire_lock(self, force: bool = False, timeout: int = 30) -> bool:
        """
        Acquire process lock, optionally terminating existing instances.

        Args:
            force: If True, terminate existing instances
            timeout: Maximum time to wait for lock acquisition

        Returns:
            True if lock acquired successfully, False otherwise
        """
        try:
            TreeLogger.info(
                "Attempting to acquire process lock",
                {"force": force, "timeout": timeout, "current_pid": self.current_pid},
                service="ProcessLockManager",
            )

            start_time = time.time()

            while time.time() - start_time < timeout:
                # Check if lock file exists and is valid
                existing_instance = self._check_existing_instance()

                if existing_instance:
                    if force:
                        TreeLogger.warning(
                            "Existing instance detected, attempting termination",
                            {
                                "existing_pid": existing_instance["pid"],
                                "existing_start_time": existing_instance.get(
                                    "start_time"
                                ),
                                "force_mode": True,
                            },
                            service="ProcessLockManager",
                        )

                        if self._terminate_existing_instance(existing_instance):
                            TreeLogger.info(
                                "Existing instance terminated successfully",
                                {"terminated_pid": existing_instance["pid"]},
                                service="ProcessLockManager",
                            )
                            # Wait a moment for cleanup
                            time.sleep(2)
                            continue
                        else:
                            TreeLogger.error(
                                "Failed to terminate existing instance",
                                None,
                                {"existing_pid": existing_instance["pid"]},
                                service="ProcessLockManager",
                            )
                            return False
                    else:
                        TreeLogger.error(
                            "Another bot instance is already running",
                            None,
                            {
                                "existing_pid": existing_instance["pid"],
                                "existing_start_time": existing_instance.get(
                                    "start_time"
                                ),
                                "force_mode": False,
                            },
                            service="ProcessLockManager",
                        )
                        return False

                # Try to acquire lock
                if self._create_lock_file():
                    self.lock_acquired = True
                    TreeLogger.info(
                        "Process lock acquired successfully",
                        {
                            "lock_file_path": self.lock_file_path,
                            "current_pid": self.current_pid,
                            "acquisition_time_ms": (time.time() - start_time) * 1000,
                        },
                        service="ProcessLockManager",
                    )
                    return True

                # Wait before retrying
                time.sleep(1)

            TreeLogger.error(
                "Failed to acquire process lock within timeout",
                None,
                {"timeout": timeout, "elapsed_time": time.time() - start_time},
                service="ProcessLockManager",
            )
            return False

        except Exception as e:
            TreeLogger.error(
                f"Error acquiring process lock: {e}",
                None,
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )
            return False

    def release_lock(self) -> bool:
        """
        Release the process lock.

        Returns:
            True if lock released successfully, False otherwise
        """
        try:
            if not self.lock_acquired:
                TreeLogger.warning(
                    "No lock to release",
                    {"current_pid": self.current_pid},
                    service="ProcessLockManager",
                )
                return True

            TreeLogger.info(
                "Releasing process lock",
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )

            success = self._remove_lock_file()

            if success:
                self.lock_acquired = False
                TreeLogger.info(
                    "Process lock released successfully",
                    {
                        "lock_file_path": self.lock_file_path,
                        "current_pid": self.current_pid,
                    },
                    service="ProcessLockManager",
                )
            else:
                TreeLogger.error(
                    "Failed to release process lock",
                    None,
                    {
                        "lock_file_path": self.lock_file_path,
                        "current_pid": self.current_pid,
                    },
                    service="ProcessLockManager",
                )

            return success

        except Exception as e:
            TreeLogger.error(
                f"Error releasing process lock: {e}",
                None,
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )
            return False

    def _check_existing_instance(self) -> dict[str, Any] | None:
        """
        Check if another instance is already running.

        Returns:
            Dict with instance info if found, None otherwise
        """
        try:
            if not os.path.exists(self.lock_file_path):
                return None

            with open(self.lock_file_path) as f:
                lock_data = f.read().strip().split("\n")

            if len(lock_data) < 2:
                TreeLogger.warning(
                    "Invalid lock file format, removing",
                    {"lock_file_path": self.lock_file_path},
                    service="ProcessLockManager",
                )
                os.remove(self.lock_file_path)
                return None

            pid = int(lock_data[0])
            start_time = lock_data[1] if len(lock_data) > 1 else "unknown"

            # Check if process is still running
            if self._is_process_running(pid):
                return {
                    "pid": pid,
                    "start_time": start_time,
                    "lock_file_path": self.lock_file_path,
                }
            else:
                TreeLogger.warning(
                    "Stale lock file detected, removing",
                    {"stale_pid": pid, "lock_file_path": self.lock_file_path},
                    service="ProcessLockManager",
                )
                os.remove(self.lock_file_path)
                return None

        except (ValueError, FileNotFoundError, PermissionError) as e:
            TreeLogger.warning(
                f"Error checking existing instance: {e}",
                {"lock_file_path": self.lock_file_path},
                service="ProcessLockManager",
            )
            # Try to remove potentially corrupted lock file
            try:
                if os.path.exists(self.lock_file_path):
                    os.remove(self.lock_file_path)
            except:
                pass
            return None
        except Exception as e:
            TreeLogger.error(
                f"Unexpected error checking existing instance: {e}",
                None,
                {"lock_file_path": self.lock_file_path},
                service="ProcessLockManager",
            )
            return None

    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process with given PID is running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            # Use psutil for cross-platform process checking
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                # Additional check: ensure it's a Python process (likely our bot)
                try:
                    cmdline = process.cmdline()
                    if any(
                        "python" in arg.lower() or "quranbot" in arg.lower()
                        for arg in cmdline
                    ):
                        return True
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    # If we can't access cmdline, assume it's running if PID exists
                    return True
            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
        except Exception as e:
            TreeLogger.warning(
                f"Error checking if process {pid} is running: {e}",
                {"pid": pid},
                service="ProcessLockManager",
            )
            return False

    def _terminate_existing_instance(self, instance_info: dict[str, Any]) -> bool:
        """
        Terminate an existing bot instance.

        Args:
            instance_info: Information about the instance to terminate

        Returns:
            True if termination successful, False otherwise
        """
        try:
            pid = instance_info["pid"]

            TreeLogger.warning(
                "Terminating existing bot instance",
                {
                    "target_pid": pid,
                    "start_time": instance_info.get("start_time", "unknown"),
                },
                service="ProcessLockManager",
            )

            if not self._is_process_running(pid):
                TreeLogger.info(
                    "Target process no longer running",
                    {"target_pid": pid},
                    service="ProcessLockManager",
                )
                return True

            process = psutil.Process(pid)

            # Try graceful termination first (SIGTERM)
            TreeLogger.info(
                "Sending SIGTERM to existing instance",
                {"target_pid": pid},
                service="ProcessLockManager",
            )

            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=15)  # Wait up to 15 seconds
                TreeLogger.info(
                    "Existing instance terminated gracefully",
                    {"target_pid": pid},
                    service="ProcessLockManager",
                )
                return True
            except psutil.TimeoutExpired:
                TreeLogger.warning(
                    "Graceful termination timed out, using SIGKILL",
                    {"target_pid": pid},
                    service="ProcessLockManager",
                )

                # Force kill if graceful termination failed
                process.kill()

                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds
                    TreeLogger.info(
                        "Existing instance force-killed",
                        {"target_pid": pid},
                        service="ProcessLockManager",
                    )
                    return True
                except psutil.TimeoutExpired:
                    TreeLogger.error(
                        "Failed to force-kill existing instance",
                        None,
                        {"target_pid": pid},
                        service="ProcessLockManager",
                    )
                    return False

        except psutil.NoSuchProcess:
            TreeLogger.info(
                "Target process no longer exists",
                {"target_pid": instance_info["pid"]},
                service="ProcessLockManager",
            )
            return True
        except psutil.AccessDenied:
            TreeLogger.error(
                "Permission denied when terminating existing instance",
                None,
                {"target_pid": instance_info["pid"]},
                service="ProcessLockManager",
            )
            return False
        except Exception as e:
            TreeLogger.error(
                f"Error terminating existing instance: {e}",
                None,
                {"target_pid": instance_info["pid"]},
                service="ProcessLockManager",
            )
            return False

    def _create_lock_file(self) -> bool:
        """
        Create and lock the lock file.

        Returns:
            True if lock file created successfully, False otherwise
        """
        try:
            # Create lock file with exclusive lock
            self.lock_file = os.open(
                self.lock_file_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write process information
            lock_content = (
                f"{self.current_pid}\n{datetime.now(APP_TIMEZONE).isoformat()}\n"
            )
            os.write(self.lock_file, lock_content.encode("utf-8"))
            os.fsync(self.lock_file)  # Force write to disk

            return True

        except OSError as e:
            if self.lock_file:
                try:
                    os.close(self.lock_file)
                except:
                    pass
                self.lock_file = None

            # Lock file might be locked by another process
            if "Resource temporarily unavailable" in str(
                e
            ) or "Operation would block" in str(e):
                return False

            TreeLogger.error(
                f"Error creating lock file: {e}",
                None,
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )
            return False
        except Exception as e:
            TreeLogger.error(
                f"Unexpected error creating lock file: {e}",
                None,
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )
            return False

    def _remove_lock_file(self) -> bool:
        """
        Remove the lock file and release the lock.

        Returns:
            True if removal successful, False otherwise
        """
        try:
            if self.lock_file:
                # Release file lock
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                os.close(self.lock_file)
                self.lock_file = None

            # Remove lock file
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)

            return True

        except Exception as e:
            TreeLogger.error(
                f"Error removing lock file: {e}",
                None,
                {
                    "lock_file_path": self.lock_file_path,
                    "current_pid": self.current_pid,
                },
                service="ProcessLockManager",
            )
            return False

    def _cleanup_on_exit(self) -> None:
        """Cleanup function called on process exit."""
        if self.lock_acquired:
            try:
                self._remove_lock_file()
            except:
                pass  # Ignore errors during exit cleanup

    def get_lock_info(self) -> dict[str, Any]:
        """
        Get information about the current lock.

        Returns:
            Dict with lock information
        """
        return {
            "lock_file_path": self.lock_file_path,
            "current_pid": self.current_pid,
            "lock_acquired": self.lock_acquired,
            "lock_file_exists": os.path.exists(self.lock_file_path),
        }


# Global instance for easy access
_process_lock_manager: ProcessLockManager | None = None


def get_process_lock_manager() -> ProcessLockManager:
    """Get global process lock manager instance."""
    global _process_lock_manager
    if _process_lock_manager is None:
        _process_lock_manager = ProcessLockManager()
    return _process_lock_manager


def ensure_single_instance(force: bool = False, timeout: int = 30) -> bool:
    """
    Ensure only one bot instance is running.

    Args:
        force: If True, terminate existing instances
        timeout: Maximum time to wait for lock acquisition

    Returns:
        True if single instance ensured, False otherwise
    """
    lock_manager = get_process_lock_manager()
    return lock_manager.acquire_lock(force=force, timeout=timeout)


def release_instance_lock() -> bool:
    """
    Release the instance lock.

    Returns:
        True if lock released successfully, False otherwise
    """
    global _process_lock_manager
    if _process_lock_manager:
        return _process_lock_manager.release_lock()
    return True
