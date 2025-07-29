# =============================================================================
# QuranBot - Data Backup Service
# =============================================================================
# Lightweight backup service that only backs up the data/ folder
# Each backup overwrites the previous one to save space
# =============================================================================

import asyncio
import gzip
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .structured_logger import StructuredLogger
from ..utils.tree_log import log_perfect_tree_section, log_error_with_traceback


class DataBackupService:
    """
    Lightweight backup service for the data/ folder only.
    
    Features:
    - Backs up only the data/ folder (not the entire project)
    - Each backup overwrites the previous one (saves space)
    - Compressed backups using gzip
    - Simple and efficient
    - Configurable backup interval
    """

    def __init__(
        self, 
        logger: StructuredLogger, 
        data_dir: Path = None,
        backup_dir: Path = None,
        backup_interval_hours: int = 6
    ):
        """
        Initialize the data backup service.
        
        Args:
            logger: Structured logger instance
            data_dir: Directory containing data files (defaults to 'data')
            backup_dir: Directory for backups (defaults to 'backup')
            backup_interval_hours: Hours between backups (default: 6 hours)
        """
        self.logger = logger
        self.data_dir = data_dir or Path("data")
        self.backup_dir = backup_dir or Path("backup")
        self.backup_interval_hours = backup_interval_hours
        
        # Single backup file that gets overwritten
        self.backup_file = self.backup_dir / "data_backup.tar.gz"
        
        # Background task
        self.backup_task = None
        self.is_running = False
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def start_backup_service(self) -> None:
        """Start the background backup service"""
        if self.is_running:
            await self.logger.warning("Data backup service already running")
            return
            
        self.is_running = True
        self.backup_task = asyncio.create_task(self._backup_loop())
        
        await self.logger.info(
            "Data backup service started",
            {
                "interval_hours": self.backup_interval_hours,
                "data_dir": str(self.data_dir),
                "backup_file": str(self.backup_file)
            }
        )
        
        log_perfect_tree_section(
            "Data Backup Service - Started",
            [
                ("target", f"📁 {self.data_dir}"),
                ("backup_file", f"💾 {self.backup_file}"),
                ("interval", f"⏰ Every {self.backup_interval_hours} hours"),
                ("mode", "🔄 Overwrite previous backup")
            ],
            "💾"
        )
        
    async def stop_backup_service(self) -> None:
        """Stop the background backup service"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.backup_task and not self.backup_task.done():
            self.backup_task.cancel()
            try:
                await self.backup_task
            except asyncio.CancelledError:
                pass
                
        await self.logger.info("Data backup service stopped")
        
        log_perfect_tree_section(
            "Data Backup Service - Stopped",
            [("status", "🛑 Backup service stopped cleanly")],
            "🛑"
        )
        
    async def _backup_loop(self) -> None:
        """Background backup loop"""
        # Create initial backup
        await self.create_backup()
        
        while self.is_running:
            try:
                # Wait for the backup interval
                interval_seconds = self.backup_interval_hours * 3600
                await asyncio.sleep(interval_seconds)
                
                if not self.is_running:
                    break
                    
                # Create backup
                await self.create_backup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.logger.error(
                    "Error in backup loop", 
                    {"error": str(e)}
                )
                log_error_with_traceback("Data backup loop error", e)
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes
                
    async def create_backup(self) -> bool:
        """
        Create a backup of the data directory.
        
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            if not self.data_dir.exists():
                await self.logger.warning(
                    "Data directory does not exist", 
                    {"data_dir": str(self.data_dir)}
                )
                return False
                
            await self.logger.debug("Starting data backup")
            
            # Create temporary backup file
            temp_backup = self.backup_file.with_suffix('.tmp')
            
            # Create tar.gz archive of data directory
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self._create_compressed_archive, 
                temp_backup
            )
            
            # Atomically replace the old backup
            if temp_backup.exists():
                if self.backup_file.exists():
                    self.backup_file.unlink()
                temp_backup.rename(self.backup_file)
                
                # Get backup info
                backup_size = self.backup_file.stat().st_size
                backup_size_mb = backup_size / (1024 * 1024)
                
                await self.logger.info(
                    "Data backup created successfully",
                    {
                        "backup_file": str(self.backup_file),
                        "size_bytes": backup_size,
                        "size_mb": f"{backup_size_mb:.2f}"
                    }
                )
                
                log_perfect_tree_section(
                    "Data Backup - Created",
                    [
                        ("status", "✅ Backup successful"),
                        ("size", f"💾 {backup_size_mb:.2f} MB"),
                        ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        ("next_backup", f"⏰ In {self.backup_interval_hours} hours")
                    ],
                    "✅"
                )
                
                return True
            else:
                await self.logger.error("Failed to create backup archive")
                return False
                
        except Exception as e:
            await self.logger.error(
                "Error creating data backup", 
                {"error": str(e)}
            )
            log_error_with_traceback("Data backup creation error", e)
            
            # Clean up temp file if it exists
            temp_backup = self.backup_file.with_suffix('.tmp')
            if temp_backup.exists():
                try:
                    temp_backup.unlink()
                except:
                    pass
                    
            return False
            
    def _create_compressed_archive(self, archive_path: Path) -> None:
        """Create compressed archive of data directory (runs in thread pool)"""
        import tarfile
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.data_dir, arcname=self.data_dir.name)
            
    async def restore_backup(self) -> bool:
        """
        Restore data from the backup file.
        
        Returns:
            True if restore was successful, False otherwise
        """
        try:
            if not self.backup_file.exists():
                await self.logger.error(
                    "No backup file found", 
                    {"backup_file": str(self.backup_file)}
                )
                return False
                
            await self.logger.info("Starting data restore from backup")
            
            # Create backup of current data before restore
            if self.data_dir.exists():
                backup_current = self.data_dir.parent / f"{self.data_dir.name}_pre_restore_backup"
                if backup_current.exists():
                    shutil.rmtree(backup_current)
                shutil.move(str(self.data_dir), str(backup_current))
                
            # Extract backup
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._extract_compressed_archive
            )
            
            await self.logger.info(
                "Data restore completed successfully",
                {"restored_from": str(self.backup_file)}
            )
            
            log_perfect_tree_section(
                "Data Restore - Completed",
                [
                    ("status", "✅ Restore successful"),
                    ("source", f"💾 {self.backup_file}"),
                    ("target", f"📁 {self.data_dir}"),
                    ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ],
                "✅"
            )
            
            return True
            
        except Exception as e:
            await self.logger.error(
                "Error restoring data backup", 
                {"error": str(e)}
            )
            log_error_with_traceback("Data restore error", e)
            return False
            
    def _extract_compressed_archive(self) -> None:
        """Extract compressed archive (runs in thread pool)"""
        import tarfile
        
        with tarfile.open(self.backup_file, "r:gz") as tar:
            tar.extractall(path=self.data_dir.parent)
            
    def get_backup_info(self) -> Dict[str, Any]:
        """Get information about the current backup"""
        try:
            if not self.backup_file.exists():
                return {
                    "exists": False,
                    "error": "No backup file found"
                }
                
            stat = self.backup_file.stat()
            return {
                "exists": True,
                "file_path": str(self.backup_file),
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_running": self.is_running,
                "interval_hours": self.backup_interval_hours
            }
            
        except Exception as e:
            return {
                "exists": False,
                "error": str(e)
            }
            
    async def manual_backup(self) -> bool:
        """Create a manual backup immediately"""
        await self.logger.info("Creating manual data backup")
        
        log_perfect_tree_section(
            "Data Backup - Manual",
            [
                ("trigger", "👤 Manual backup requested"),
                ("target", f"📁 {self.data_dir}")
            ],
            "👤"
        )
        
        return await self.create_backup() 