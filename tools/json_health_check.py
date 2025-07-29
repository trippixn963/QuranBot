#!/usr/bin/env python3
# =============================================================================
# QuranBot - JSON Health Check Tool
# =============================================================================
# Standalone tool for checking and repairing JSON file corruption
# Can be run independently or integrated into maintenance scripts
# =============================================================================

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.json_validator import JSONValidator, create_default_schemas, validate_quiz_state, validate_quiz_stats
from src.core.structured_logger import StructuredLogger


def setup_logger():
    """Setup simple logger for the health check tool"""
    import logging
    
    # Create simple logger instead of async StructuredLogger
    logger = logging.getLogger("json_health_check")
    logger.setLevel(logging.INFO)
    
    # Simple mock logger for the JSONValidator
    class MockLogger:
        def debug(self, msg, context=None):
            pass
        def info(self, msg, context=None):
            print(f"[INFO] {msg}")
        def warning(self, msg, context=None):
            print(f"[WARNING] {msg}")
        def error(self, msg, context=None):
            print(f"[ERROR] {msg}")
    
    return MockLogger()


def print_banner():
    """Print tool banner"""
    print("=" * 70)
    print("🛡️  QURANBOT JSON HEALTH CHECK TOOL")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def check_all_files(data_dir: Path, repair: bool = False) -> dict:
    """Check all JSON files in data directory"""
    logger = setup_logger()
    json_validator = JSONValidator(logger)
    schemas = create_default_schemas()
    
    # All known JSON files
    known_files = [
        # Critical files
        "quiz_state.json",
        "quiz_stats.json", 
        "playback_state.json",
        "bot_stats.json",
        "metadata_cache.json",
        "last_mecca_notification.json",
        # Optional files
        "listening_stats.json",
        "recent_questions.json",
        "daily_verse_state.json",
        "rich_presence_state.json",
        "conversation_memory.json",
        "mecca_prayer_cache.json",
        "user_cache.json"
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_files": 0,
        "valid_files": 0,
        "corrupted_files": 0,
        "missing_files": 0,
        "repaired_files": 0,
        "details": []
    }
    
    print("🔍 Checking JSON file integrity...")
    print()
    
    for filename in known_files:
        file_path = data_dir / filename
        file_result = {
            "filename": filename,
            "path": str(file_path),
            "exists": file_path.exists(),
            "valid": False,
            "size": 0,
            "error": None,
            "action": "none"
        }
        
        results["total_files"] += 1
        
        if not file_path.exists():
            print(f"❓ {filename:<30} - Missing")
            file_result["error"] = "File does not exist"
            results["missing_files"] += 1
        else:
            # Validate file
            validation_result = json_validator.validate_json_file(file_path)
            file_result.update(validation_result)
            
            if validation_result["valid"]:
                print(f"✅ {filename:<30} - Valid ({validation_result['size']} bytes)")
                results["valid_files"] += 1
            else:
                print(f"❌ {filename:<30} - {validation_result['error']}")
                results["corrupted_files"] += 1
                
                # Attempt repair if requested
                if repair:
                    default_data = schemas.get(filename, {})
                    if json_validator.repair_json_file(file_path, default_data):
                        print(f"🔧 {filename:<30} - Repaired successfully")
                        file_result["action"] = "repaired"
                        results["repaired_files"] += 1
                        results["valid_files"] += 1
                        results["corrupted_files"] -= 1
                    else:
                        print(f"💥 {filename:<30} - Repair failed")
                        file_result["action"] = "repair_failed"
        
        results["details"].append(file_result)
    
    print()
    return results


def check_specific_file(file_path: Path, repair: bool = False) -> dict:
    """Check a specific JSON file"""
    logger = setup_logger()
    json_validator = JSONValidator(logger)
    schemas = create_default_schemas()
    
    print(f"🔍 Checking file: {file_path}")
    print()
    
    if not file_path.exists():
        print("❌ File does not exist")
        return {"valid": False, "error": "File does not exist"}
    
    # Validate file
    result = json_validator.validate_json_file(file_path)
    
    if result["valid"]:
        print(f"✅ File is valid ({result['size']} bytes)")
        print(f"📅 Last modified: {result['last_modified']}")
    else:
        print(f"❌ File is invalid: {result['error']}")
        
        if repair:
            print("🔧 Attempting repair...")
            filename = file_path.name
            default_data = schemas.get(filename, {})
            
            if json_validator.repair_json_file(file_path, default_data):
                print("✅ File repaired successfully")
                result["action"] = "repaired"
            else:
                print("❌ Repair failed")
                result["action"] = "repair_failed"
    
    print()
    return result


def validate_quiz_files(data_dir: Path) -> dict:
    """Perform specific validation on quiz-related files"""
    logger = setup_logger()
    json_validator = JSONValidator(logger)
    
    print("🎯 Performing specific quiz file validation...")
    print()
    
    results = {}
    
    # Validate quiz_state.json
    quiz_state_path = data_dir / "quiz_state.json"
    if quiz_state_path.exists():
        try:
            data = json_validator.safe_read_json(quiz_state_path, validator=validate_quiz_state)
            interval = data.get("schedule_config", {}).get("send_interval_hours", 0)
            print(f"✅ quiz_state.json - Valid (interval: {interval} hours)")
            results["quiz_state"] = {"valid": True, "interval": interval}
        except Exception as e:
            print(f"❌ quiz_state.json - Invalid: {e}")
            results["quiz_state"] = {"valid": False, "error": str(e)}
    else:
        print("❓ quiz_state.json - Missing")
        results["quiz_state"] = {"valid": False, "error": "Missing"}
    
    # Validate quiz_stats.json
    quiz_stats_path = data_dir / "quiz_stats.json"
    if quiz_stats_path.exists():
        try:
            data = json_validator.safe_read_json(quiz_stats_path, validator=validate_quiz_stats)
            stats = {
                "questions_sent": data.get("questions_sent", 0),
                "correct_answers": data.get("correct_answers", 0),
                "total_attempts": data.get("total_attempts", 0)
            }
            print(f"✅ quiz_stats.json - Valid (questions: {stats['questions_sent']}, correct: {stats['correct_answers']})")
            results["quiz_stats"] = {"valid": True, "stats": stats}
        except Exception as e:
            print(f"❌ quiz_stats.json - Invalid: {e}")
            results["quiz_stats"] = {"valid": False, "error": str(e)}
    else:
        print("❓ quiz_stats.json - Missing")
        results["quiz_stats"] = {"valid": False, "error": "Missing"}
    
    print()
    return results


def print_summary(results: dict):
    """Print summary of health check results"""
    print("=" * 50)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 50)
    print(f"📂 Total files checked: {results['total_files']}")
    print(f"✅ Valid files: {results['valid_files']}")
    print(f"❌ Corrupted files: {results['corrupted_files']}")
    print(f"❓ Missing files: {results['missing_files']}")
    if results.get('repaired_files', 0) > 0:
        print(f"🔧 Repaired files: {results['repaired_files']}")
    
    health_percentage = (results['valid_files'] / results['total_files']) * 100 if results['total_files'] > 0 else 0
    print(f"💪 Overall health: {health_percentage:.1f}%")
    
    if health_percentage == 100:
        print("🎉 All files are healthy!")
    elif health_percentage >= 90:
        print("✅ File system is in good health")
    elif health_percentage >= 70:
        print("⚠️  Some issues detected - consider running with --repair")
    else:
        print("🚨 Multiple issues detected - repair recommended")
    
    print("=" * 50)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="QuranBot JSON Health Check Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/json_health_check.py                    # Check all files
  python tools/json_health_check.py --repair           # Check and repair files
  python tools/json_health_check.py --file quiz_state.json  # Check specific file
  python tools/json_health_check.py --quiz             # Validate quiz files specifically
        """
    )
    
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory path (default: data)"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="Check specific file instead of all files"
    )
    
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Attempt to repair corrupted files"
    )
    
    parser.add_argument(
        "--quiz",
        action="store_true",
        help="Perform specific quiz file validation"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    if not args.json:
        print_banner()
    
    # Ensure data directory exists
    args.data_dir.mkdir(exist_ok=True)
    
    try:
        if args.file:
            # Check specific file
            file_path = args.data_dir / args.file
            result = check_specific_file(file_path, repair=args.repair)
            if args.json:
                print(json.dumps(result, indent=2))
        elif args.quiz:
            # Quiz-specific validation
            result = validate_quiz_files(args.data_dir)
            if args.json:
                print(json.dumps(result, indent=2))
        else:
            # Check all files
            results = check_all_files(args.data_dir, repair=args.repair)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print_summary(results)
                
                # Exit with error code if issues found
                if results['corrupted_files'] > 0 or results['missing_files'] > 0:
                    sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 