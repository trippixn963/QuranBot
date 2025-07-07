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


def extract_changelog_features(changelog_content, version):
    """Extract key features from changelog for a specific version"""
    features = []

    # Find the section for this version
    version_pattern = rf"## \[{re.escape(version)}\]"
    lines = changelog_content.split("\n")

    in_version_section = False
    in_added_section = False

    for line in lines:
        if re.match(version_pattern, line):
            in_version_section = True
            continue
        elif in_version_section and line.startswith("## ["):
            # Hit the next version section, stop
            break
        elif in_version_section:
            if line.startswith("### Added"):
                in_added_section = True
                continue
            elif line.startswith("### ") and in_added_section:
                in_added_section = False
                continue
            elif in_added_section and line.startswith("- **"):
                # Extract feature line
                feature_match = re.match(r"- \*\*([^*]+)\*\*[^:]*: (.+)", line)
                if feature_match:
                    emoji_title = feature_match.group(1)
                    description = feature_match.group(2)
                    # Clean up the description and format properly
                    clean_description = description.strip()
                    features.append(f"{emoji_title} - {clean_description}")

    return features


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
        features = extract_changelog_features(changelog_content, version)

        if i == 0:
            version_history.append(f"### v{version} (Latest)")
        else:
            version_history.append(f"### v{version}")

        # Add features with proper formatting
        for feature in features[:9]:  # Limit to 9 features per version
            # Remove any duplicate emoji prefix and format properly
            clean_feature = feature.replace("🎯 ", "").replace("**", "")
            version_history.append(f"🎯 **{clean_feature}")

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
