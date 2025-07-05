# =============================================================================
# QuranBot - Development Testing Suite
# =============================================================================
# Comprehensive testing to ensure bot stability before VPS deployment
# Tests all critical functionality without affecting production environment
# =============================================================================

import asyncio
import os
import subprocess
import sys
import traceback
from pathlib import Path
from unittest.mock import AsyncMock, Mock

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

BOT_NAME = "QuranBot Development Tester"
BOT_VERSION = "1.2.0"


class DevelopmentTester:
    """Comprehensive testing suite for QuranBot development environment"""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        self.test_results = []

        # Change to project root directory for all operations
        self.original_dir = os.getcwd()
        self.project_root = os.path.join(os.path.dirname(__file__), "..")
        os.chdir(self.project_root)

    def test_environment_setup(self):
        """Test development environment configuration"""
        log_section_start("Environment Setup Tests", "🔧")

        try:
            # Test .env file existence
            if os.path.exists("config/.env"):
                log_tree_branch("env_file", "✅ Found")
                self.passed_tests += 1
            else:
                log_tree_branch("env_file", "❌ Missing - create from env_template.txt")
                self.failed_tests += 1
                self.test_results.append("FAIL: .env file missing")

            # Test src directory structure
            required_dirs = ["src", "src/bot", "src/utils", "src/config"]

            for dir_path in required_dirs:
                if os.path.exists(dir_path):
                    log_tree_branch(f"directory_{dir_path}", "✅ Found")
                    self.passed_tests += 1
                else:
                    log_tree_branch(f"directory_{dir_path}", "❌ Missing")
                    self.failed_tests += 1
                    self.test_results.append(f"FAIL: {dir_path} directory missing")

            # Test Python files exist
            required_files = [
                "main.py",
                "bot_manager.py",
                "src/bot/main.py",
                "src/utils/tree_log.py",
            ]

            for file_path in required_files:
                if os.path.exists(file_path):
                    log_tree_branch(f"file_{file_path}", "✅ Found")
                    self.passed_tests += 1
                else:
                    log_tree_branch(f"file_{file_path}", "❌ Missing")
                    self.failed_tests += 1
                    self.test_results.append(f"FAIL: {file_path} missing")

            log_tree_final("environment_setup", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Environment setup test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Environment setup test crashed")

    def test_python_syntax(self):
        """Test Python syntax for all files"""
        log_section_start("Python Syntax Tests", "🐍")

        python_files = [
            "main.py",
            "bot_manager.py",
            "tools/format_code.py",
            "tools/test_bot.py",
            "src/bot/main.py",
            "src/utils/tree_log.py",
        ]

        try:
            for file_path in python_files:
                if not os.path.exists(file_path):
                    log_tree_branch(f"syntax_{file_path}", "⚠️ File not found")
                    self.warnings += 1
                    continue

                try:
                    # Test Python syntax compilation
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", file_path],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    log_tree_branch(f"syntax_{file_path}", "✅ Valid")
                    self.passed_tests += 1

                except subprocess.CalledProcessError as e:
                    log_tree_branch(f"syntax_{file_path}", "❌ Syntax Error")
                    log_error_with_traceback(f"Syntax error in {file_path}", e)
                    self.failed_tests += 1
                    self.test_results.append(f"FAIL: Syntax error in {file_path}")

            log_tree_final("python_syntax", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Python syntax test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Python syntax test crashed")

    def test_imports(self):
        """Test all imports can be resolved"""
        log_section_start("Import Tests", "📦")

        try:
            # Test standard library imports
            standard_imports = [
                "os",
                "sys",
                "traceback",
                "asyncio",
                "glob",
                "json",
                "datetime",
                "pathlib",
                "subprocess",
                "time",
                "secrets",
            ]

            for module in standard_imports:
                try:
                    __import__(module)
                    log_tree_branch(f"stdlib_{module}", "✅ Available")
                    self.passed_tests += 1
                except ImportError as e:
                    log_tree_branch(f"stdlib_{module}", "❌ Missing")
                    self.failed_tests += 1
                    self.test_results.append(f"FAIL: Standard library {module} missing")

            # Test third-party imports
            third_party_imports = ["discord", "psutil", "pytz", "dotenv"]

            for module in third_party_imports:
                try:
                    __import__(module)
                    log_tree_branch(f"3rdparty_{module}", "✅ Available")
                    self.passed_tests += 1
                except ImportError as e:
                    log_tree_branch(f"3rdparty_{module}", "❌ Missing")
                    self.failed_tests += 1
                    self.test_results.append(
                        f"FAIL: Third-party {module} missing - run pip install"
                    )

            # Test local imports
            try:
                from utils.tree_log import log_tree

                log_tree_branch("local_tree_log", "✅ Available")
                self.passed_tests += 1
            except ImportError as e:
                log_tree_branch("local_tree_log", "❌ Missing")
                self.failed_tests += 1
                self.test_results.append("FAIL: Local tree_log import failed")

            log_tree_final("imports", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Import test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Import test crashed")

    def test_configuration_validation(self):
        """Test configuration validation without connecting to Discord"""
        log_section_start("Configuration Tests", "⚙️")

        try:
            from dotenv import load_dotenv

            load_dotenv("config/.env")

            # Test environment variables
            required_env_vars = ["DISCORD_TOKEN", "GUILD_ID", "TARGET_CHANNEL_ID"]

            for var_name in required_env_vars:
                value = os.getenv(var_name)
                if value:
                    if var_name == "DISCORD_TOKEN":
                        # Don't log the actual token
                        log_tree_branch(f"env_{var_name}", "✅ Set (hidden)")
                    else:
                        log_tree_branch(f"env_{var_name}", f"✅ {value}")
                    self.passed_tests += 1
                else:
                    log_tree_branch(f"env_{var_name}", "❌ Missing")
                    self.failed_tests += 1
                    self.test_results.append(
                        f"FAIL: {var_name} environment variable missing"
                    )

            # Test FFmpeg availability
            ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")
            try:
                result = subprocess.run(
                    [ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                log_tree_branch("ffmpeg", "✅ Available")
                self.passed_tests += 1
            except (subprocess.CalledProcessError, FileNotFoundError):
                log_tree_branch("ffmpeg", "❌ Not found")
                self.warnings += 1
                self.test_results.append("WARN: FFmpeg not found - audio may not work")

            # Test audio folder
            audio_folder = "audio/Saad Al Ghamdi"
            if os.path.exists(audio_folder):
                audio_files = [
                    f for f in os.listdir(audio_folder) if f.endswith(".mp3")
                ]
                log_tree_branch("audio_folder", f"✅ Found ({len(audio_files)} files)")
                self.passed_tests += 1
            else:
                log_tree_branch("audio_folder", "⚠️ Not found")
                self.warnings += 1
                self.test_results.append("WARN: Audio folder missing")

            log_tree_final("configuration", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Configuration test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Configuration test crashed")

    def test_logging_system(self):
        """Test the tree logging system functionality"""
        log_section_start("Logging System Tests", "📊")

        try:
            # Test basic logging functions
            from utils.tree_log import (
                get_timestamp,
                log_critical_error,
                log_error_with_traceback,
                log_tree,
                log_tree_branch,
                log_tree_final,
                setup_log_directories,
            )

            # Test timestamp generation
            timestamp = get_timestamp()
            if timestamp and "[" in timestamp and "]" in timestamp:
                log_tree_branch("timestamp_format", "✅ Valid")
                self.passed_tests += 1
            else:
                log_tree_branch("timestamp_format", "❌ Invalid")
                self.failed_tests += 1
                self.test_results.append("FAIL: Timestamp format invalid")

            # Test log directory creation
            log_dir = setup_log_directories()
            if log_dir and log_dir.exists():
                log_tree_branch("log_directories", "✅ Created")
                self.passed_tests += 1
            else:
                log_tree_branch("log_directories", "❌ Failed")
                self.failed_tests += 1
                self.test_results.append("FAIL: Log directory creation failed")

            # Test error logging (with mock exception)
            try:
                raise ValueError("Test exception for logging")
            except Exception as e:
                log_error_with_traceback("Test error logging", e)
                log_tree_branch("error_logging", "✅ Working")
                self.passed_tests += 1

            log_tree_final("logging_system", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Logging system test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Logging system test crashed")

    def test_bot_manager(self):
        """Test bot manager functionality"""
        log_section_start("Bot Manager Tests", "🤖")

        try:
            # Import bot manager functions
            sys.path.insert(0, ".")
            import bot_manager

            # Test process finding (should work without errors)
            processes = bot_manager.find_bot_processes()
            log_tree_branch("process_detection", f"✅ Found {len(processes)} processes")
            self.passed_tests += 1

            # Test uptime formatting
            uptime = bot_manager.format_uptime(3661)  # 1 hour, 1 minute, 1 second
            if "1h" in uptime and "1m" in uptime:
                log_tree_branch("uptime_format", "✅ Valid")
                self.passed_tests += 1
            else:
                log_tree_branch("uptime_format", "❌ Invalid")
                self.failed_tests += 1
                self.test_results.append("FAIL: Uptime formatting broken")

            log_tree_final("bot_manager", "✅ Complete")

        except Exception as e:
            log_error_with_traceback("Bot manager test failed", e)
            self.failed_tests += 1
            self.test_results.append("FAIL: Bot manager test crashed")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        log_section_start("Test Report", "📋")

        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        log_tree_branch("total_tests", total_tests)
        log_tree_branch("passed", self.passed_tests)
        log_tree_branch("failed", self.failed_tests)
        log_tree_branch("warnings", self.warnings)
        log_tree_branch("success_rate", f"{success_rate:.1f}%")

        # Deployment readiness assessment
        if self.failed_tests == 0:
            if self.warnings == 0:
                log_tree_final("deployment_status", "✅ READY FOR VPS DEPLOYMENT")
                return "READY"
            else:
                log_tree_final("deployment_status", "⚠️ READY WITH WARNINGS")
                return "READY_WITH_WARNINGS"
        else:
            log_tree_final("deployment_status", "❌ NOT READY - FIX ISSUES FIRST")
            return "NOT_READY"

    def run_all_tests(self):
        """Run complete test suite"""
        try:
            log_run_separator()
            run_id = log_run_header(BOT_NAME, BOT_VERSION)

            log_section_start("QuranBot Development Testing", "🧪")
            log_tree_branch("purpose", "Validate code before VPS deployment")
            log_tree_final("environment", "Development (Local)")

            # Run all test categories
            self.test_environment_setup()
            self.test_python_syntax()
            self.test_imports()
            self.test_configuration_validation()
            self.test_logging_system()
            self.test_bot_manager()

            # Generate final report
            deployment_status = self.generate_test_report()

            # Print any failures or warnings
            if self.test_results:
                log_section_start("Issues Found", "⚠️")
                for result in self.test_results:
                    if result.startswith("FAIL:"):
                        log_tree_branch("failure", result[5:])
                    elif result.startswith("WARN:"):
                        log_tree_branch("warning", result[5:])

            log_run_end(run_id, f"Testing complete - {deployment_status}")
            return deployment_status == "READY"

        except Exception as e:
            log_critical_error("Fatal error in test suite", e)
            return False
        finally:
            # Change back to original directory
            os.chdir(self.original_dir)


def main():
    """Main function to run development tests"""
    try:
        tester = DevelopmentTester()
        success = tester.run_all_tests()

        if success:
            print("\n🎉 All tests passed! Code is ready for VPS deployment.")
            return True
        else:
            print("\n❌ Tests failed! Fix issues before deploying to VPS.")
            return False

    except Exception as e:
        log_critical_error("Fatal error in test runner", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
