# =============================================================================
# QuranBot - Main Entry Point (Open Source Edition)
# =============================================================================
# This is an open source project provided AS-IS without official support.
# Feel free to use, modify, and learn from this code under the license terms.
#
# Purpose:
# - Primary entry point for the QuranBot Discord application
# - Handles instance management, bot initialization, and graceful shutdown
# - Demonstrates professional Discord bot architecture and best practices
#
# Key Features:
# - Automatic instance detection and management
# - Graceful shutdown and error handling
# - Comprehensive logging and state management
# - Process isolation and safety checks
# =============================================================================

import os
import sys
import time
import traceback
from pathlib import Path

import psutil

# Configure Python path to allow imports from src/
# This ensures consistent imports regardless of how the bot is launched
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import core bot components
# The bot token should be configured in your environment variables
from bot.main import DISCORD_TOKEN, bot
from src.utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_run_end,
    log_run_header,
    log_run_separator,
    log_spacing,
    log_status,
    log_user_interaction,
)

# Version information is centralized in version.py for consistency
from src.version import BOT_NAME, BOT_VERSION

# =============================================================================
# Instance Detection and Management
# =============================================================================
# This section handles multiple bot instance detection and management.
# It's crucial for preventing conflicts and ensuring clean bot operation.
#
# Key Capabilities:
# - Detects other running QuranBot instances
# - Automatically terminates conflicting instances
# - Provides detailed logging of instance management
# - Ensures only one bot instance runs per directory
# =============================================================================


def check_existing_instances():
    """
    Detect and automatically terminate existing bot instances.

    Scans running processes to find other QuranBot instances and stops them
    to prevent conflicts. Uses PID matching and working directory verification.

    Returns:
        bool: True if safe to proceed, False if critical error occurred
    """

    current_pid = os.getpid()
    bot_processes = []

    try:
        # Scan all running processes for QuranBot instances
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Skip current process
                if proc.info["pid"] == current_pid:
                    continue

                # Check for Python processes that might be running QuranBot
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline)

                        # Look for main.py in command line
                        if "main.py" in cmdline_str:
                            try:
                                # Verify it's actually QuranBot by checking working directory
                                proc_cwd = proc.cwd()
                                current_cwd = os.getcwd()

                                if "QuranBot" in proc_cwd:
                                    # Check if it's the same project directory
                                    if os.path.normpath(proc_cwd) == os.path.normpath(
                                        current_cwd
                                    ):
                                        bot_processes.append(proc)
                                    elif "QuranBot" in proc_cwd:
                                        bot_processes.append(proc)

                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Process ended or access denied - skip for safety
                                continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended or we don't have access - continue scanning
                continue

    except Exception as e:
        log_error_with_traceback("Process scanning failed during instance detection", e)
        log_perfect_tree_section(
            "Instance Detection - Warning",
            [
                ("detection_result", "⚠️ Proceeding without complete instance check"),
            ],
            "⚠️",
        )
        return True

    # Process detection results
    if not bot_processes:
        log_perfect_tree_section(
            "Instance Detection",
            [
                ("existing_instances", "None detected"),
                ("detection_result", "✅ Safe to proceed"),
            ],
            "🔍",
        )
        return True

    # Found existing instances - prepare to stop them
    instance_items = [
        ("existing_instances", f"{len(bot_processes)} found"),
    ]

    for i, proc in enumerate(bot_processes, 1):
        try:
            cmdline_display = (
                " ".join(proc.cmdline()[:3]) + "..."
                if len(proc.cmdline()) > 3
                else " ".join(proc.cmdline())
            )
            instance_items.append(
                (f"instance_{i}", f"PID {proc.pid} - {cmdline_display}")
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            instance_items.append(
                (f"instance_{i}", f"PID {proc.pid} - (process ended)")
            )

    instance_items.append(
        ("detection_result", "🤖 Automatically stopping existing instances")
    )

    log_perfect_tree_section(
        "Instance Detection",
        instance_items,
        "🔍",
    )
    log_spacing()

    # Automatically terminate existing instances
    return stop_existing_instances(bot_processes)


def stop_existing_instances(bot_processes):
    """
    Terminate existing bot instances gracefully with fallback to force kill.

    Attempts graceful shutdown first, then force kills if necessary.
    Tracks success/failure rates and provides detailed logging.

    Args:
        bot_processes: List of psutil.Process objects to terminate

    Returns:
        bool: True if termination completed (regardless of individual failures)
    """

    stopped_count = 0
    failed_count = 0
    termination_items = []

    for i, proc in enumerate(bot_processes, 1):
        try:
            termination_items.append((f"terminating_{i}", f"PID {proc.pid}"))

            # Attempt graceful termination first
            proc.terminate()

            # Wait for graceful shutdown with timeout
            try:
                proc.wait(timeout=5)
                termination_items.append(
                    (f"result_{i}", f"PID {proc.pid} - Graceful shutdown")
                )
                stopped_count += 1

            except psutil.TimeoutExpired:
                # Graceful shutdown failed - force kill
                termination_items.append(
                    (f"forcing_{i}", f"PID {proc.pid} - Timeout, force killing")
                )
                proc.kill()
                proc.wait(timeout=3)
                termination_items.append(
                    (f"result_{i}", f"PID {proc.pid} - Force killed")
                )
                stopped_count += 1

        except psutil.NoSuchProcess:
            termination_items.append(
                (f"result_{i}", f"PID {proc.pid} - Already terminated")
            )
            stopped_count += 1

        except psutil.AccessDenied:
            termination_items.append((f"result_{i}", f"PID {proc.pid} - Access denied"))
            failed_count += 1

        except Exception as e:
            log_error_with_traceback(f"Failed to terminate process PID {proc.pid}", e)
            termination_items.append(
                (f"result_{i}", f"PID {proc.pid} - Error occurred")
            )
            failed_count += 1

    # Allow time for processes to fully terminate
    if bot_processes:
        termination_items.append(
            ("cleanup_wait", "Waiting for processes to terminate...")
        )
        time.sleep(2)

    # Report final termination results
    if failed_count == 0:
        termination_items.append(
            ("termination_result", f"✅ All {stopped_count} instances terminated")
        )
        log_perfect_tree_section(
            "Instance Termination",
            termination_items,
            "🛑",
        )
    else:
        termination_items.append(
            ("termination_result", f"⚠️ {stopped_count} stopped, {failed_count} failed")
        )
        log_perfect_tree_section(
            "Instance Termination",
            termination_items,
            "🛑",
        )

    return True  # Continue execution regardless of individual failures


# =============================================================================
# Bot Initialization and Startup
# =============================================================================
# This section manages the bot's lifecycle from startup to shutdown.
#
# Implementation Details:
# - Initializes core bot systems and dependencies
# - Handles Discord connection management
# - Provides comprehensive error handling
# - Manages graceful shutdowns (both user-triggered and automatic)
# - Maintains state persistence across sessions
#
# Error Handling:
# - Catches and logs all runtime errors
# - Handles Discord-specific connection issues
# - Provides detailed crash reports for debugging
# - Ensures clean shutdown even during errors
# =============================================================================


def initialize_bot():
    """
    Initialize and start the Discord bot with proper error handling.

    Handles bot startup, runtime errors, and graceful shutdown.
    Manages state persistence and logging throughout the bot lifecycle.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """

    try:
        # Log startup information
        log_perfect_tree_section(
            "Bot Initialization",
            [
                ("bot_name", BOT_NAME),
                ("version", BOT_VERSION),
                ("discord_token", "***CONFIGURED***"),
                ("project_structure", "Organized in src/ directory"),
                ("instance_management", "✅ Completed"),
                ("entry_point", "main.py"),
            ],
            "🚀",
        )

        # Start the Discord bot with connection error handling
        try:
            bot.run(DISCORD_TOKEN)
            # Normal shutdown (this line is rarely reached)
            log_perfect_tree_section(
                "Bot Shutdown - Normal",
                [
                    ("bot_status", "✅ Bot terminated normally"),
                ],
                "✅",
            )
            return 0

        except Exception as bot_error:
            # Handle specific Discord connection errors
            error_type = type(bot_error).__name__
            error_message = str(bot_error)

            # Check for connection reset errors that are normal during shutdown
            if (
                "ClientConnectionResetError" in error_type
                or "closing transport" in error_message
            ):
                log_perfect_tree_section(
                    "Bot Shutdown - Connection Reset",
                    [
                        (
                            "connection_status",
                            "✅ Bot disconnected (connection reset during shutdown)",
                        ),
                        ("bot_status", "✅ Bot terminated normally"),
                    ],
                    "✅",
                )
                return 0
            elif "ConnectionClosed" in error_type:
                log_perfect_tree_section(
                    "Bot Shutdown - Connection Closed",
                    [
                        (
                            "connection_status",
                            "✅ Bot disconnected (connection closed)",
                        ),
                        ("bot_status", "✅ Bot terminated normally"),
                    ],
                    "✅",
                )
                return 0
            else:
                # Re-raise other errors for normal error handling
                raise bot_error

    except KeyboardInterrupt:
        # User interrupted with Ctrl+C
        log_spacing()

        # Mark shutdown in state manager
        try:
            from src.utils.state_manager import state_manager

            state_manager.mark_shutdown()

            log_perfect_tree_section(
                "User Shutdown",
                [
                    ("shutdown_reason", "User interrupt (Ctrl+C)"),
                    ("state_saved", "✅ Shutdown time recorded"),
                    ("shutdown_status", "✅ Graceful shutdown completed"),
                ],
                "👋",
            )
        except Exception as e:
            log_error_with_traceback("Failed to save shutdown state", e)
            log_perfect_tree_section(
                "User Shutdown",
                [
                    ("shutdown_reason", "User interrupt (Ctrl+C)"),
                    ("state_error", "❌ Failed to save shutdown state"),
                    ("shutdown_status", "✅ Graceful shutdown completed"),
                ],
                "👋",
            )

        return 0

    except Exception as e:
        # Bot crashed with unhandled exception
        log_spacing()
        log_error_with_traceback("Bot crashed with unhandled exception", e)

        # Mark shutdown in state manager
        try:
            from src.utils.state_manager import state_manager

            state_manager.mark_shutdown()

            log_perfect_tree_section(
                "Bot Error",
                [
                    ("state_saved", "✅ Crash time recorded"),
                    ("error_status", f"❌ Bot crashed: {str(e)}"),
                ],
                "❌",
            )
        except Exception as state_error:
            log_error_with_traceback("Failed to save crash state", state_error)
            log_perfect_tree_section(
                "Bot Error",
                [
                    ("state_error", "❌ Failed to save crash state"),
                    ("error_status", f"❌ Bot crashed: {str(e)}"),
                ],
                "❌",
            )

        return 1


# =============================================================================
# Main Entry Point
# =============================================================================
# Primary execution entry point for QuranBot
#
# Startup Flow:
# 1. Initialize logging system with unique run ID
# 2. Perform instance detection and conflict resolution
# 3. Initialize bot systems and establish Discord connection
# 4. Monitor for shutdown triggers or errors
# 5. Perform graceful shutdown and cleanup
#
# Usage:
# - Run directly: python main.py
# - Environment Setup: Ensure DISCORD_TOKEN is set
# - Dependencies: See requirements.txt for necessary packages
# - Logs: Check logs/ directory for detailed operation logs
# =============================================================================


if __name__ == "__main__":
    # Initialize logging session
    log_run_separator()
    run_id = log_run_header(BOT_NAME, BOT_VERSION)

    try:
        # Phase 1: Instance Detection and Management
        if not check_existing_instances():
            log_critical_error("Instance detection failed", "Cannot proceed safely")
            log_run_end(run_id, "Instance detection failure")
            sys.exit(1)

        # Phase 2: Bot Initialization and Runtime
        exit_code = initialize_bot()

        # Phase 3: Clean Exit
        if exit_code == 0:
            log_run_end(run_id, "Normal shutdown")
        else:
            log_run_end(run_id, "Error shutdown")

        sys.exit(exit_code)

    except Exception as e:
        # Critical error in main entry point
        log_spacing()
        log_critical_error("Fatal error in main entry point", e)
        log_perfect_tree_section(
            "Critical Error",
            [
                ("critical_status", "💥 Application failed to start"),
            ],
            "💥",
        )

        log_run_end(run_id, f"Critical failure: {str(e)}")
        sys.exit(1)
