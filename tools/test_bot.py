#!/usr/bin/env python3
# =============================================================================
# QuranBot Development Test Suite
# =============================================================================
# Comprehensive testing for development environment before VPS deployment
# =============================================================================

import ast
import importlib.util
import os
import sys
import traceback
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.tree_log import (
    log_error_with_traceback,
    log_section_start,
    log_tree_branch,
    log_tree_final,
)

# =============================================================================
# Test Configuration
# =============================================================================

BOT_VERSION = "1.3.0"
REQUIRED_FILES = [
    "main.py",
    "bot_manager.py",
    "src/bot/main.py",
    "src/utils/tree_log.py",
    "src/utils/surah_mapper.py",
    "config/.env",
    "requirements.txt",
]

REQUIRED_DIRECTORIES = ["src", "src/bot", "src/utils", "config", "audio"]

PYTHON_FILES = [
    "main.py",
    "bot_manager.py",
    "src/bot/main.py",
    "src/utils/tree_log.py",
    "src/utils/surah_mapper.py",
    "tools/test_bot.py",
]

# =============================================================================
# Test Functions
# =============================================================================


def test_directory_structure():
    """Test that all required directories exist"""
    log_section_start("Testing Directory Structure", "📁")

    missing_dirs = []
    for directory in REQUIRED_DIRECTORIES:
        if not os.path.exists(directory):
            missing_dirs.append(directory)

    if missing_dirs:
        log_tree_branch("status", "❌ Missing Directories")
        for missing in missing_dirs:
            log_tree_branch("missing", missing)
        return False

    log_tree_final(
        "status", f"✅ Directory Structure Valid ({len(REQUIRED_DIRECTORIES)} dirs)"
    )
    return True


def test_required_files():
    """Test that all required files exist"""
    log_section_start("Testing Required Files", "📄")

    missing_files = []
    for file_path in REQUIRED_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        log_tree_branch("status", "❌ Missing Files")
        for missing in missing_files:
            log_tree_branch("missing", missing)
        return False

    log_tree_final("status", f"✅ Required Files Present ({len(REQUIRED_FILES)} files)")
    return True


def test_python_syntax():
    """Test Python syntax for all Python files"""
    log_section_start("Testing Python Syntax", "🐍")

    syntax_errors = []
    for file_path in PYTHON_FILES:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
                log_tree_branch("checked", f"✅ {file_path}")
            except SyntaxError as e:
                error_msg = f"{file_path}: {e}"
                syntax_errors.append(error_msg)
                log_tree_branch("error", f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"{file_path}: {e}"
                syntax_errors.append(error_msg)
                log_tree_branch("error", f"❌ {error_msg}")

    if syntax_errors:
        log_tree_final(
            "status", f"❌ Python Syntax Errors ({len(syntax_errors)} errors)"
        )
        return False

    log_tree_final("status", f"✅ Python Syntax Valid ({len(PYTHON_FILES)} files)")
    return True


def test_imports():
    """Test that all imports can be resolved"""
    log_section_start("Testing Import Resolution", "📦")

    import_errors = []

    # Test standard library imports
    try:
        import asyncio
        import logging
        import os
        import sys
        import traceback

        log_tree_branch("standard_library", "✅ OK")
    except Exception as e:
        import_errors.append(f"Standard library: {e}")
        log_tree_branch("standard_library", f"❌ {e}")

    # Test third-party imports
    try:
        import discord
        import dotenv
        import psutil

        log_tree_branch("third_party", "✅ OK")
    except Exception as e:
        import_errors.append(f"Third-party: {e}")
        log_tree_branch("third_party", f"❌ {e}")

    # Test local imports
    try:
        from src.utils.surah_mapper import format_now_playing, get_surah_info
        from src.utils.tree_log import log_tree_branch as test_import

        log_tree_branch("local_imports", "✅ OK")
    except Exception as e:
        import_errors.append(f"Local: {e}")
        log_tree_branch("local_imports", f"❌ {e}")

    if import_errors:
        log_tree_final("status", f"❌ Import Errors ({len(import_errors)} errors)")
        return False

    log_tree_final("status", "✅ All Imports Resolved")
    return True


def test_environment_config():
    """Test environment configuration without connecting to Discord"""
    log_section_start("Testing Environment Config", "⚙️")

    try:
        from dotenv import load_dotenv

        load_dotenv("config/.env")

        required_vars = [
            "DISCORD_TOKEN",
            "GUILD_ID",
            "TARGET_CHANNEL_ID",
            "ADMIN_USER_ID",
        ]
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
                log_tree_branch(var, "❌ Missing")
            else:
                log_tree_branch(var, "✅ Present")

        if missing_vars:
            log_tree_final(
                "status",
                f"❌ Missing Environment Variables ({len(missing_vars)} missing)",
            )
            return False

        log_tree_final(
            "status", f"✅ Environment Config Valid ({len(required_vars)} variables)"
        )
        return True

    except Exception as e:
        log_error_with_traceback("Environment Config Test Failed", e)
        return False


def test_audio_directory():
    """Test audio directory structure"""
    log_section_start("Testing Audio Directory", "🎵")

    audio_dir = "audio"
    if not os.path.exists(audio_dir):
        log_tree_final("status", f"❌ Audio Directory Missing: {audio_dir}")
        return False

    # Check for reciter directories
    reciters = [
        d for d in os.listdir(audio_dir) if os.path.isdir(os.path.join(audio_dir, d))
    ]

    if not reciters:
        log_tree_final("status", f"⚠️ No Reciter Directories Found in {audio_dir}")
        return False

    # Check for audio files in first reciter directory
    first_reciter = os.path.join(audio_dir, reciters[0])
    audio_files = [f for f in os.listdir(first_reciter) if f.endswith(".mp3")]

    log_tree_branch("reciters", f"{len(reciters)} found")
    log_tree_branch("sample_reciter", reciters[0])
    log_tree_branch("sample_files", f"{len(audio_files)} MP3 files")
    log_tree_final("status", "✅ Audio Directory Valid")
    return True


def test_logging_system():
    """Test the logging system functionality"""
    log_section_start("Testing Logging System", "📝")

    try:
        # Test basic logging
        log_tree_branch("basic_logging", "✅ Testing tree structure")

        # Test error logging
        from src.utils.tree_log import log_error_with_traceback

        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            log_error_with_traceback("Test Error Logging", e)

        log_tree_final("status", "✅ Logging System Functional")
        return True

    except Exception as e:
        print(f"❌ Logging System Error: {e}")
        return False


def test_surah_mapper():
    """Test Surah mapping functionality"""
    log_section_start("Testing Surah Mapper", "📖")

    try:
        from src.utils.surah_mapper import (
            SURAH_DATABASE,
            format_now_playing,
            get_surah_display,
            get_surah_info,
            get_surah_stats,
            validate_surah_number,
        )

        # Test database completeness
        total_surahs = len(SURAH_DATABASE)
        if total_surahs != 114:
            log_tree_branch("database", f"❌ Expected 114 Surahs, found {total_surahs}")
            return False
        log_tree_branch("database", f"✅ All 114 Surahs present")

        # Test specific Surahs
        test_surahs = [1, 2, 36, 55, 112, 114]
        for surah_num in test_surahs:
            surah = get_surah_info(surah_num)
            if not surah:
                log_tree_branch("surah_info", f"❌ Surah {surah_num} missing")
                return False
            display = get_surah_display(surah_num, "short")
            log_tree_branch(f"surah_{surah_num}", f"✅ {display}")

        # Test validation
        if not validate_surah_number(1) or not validate_surah_number(114):
            log_tree_branch("validation", "❌ Validation failed for valid numbers")
            return False
        if validate_surah_number(0) or validate_surah_number(115):
            log_tree_branch("validation", "❌ Validation passed for invalid numbers")
            return False
        log_tree_branch("validation", "✅ Number validation working")

        # Test formatting
        now_playing = format_now_playing(36, "Saad Al Ghamdi")
        if "Ya-Sin" not in now_playing or "💚" not in now_playing:
            log_tree_branch("formatting", "❌ Now playing format incorrect")
            return False
        log_tree_branch("formatting", "✅ Now playing format working")

        # Test statistics
        stats = get_surah_stats()
        expected_keys = [
            "total_surahs",
            "meccan_surahs",
            "medinan_surahs",
            "total_verses",
        ]
        for key in expected_keys:
            if key not in stats:
                log_tree_branch("statistics", f"❌ Missing stat: {key}")
                return False
        log_tree_branch(
            "statistics",
            f"✅ Stats: {stats['total_surahs']} Surahs, {stats['total_verses']} verses",
        )

        log_tree_final("status", "✅ Surah Mapper OK")
        return True

    except Exception as e:
        log_error_with_traceback("Surah mapper test failed", e)
        log_tree_final("status", "❌ Surah Mapper Error")
        return False


def test_bot_manager():
    """Test bot manager functionality"""
    log_section_start("Testing Bot Manager", "🤖")

    try:
        # Import bot manager
        import bot_manager

        log_tree_branch("import", "✅ Bot manager imported")

        # Test status check (should not find running bot in test)
        processes = bot_manager.find_bot_processes()
        log_tree_branch("status_check", "✅ Status check functional")

        log_tree_final("status", "✅ Bot Manager Functional")
        return True

    except Exception as e:
        log_error_with_traceback("Bot Manager Test Failed", e)
        return False


# =============================================================================
# Main Test Runner
# =============================================================================


def run_all_tests():
    """Run all tests and provide summary"""

    log_section_start(f"QuranBot v{BOT_VERSION} Development Test Suite", "🧪")
    log_tree_branch("environment", "Development (Mac)")
    log_tree_branch("target", "VPS Deployment Readiness")
    log_tree_final("purpose", "Comprehensive pre-deployment validation")

    tests = [
        ("Directory Structure", test_directory_structure),
        ("Required Files", test_required_files),
        ("Python Syntax", test_python_syntax),
        ("Import Resolution", test_imports),
        ("Environment Config", test_environment_config),
        ("Audio Directory", test_audio_directory),
        ("Logging System", test_logging_system),
        ("Surah Mapper", test_surah_mapper),
        ("Bot Manager", test_bot_manager),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_error_with_traceback(f"Test '{test_name}' crashed", e)
            failed += 1

    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0

    log_section_start("Test Summary", "📊")
    log_tree_branch("total_tests", total)
    log_tree_branch("passed", f"✅ {passed}")
    log_tree_branch("failed", f"❌ {failed}")
    log_tree_branch("success_rate", f"{success_rate:.1f}%")

    if failed == 0:
        log_tree_final("status", "🎉 All Tests Passed - Ready for VPS Deployment!")
    else:
        log_tree_final("status", "⚠️ Tests Failed - Fix Issues Before VPS Deployment")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
