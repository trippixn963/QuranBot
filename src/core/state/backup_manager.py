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
from monitoring.logging.logger import log_tree_start, log_tree_item, log_tree_end


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

            # Initialize logger
            self.logger = logging.getLogger(__name__)

            # Validate backup script existence
            self._validate_backup_scripts()

            self.logger.info(f"✅ Backup manager initialized for: {self.bot_root}")

        except Exception as e:
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"❌ Failed to initialize backup manager: {e}")
            self.logger.error(
                f"🔍 Backup manager init error traceback: {traceback.format_exc()}"
            )
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
                self.logger.warning(
                    f"⚠️ Linux backup script not found: {self.backup_script_linux}"
                )

            # Check if Windows script exists
            if not os.path.exists(self.backup_script_windows):
                self.logger.warning(
                    f"⚠️ Windows backup script not found: {self.backup_script_windows}"
                )

            # At least one script should exist
            if not os.path.exists(self.backup_script_linux) and not os.path.exists(
                self.backup_script_windows
            ):
                self.logger.error("❌ No backup scripts found!")

        except Exception as e:
            self.logger.error(f"❌ Error validating backup scripts: {e}")
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
            self.logger.error(f"❌ Error getting backup script: {e}")
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
            self.logger.info("🔄 Starting automated backup...")

            # Get appropriate backup script
            backup_script = self._get_backup_script()
            self.logger.info(f"📜 Using backup script: {backup_script}")

            # Make sure backup script is executable (for Linux/macOS)
            if backup_script.endswith(".sh"):
                try:
                    os.chmod(backup_script, 0o755)
                    self.logger.debug("✅ Backup script made executable")
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Could not make backup script executable: {e}"
                    )

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
            self.logger.info("🚀 Executing backup script...")
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
                    self.logger.info("✅ Data backup completed successfully")
                    if stdout:
                        self.logger.debug(f"📄 Backup output: {stdout.strip()}")
                    log_tree_start("Backup Operation Summary")
                    log_tree_item(f"📦 Backup script: {backup_script}")
                    log_tree_item(f"📁 Backup directory: {self.bot_root}")
                    log_tree_item("✅ Data backup completed successfully", is_last=True)
                    log_tree_end()
                    return True
                else:
                    error_msg = stderr.strip() if stderr else "Unknown error"
                    self.logger.error(
                        f"❌ Backup failed with return code {process.returncode}"
                    )
                    self.logger.error(f"🔍 Backup error: {error_msg}")
                    if stdout:
                        self.logger.debug(f"📄 Backup stdout: {stdout.strip()}")
                    return False

            except subprocess.TimeoutExpired:
                self.logger.error("⏰ Backup timed out after 5 minutes")
                process.kill()
                process.communicate()  # Clean up
                return False

        except FileNotFoundError as e:
            self.logger.error(f"❌ Backup script not found: {e}")
            return False
        except PermissionError as e:
            self.logger.error(f"❌ Permission denied for backup script: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error during backup: {e}")
            self.logger.error(f"🔍 Backup error traceback: {traceback.format_exc()}")
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
                self.logger.warning(f"⚠️ Backup file not found: {backup_path}")
                return False

            # Check file size
            file_size = os.path.getsize(backup_path)
            if file_size == 0:
                self.logger.error(f"❌ Backup file is empty: {backup_path}")
                return False

            self.logger.info(
                f"✅ Backup verification passed: {backup_path} ({file_size} bytes)"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Error verifying backup: {e}")
            return False

    def get_backup_info(self) -> Dict[str, Any]:
        """
        Get information about the backup system.

        Returns:
            Dict[str, Any]: Dictionary containing backup system information
        """
        try:
            import platform

            return {
                "bot_root": self.bot_root,
                "platform": platform.system(),
                "linux_script_exists": os.path.exists(self.backup_script_linux),
                "windows_script_exists": os.path.exists(self.backup_script_windows),
                "backup_script_linux": self.backup_script_linux,
                "backup_script_windows": self.backup_script_windows,
                "current_script": self._get_backup_script(),
            }

        except Exception as e:
            self.logger.error(f"❌ Error getting backup info: {e}")
            return {"error": str(e)}
