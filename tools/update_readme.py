#!/usr/bin/env python3
# =============================================================================
# QuranBot - README Update Utility
# =============================================================================
# Automatically sync README version history with CHANGELOG.md
# Usage: python tools/update_readme.py
# =============================================================================

import argparse
import re
import sys
from pathlib import Path


def extract_changelog_features(version):
    """Extract features from CHANGELOG.md for a specific version"""
    try:
        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()

        # Find the version section
        version_pattern = rf"## \[{re.escape(version)}\]"
        match = re.search(version_pattern, content)
        if not match:
            return []

        # Extract content until next version or end
        start_pos = match.end()
        next_version_match = re.search(r"## \[[\d.]+\]", content[start_pos:])
        if next_version_match:
            end_pos = start_pos + next_version_match.start()
            section_content = content[start_pos:end_pos]
        else:
            section_content = content[start_pos:]

        # Extract features from Added and Enhanced sections
        features = []

        # Look for Added section
        added_match = re.search(
            r"### Added\s*\n(.*?)(?=###|\Z)", section_content, re.DOTALL
        )
        if added_match:
            added_content = added_match.group(1)
            # Extract bullet points
            bullet_matches = re.findall(
                r"- \*\*(.*?)\*\*: (.*?)(?=\n- |\n\n|\Z)", added_content, re.DOTALL
            )
            for title, description in bullet_matches:
                clean_title = title.strip()
                clean_desc = description.strip().replace("\n", " ")
                features.append(f"{clean_title}: {clean_desc}")

        # Look for Enhanced section
        enhanced_match = re.search(
            r"### Enhanced\s*\n(.*?)(?=###|\Z)", section_content, re.DOTALL
        )
        if enhanced_match:
            enhanced_content = enhanced_match.group(1)
            # Extract bullet points
            bullet_matches = re.findall(
                r"- \*\*(.*?)\*\*: (.*?)(?=\n- |\n\n|\Z)", enhanced_content, re.DOTALL
            )
            for title, description in bullet_matches:
                clean_title = title.strip()
                clean_desc = description.strip().replace("\n", " ")
                features.append(f"{clean_title}: {clean_desc}")

        return features[:9]  # Limit to 9 features

    except Exception as e:
        print(f"Error extracting changelog features: {e}")
        return []


def update_readme_version_history():
    """Update README version history from CHANGELOG.md"""
    project_root = Path(__file__).parent.parent
    readme_file = project_root / "README.md"
    changelog_file = project_root / "CHANGELOG.md"

    if not readme_file.exists():
        print(f"❌ README file not found: {readme_file}")
        return False

    if not changelog_file.exists():
        print(f"❌ CHANGELOG file not found: {changelog_file}")
        return False

    # Read files
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_content = f.read()

    with open(changelog_file, "r", encoding="utf-8") as f:
        changelog_content = f.read()

    # Extract version information from changelog
    version_pattern = r"## \[(\d+\.\d+\.\d+)\]"
    versions = re.findall(version_pattern, changelog_content)

    if not versions:
        print("❌ No versions found in CHANGELOG.md")
        return False

    print(f"📋 Found {len(versions)} versions in CHANGELOG.md")

    # Build new version history section
    version_history = []

    for i, version in enumerate(versions[:5]):  # Show latest 5 versions
        features = extract_changelog_features(version)

        if i == 0:
            version_history.append(f"### v{version} (Latest)")
        else:
            version_history.append(f"### v{version}")

        # Add features with proper formatting
        for feature in features:
            # Remove any duplicate emoji prefix and format properly
            clean_feature = feature.replace("🎯 ", "").replace("**", "").strip()
            version_history.append(f"- **{clean_feature}**")

        version_history.append("")  # Empty line between versions

        print(f"  ✅ v{version}: {len(features)} features extracted")

    # Remove last empty line
    if version_history and version_history[-1] == "":
        version_history.pop()

    new_version_section = "\n".join(version_history)

    # Find and replace the version history section
    version_history_pattern = r"## 📋 Version History\n\n.*?(?=\n## [^📋]|\n### 📁|\Z)"
    replacement = f"## 📋 Version History\n\n{new_version_section}\n"

    new_readme_content = re.sub(
        version_history_pattern, replacement, readme_content, flags=re.DOTALL
    )

    if new_readme_content == readme_content:
        print("⚠️ No changes needed in README version history")
        return True

    # Write updated README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_readme_content)

    print(f"✅ Updated README version history with {len(versions)} versions")
    return True


def update_readme_version_badge():
    """Update the version badge in README to match current version"""
    project_root = Path(__file__).parent.parent
    readme_file = project_root / "README.md"

    # Import current version
    sys.path.insert(0, str(project_root))
    try:
        from src.version import __version__

        current_version = __version__
    except ImportError:
        print("❌ Could not import current version")
        return False

    if not readme_file.exists():
        print(f"❌ README file not found: {readme_file}")
        return False

    # Read README
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_content = f.read()

    # Update version badge
    version_badge_pattern = (
        r"\[!\[Version\]\(https://img\.shields\.io/badge/version-[^)]+\)\]"
    )
    new_badge = (
        f"[![Version](https://img.shields.io/badge/version-{current_version}-blue.svg)]"
    )

    new_readme_content = re.sub(version_badge_pattern, new_badge, readme_content)

    if new_readme_content == readme_content:
        print("⚠️ No changes needed in README version badge")
        return True

    # Write updated README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_readme_content)

    print(f"✅ Updated README version badge to v{current_version}")
    return True


def update_readme_logging_example():
    """Update the logging example to show current version"""
    project_root = Path(__file__).parent.parent
    readme_file = project_root / "README.md"

    # Import current version
    sys.path.insert(0, str(project_root))
    try:
        from src.version import __version__

        current_version = __version__
    except ImportError:
        print("❌ Could not import current version")
        return False

    if not readme_file.exists():
        print(f"❌ README file not found: {readme_file}")
        return False

    # Read README
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_content = f.read()

    # Update logging example version
    logging_pattern = r"🎯 QuranBot v[\d.]+( - Run ID: [A-Z0-9]+)"
    new_logging = f"🎯 QuranBot v{current_version}\\1"

    new_readme_content = re.sub(logging_pattern, new_logging, readme_content)

    # Also update the version line
    version_line_pattern = r"├─ version: [\d.]+"
    new_version_line = f"├─ version: {current_version}"

    new_readme_content = re.sub(
        version_line_pattern, new_version_line, new_readme_content
    )

    if new_readme_content == readme_content:
        print("⚠️ No changes needed in README logging example")
        return True

    # Write updated README
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(new_readme_content)

    print(f"✅ Updated README logging example to v{current_version}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Update README.md with latest version information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/update_readme.py                    # Update everything
  python tools/update_readme.py --version-only    # Update version info only
  python tools/update_readme.py --history-only    # Update version history only

This tool updates:
  - Version history from CHANGELOG.md
  - Version badge in header
  - Version in logging examples
        """,
    )

    parser.add_argument(
        "--version-only",
        action="store_true",
        help="Only update version badge and logging examples",
    )

    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Only update version history from CHANGELOG.md",
    )

    args = parser.parse_args()

    print("🔄 Updating README.md...")

    success = True

    if args.version_only:
        success &= update_readme_version_badge()
        success &= update_readme_logging_example()
    elif args.history_only:
        success &= update_readme_version_history()
    else:
        # Update everything
        success &= update_readme_version_history()
        success &= update_readme_version_badge()
        success &= update_readme_logging_example()

    if success:
        print("\n🎉 README.md successfully updated!")
        print("\nNext steps:")
        print("  1. Review the changes")
        print("  2. Commit the updated README")
        print("  3. Push to repository")
        return 0
    else:
        print("\n❌ README update failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
