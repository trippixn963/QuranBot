"""
Log cleanup and compression system for QuranBot.
Automatically compresses old logs, deletes very old logs, and archives important events.
"""

import os
import zipfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Any
import json

class LogCleanupManager:
    """Manages log file cleanup, compression, and archiving."""
    
    def __init__(self, logs_dir: str = "logs"):
        """Initialize the log cleanup manager."""
        self.logs_dir = Path(logs_dir)
        self.archives_dir = self.logs_dir / "archives"
        self.important_dir = self.logs_dir / "important"
        
        # Create necessary directories
        self.logs_dir.mkdir(exist_ok=True)
        self.archives_dir.mkdir(exist_ok=True)
        self.important_dir.mkdir(exist_ok=True)
        
        # Configuration
        self.compress_after_days = 7
        self.delete_after_days = 30
        self.keep_error_logs_days = 90  # Keep error logs longer
        
    def get_date_folders(self) -> List[Path]:
        """Get all date folders in the logs directory."""
        if not self.logs_dir.exists():
            return []
        
        date_folders = []
        for item in self.logs_dir.iterdir():
            if item.is_dir() and self._is_date_folder(item.name):
                date_folders.append(item)
        
        return sorted(date_folders)
    
    def _is_date_folder(self, folder_name: str) -> bool:
        """Check if a folder name is a date folder (YYYY-MM-DD)."""
        try:
            datetime.strptime(folder_name, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def get_folder_age_days(self, folder_path: Path) -> int:
        """Get the age of a folder in days."""
        try:
            folder_date = datetime.strptime(folder_path.name, '%Y-%m-%d')
            age = datetime.now() - folder_date
            return age.days
        except ValueError:
            return 999  # Very old if we can't parse the date
    
    def compress_old_logs(self) -> Dict[str, Any]:
        """Compress logs older than compress_after_days."""
        results = {
            'compressed': [],
            'errors': [],
            'skipped': []
        }
        
        date_folders = self.get_date_folders()
        today = datetime.now()
        
        for folder in date_folders:
            age_days = self.get_folder_age_days(folder)
            
            # Skip if too new or too old (will be deleted)
            if age_days < self.compress_after_days or age_days >= self.delete_after_days:
                results['skipped'].append(folder.name)
                continue
            
            # Check if already compressed
            archive_name = f"{folder.name}.zip"
            archive_path = self.archives_dir / archive_name
            
            if archive_path.exists():
                results['skipped'].append(f"{folder.name} (already compressed)")
                continue
            
            try:
                # Create zip archive
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in folder.rglob('*'):
                        if file_path.is_file():
                            # Add file to zip with relative path
                            arcname = file_path.relative_to(folder)
                            zipf.write(file_path, arcname)
                
                # Archive important files (errors, critical events)
                self._archive_important_files(folder)
                
                # Remove original folder after successful compression
                shutil.rmtree(folder)
                
                results['compressed'].append(folder.name)
                
            except Exception as e:
                results['errors'].append(f"{folder.name}: {str(e)}")
        
        return results
    
    def _archive_important_files(self, folder: Path):
        """Archive important log files (errors, critical events) separately."""
        important_date_dir = self.important_dir / folder.name
        important_date_dir.mkdir(exist_ok=True)
        
        # Files to archive as important
        important_patterns = [
            '*-errors.log',
            'quranbot-errors.log'
        ]
        
        for pattern in important_patterns:
            for file_path in folder.glob(pattern):
                if file_path.is_file():
                    # Copy to important directory
                    dest_path = important_date_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
    
    def delete_old_logs(self) -> Dict[str, Any]:
        """Delete logs older than delete_after_days."""
        results = {
            'deleted': [],
            'errors': [],
            'skipped': []
        }
        
        date_folders = self.get_date_folders()
        
        for folder in date_folders:
            age_days = self.get_folder_age_days(folder)
            
            if age_days >= self.delete_after_days:
                try:
                    # Check if compressed version exists
                    archive_name = f"{folder.name}.zip"
                    archive_path = self.archives_dir / archive_name
                    
                    if archive_path.exists():
                        # Delete compressed version too
                        archive_path.unlink()
                        results['deleted'].append(f"{folder.name} (compressed)")
                    else:
                        # Delete uncompressed folder
                        shutil.rmtree(folder)
                        results['deleted'].append(folder.name)
                        
                except Exception as e:
                    results['errors'].append(f"{folder.name}: {str(e)}")
            else:
                results['skipped'].append(folder.name)
        
        return results
    
    def cleanup_old_archives(self) -> Dict[str, Any]:
        """Clean up old archives and important logs."""
        results = {
            'deleted_archives': [],
            'deleted_important': [],
            'errors': []
        }
        
        # Clean up old archives
        for archive_file in self.archives_dir.glob("*.zip"):
            try:
                # Extract date from filename (YYYY-MM-DD.zip)
                date_str = archive_file.stem
                if self._is_date_folder(date_str):
                    age_days = self.get_folder_age_days(Path(date_str))
                    if age_days >= self.delete_after_days:
                        archive_file.unlink()
                        results['deleted_archives'].append(archive_file.name)
            except Exception as e:
                results['errors'].append(f"Archive {archive_file.name}: {str(e)}")
        
        # Clean up old important logs
        for important_folder in self.important_dir.iterdir():
            if important_folder.is_dir() and self._is_date_folder(important_folder.name):
                try:
                    age_days = self.get_folder_age_days(important_folder)
                    if age_days >= self.keep_error_logs_days:
                        shutil.rmtree(important_folder)
                        results['deleted_important'].append(important_folder.name)
                except Exception as e:
                    results['errors'].append(f"Important {important_folder.name}: {str(e)}")
        
        return results
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get statistics about the current log state."""
        date_folders = self.get_date_folders()
        archive_files = list(self.archives_dir.glob("*.zip"))
        important_folders = [f for f in self.important_dir.iterdir() if f.is_dir()]
        
        total_size = 0
        folder_sizes = {}
        
        # Calculate sizes
        for folder in date_folders:
            size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
            folder_sizes[folder.name] = size
            total_size += size
        
        for archive in archive_files:
            total_size += archive.stat().st_size
        
        for folder in important_folders:
            size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
            total_size += size
        
        return {
            'active_folders': len(date_folders),
            'archived_folders': len(archive_files),
            'important_folders': len(important_folders),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'folder_sizes': folder_sizes,
            'oldest_folder': min([f.name for f in date_folders]) if date_folders else None,
            'newest_folder': max([f.name for f in date_folders]) if date_folders else None
        }
    
    def run_full_cleanup(self) -> Dict[str, Any]:
        """Run the complete cleanup process."""
        results = {
            'compression': self.compress_old_logs(),
            'deletion': self.delete_old_logs(),
            'archive_cleanup': self.cleanup_old_archives(),
            'stats': self.get_cleanup_stats()
        }
        
        return results

def setup_log_cleanup_scheduler():
    """Set up automatic log cleanup scheduling."""
    import asyncio
    from datetime import datetime, time
    
    async def cleanup_scheduler():
        """Run cleanup every day at 2 AM."""
        while True:
            now = datetime.now()
            
            # Calculate time until next 2 AM
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            
            # Wait until next run
            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            
            # Run cleanup
            try:
                cleanup_manager = LogCleanupManager()
                results = cleanup_manager.run_full_cleanup()
                
                # Log cleanup results
                logger = logging.getLogger('QuranBot')
                logger.info(f"Log cleanup completed: {results['stats']['active_folders']} active folders, "
                           f"{results['stats']['archived_folders']} archived, "
                           f"{results['stats']['total_size_mb']}MB total")
                
                if results['compression']['compressed']:
                    logger.info(f"Compressed: {', '.join(results['compression']['compressed'])}")
                
                if results['deletion']['deleted']:
                    logger.info(f"Deleted: {', '.join(results['deletion']['deleted'])}")
                
            except Exception as e:
                logger = logging.getLogger('QuranBot')
                logger.error(f"Log cleanup failed: {str(e)}")
    
    return cleanup_scheduler

# Example usage:
if __name__ == "__main__":
    # Manual cleanup
    cleanup_manager = LogCleanupManager()
    results = cleanup_manager.run_full_cleanup()
    
    print("Cleanup Results:")
    print(f"Compressed: {results['compression']['compressed']}")
    print(f"Deleted: {results['deletion']['deleted']}")
    print(f"Stats: {results['stats']}") 