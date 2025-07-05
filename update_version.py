# =============================================================================
# QuranBot - Version Update Helper
# =============================================================================
# Script to help update bot version and maintain changelog
# =============================================================================

import re
from datetime import datetime

def update_bot_version(new_version):
    """Update the version in bot.py"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update version constant
    updated_content = re.sub(
        r'BOT_VERSION = "[^"]*"',
        f'BOT_VERSION = "{new_version}"',
        content
    )
    
    with open('bot.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"✅ Updated bot.py version to {new_version}")

def add_changelog_entry(version, changes):
    """Add a new entry to CHANGELOG.md"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the [Unreleased] section and add new version after it
    new_entry = f"\n## [{version}] - {today}\n\n{changes}\n"
    
    updated_content = content.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n{new_entry}"
    )
    
    with open('CHANGELOG.md', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"✅ Added changelog entry for version {version}")

def main():
    """Interactive version update"""
    print("🔄 QuranBot Version Update Tool")
    print("=" * 40)
    
    current_version = input("Enter new version (e.g., 1.1.0): ").strip()
    
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
    
    print(f"\nUpdating to version {current_version}...")
    update_bot_version(current_version)
    add_changelog_entry(current_version, changelog_text)
    
    print(f"\n✅ Version {current_version} update complete!")
    print("📝 Remember to commit your changes!")

if __name__ == "__main__":
    main() 