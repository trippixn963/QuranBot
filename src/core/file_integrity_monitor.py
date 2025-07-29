# =============================================================================
# QuranBot - File Integrity Monitor
# =============================================================================
# Background monitor that validates JSON files and performs auto-repair
# Prevents corruption issues by checking files during startup and periodically
# =============================================================================

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from .json_validator import JSONValidator, create_default_schemas
from .structured_logger import StructuredLogger
from ..utils.tree_log import log_perfect_tree_section, log_error_with_traceback


class FileIntegrityMonitor:
    """
    Monitor for JSON file integrity with automatic repair capabilities.
    
    Features:
    - Startup validation of all critical JSON files
    - Automatic repair of corrupted files
    - Periodic integrity checks
    - Detailed reporting
    - Backup management
    """

    def __init__(self, logger: StructuredLogger, data_dir: Path = None):
        """
        Initialize file integrity monitor.
        
        Args:
            logger: Structured logger instance
            data_dir: Directory containing data files (defaults to 'data')
        """
        self.logger = logger
        self.data_dir = data_dir or Path("data")
        self.json_validator = JSONValidator(logger)
        
        # Critical files that must be valid for bot operation
        self.critical_files = [
            "quiz_state.json",
            "quiz_stats.json", 
            "playback_state.json",
            "bot_stats.json",
            "metadata_cache.json",
            "last_mecca_notification.json"
        ]
        
        # Optional files that can be recreated if corrupted
        self.optional_files = [
            "listening_stats.json",
            "recent_questions.json",
            "daily_verse_state.json",
            "rich_presence_state.json"
        ]
        
        self.monitoring_task = None
        self.is_monitoring = False
        
    async def startup_validation(self) -> bool:
        """
        Perform comprehensive validation during bot startup.
        
        Returns:
            True if all critical files are valid or were successfully repaired
        """
        log_perfect_tree_section(
            "File Integrity Monitor - Startup Validation",
            [
                ("status", "🔍 Checking JSON file integrity"),
                ("critical_files", len(self.critical_files)),
                ("optional_files", len(self.optional_files))
            ],
            "🛡️"
        )
        
        results = {
            "critical": await self._validate_files(self.critical_files, is_critical=True),
            "optional": await self._validate_files(self.optional_files, is_critical=False)
        }
        
        # Summary
        critical_valid = sum(1 for r in results["critical"] if r["valid"])
        critical_total = len(results["critical"])
        optional_valid = sum(1 for r in results["optional"] if r["valid"])
        optional_total = len(results["optional"])
        
        all_critical_valid = critical_valid == critical_total
        
        log_perfect_tree_section(
            "File Integrity Monitor - Validation Complete",
            [
                ("critical_files", f"{critical_valid}/{critical_total} valid"),
                ("optional_files", f"{optional_valid}/{optional_total} valid"),
                ("status", "✅ Ready" if all_critical_valid else "⚠️ Issues detected"),
                ("action", "Bot can start" if all_critical_valid else "Manual review needed")
            ],
            "✅" if all_critical_valid else "⚠️"
        )
        
        return all_critical_valid
        
    async def _validate_files(self, file_list: List[str], is_critical: bool) -> List[Dict[str, Any]]:
        """Validate a list of files"""
        results = []
        schemas = create_default_schemas()
        
        for filename in file_list:
            file_path = self.data_dir / filename
            result = await self._validate_single_file(file_path, schemas.get(filename, {}), is_critical)
            results.append(result)
            
        return results
        
    async def _validate_single_file(
        self, 
        file_path: Path, 
        default_schema: Dict[str, Any],
        is_critical: bool
    ) -> Dict[str, Any]:
        """Validate a single JSON file"""
        result = {
            "file_path": str(file_path),
            "filename": file_path.name,
            "valid": False,
            "action_taken": None,
            "error": None
        }
        
        try:
            # Check file integrity
            validation_result = self.json_validator.validate_json_file(file_path)
            
            if validation_result["valid"]:
                result["valid"] = True
                result["action_taken"] = "none_needed"
                
                log_perfect_tree_section(
                    f"File Validation - {file_path.name}",
                    [
                        ("status", "✅ Valid"),
                        ("size", f"{validation_result['size']} bytes")
                    ],
                    "✅"
                )
                
            else:
                # File is corrupted or missing
                error = validation_result.get("error", "Unknown error")
                result["error"] = error
                
                log_perfect_tree_section(
                    f"File Validation - {file_path.name}",
                    [
                        ("status", "❌ Invalid"),
                        ("error", error),
                        ("action", "Attempting repair")
                    ],
                    "🔧"
                )
                
                # Attempt repair
                if await self._repair_file(file_path, default_schema, is_critical):
                    result["valid"] = True
                    result["action_taken"] = "repaired"
                    
                    log_perfect_tree_section(
                        f"File Repair - {file_path.name}",
                        [
                            ("status", "✅ Repaired successfully"),
                            ("action", "File restored with defaults")
                        ],
                        "🔧"
                    )
                else:
                    result["action_taken"] = "repair_failed"
                    
                    log_perfect_tree_section(
                        f"File Repair - {file_path.name}",
                        [
                            ("status", "❌ Repair failed"),
                            ("critical", "Yes" if is_critical else "No")
                        ],
                        "❌"
                    )
                    
        except Exception as e:
            result["error"] = str(e)
            log_error_with_traceback(f"Error validating {file_path}", e)
            
        return result
        
    async def _repair_file(
        self, 
        file_path: Path, 
        default_schema: Dict[str, Any], 
        is_critical: bool
    ) -> bool:
        """Attempt to repair a corrupted file"""
        try:
            success = self.json_validator.repair_json_file(file_path, default_schema)
            
            if success:
                # Verify the repair worked
                validation_result = self.json_validator.validate_json_file(file_path)
                return validation_result["valid"]
                
            return False
            
        except Exception as e:
            log_error_with_traceback(f"Error repairing {file_path}", e)
            return False
            
    async def start_periodic_monitoring(self, interval_seconds: int = 300) -> None:
        """
        Start periodic file integrity monitoring.
        
        Args:
            interval_seconds: How often to check files (default: 5 minutes)
        """
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        
        log_perfect_tree_section(
            "File Integrity Monitor - Periodic Monitoring Started",
            [
                ("interval", f"{interval_seconds} seconds"),
                ("files_monitored", len(self.critical_files) + len(self.optional_files))
            ],
            "🔄"
        )
        
    async def stop_monitoring(self) -> None:
        """Stop periodic monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
                
        self.is_monitoring = False
        
        log_perfect_tree_section(
            "File Integrity Monitor - Monitoring Stopped",
            [("status", "✅ Monitoring stopped cleanly")],
            "🛑"
        )
        
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(interval_seconds)
                
                if not self.is_monitoring:
                    break
                    
                # Quick validation of critical files only
                critical_results = await self._validate_files(self.critical_files, is_critical=True)
                
                # Check if any critical files had issues
                issues = [r for r in critical_results if not r["valid"]]
                
                if issues:
                    log_perfect_tree_section(
                        "File Integrity Monitor - Issues Detected",
                        [
                            ("issues_found", len(issues)),
                            ("action", "Auto-repair attempted"),
                            ("time", datetime.now().strftime("%H:%M:%S"))
                        ],
                        "⚠️"
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error_with_traceback("Error in file monitoring loop", e)
                await asyncio.sleep(60)  # Wait before retrying
                
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            "is_monitoring": self.is_monitoring,
            "critical_files_count": len(self.critical_files),
            "optional_files_count": len(self.optional_files),
            "task_status": "running" if self.monitoring_task and not self.monitoring_task.done() else "stopped"
        }
        
    async def manual_check(self) -> Dict[str, Any]:
        """Perform manual integrity check"""
        log_perfect_tree_section(
            "File Integrity Monitor - Manual Check",
            [
                ("status", "🔍 Starting manual integrity check"),
                ("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ],
            "🔍"
        )
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "critical": await self._validate_files(self.critical_files, is_critical=True),
            "optional": await self._validate_files(self.optional_files, is_critical=False)
        }
        
        return results 