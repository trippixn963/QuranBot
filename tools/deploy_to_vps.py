#!/usr/bin/env python3
# =============================================================================
# QuranBot VPS Deployment Safety Script
# =============================================================================
# Ensures safe deployment from Mac development to VPS production
# =============================================================================

import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.tree_log import log_error_with_traceback, tree_log

# =============================================================================
# Deployment Configuration
# =============================================================================

BOT_VERSION = "1.3.0"
VPS_USER = "root"  # Update with your VPS username
VPS_HOST = "your-vps-ip"  # Update with your VPS IP
VPS_PATH = "/opt/quranbot"  # Update with your VPS path

DEPLOYMENT_FILES = [
    "main.py",
    "bot_manager.py",
    "src/",
    "config/.env",
    "requirements.txt",
    "audio/",
]

# =============================================================================
# Pre-Deployment Safety Checks
# =============================================================================


def run_development_tests():
    """Run comprehensive development tests before deployment"""
    tree_log("🧪", "Running Development Tests...", {})

    try:
        result = subprocess.run(
            [sys.executable, "tools/test_bot.py"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode == 0:
            tree_log("✅", "Development Tests Passed", {"status": "READY"})
            return True
        else:
            tree_log(
                "❌",
                "Development Tests Failed",
                {"error": result.stderr, "output": result.stdout},
            )
            return False

    except Exception as e:
        log_error_with_traceback("Failed to run development tests", e)
        return False


def check_git_status():
    """Ensure all changes are committed"""
    tree_log("📝", "Checking Git Status...", {})

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.stdout.strip():
            tree_log(
                "❌",
                "Uncommitted Changes Found",
                {"changes": result.stdout.strip().split("\n")},
            )
            return False

        tree_log("✅", "Git Repository Clean", {"status": "OK"})
        return True

    except Exception as e:
        log_error_with_traceback("Git status check failed", e)
        return False


def validate_environment():
    """Validate production environment configuration"""
    tree_log("⚙️", "Validating Environment...", {})

    try:
        from dotenv import load_dotenv

        load_dotenv("config/.env")

        # Check critical environment variables
        required_vars = [
            "DISCORD_TOKEN",
            "GUILD_ID",
            "TARGET_CHANNEL_ID",
            "ADMIN_USER_ID",
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            tree_log("❌", "Missing Environment Variables", {"missing": missing})
            return False

        tree_log("✅", "Environment Valid", {"variables": len(required_vars)})
        return True

    except Exception as e:
        log_error_with_traceback("Environment validation failed", e)
        return False


def check_audio_files():
    """Verify audio files are present"""
    tree_log("🎵", "Checking Audio Files...", {})

    audio_dir = project_root / "audio"
    if not audio_dir.exists():
        tree_log("❌", "Audio Directory Missing", {"path": str(audio_dir)})
        return False

    # Check for reciter directories
    reciters = [d for d in audio_dir.iterdir() if d.is_dir()]
    if not reciters:
        tree_log("❌", "No Reciter Directories Found", {"path": str(audio_dir)})
        return False

    # Check for MP3 files
    total_files = 0
    for reciter_dir in reciters:
        mp3_files = list(reciter_dir.glob("*.mp3"))
        total_files += len(mp3_files)

    if total_files == 0:
        tree_log("❌", "No Audio Files Found", {"reciters": len(reciters)})
        return False

    tree_log(
        "✅",
        "Audio Files Present",
        {"reciters": len(reciters), "total_files": total_files},
    )
    return True


# =============================================================================
# Deployment Functions
# =============================================================================


def generate_deployment_commands():
    """Generate safe deployment commands"""
    tree_log("📋", "Generating Deployment Commands...", {})

    commands = [
        "# QuranBot VPS Deployment Commands",
        f"# Version: {BOT_VERSION}",
        f"# Generated for: {VPS_USER}@{VPS_HOST}",
        "",
        "# 1. Stop existing bot (if running)",
        f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && python bot_manager.py stop'",
        "",
        "# 2. Backup current deployment",
        f"ssh {VPS_USER}@{VPS_HOST} 'cp -r {VPS_PATH} {VPS_PATH}_backup_$(date +%Y%m%d_%H%M%S)'",
        "",
        "# 3. Upload new files",
        f"rsync -avz --delete main.py bot_manager.py src/ requirements.txt {VPS_USER}@{VPS_HOST}:{VPS_PATH}/",
        f"rsync -avz config/.env {VPS_USER}@{VPS_HOST}:{VPS_PATH}/config/",
        f"rsync -avz audio/ {VPS_USER}@{VPS_HOST}:{VPS_PATH}/audio/",
        "",
        "# 4. Install dependencies",
        f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && pip install -r requirements.txt'",
        "",
        "# 5. Start bot",
        f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && nohup python main.py > bot.log 2>&1 &'",
        "",
        "# 6. Verify deployment",
        f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && python bot_manager.py status'",
    ]

    return commands


def save_deployment_guide():
    """Save deployment guide to file"""
    commands = generate_deployment_commands()

    guide_path = project_root / "VPS_DEPLOYMENT_GUIDE.md"
    with open(guide_path, "w") as f:
        f.write("# QuranBot VPS Deployment Guide\n\n")
        f.write(f"**Version:** {BOT_VERSION}\n")
        f.write(f"**Target:** {VPS_USER}@{VPS_HOST}\n")
        f.write(f"**Path:** {VPS_PATH}\n\n")
        f.write("## Pre-Deployment Checklist\n\n")
        f.write("- [ ] All development tests passed\n")
        f.write("- [ ] Git repository is clean\n")
        f.write("- [ ] Environment variables configured\n")
        f.write("- [ ] Audio files present\n")
        f.write("- [ ] VPS access confirmed\n\n")
        f.write("## Deployment Commands\n\n")
        f.write("```bash\n")
        f.write("\n".join(commands))
        f.write("\n```\n\n")
        f.write("## Post-Deployment Verification\n\n")
        f.write("1. Check bot status: `python bot_manager.py status`\n")
        f.write("2. Check Discord connection\n")
        f.write("3. Verify audio streaming\n")
        f.write("4. Monitor logs for errors\n\n")
        f.write("## Rollback (if needed)\n\n")
        f.write("```bash\n")
        f.write(
            f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && python bot_manager.py stop'\n"
        )
        f.write(
            f"ssh {VPS_USER}@{VPS_HOST} 'rm -rf {VPS_PATH} && mv {VPS_PATH}_backup_* {VPS_PATH}'\n"
        )
        f.write(f"ssh {VPS_USER}@{VPS_HOST} 'cd {VPS_PATH} && python main.py'\n")
        f.write("```\n")

    tree_log("📄", "Deployment Guide Saved", {"path": str(guide_path)})


# =============================================================================
# Main Deployment Safety Function
# =============================================================================


def main():
    """Main deployment safety check"""

    tree_log(
        "🚀",
        f"QuranBot v{BOT_VERSION} VPS Deployment Safety Check",
        {
            "environment": "Mac Development → VPS Production",
            "target": f"{VPS_USER}@{VPS_HOST}",
            "path": VPS_PATH,
        },
    )

    # Run all safety checks
    checks = [
        ("Development Tests", run_development_tests),
        ("Git Status", check_git_status),
        ("Environment Config", validate_environment),
        ("Audio Files", check_audio_files),
    ]

    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
            tree_log("⚠️", f"Safety Check Failed: {check_name}", {})

    if all_passed:
        tree_log("✅", "All Safety Checks Passed", {"status": "READY FOR DEPLOYMENT"})
        save_deployment_guide()
        tree_log(
            "🎯",
            "Next Steps",
            {
                "1": "Review VPS_DEPLOYMENT_GUIDE.md",
                "2": "Update VPS connection details in this script",
                "3": "Execute deployment commands manually",
                "4": "Verify deployment success",
            },
        )
    else:
        tree_log(
            "❌",
            "Safety Checks Failed",
            {"status": "NOT READY", "action": "Fix failing checks before deployment"},
        )
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
