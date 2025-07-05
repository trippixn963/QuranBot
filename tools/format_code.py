# =============================================================================
# QuranBot - Code Formatting Utility
# =============================================================================
# Utility script to format entire codebase with Black and organize imports
# Maintains consistent code style across all Python files
# =============================================================================

import os
import subprocess
import sys
import traceback
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_section_start,
    log_tree_branch,
    log_tree_final,
)

BOT_NAME = "QuranBot Code Formatter"
PYTHON_FILES = [
    "main.py",
    "bot_manager.py",
    "tools/update_version.py",
    "tools/format_code.py",
    "tools/test_bot.py",
    "tools/deploy_to_vps.py",
    "src/bot/main.py",
    "src/utils/tree_log.py",
    "src/__init__.py",
    "src/bot/__init__.py",
    "src/config/__init__.py",
    "src/utils/__init__.py",
]


def check_formatter_availability():
    """Check if Black and isort are installed and available"""
    log_section_start("Formatter Availability Check", "🔧")

    try:
        # Check Black
        result = subprocess.run(
            ["black", "--version"], capture_output=True, text=True, check=True
        )
        log_tree_branch("black_version", result.stdout.strip())

        # Check isort
        result = subprocess.run(
            ["isort", "--version"], capture_output=True, text=True, check=True
        )
        log_tree_branch("isort_version", result.stdout.strip())

        log_tree_final("status", "✅ All formatters available")
        return True

    except subprocess.CalledProcessError as e:
        log_error_with_traceback("Formatter check failed", e)
        return False
    except FileNotFoundError as e:
        log_critical_error("Formatters not installed - run: pip install black isort", e)
        return False
    except Exception as e:
        log_error_with_traceback("Unexpected error checking formatters", e)
        return False


def format_python_files():
    """Format all Python files with Black and organize imports with isort"""
    log_section_start("Code Formatting", "🎨")

    formatted_count = 0
    error_count = 0

    # Change to project root directory
    original_dir = os.getcwd()
    project_root = os.path.join(os.path.dirname(__file__), "..")
    os.chdir(project_root)

    try:
        for file_path in PYTHON_FILES:
            try:
                if not os.path.exists(file_path):
                    log_tree_branch("skipped", f"File not found: {file_path}")
                    continue

                log_tree_branch("formatting", file_path)

                # Format with Black
                try:
                    subprocess.run(
                        ["black", "--line-length=88", file_path],
                        check=True,
                        capture_output=True,
                    )
                    log_tree_branch("black_result", "✅ Formatted")
                except subprocess.CalledProcessError as e:
                    log_error_with_traceback(
                        f"Black formatting failed for {file_path}", e
                    )
                    error_count += 1
                    continue

                # Organize imports with isort
                try:
                    subprocess.run(
                        ["isort", "--profile=black", file_path],
                        check=True,
                        capture_output=True,
                    )
                    log_tree_branch("isort_result", "✅ Imports organized")
                except subprocess.CalledProcessError as e:
                    log_error_with_traceback(
                        f"Import organization failed for {file_path}", e
                    )
                    error_count += 1
                    continue

                formatted_count += 1

            except Exception as e:
                log_error_with_traceback(f"Unexpected error formatting {file_path}", e)
                error_count += 1

        # Report results
        log_tree_branch("files_formatted", formatted_count)
        log_tree_branch("errors", error_count)

        if error_count == 0:
            log_tree_final("status", "✅ All files formatted successfully")
            return True
        else:
            log_tree_final("status", f"⚠️ Completed with {error_count} errors")
            return False
    finally:
        # Change back to original directory
        os.chdir(original_dir)


def main():
    """Main function to run code formatting"""
    try:
        log_section_start(f"{BOT_NAME} Started", "🚀")

        # Check if formatters are available
        if not check_formatter_availability():
            log_critical_error("Cannot proceed without formatters installed")
            return False

        # Format all Python files
        success = format_python_files()

        if success:
            log_section_start("Formatting Complete", "🎉")
            log_tree_branch("result", "All Python files formatted consistently")
            log_tree_final("next_steps", "Code is now ready for development")

        return success

    except Exception as e:
        log_critical_error("Fatal error in code formatter", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
