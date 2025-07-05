# =============================================================================
# QuranBot - VPS Deployment Safety Script
# =============================================================================
# Ensures comprehensive testing before deploying to production VPS
# Prevents broken code from reaching production environment
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
    log_run_end,
    log_run_header,
    log_run_separator,
    log_section_start,
    log_tree_branch,
    log_tree_final,
    log_warning_with_context,
)

BOT_NAME = "QuranBot VPS Deployer"
BOT_VERSION = "1.2.0"


class VPSDeployer:
    """Safe deployment system for QuranBot VPS production environment"""

    def __init__(self):
        self.deployment_ready = False
        self.safety_checks_passed = False
        self.vps_config = {"host": None, "username": None, "project_path": None}

    def run_development_tests(self):
        """Run comprehensive development tests before deployment"""
        log_section_start("Pre-Deployment Testing", "🧪")

        try:
            # Run the development test suite
            log_tree_branch("running", "Development test suite")

            result = subprocess.run(
                [sys.executable, "tools/test_bot.py"],
                capture_output=True,
                text=True,
                cwd="..",
            )

            if result.returncode == 0:
                log_tree_branch("test_result", "✅ All tests passed")
                log_tree_final("status", "Safe for deployment")
                return True
            else:
                log_tree_branch("test_result", "❌ Tests failed")
                log_tree_branch(
                    "stdout", result.stdout[-500:] if result.stdout else "No output"
                )
                log_tree_branch(
                    "stderr", result.stderr[-500:] if result.stderr else "No errors"
                )
                log_tree_final("status", "❌ NOT SAFE FOR DEPLOYMENT")
                return False

        except Exception as e:
            log_error_with_traceback("Failed to run development tests", e)
            return False

    def format_code_before_deployment(self):
        """Ensure code is properly formatted before deployment"""
        log_section_start("Code Formatting", "🎨")

        try:
            # Run code formatter
            result = subprocess.run(
                [sys.executable, "tools/format_code.py"],
                capture_output=True,
                text=True,
                cwd="..",
            )

            if result.returncode == 0:
                log_tree_branch("formatting", "✅ Code formatted successfully")
                return True
            else:
                log_tree_branch("formatting", "❌ Code formatting failed")
                log_error_with_traceback(
                    "Code formatting failed", Exception(result.stderr)
                )
                return False

        except Exception as e:
            log_error_with_traceback("Failed to run code formatter", e)
            return False

    def validate_git_status(self):
        """Ensure git repository is in a clean state"""
        log_section_start("Git Repository Validation", "📚")

        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                log_tree_branch("git_status", "⚠️ Uncommitted changes found")
                log_tree_branch("changes", result.stdout.strip())
                log_warning_with_context(
                    "Uncommitted changes detected",
                    "Consider committing changes before deployment",
                )
                return "WARNING"
            else:
                log_tree_branch("git_status", "✅ Repository is clean")
                return "CLEAN"

        except subprocess.CalledProcessError as e:
            log_tree_branch("git_status", "❌ Not a git repository or git error")
            log_warning_with_context("Git validation failed", str(e))
            return "ERROR"
        except FileNotFoundError:
            log_tree_branch("git_status", "⚠️ Git not installed")
            return "NO_GIT"
        except Exception as e:
            log_error_with_traceback("Git validation failed", e)
            return "ERROR"

    def create_deployment_checklist(self):
        """Create deployment checklist for manual verification"""
        log_section_start("Deployment Checklist", "📋")

        checklist = [
            "✅ All development tests passed",
            "✅ Code is properly formatted",
            "✅ No syntax errors in any Python files",
            "✅ All imports can be resolved",
            "✅ Environment variables are configured",
            "✅ Audio files are present (if needed)",
            "✅ FFmpeg is available (if needed)",
            "⚠️  Verify VPS has correct Python version",
            "⚠️  Verify VPS has all required dependencies",
            "⚠️  Verify VPS .env file is configured",
            "⚠️  Verify VPS audio files are present",
            "⚠️  Verify VPS FFmpeg installation",
            "⚠️  Test bot on VPS before full deployment",
        ]

        log_tree_branch("checklist_items", len(checklist))
        for i, item in enumerate(checklist, 1):
            log_tree_branch(f"item_{i}", item)

        log_tree_final("manual_verification", "Required before VPS deployment")
        return checklist

    def generate_deployment_commands(self):
        """Generate safe deployment commands for VPS"""
        log_section_start("Deployment Commands", "🚀")

        commands = [
            "# VPS Deployment Commands (run these manually on VPS)",
            "",
            "# 1. Navigate to project directory",
            "cd /path/to/QuranBot",
            "",
            "# 2. Stop existing bot (if running)",
            "python bot_manager.py stop",
            "",
            "# 3. Pull latest code from git",
            "git pull origin master",
            "",
            "# 4. Install/update dependencies",
            "pip install -r requirements.txt",
            "",
            "# 5. Run tests on VPS",
            "python test_bot.py",
            "",
            "# 6. If tests pass, start bot",
            "python bot_manager.py start",
            "",
            "# 7. Verify bot is running",
            "python bot_manager.py status",
            "",
            "# 8. Monitor logs for any issues",
            "tail -f logs/$(date +%Y-%m-%d)/$(date +%Y-%m-%d).log",
        ]

        log_tree_branch("commands_generated", len(commands))
        log_tree_final("manual_execution", "Copy commands to VPS terminal")

        return commands

    def save_deployment_guide(self, commands):
        """Save deployment guide to file"""
        try:
            guide_path = "VPS_DEPLOYMENT_GUIDE.md"

            with open(guide_path, "w", encoding="utf-8") as f:
                f.write("# QuranBot VPS Deployment Guide\n\n")
                f.write("## ⚠️ IMPORTANT: Read Before Deploying\n\n")
                f.write(
                    "This guide ensures safe deployment to production VPS without breaking the bot.\n\n"
                )
                f.write("## Pre-Deployment Checklist\n\n")
                f.write("- [ ] All development tests passed locally\n")
                f.write("- [ ] Code is properly formatted\n")
                f.write("- [ ] Git repository is in clean state\n")
                f.write("- [ ] VPS environment is prepared\n\n")
                f.write("## Deployment Commands\n\n")
                f.write("Execute these commands **one by one** on your VPS:\n\n")
                f.write("```bash\n")
                for command in commands:
                    f.write(f"{command}\n")
                f.write("```\n\n")
                f.write("## Safety Notes\n\n")
                f.write("- Always run `python test_bot.py` on VPS before starting\n")
                f.write("- Monitor logs after deployment\n")
                f.write("- Keep backup of working version\n")
                f.write("- Test in development environment first\n\n")
                f.write("## Rollback Plan\n\n")
                f.write("If deployment fails:\n")
                f.write("1. `python bot_manager.py stop`\n")
                f.write("2. `git checkout previous-working-commit`\n")
                f.write("3. `python bot_manager.py start`\n")

            log_tree_branch("guide_saved", guide_path)
            return True

        except Exception as e:
            log_error_with_traceback("Failed to save deployment guide", e)
            return False

    def run_deployment_safety_check(self):
        """Run complete deployment safety check"""
        try:
            log_run_separator()
            run_id = log_run_header(BOT_NAME, BOT_VERSION)

            log_section_start("VPS Deployment Safety Check", "🛡️")
            log_tree_branch("purpose", "Prevent broken code from reaching production")
            log_tree_branch("environment", "Development → Production")
            log_tree_final("target", "VPS Production Environment")

            # Step 1: Format code
            if not self.format_code_before_deployment():
                log_critical_error("Code formatting failed - deployment aborted")
                log_run_end(run_id, "ABORTED - Code formatting failed")
                return False

            # Step 2: Run comprehensive tests
            if not self.run_development_tests():
                log_critical_error("Development tests failed - deployment aborted")
                log_run_end(run_id, "ABORTED - Tests failed")
                return False

            # Step 3: Validate git status
            git_status = self.validate_git_status()

            # Step 4: Create deployment checklist
            checklist = self.create_deployment_checklist()

            # Step 5: Generate deployment commands
            commands = self.generate_deployment_commands()

            # Step 6: Save deployment guide
            if not self.save_deployment_guide(commands):
                log_warning_with_context(
                    "Failed to save deployment guide", "Manual deployment required"
                )

            # Final assessment
            log_section_start("Deployment Assessment", "📊")
            log_tree_branch("tests_passed", "✅ Yes")
            log_tree_branch("code_formatted", "✅ Yes")
            log_tree_branch("git_status", git_status)
            log_tree_branch("deployment_guide", "✅ Generated")

            if git_status in ["CLEAN", "WARNING"]:
                log_tree_final("deployment_status", "✅ SAFE FOR VPS DEPLOYMENT")
                log_section_start("Next Steps", "👉")
                log_tree_branch("step_1", "Review VPS_DEPLOYMENT_GUIDE.md")
                log_tree_branch("step_2", "Execute commands manually on VPS")
                log_tree_branch("step_3", "Run tests on VPS before starting bot")
                log_tree_final("step_4", "Monitor logs after deployment")

                log_run_end(run_id, "READY FOR DEPLOYMENT")
                return True
            else:
                log_tree_final(
                    "deployment_status", "❌ NOT SAFE - Fix git issues first"
                )
                log_run_end(run_id, "NOT READY - Git issues")
                return False

        except Exception as e:
            log_critical_error("Fatal error in deployment safety check", e)
            log_run_end(run_id, "FAILED - Fatal error")
            return False


def main():
    """Main function to run deployment safety check"""
    try:
        deployer = VPSDeployer()
        ready = deployer.run_deployment_safety_check()

        if ready:
            print("\n🎉 Code is ready for VPS deployment!")
            print("📋 Check VPS_DEPLOYMENT_GUIDE.md for next steps")
            return True
        else:
            print("\n❌ Code is NOT ready for VPS deployment!")
            print("🔧 Fix issues before attempting deployment")
            return False

    except Exception as e:
        log_critical_error("Fatal error in deployment script", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
