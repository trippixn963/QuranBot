#!/usr/bin/env python3
# =============================================================================
# QuranBot - Version Update Utility
# =============================================================================
# Simple utility to update the centralized version number across the project
# Usage: python tools/update_version.py 2.1.0
# =============================================================================

import argparse
import os
import re
import sys
from pathlib import Path


def validate_version(version_string):
    """Validate semantic version format (MAJOR.MINOR.PATCH)"""
    pattern = r"^\d+\.\d+\.\d+$"
    if not re.match(pattern, version_string):
        return False

    try:
        major, minor, patch = map(int, version_string.split("."))
        return major >= 0 and minor >= 0 and patch >= 0
    except ValueError:
        return False


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
                    features.append(f"{emoji_title} - {description}")

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

    # Build new version history section
    version_history = []

    for i, version in enumerate(versions[:5]):  # Show latest 5 versions
        features = extract_changelog_features(changelog_content, version)

        if i == 0:
            version_history.append(f"### v{version} (Latest)")
        else:
            version_history.append(f"### v{version}")

        # Add features
        for feature in features[:9]:  # Limit to 9 features per version
            version_history.append(f"🎯 **{feature}")

        version_history.append("")  # Empty line between versions

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


def update_version_file(version_string):
    """Update the centralized version.py file"""
    project_root = Path(__file__).parent.parent
    version_file = project_root / "src" / "version.py"

    if not version_file.exists():
        print(f"❌ Version file not found: {version_file}")
        return False

    # Parse version components
    major, minor, patch = map(int, version_string.split("."))

    # Read current content
    with open(version_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Update version components
    content = re.sub(
        r'__version__ = "[^"]*"', f'__version__ = "{version_string}"', content
    )
    content = re.sub(r"VERSION_MAJOR = \d+", f"VERSION_MAJOR = {major}", content)
    content = re.sub(r"VERSION_MINOR = \d+", f"VERSION_MINOR = {minor}", content)
    content = re.sub(r"VERSION_PATCH = \d+", f"VERSION_PATCH = {patch}", content)

    # Write updated content
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Updated {version_file}")
    return True


def update_fallback_version(version_string):
    """Update the fallback version in utils/__init__.py"""
    project_root = Path(__file__).parent.parent
    utils_init = project_root / "src" / "utils" / "__init__.py"

    if not utils_init.exists():
        print(f"❌ Utils init file not found: {utils_init}")
        return False

    # Parse version components for tuple
    major, minor, patch = map(int, version_string.split("."))

    # Read current content
    with open(utils_init, "r", encoding="utf-8") as f:
        content = f.read()

    # Update fallback version
    content = re.sub(
        r'BOT_VERSION = "[^"]*"  # Keep in sync with src/version\.py',
        f'BOT_VERSION = "{version_string}"  # Keep in sync with src/version.py',
        content,
    )
    content = re.sub(
        r"return \(\d+, \d+, \d+\)  # Keep in sync with src/version\.py",
        f"return ({major}, {minor}, {patch})  # Keep in sync with src/version.py",
        content,
    )

    # Write updated content
    with open(utils_init, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Updated fallback version in {utils_init}")
    return True


def update_author(author_string):
    """Update the centralized author information"""
    project_root = Path(__file__).parent.parent
    version_file = project_root / "src" / "version.py"
    utils_init = project_root / "src" / "utils" / "__init__.py"

    success = True

    # Update main version file
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            r'__author__ = "[^"]*"', f'__author__ = "{author_string}"', content
        )

        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Updated author in {version_file}")
    else:
        print(f"❌ Version file not found: {version_file}")
        success = False

    # Update fallback in utils
    if utils_init.exists():
        with open(utils_init, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            r'__author__ = "[^"]*"  # Keep in sync with src/version\.py',
            f'__author__ = "{author_string}"  # Keep in sync with src/version.py',
            content,
        )

        with open(utils_init, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Updated fallback author in {utils_init}")
    else:
        print(f"❌ Utils init file not found: {utils_init}")
        success = False

    return success


def verify_version_consistency():
    """Verify that all version imports work correctly and are consistent"""
    project_root = Path(__file__).parent.parent

    print("🔍 Verifying version and author consistency...")

    # Test imports from different contexts
    test_imports = [
        (
            "src.version",
            "from src.version import __version__, __author__, BOT_VERSION",
            True,
            True,
        ),
        ("src", "from src import __version__, __author__", True, True),
        ("src.utils", "from src.utils import BOT_VERSION, __author__", True, True),
        (
            "src.bot.main",
            "from src.bot.main import BOT_VERSION",
            True,
            False,
        ),  # No author export
        (
            "src.commands.credits",
            "from src.commands.credits import BOT_VERSION",
            True,
            False,
        ),  # No author export
    ]

    success = True
    versions_found = set()
    authors_found = set()

    # Add project root to Python path
    old_path = sys.path[:]
    sys.path.insert(0, str(project_root))

    try:
        for (
            module_name,
            import_statement,
            expect_version,
            expect_author,
        ) in test_imports:
            try:
                # Change to project root for imports
                old_cwd = os.getcwd()
                os.chdir(project_root)

                # Create a temporary namespace for testing
                namespace = {}
                exec(import_statement, namespace)

                # Extract version info
                version = namespace.get("__version__") or namespace.get("BOT_VERSION")
                author = namespace.get("__author__")

                if expect_version:
                    if version:
                        versions_found.add(version)
                        print(f"  ✅ {module_name}: v{version}")
                    else:
                        print(f"  ❌ {module_name}: No version found")
                        success = False

                if expect_author:
                    if author:
                        authors_found.add(author)
                        print(f"     👤 Author: {author}")
                    else:
                        print(f"     ❌ No author found")
                        success = False
                else:
                    # Module doesn't export author - that's OK
                    if author:
                        authors_found.add(author)
                        print(f"     👤 Author: {author}")
                    else:
                        print(f"     ℹ️ No author export (expected)")

            except Exception as e:
                print(f"  ❌ {module_name}: Import failed - {e}")
                success = False
            finally:
                os.chdir(old_cwd)

    finally:
        # Restore original Python path
        sys.path[:] = old_path

    # Check consistency
    if len(versions_found) > 1:
        print(f"\n❌ Version inconsistency detected!")
        print(f"   Found versions: {', '.join(sorted(versions_found))}")
        success = False
    elif len(versions_found) == 1:
        print(f"\n✅ All modules using consistent version: {list(versions_found)[0]}")

    if len(authors_found) > 1:
        print(f"\n❌ Author inconsistency detected!")
        print(f"   Found authors: {', '.join(sorted(authors_found))}")
        success = False
    elif len(authors_found) == 1:
        print(f"✅ All modules using consistent author: {list(authors_found)[0]}")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Update QuranBot version across all files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/update_version.py 2.1.0                    # Update to version 2.1.0
  python tools/update_version.py 3.0.0                    # Update to version 3.0.0
  python tools/update_version.py --author "John Smith"    # Update author only
  python tools/update_version.py 2.1.0 --author "John"   # Update both version and author
  python tools/update_version.py --verify-only           # Verify consistency only

This tool updates:
  - src/version.py (main version and author file)
  - src/utils/__init__.py (fallback version and author)
  - Verifies all imports work correctly
        """,
    )

    parser.add_argument(
        "version",
        nargs="?",  # Make version optional
        help="New version number in MAJOR.MINOR.PATCH format (e.g., 2.1.0)",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current version consistency without updating",
    )

    parser.add_argument(
        "--author",
        type=str,
        help="Update author information (e.g., 'John (Discord: Trippixn)')",
    )

    args = parser.parse_args()

    if args.verify_only:
        print("🔍 Verifying current version consistency...")
        success = verify_version_consistency()
        return 0 if success else 1

    # Handle author-only updates
    if args.author and not args.version:
        print(f"🔄 Updating QuranBot author to: {args.author}")
        success = update_author(args.author)

        if success:
            print("\n🔍 Verifying consistency...")
            success &= verify_version_consistency()

        if success:
            print(f"\n🎉 Successfully updated author to: {args.author}!")
            return 0
        else:
            print("\n❌ Author update failed!")
            return 1

    # Version is required when not using --verify-only or --author
    if not args.version:
        parser.error("version is required when not using --verify-only or --author")

    # Validate version format
    if not validate_version(args.version):
        print(f"❌ Invalid version format: {args.version}")
        print("   Expected format: MAJOR.MINOR.PATCH (e.g., 2.1.0)")
        return 1

    print(f"🔄 Updating QuranBot version to {args.version}...")

    # Update version files
    success = True
    success &= update_version_file(args.version)
    success &= update_fallback_version(args.version)

    # Update author if provided
    if args.author:
        print(f"🔄 Also updating author to: {args.author}")
        success &= update_author(args.author)

    if success:
        print("\n🔍 Verifying version consistency...")
        success &= verify_version_consistency()

    # Update README if version was updated successfully
    if success and args.version:
        print("\n📋 Updating README version history...")
        success &= update_readme_version_history()

    if success:
        update_msg = f"Successfully updated QuranBot to version {args.version}!"
        if args.author:
            update_msg += f" Author: {args.author}"
        print(f"\n🎉 {update_msg}")
        print("\nNext steps:")
        print("  1. Test the bot locally")
        print("  2. Commit the changes")
        print("  3. Create a new release")
        print("  4. Deploy to production")
        return 0
    else:
        print("\n❌ Update failed!")
        return 1


if __name__ == "__main__":
    exit(main())
