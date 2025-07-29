# =============================================================================
# QuranBot - JSON Validation & Protection Service
# =============================================================================
# Centralized service for JSON file operations with corruption prevention,
# atomic writes, validation, and automatic recovery mechanisms.
# Prevents the JSON corruption issues that can disrupt bot operations.
# =============================================================================

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from .exceptions import StateError
from .structured_logger import StructuredLogger


class JSONValidator:
    """
    Comprehensive JSON file validation and protection service.
    
    Features:
    - Atomic write operations (write to temp, then move)
    - Corruption detection and recovery
    - Schema validation
    - Automatic backup creation
    - Graceful error handling
    - Detailed logging
    """

    def __init__(self, logger: StructuredLogger, backup_dir: Path = None):
        """
        Initialize JSON validator.
        
        Args:
            logger: Structured logger instance
            backup_dir: Directory for backup files (defaults to backup/json_backups)
        """
        self.logger = logger
        self.backup_dir = backup_dir or Path("backup/json_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def safe_read_json(
        self, 
        file_path: Path, 
        default_data: Dict[str, Any] = None,
        validator: Callable[[Dict[str, Any]], bool] = None
    ) -> Dict[str, Any]:
        """
        Safely read JSON file with corruption protection.
        
        Args:
            file_path: Path to JSON file
            default_data: Default data if file doesn't exist or is corrupted
            validator: Optional validation function for the loaded data
            
        Returns:
            Loaded JSON data or default data
            
        Raises:
            StateError: If file is corrupted and no default provided
        """
        if default_data is None:
            default_data = {}
            
        try:
            if not file_path.exists():
                return default_data.copy()
                
            # Check if file is empty
            if file_path.stat().st_size == 0:
                self.logger.warning(
                    f"Empty JSON file detected: {file_path}",
                    {"file_path": str(file_path), "action": "using_default"}
                )
                return default_data.copy()
                
            # Attempt to load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate data structure
            if not isinstance(data, dict):
                raise ValueError(f"JSON root must be a dictionary, got {type(data).__name__}")
                
            # Run custom validator if provided
            if validator and not validator(data):
                raise ValueError("JSON data failed custom validation")
                
            self.logger.debug(
                f"Successfully loaded JSON: {file_path}",
                {"file_path": str(file_path), "data_size": len(str(data))}
            )
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(
                f"JSON decode error in {file_path}: {e}",
                {"file_path": str(file_path), "error": str(e), "position": e.pos}
            )
            return self._attempt_recovery(file_path, default_data)
            
        except Exception as e:
            self.logger.error(
                f"Error reading JSON file {file_path}: {e}",
                {"file_path": str(file_path), "error": str(e)}
            )
            return self._attempt_recovery(file_path, default_data)
            
    def safe_write_json(
        self,
        file_path: Path,
        data: Dict[str, Any],
        create_backup: bool = True,
        validator: Callable[[Dict[str, Any]], bool] = None
    ) -> bool:
        """
        Safely write JSON file with atomic operations.
        
        Args:
            file_path: Path to JSON file
            data: Data to write
            create_backup: Whether to create backup before writing
            validator: Optional validation function for the data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate data before writing
            if not isinstance(data, dict):
                raise ValueError(f"Data must be a dictionary, got {type(data).__name__}")
                
            if validator and not validator(data):
                raise ValueError("Data failed custom validation")
                
            # Create backup if requested and file exists
            if create_backup and file_path.exists():
                self._create_backup(file_path)
                
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use atomic write (write to temp file, then move)
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.tmp',
                dir=file_path.parent,
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                json.dump(data, tmp_file, indent=2, ensure_ascii=False)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Ensure data is written to disk
                temp_path = tmp_file.name
                
            # Atomic move
            os.replace(temp_path, file_path)
            
            self.logger.debug(
                f"Successfully wrote JSON: {file_path}",
                {"file_path": str(file_path), "data_size": len(str(data))}
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"Error writing JSON file {file_path}: {e}",
                {"file_path": str(file_path), "error": str(e)}
            )
            # Clean up temp file if it exists
            if 'temp_path' in locals() and Path(temp_path).exists():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return False
            
    def validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate JSON file integrity.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Validation result with status and details
        """
        result = {
            "file_path": str(file_path),
            "exists": file_path.exists(),
            "valid": False,
            "size": 0,
            "error": None,
            "last_modified": None
        }
        
        try:
            if not file_path.exists():
                result["error"] = "File does not exist"
                return result
                
            stat = file_path.stat()
            result["size"] = stat.st_size
            result["last_modified"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            
            if stat.st_size == 0:
                result["error"] = "File is empty"
                return result
                
            # Try to parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, dict):
                result["error"] = f"JSON root is not a dictionary: {type(data).__name__}"
                return result
                
            result["valid"] = True
            return result
            
        except json.JSONDecodeError as e:
            result["error"] = f"JSON decode error: {e} at position {e.pos}"
            return result
        except Exception as e:
            result["error"] = f"Error reading file: {e}"
            return result
            
    def repair_json_file(
        self,
        file_path: Path,
        default_data: Dict[str, Any] = None
    ) -> bool:
        """
        Attempt to repair a corrupted JSON file.
        
        Args:
            file_path: Path to corrupted JSON file
            default_data: Default data to use if repair fails
            
        Returns:
            True if repaired successfully
        """
        if default_data is None:
            default_data = {}
            
        try:
            # First, create a backup of the corrupted file
            if file_path.exists():
                corrupted_backup = self.backup_dir / f"{file_path.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    corrupted_backup.write_bytes(file_path.read_bytes())
                    self.logger.info(
                        f"Created backup of corrupted file: {corrupted_backup}",
                        {"original": str(file_path), "backup": str(corrupted_backup)}
                    )
                except Exception as e:
                    self.logger.warning(f"Could not backup corrupted file: {e}")
                    
            # Try to restore from recent backup
            if self._try_restore_from_backup(file_path):
                return True
                
            # Last resort: create new file with default data
            return self.safe_write_json(file_path, default_data, create_backup=False)
            
        except Exception as e:
            self.logger.error(
                f"Error repairing JSON file {file_path}: {e}",
                {"file_path": str(file_path), "error": str(e)}
            )
            return False
            
    def _attempt_recovery(self, file_path: Path, default_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to recover from corruption"""
        self.logger.warning(
            f"Attempting recovery for corrupted JSON: {file_path}",
            {"file_path": str(file_path)}
        )
        
        # Try to restore from backup
        if self._try_restore_from_backup(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
                
        # Fall back to default data
        self.logger.warning(
            f"Using default data for corrupted JSON: {file_path}",
            {"file_path": str(file_path)}
        )
        return default_data.copy()
        
    def _create_backup(self, file_path: Path) -> None:
        """Create backup of JSON file"""
        try:
            backup_path = self.backup_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup.json"
            backup_path.write_bytes(file_path.read_bytes())
            
            # Keep only last 5 backups
            backups = sorted(self.backup_dir.glob(f"{file_path.stem}_*.backup.json"))
            for old_backup in backups[:-5]:
                old_backup.unlink()
                
        except Exception as e:
            self.logger.warning(f"Could not create backup for {file_path}: {e}")
            
    def _try_restore_from_backup(self, file_path: Path) -> bool:
        """Try to restore file from most recent backup"""
        try:
            backups = sorted(
                self.backup_dir.glob(f"{file_path.stem}_*.backup.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for backup in backups:
                try:
                    # Validate backup file
                    with open(backup, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    if isinstance(data, dict):
                        # Restore from backup
                        file_path.write_bytes(backup.read_bytes())
                        self.logger.info(
                            f"Restored {file_path} from backup: {backup}",
                            {"file_path": str(file_path), "backup": str(backup)}
                        )
                        return True
                        
                except Exception:
                    continue
                    
            return False
            
        except Exception as e:
            self.logger.warning(f"Error restoring from backup: {e}")
            return False


def create_default_schemas() -> Dict[str, Dict[str, Any]]:
    """Create default JSON schemas for QuranBot files"""
    return {
        "quiz_state.json": {
            "schedule_config": {
                "send_interval_hours": 3.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        },
        "quiz_stats.json": {
            "questions_sent": 0,
            "correct_answers": 0,
            "total_attempts": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        "metadata_cache.json": {
            "cache": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        "last_mecca_notification.json": {
            "last_notification": None
        }
    }


def validate_quiz_state(data: Dict[str, Any]) -> bool:
    """Validator for quiz_state.json"""
    if "schedule_config" not in data:
        return False
    config = data["schedule_config"]
    if not isinstance(config.get("send_interval_hours"), (int, float)):
        return False
    return True


def validate_quiz_stats(data: Dict[str, Any]) -> bool:
    """Validator for quiz_stats.json"""
    required_fields = ["questions_sent", "correct_answers", "total_attempts"]
    for field in required_fields:
        if field not in data or not isinstance(data[field], int):
            return False
    return True 