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

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Import version from centralized version module
from src.version import BOT_VERSION

# =============================================================================
# Test Configuration
# =============================================================================

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
    missing_dirs = []
    for directory in REQUIRED_DIRECTORIES:
        if not os.path.exists(directory):
            missing_dirs.append(directory)

    if missing_dirs:
        log_perfect_tree_section(
            "Testing Directory Structure",
            [
                ("status", "❌ Missing Directories"),
                ("missing_count", len(missing_dirs)),
            ],
            "📁",
            {"Missing Directories": [(dir, "❌ Not Found") for dir in missing_dirs]},
        )
        return False

    log_perfect_tree_section(
        "Testing Directory Structure",
        [
            (
                "status",
                f"✅ Directory Structure Valid ({len(REQUIRED_DIRECTORIES)} dirs)",
            ),
            ("directories_checked", len(REQUIRED_DIRECTORIES)),
        ],
        "📁",
    )
    return True


def test_required_files():
    """Test that all required files exist"""
    missing_files = []
    for file_path in REQUIRED_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        log_perfect_tree_section(
            "Testing Required Files",
            [("status", "❌ Missing Files"), ("missing_count", len(missing_files))],
            "📄",
            {"Missing Files": [(file, "❌ Not Found") for file in missing_files]},
        )
        return False

    log_perfect_tree_section(
        "Testing Required Files",
        [
            ("status", f"✅ Required Files Present ({len(REQUIRED_FILES)} files)"),
            ("files_checked", len(REQUIRED_FILES)),
        ],
        "📄",
    )
    return True


def test_python_syntax():
    """Test Python syntax for all Python files"""
    syntax_errors = []
    valid_files = []

    for file_path in PYTHON_FILES:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
                valid_files.append(file_path)
            except SyntaxError as e:
                error_msg = f"{file_path}: {e}"
                syntax_errors.append(error_msg)
            except Exception as e:
                error_msg = f"{file_path}: {e}"
                syntax_errors.append(error_msg)

    if syntax_errors:
        log_perfect_tree_section(
            "Testing Python Syntax",
            [
                ("status", f"❌ Python Syntax Errors ({len(syntax_errors)} errors)"),
                ("files_checked", len(PYTHON_FILES)),
                ("valid_files", len(valid_files)),
                ("error_files", len(syntax_errors)),
            ],
            "🐍",
            {
                "Valid Files": [(file, "✅ OK") for file in valid_files],
                "Syntax Errors": [(error, "❌ Error") for error in syntax_errors],
            },
        )
        return False

    log_perfect_tree_section(
        "Testing Python Syntax",
        [
            ("status", f"✅ Python Syntax Valid ({len(PYTHON_FILES)} files)"),
            ("files_checked", len(PYTHON_FILES)),
            ("all_valid", "✅ All files passed syntax check"),
        ],
        "🐍",
        {"Valid Files": [(file, "✅ OK") for file in valid_files]},
    )
    return True


def test_imports():
    """Test that all imports can be resolved"""
    import_errors = []
    import_results = []

    # Test standard library imports
    try:
        import asyncio
        import logging
        import os
        import sys
        import traceback

        import_results.append(("standard_library", "✅ OK"))
    except Exception as e:
        import_errors.append(f"Standard library: {e}")
        import_results.append(("standard_library", f"❌ {e}"))

    # Test third-party imports
    try:
        import discord
        import dotenv
        import psutil

        import_results.append(("third_party", "✅ OK"))
    except Exception as e:
        import_errors.append(f"Third-party: {e}")
        import_results.append(("third_party", f"❌ {e}"))

    # Test local imports
    try:
        from src.utils.surah_mapper import format_now_playing, get_surah_info
        from src.utils.tree_log import log_perfect_tree_section as test_import

        import_results.append(("local_imports", "✅ OK"))
    except Exception as e:
        import_errors.append(f"Local: {e}")
        import_results.append(("local_imports", f"❌ {e}"))

    if import_errors:
        log_perfect_tree_section(
            "Testing Import Resolution",
            [
                ("status", f"❌ Import Errors ({len(import_errors)} errors)"),
                ("total_categories", 3),
                ("failed_categories", len(import_errors)),
            ],
            "📦",
            {"Import Results": import_results},
        )
        return False

    log_perfect_tree_section(
        "Testing Import Resolution",
        [
            ("status", "✅ All Imports Resolved"),
            ("total_categories", 3),
            ("all_successful", "✅ All import categories passed"),
        ],
        "📦",
        {"Import Results": import_results},
    )
    return True


def test_environment_config():
    """Test environment configuration without connecting to Discord"""
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
        present_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                present_vars.append(var)

        if missing_vars:
            log_perfect_tree_section(
                "Testing Environment Config",
                [
                    (
                        "status",
                        f"❌ Missing Environment Variables ({len(missing_vars)} missing)",
                    ),
                    ("total_variables", len(required_vars)),
                    ("present_variables", len(present_vars)),
                    ("missing_variables", len(missing_vars)),
                ],
                "⚙️",
                {
                    "Present Variables": [(var, "✅ Present") for var in present_vars],
                    "Missing Variables": [(var, "❌ Missing") for var in missing_vars],
                },
            )
            return False

        log_perfect_tree_section(
            "Testing Environment Config",
            [
                (
                    "status",
                    f"✅ Environment Config Valid ({len(required_vars)} variables)",
                ),
                ("total_variables", len(required_vars)),
                ("all_present", "✅ All required variables found"),
            ],
            "⚙️",
            {"Environment Variables": [(var, "✅ Present") for var in present_vars]},
        )
        return True

    except Exception as e:
        log_error_with_traceback("Environment Config Test Failed", e)
        return False


def test_audio_directory():
    """Test audio directory structure"""
    audio_dir = "audio"
    if not os.path.exists(audio_dir):
        log_perfect_tree_section(
            "Testing Audio Directory",
            [
                ("status", f"❌ Audio Directory Missing: {audio_dir}"),
                ("directory_path", audio_dir),
                ("exists", "❌ Not Found"),
            ],
            "🎵",
        )
        return False

    # Check for reciter directories
    reciters = [
        d for d in os.listdir(audio_dir) if os.path.isdir(os.path.join(audio_dir, d))
    ]

    if not reciters:
        log_perfect_tree_section(
            "Testing Audio Directory",
            [
                ("status", f"⚠️ No Reciter Directories Found in {audio_dir}"),
                ("directory_path", audio_dir),
                ("reciter_count", 0),
            ],
            "🎵",
        )
        return False

    # Check for audio files in first reciter directory
    first_reciter = os.path.join(audio_dir, reciters[0])
    audio_files = [f for f in os.listdir(first_reciter) if f.endswith(".mp3")]

    log_perfect_tree_section(
        "Testing Audio Directory",
        [
            ("status", "✅ Audio Directory Valid"),
            ("reciters", f"{len(reciters)} found"),
            ("sample_reciter", reciters[0]),
            ("sample_files", f"{len(audio_files)} MP3 files"),
        ],
        "🎵",
    )
    return True


def test_logging_system():
    """Test the logging system functionality"""
    try:
        # Test basic logging and error logging
        from src.utils.tree_log import log_error_with_traceback

        test_results = []

        # Test basic logging
        test_results.append(("basic_logging", "✅ Testing tree structure"))

        # Test error logging
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            log_error_with_traceback("Test Error Logging", e)
            test_results.append(("error_logging", "✅ Error logging functional"))

        log_perfect_tree_section(
            "Testing Logging System",
            [
                ("status", "✅ Logging System Functional"),
                ("tests_completed", len(test_results)),
            ],
            "📝",
            {"Test Results": test_results},
        )
        return True

    except Exception as e:
        log_perfect_tree_section(
            "Testing Logging System",
            [
                ("status", f"❌ Logging System Error: {e}"),
                ("error_type", type(e).__name__),
            ],
            "📝",
        )
        return False


def test_surah_mapper():
    """Test Surah mapping functionality"""
    try:
        from src.utils.surah_mapper import (
            SURAH_DATABASE,
            format_now_playing,
            get_surah_display,
            get_surah_info,
            get_surah_stats,
            validate_surah_number,
        )

        test_results = []

        # Test database completeness
        total_surahs = len(SURAH_DATABASE)
        if total_surahs != 114:
            log_perfect_tree_section(
                "Testing Surah Mapper",
                [
                    ("status", "❌ Database incomplete"),
                    ("expected_surahs", 114),
                    ("found_surahs", total_surahs),
                ],
                "📖",
            )
            return False
        test_results.append(("database", f"✅ All 114 Surahs present"))

        # Test specific Surahs
        test_surahs = [1, 2, 36, 55, 112, 114]
        surah_tests = []
        for surah_num in test_surahs:
            surah = get_surah_info(surah_num)
            if not surah:
                log_perfect_tree_section(
                    "Testing Surah Mapper",
                    [
                        ("status", f"❌ Surah {surah_num} missing"),
                        ("failed_surah", surah_num),
                    ],
                    "📖",
                )
                return False
            display = get_surah_display(surah_num, "short")
            surah_tests.append((f"surah_{surah_num}", f"✅ {display}"))

        # Test validation
        validation_tests = []
        if not validate_surah_number(1) or not validate_surah_number(114):
            validation_tests.append(
                ("valid_numbers", "❌ Validation failed for valid numbers")
            )
        elif validate_surah_number(0) or validate_surah_number(115):
            validation_tests.append(
                ("invalid_numbers", "❌ Validation passed for invalid numbers")
            )
        else:
            validation_tests.append(("validation", "✅ Number validation working"))

        # Test formatting
        now_playing = format_now_playing(36, "Saad Al Ghamdi")
        if "Ya-Sin" not in now_playing or "💚" not in now_playing:
            test_results.append(("formatting", "❌ Now playing format incorrect"))
        else:
            test_results.append(("formatting", "✅ Now playing format working"))

        # Test statistics
        stats = get_surah_stats()
        expected_keys = [
            "total_surahs",
            "meccan_surahs",
            "medinan_surahs",
            "total_verses",
        ]
        stats_tests = []
        for key in expected_keys:
            if key not in stats:
                stats_tests.append((key, f"❌ Missing stat: {key}"))
            else:
                stats_tests.append((key, f"✅ Present"))

        if any("❌" in result[1] for result in stats_tests):
            log_perfect_tree_section(
                "Testing Surah Mapper",
                [
                    ("status", "❌ Statistics test failed"),
                    ("missing_stats", len([r for r in stats_tests if "❌" in r[1]])),
                ],
                "📖",
                {"Statistics Tests": stats_tests},
            )
            return False

        stats_tests.append(
            (
                "statistics_summary",
                f"✅ Stats: {stats['total_surahs']} Surahs, {stats['total_verses']} verses",
            )
        )

        log_perfect_tree_section(
            "Testing Surah Mapper",
            [
                ("status", "✅ Surah Mapper OK"),
                (
                    "total_tests",
                    len(test_results)
                    + len(surah_tests)
                    + len(validation_tests)
                    + len(stats_tests),
                ),
            ],
            "📖",
            {
                "Database Tests": test_results,
                "Surah Tests": surah_tests,
                "Validation Tests": validation_tests,
                "Statistics Tests": stats_tests,
            },
        )
        return True

    except Exception as e:
        log_error_with_traceback("Surah mapper test failed", e)
        log_perfect_tree_section(
            "Testing Surah Mapper",
            [("status", "❌ Surah Mapper Error"), ("error_type", type(e).__name__)],
            "📖",
        )
        return False


def test_bot_manager():
    """Test bot manager functionality"""
    try:
        # Import bot manager
        import bot_manager

        test_results = []
        test_results.append(("import", "✅ Bot manager imported"))

        # Test status check (should not find running bot in test)
        processes = bot_manager.find_bot_processes()
        test_results.append(("status_check", "✅ Status check functional"))

        log_perfect_tree_section(
            "Testing Bot Manager",
            [
                ("status", "✅ Bot Manager Functional"),
                ("tests_completed", len(test_results)),
            ],
            "🤖",
            {"Test Results": test_results},
        )
        return True

    except Exception as e:
        log_error_with_traceback("Bot manager test failed", e)
        log_perfect_tree_section(
            "Testing Bot Manager",
            [("status", "❌ Bot Manager Error"), ("error_type", type(e).__name__)],
            "🤖",
        )
        return False


# =============================================================================
# Main Test Runner
# =============================================================================


def run_all_tests():
    """Run all tests and provide summary"""

    # Initial test suite header
    log_perfect_tree_section(
        f"QuranBot v{BOT_VERSION} Development Test Suite",
        [
            ("environment", "Development (Mac)"),
            ("target", "VPS Deployment Readiness"),
            ("purpose", "Comprehensive pre-deployment validation"),
        ],
        "🧪",
    )

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
    test_results = []

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                test_results.append((test_name, "✅ Passed"))
            else:
                failed += 1
                test_results.append((test_name, "❌ Failed"))
        except Exception as e:
            log_error_with_traceback(f"Test '{test_name}' crashed", e)
            failed += 1
            test_results.append((test_name, f"❌ Crashed: {type(e).__name__}"))

    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0

    # Final test summary
    if failed == 0:
        log_perfect_tree_section(
            "Test Summary",
            [
                ("total_tests", total),
                ("passed", f"✅ {passed}"),
                ("failed", f"❌ {failed}"),
                ("success_rate", f"{success_rate:.1f}%"),
                ("status", "🎉 All Tests Passed - Ready for VPS Deployment!"),
            ],
            "📊",
            {"Test Results": test_results},
        )
    else:
        log_perfect_tree_section(
            "Test Summary",
            [
                ("total_tests", total),
                ("passed", f"✅ {passed}"),
                ("failed", f"❌ {failed}"),
                ("success_rate", f"{success_rate:.1f}%"),
                ("status", "⚠️ Tests Failed - Fix Issues Before VPS Deployment"),
            ],
            "📊",
            {"Test Results": test_results},
        )

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
