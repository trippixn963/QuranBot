# =============================================================================
# QuranBot - Version Update Helper
# =============================================================================
# Script to help update bot version and maintain changelog
# =============================================================================

import os
import re
import sys
import traceback
from datetime import datetime

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_section_start,
    log_tree_branch,
    log_tree_final,
)


def update_bot_version(new_version):
    """Update the version in bot.py"""
    try:
        log_section_start("Version Update", "🔄")

        if not os.path.exists("src/bot/main.py"):
            log_tree_branch("bot_file_check", "❌ src/bot/main.py not found")
            return False

        with open("src/bot/main.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Update version constant
        updated_content = re.sub(
            r'BOT_VERSION = "[^"]*"', f'BOT_VERSION = "{new_version}"', content
        )

        with open("src/bot/main.py", "w", encoding="utf-8") as f:
            f.write(updated_content)

        log_tree_branch("version_update", f"✅ Updated to {new_version}")
        return True

    except Exception as e:
        log_error_with_traceback("Failed to update bot version", e)
        return False


def add_changelog_entry(version, changes):
    """Add a new entry to CHANGELOG.md"""
    try:
        log_section_start("Changelog Update", "📝")

        if not os.path.exists("CHANGELOG.md"):
            log_tree_branch("changelog_check", "❌ CHANGELOG.md not found")
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()

        # Find the [Unreleased] section and add new version after it
        new_entry = f"\n## [{version}] - {today}\n\n{changes}\n"

        updated_content = content.replace(
            "## [Unreleased]", f"## [Unreleased]\n{new_entry}"
        )

        with open("CHANGELOG.md", "w", encoding="utf-8") as f:
            f.write(updated_content)

        log_tree_branch("changelog_update", f"✅ Added entry for {version}")
        return True

    except Exception as e:
        log_error_with_traceback("Failed to update changelog", e)
        return False


def main():
    """Interactive version update"""
    try:
        log_section_start("QuranBot Version Update Tool", "🚀")

        current_version = input("Enter new version (e.g., 1.1.0): ").strip()

        if not current_version:
            log_tree_branch("version_input", "❌ No version provided")
            return False

        log_tree_branch("target_version", current_version)

        print("\nEnter changelog entries (press Enter twice to finish):")
        print("Format: ### Added/Changed/Fixed")
        print("- Description of change")

        changes = []
        while True:
            line = input()
            if line == "" and changes:
                break
            changes.append(line)

        changelog_text = "\n".join(changes)

        log_section_start("Processing Updates", "⚙️")

        # Update version
        version_success = update_bot_version(current_version)

        # Update changelog
        changelog_success = add_changelog_entry(current_version, changelog_text)

        if version_success and changelog_success:
            log_section_start("Update Complete", "✅")
            log_tree_branch("version", f"Updated to {current_version}")
            log_tree_branch("changelog", "Updated with new entries")
            log_tree_final("next_steps", "Remember to commit your changes!")
            return True
        else:
            log_critical_error("Version update failed - check errors above")
            return False

    except KeyboardInterrupt:
        log_tree_branch("user_action", "❌ Cancelled by user")
        return False
    except Exception as e:
        log_critical_error("Fatal error in version update tool", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
