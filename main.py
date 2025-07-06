# =============================================================================
# QuranBot - Main Entry Point
# =============================================================================
# Primary entry point for the QuranBot Discord application
# Handles instance management, bot initialization, and graceful shutdown
# =============================================================================

import os
import sys
import time
import traceback

import psutil

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import bot components
from bot.main import BOT_NAME, BOT_VERSION, DISCORD_TOKEN, bot
from utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_run_end,
    log_run_header,
    log_run_separator,
    log_section_start,
    log_spacing,
    log_tree_branch,
    log_tree_final,
    log_warning_with_context,
)

# =============================================================================
# Instance Detection and Management
# =============================================================================


def check_existing_instances():
    """
    Detect and automatically terminate existing bot instances.

    Scans running processes to find other QuranBot instances and stops them
    to prevent conflicts. Uses PID matching and working directory verification.

    Returns:
        bool: True if safe to proceed, False if critical error occurred
    """
    log_section_start("Instance Detection", "🔍")

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
                                        log_tree_branch(
                                            "instance_found",
                                            f"PID {proc.info['pid']} (same directory)",
                                        )
                                        bot_processes.append(proc)
                                    elif "QuranBot" in proc_cwd:
                                        log_tree_branch(
                                            "instance_found",
                                            f"PID {proc.info['pid']} (different QuranBot)",
                                        )
                                        bot_processes.append(proc)

                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Process ended or access denied - skip for safety
                                continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended or we don't have access - continue scanning
                continue

    except Exception as e:
        log_error_with_traceback("Process scanning failed during instance detection", e)
        log_tree_final(
            "detection_result", "⚠️ Proceeding without complete instance check"
        )
        return True

    # Process detection results
    if not bot_processes:
        log_tree_branch("existing_instances", "None detected")
        log_tree_final("detection_result", "✅ Safe to proceed")
        return True

    # Found existing instances - prepare to stop them
    log_tree_branch("existing_instances", f"{len(bot_processes)} found")

    for i, proc in enumerate(bot_processes, 1):
        try:
            cmdline_display = (
                " ".join(proc.cmdline()[:3]) + "..."
                if len(proc.cmdline()) > 3
                else " ".join(proc.cmdline())
            )
            log_tree_branch(f"instance_{i}", f"PID {proc.pid} - {cmdline_display}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            log_tree_branch(f"instance_{i}", f"PID {proc.pid} - (process ended)")

    log_tree_final("detection_result", "🤖 Automatically stopping existing instances")
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
    log_section_start("Instance Termination", "🛑")

    stopped_count = 0
    failed_count = 0

    for i, proc in enumerate(bot_processes, 1):
        try:
            log_tree_branch(f"terminating_{i}", f"PID {proc.pid}")

            # Attempt graceful termination first
            proc.terminate()

            # Wait for graceful shutdown with timeout
            try:
                proc.wait(timeout=5)
                log_tree_branch(f"result_{i}", f"PID {proc.pid} - Graceful shutdown")
                stopped_count += 1

            except psutil.TimeoutExpired:
                # Graceful shutdown failed - force kill
                log_tree_branch(
                    f"forcing_{i}", f"PID {proc.pid} - Timeout, force killing"
                )
                proc.kill()
                proc.wait(timeout=3)
                log_tree_branch(f"result_{i}", f"PID {proc.pid} - Force killed")
                stopped_count += 1

        except psutil.NoSuchProcess:
            log_tree_branch(f"result_{i}", f"PID {proc.pid} - Already terminated")
            stopped_count += 1

        except psutil.AccessDenied:
            log_tree_branch(f"result_{i}", f"PID {proc.pid} - Access denied")
            failed_count += 1

        except Exception as e:
            log_error_with_traceback(f"Failed to terminate process PID {proc.pid}", e)
            failed_count += 1

    # Allow time for processes to fully terminate
    if bot_processes:
        log_tree_branch("cleanup_wait", "Waiting for processes to terminate...")
        time.sleep(2)

    # Report final termination results
    if failed_count == 0:
        log_tree_final(
            "termination_result", f"✅ All {stopped_count} instances terminated"
        )
    else:
        log_tree_final(
            "termination_result", f"⚠️ {stopped_count} stopped, {failed_count} failed"
        )

    return True  # Continue execution regardless of individual failures


# =============================================================================
# Bot Initialization and Startup
# =============================================================================


def initialize_bot():
    """
    Initialize and start the Discord bot with proper error handling.

    Handles bot startup, runtime errors, and graceful shutdown.
    Manages state persistence and logging throughout the bot lifecycle.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    log_section_start(f"Bot Initialization", "🚀")

    try:
        # Log startup information
        log_tree_branch("bot_name", BOT_NAME)
        log_tree_branch("version", BOT_VERSION)
        log_tree_branch("discord_token", "***CONFIGURED***")
        log_tree_branch("project_structure", "Organized in src/ directory")
        log_tree_branch("instance_management", "✅ Completed")
        log_tree_final("entry_point", "main.py")

        log_spacing()
        log_section_start("Discord Bot Runtime", "🤖")

        # Start the Discord bot
        bot.run(DISCORD_TOKEN)

        # Normal shutdown (this line is rarely reached)
        log_tree_final("bot_status", "✅ Bot terminated normally")
        return 0

    except KeyboardInterrupt:
        # User interrupted with Ctrl+C
        log_spacing()
        log_section_start("User Shutdown", "👋")
        log_tree_branch("shutdown_reason", "User interrupt (Ctrl+C)")

        # Mark shutdown in state manager
        try:
            from src.utils.state_manager import state_manager

            state_manager.mark_shutdown()
            log_tree_branch("state_saved", "✅ Shutdown time recorded")
        except Exception as e:
            log_error_with_traceback("Failed to save shutdown state", e)

        log_tree_final("shutdown_status", "✅ Graceful shutdown completed")
        return 0

    except Exception as e:
        # Bot crashed with unhandled exception
        log_spacing()
        log_section_start("Bot Error", "❌")
        log_error_with_traceback("Bot crashed with unhandled exception", e)

        # Mark shutdown in state manager
        try:
            from src.utils.state_manager import state_manager

            state_manager.mark_shutdown()
            log_tree_branch("state_saved", "✅ Crash time recorded")
        except Exception as state_error:
            log_error_with_traceback("Failed to save crash state", state_error)

        log_tree_final("error_status", f"❌ Bot crashed: {str(e)}")
        return 1


# =============================================================================
# Main Entry Point
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
        log_section_start("Critical Error", "💥")
        log_critical_error("Fatal error in main entry point", e)
        log_tree_final("critical_status", "💥 Application failed to start")

        log_run_end(run_id, f"Critical failure: {str(e)}")
        sys.exit(1)
