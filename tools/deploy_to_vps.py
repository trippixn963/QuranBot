#!/usr/bin/env python3
# =============================================================================
# QuranBot - VPS Deployment Safety Tool
# =============================================================================
# Safe deployment script with comprehensive pre-deployment checks
# =============================================================================

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.tree_log import log_error_with_traceback, log_perfect_tree_section

# Import version from centralized version module
from src.version import BOT_VERSION

# =============================================================================
# Deployment Configuration
# =============================================================================

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
    log_perfect_tree_section(
        "Running Development Tests",
        [
            ("status", "🧪 Executing test suite"),
        ],
        "🧪",
    )

    try:
        result = subprocess.run(
            ["python", "tools/test_bot.py"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode == 0:
            log_perfect_tree_section(
                "Development Tests Passed",
                [
                    ("status", "✅ All tests passed"),
                    ("result", "READY FOR DEPLOYMENT"),
                ],
                "✅",
            )
            return True
        else:
            log_perfect_tree_section(
                "Development Tests Failed",
                [
                    ("status", "❌ Tests failed"),
                    (
                        "error",
                        result.stderr[:100] if result.stderr else "Unknown error",
                    ),
                ],
                "❌",
            )
            return False

    except Exception as e:
        log_error_with_traceback("Error running development tests", e)
        return False


def check_git_status():
    """Ensure all changes are committed"""
    log_perfect_tree_section(
        "Checking Git Status",
        [
            ("status", "📝 Verifying repository state"),
        ],
        "📝",
    )

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.stdout.strip():
            log_perfect_tree_section(
                "Uncommitted Changes Found",
                [
                    ("status", "❌ Repository has uncommitted changes"),
                    ("action", "Please commit all changes before deployment"),
                ],
                "❌",
            )
            return False

        log_perfect_tree_section(
            "Git Repository Clean",
            [
                ("status", "✅ All changes committed"),
            ],
            "✅",
        )
        return True

    except Exception as e:
        log_error_with_traceback("Error checking git status", e)
        return False


def validate_environment():
    """Validate production environment configuration"""
    log_perfect_tree_section(
        "Validating Environment",
        [
            ("status", "⚙️ Checking environment variables"),
        ],
        "⚙️",
    )

    try:
        required_vars = [
            "DISCORD_TOKEN",
            "TARGET_CHANNEL_ID",
            "GUILD_ID",
            "PANEL_CHANNEL_ID",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]

        if missing:
            log_perfect_tree_section(
                "Missing Environment Variables",
                [
                    ("status", "❌ Required variables missing"),
                    ("missing_vars", ", ".join(missing)),
                ],
                "❌",
            )
            return False

        log_perfect_tree_section(
            "Environment Valid",
            [
                ("status", "✅ All required variables present"),
                ("variables_count", len(required_vars)),
            ],
            "✅",
        )
        return True

    except Exception as e:
        log_error_with_traceback("Error validating environment", e)
        return False


def check_audio_files():
    """Verify audio files are present"""
    log_perfect_tree_section(
        "Checking Audio Files",
        [
            ("status", "🎵 Verifying audio directory"),
        ],
        "🎵",
    )

    audio_dir = project_root / "audio"
    if not audio_dir.exists():
        log_perfect_tree_section(
            "Audio Directory Missing",
            [
                ("status", "❌ Audio directory not found"),
                ("path", str(audio_dir)),
            ],
            "❌",
        )
        return False

    # Check for reciter directories
    reciters = [d for d in audio_dir.iterdir() if d.is_dir()]
    if not reciters:
        log_perfect_tree_section(
            "No Reciter Directories Found",
            [
                ("status", "❌ No reciter directories"),
                ("path", str(audio_dir)),
            ],
            "❌",
        )
        return False

    # Count audio files
    total_files = 0
    for reciter_dir in reciters:
        mp3_files = list(reciter_dir.glob("*.mp3"))
        total_files += len(mp3_files)

    if total_files == 0:
        log_perfect_tree_section(
            "No Audio Files Found",
            [
                ("status", "❌ No MP3 files found"),
                ("reciters", len(reciters)),
            ],
            "❌",
        )
        return False

    log_perfect_tree_section(
        "Audio Files Present",
        [
            ("status", "✅ Audio files verified"),
            ("reciters", len(reciters)),
            ("total_files", total_files),
        ],
        "✅",
    )
    return True


# =============================================================================
# Deployment Functions
# =============================================================================


def generate_deployment_commands():
    """Generate safe deployment commands"""
    log_perfect_tree_section(
        "Generating Deployment Commands",
        [
            ("status", "📋 Creating deployment guide"),
        ],
        "📋",
    )

    commands = [
        "# QuranBot VPS Deployment Commands",
        f"# Version: {BOT_VERSION}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "# 1. Connect to VPS",
        f"ssh {VPS_USER}@{VPS_HOST}",
        "",
        "# 2. Navigate to project directory",
        f"cd {VPS_PATH}",
        "",
        "# 3. Pull latest changes",
        "git pull origin master",
        "",
        "# 4. Install/update dependencies",
        "pip install -r requirements.txt",
        "",
        "# 5. Restart bot service",
        "sudo systemctl restart quranbot",
        "",
        "# 6. Check service status",
        "sudo systemctl status quranbot",
        "",
        "# 7. View logs",
        "sudo journalctl -u quranbot -f",
    ]

    guide_path = project_root / "deployment_guide.md"
    with open(guide_path, "w") as f:
        f.write("# QuranBot VPS Deployment Guide\n\n")
        f.write("## Pre-Deployment Safety Checks ✅\n\n")
        f.write("All safety checks have passed. The bot is ready for deployment.\n\n")
        f.write("## Deployment Commands\n\n")
        f.write("```bash\n")
        f.write("\n".join(commands))
        f.write("\n```\n")

    log_perfect_tree_section(
        "Deployment Guide Saved",
        [
            ("status", "📄 Guide created"),
            ("path", str(guide_path)),
        ],
        "📄",
    )


# =============================================================================
# Main Deployment Safety Function
# =============================================================================


def main():
    """Main deployment safety check"""

    log_perfect_tree_section(
        f"QuranBot v{BOT_VERSION} VPS Deployment Safety Check",
        [
            ("version", BOT_VERSION),
            ("status", "🚀 Starting safety checks"),
        ],
        "🚀",
    )

    # Safety checks
    checks = [
        ("Development Tests", run_development_tests),
        ("Git Status", check_git_status),
        ("Environment", validate_environment),
        ("Audio Files", check_audio_files),
    ]

    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
            log_perfect_tree_section(
                f"Safety Check Failed: {check_name}",
                [
                    ("check", check_name),
                    ("status", "⚠️ Failed"),
                ],
                "⚠️",
            )

    if all_passed:
        log_perfect_tree_section(
            "All Safety Checks Passed",
            [
                ("status", "✅ Ready for deployment"),
                ("result", "DEPLOYMENT APPROVED"),
            ],
            "✅",
        )
        generate_deployment_commands()
        log_perfect_tree_section(
            "Next Steps",
            [
                ("action", "📋 Review deployment_guide.md"),
                ("command", "Execute deployment commands on VPS"),
                ("monitoring", "Monitor logs after deployment"),
            ],
            "🎯",
        )
    else:
        log_perfect_tree_section(
            "Safety Checks Failed",
            [
                ("status", "❌ Deployment blocked"),
                ("action", "Fix issues and re-run safety checks"),
            ],
            "❌",
        )
        return 1

    return 0


if __name__ == "__main__":
    success = main()
    sys.exit(success)
