"""
Backup Manager for the Discord Quran Bot.
Provides automated backup functionality for bot data and configuration.

This module provides comprehensive backup management including:
- Automated data directory backups
- Cross-platform backup script execution
- Backup verification and validation
- Comprehensive error handling and logging
- Backup cleanup and rotation

Features:
    - Automated backup creation
    - Backup script execution with timeout
    - Cross-platform compatibility
    - Backup verification
    - Comprehensive error handling
    - Detailed logging and monitoring

Author: John (Discord: Trippxin)
Version: 2.0.0
"""

import os
import subprocess
import logging
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from src.monitoring.logging.tree_log import tree_log


class BackupManager:
    """
    Backup Manager for automated data backup functionality.

    This class provides comprehensive backup management for the Quran Bot
    including automated backup creation, verification, and cleanup.

    Features:
        - Automated backup creation
        - Cross-platform backup script execution
        - Backup verification and validation
        - Comprehensive error handling
        - Detailed logging and monitoring
    """

    def __init__(self, bot_root_dir: Optional[str] = None):
        """
        Initialize the backup manager.

        Args:
            bot_root_dir (Optional[str]): Root directory of the bot.
            If None, will try to detect automatically.
        """
        try:
            if bot_root_dir is None:
                # Try to detect bot root directory
                current_file = Path(__file__).resolve()
                self.bot_root = str(current_file.parent.parent.parent.parent)
            else:
                self.bot_root = bot_root_dir

            # Set up backup script paths for different platforms
            self.backup_script_linux = os.path.join(
                self.bot_root, "scripts", "linux", "backup_data.sh"
            )
            self.backup_script_windows = os.path.join(
                self.bot_root, "scripts", "windows", "backup_data.ps1"
            )

            # Validate backup script existence
            self._validate_backup_scripts()

            tree_log('info', 'Backup manager initialized', {'event': 'BACKUP_MANAGER_INIT', 'bot_root': self.bot_root})

        except Exception as e:
            tree_log('error', 'Failed to initialize backup manager', {'event': 'BACKUP_MANAGER_INIT_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            raise

    def _validate_backup_scripts(self) -> None:
        """
        Validate that backup scripts exist and are accessible.

        Raises:
            FileNotFoundError: If backup scripts are not found
        """
        try:
            # Check if Linux script exists
            if not os.path.exists(self.backup_script_linux):
                tree_log('warning', 'Linux backup script not found', {'event': 'BACKUP_SCRIPT_LINUX_MISSING', 'path': self.backup_script_linux})

            # Check if Windows script exists
            if not os.path.exists(self.backup_script_windows):
                tree_log('warning', 'Windows backup script not found', {'event': 'BACKUP_SCRIPT_WINDOWS_MISSING', 'path': self.backup_script_windows})

            # At least one script should exist
            if not os.path.exists(self.backup_script_linux) and not os.path.exists(
                self.backup_script_windows
            ):
                tree_log('error', 'No backup scripts found', {'event': 'BACKUP_SCRIPTS_MISSING'})

        except Exception as e:
            from src.monitoring.logging.tree_log import tree_log
            tree_log('error', 'Error validating backup scripts', {'event': 'BACKUP_SCRIPT_VALIDATE_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            raise

    def _get_backup_script(self) -> str:
        """
        Get the appropriate backup script for the current platform.

        Returns:
            str: Path to the appropriate backup script

        Raises:
            FileNotFoundError: If no suitable backup script is found
        """
        try:
            import platform

            system = platform.system().lower()

            if system == "linux" or system == "darwin":  # Linux or macOS
                if os.path.exists(self.backup_script_linux):
                    return self.backup_script_linux
                else:
                    raise FileNotFoundError(
                        f"Linux backup script not found: {self.backup_script_linux}"
                    )
            elif system == "windows":
                if os.path.exists(self.backup_script_windows):
                    return self.backup_script_windows
                else:
                    raise FileNotFoundError(
                        f"Windows backup script not found: {self.backup_script_windows}"
                    )
            else:
                # Try Linux script as fallback
                if os.path.exists(self.backup_script_linux):
                    return self.backup_script_linux
                else:
                    raise FileNotFoundError(
                        "No suitable backup script found for this platform"
                    )

        except Exception as e:
            from src.monitoring.logging.tree_log import tree_log
            tree_log('error', 'Error getting backup script', {'event': 'BACKUP_SCRIPT_GET_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            raise

    async def create_backup(self) -> bool:
        """
        Create a backup of the data directory.

        This method executes the appropriate backup script for the current
        platform and handles all error cases with comprehensive logging.

        Returns:
            bool: True if backup was successful, False otherwise
        """
        try:
            tree_log('info', 'Starting automated backup', {'event': 'BACKUP_START'})

            # Get appropriate backup script
            backup_script = self._get_backup_script()
            tree_log('info', 'Using backup script', {'event': 'BACKUP_SCRIPT_USED', 'script': backup_script})

            # Make sure backup script is executable (for Linux/macOS)
            if backup_script.endswith(".sh"):
                try:
                    os.chmod(backup_script, 0o755)
                    tree_log('debug', 'Backup script made executable', {'event': 'BACKUP_SCRIPT_EXECUTABLE'})
                except Exception as e:
                    tree_log('warning', 'Could not make backup script executable', {'event': 'BACKUP_SCRIPT_CHMOD_ERROR', 'error': str(e)})

            # Prepare command based on script type
            if backup_script.endswith(".sh"):
                cmd = [backup_script]
            elif backup_script.endswith(".ps1"):
                cmd = [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    backup_script,
                ]
            else:
                raise ValueError(f"Unsupported backup script type: {backup_script}")

            # Run backup script with timeout
            tree_log('info', 'Executing backup script', {'event': 'BACKUP_EXECUTE'})
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.bot_root,
                text=True,  # Use text mode for better error handling
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout

                if process.returncode == 0:
                    tree_log('info', 'Data backup completed successfully', {'event': 'BACKUP_SUCCESS'})
                    if stdout:
                        tree_log('debug', 'Backup output', {'event': 'BACKUP_OUTPUT', 'output': stdout.strip()})
                    tree_log('tree', 'Backup Operation Summary', {'event': 'BACKUP_TREE_SUMMARY', 'script': backup_script, 'directory': self.bot_root, 'result': 'success'})
                    return True
                else:
                    error_msg = stderr.strip() if stderr else "Unknown error"
                    tree_log('error', 'Backup failed', {'event': 'BACKUP_FAIL', 'returncode': process.returncode, 'error': error_msg})
                    if stdout:
                        tree_log('debug', 'Backup stdout', {'event': 'BACKUP_STDOUT', 'output': stdout.strip()})
                    return False

            except subprocess.TimeoutExpired:
                tree_log('error', 'Backup timed out after 5 minutes', {'event': 'BACKUP_TIMEOUT'})
                process.kill()
                process.communicate()  # Clean up
                return False

        except FileNotFoundError as e:
            tree_log('error', 'Backup script not found', {'event': 'BACKUP_SCRIPT_NOT_FOUND', 'error': str(e)})
            return False
        except PermissionError as e:
            tree_log('error', 'Permission denied for backup script', {'event': 'BACKUP_PERMISSION_DENIED', 'error': str(e)})
            return False
        except Exception as e:
            from src.monitoring.logging.tree_log import tree_log
            tree_log('error', 'Unexpected error during backup', {'event': 'BACKUP_UNEXPECTED_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def verify_backup(self, backup_path: str) -> bool:
        """
        Verify that a backup file exists and is valid.

        Args:
            backup_path (str): Path to the backup file to verify

        Returns:
            bool: True if backup is valid, False otherwise
        """
        try:
            if not os.path.exists(backup_path):
                tree_log('warning', 'Backup file not found', {'event': 'BACKUP_FILE_NOT_FOUND', 'path': backup_path})
                return False

            # Check file size
            file_size = os.path.getsize(backup_path)
            if file_size == 0:
                tree_log('error', 'Backup file is empty', {'event': 'BACKUP_FILE_EMPTY', 'path': backup_path})
                return False

            tree_log('info', 'Backup verification passed', {'event': 'BACKUP_VERIFY_SUCCESS', 'path': backup_path, 'size': file_size})
            return True

        except Exception as e:
            from src.monitoring.logging.tree_log import tree_log
            tree_log('error', 'Error verifying backup', {'event': 'BACKUP_VERIFY_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return False

    def get_backup_info(self) -> Dict[str, Any]:
        """
        Get information about the backup system.

        Returns:
            Dict[str, Any]: Dictionary containing backup system information
        """
        try:
            import platform

            info = {
                "bot_root": self.bot_root,
                "platform": platform.system(),
                "linux_script_exists": os.path.exists(self.backup_script_linux),
                "windows_script_exists": os.path.exists(self.backup_script_windows),
                "backup_script_linux": self.backup_script_linux,
                "backup_script_windows": self.backup_script_windows,
                "current_script": self._get_backup_script(),
            }
            tree_log('info', 'Backup info retrieved', {'event': 'BACKUP_INFO', **info})
            return info

        except Exception as e:
            tree_log('error', 'Error getting backup info', {'event': 'BACKUP_INFO_ERROR', 'error': str(e), 'traceback': traceback.format_exc()})
            return {"error": str(e)}
