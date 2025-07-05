# =============================================================================
# QuranBot - Main Entry Point
# =============================================================================
# Entry point for the QuranBot application with proper project structure
# Includes instance detection to prevent multiple bot instances
# =============================================================================

import os
import sys
import time
import traceback

import psutil

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import and run the bot
from bot.main import BOT_NAME, BOT_VERSION, DISCORD_TOKEN, bot
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


def check_existing_instances():
    """
    Check for existing bot instances and automatically stop them.
    Returns True if we should continue, False if we should exit.
    """
    log_section_start("Instance Detection", "🔍")

    current_pid = os.getpid()
    bot_processes = []

    try:
        # Look for other Python processes running this bot
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Skip our own process
                if proc.info["pid"] == current_pid:
                    continue

                # Check if it's a Python process (including virtual environments)
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        # Check if it's running main.py and verify it's in QuranBot directory
                        if "main.py" in cmdline_str:
                            # Additional verification: check working directory
                            try:
                                proc_cwd = proc.cwd()
                                if "QuranBot" in proc_cwd:
                                    # Extra verification for virtual environments
                                    # Check if it's running from the same project directory
                                    current_cwd = os.getcwd()
                                    if os.path.normpath(proc_cwd) == os.path.normpath(
                                        current_cwd
                                    ):
                                        log_tree_branch(
                                            "venv_detected",
                                            f"Virtual environment process detected",
                                        )
                                        bot_processes.append(proc)
                                    elif "QuranBot" in proc_cwd:
                                        # Regular QuranBot process
                                        bot_processes.append(proc)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # If we can't get cwd, skip this process for safety
                                pass

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended or we don't have access
                continue

    except Exception as e:
        log_error_with_traceback(
            "Failed to check processes during instance detection", e
        )
        log_tree_final("status", "Proceeding without instance check")
        return True

    if not bot_processes:
        log_tree_branch("existing_instances", "None found")
        log_tree_final("status", "✅ Safe to proceed")
        return True

    # Found existing instances - automatically stop them
    log_tree_branch("existing_instances", f"Found {len(bot_processes)} instance(s)")

    for i, proc in enumerate(bot_processes, 1):
        try:
            log_tree_branch(
                f"instance_{i}", f"PID {proc.pid} - {' '.join(proc.cmdline())}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            log_tree_branch(f"instance_{i}", f"PID {proc.pid} - (process ended)")

    log_tree_final("action", "🤖 Automatically stopping existing instances...")

    # Automatically stop existing instances
    return stop_existing_instances(bot_processes)


def stop_existing_instances(bot_processes):
    """
    Stop existing bot instances.
    Returns True if successful, False otherwise.
    """
    log_section_start("Stopping Bot", "🛑")

    stopped_count = 0
    failed_count = 0

    for proc in bot_processes:
        try:
            log_tree_branch("stopping", f"PID {proc.pid}")

            # First try graceful termination
            proc.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                proc.wait(timeout=5)
                log_tree_branch("result", f"PID {proc.pid} - Gracefully stopped")
                stopped_count += 1
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                log_tree_branch("forcing", f"PID {proc.pid} - Graceful shutdown failed")
                proc.kill()
                proc.wait(timeout=3)
                log_tree_branch("result", f"PID {proc.pid} - Force killed")
                stopped_count += 1

        except psutil.NoSuchProcess:
            log_tree_branch("result", f"PID {proc.pid} - Already stopped")
            stopped_count += 1
        except psutil.AccessDenied:
            log_tree_branch("result", f"PID {proc.pid} - Access denied")
            failed_count += 1
        except Exception as e:
            log_error_with_traceback(f"Error stopping process PID {proc.pid}", e)
            failed_count += 1

    # Wait a moment for processes to fully stop
    time.sleep(2)

    if failed_count == 0:
        log_tree_final("status", f"✅ All {stopped_count} instances stopped")
        return True
    else:
        log_tree_final(
            "status",
            f"⚠️ {stopped_count} stopped, {failed_count} failed - continuing anyway",
        )
        return True  # Continue anyway since this is automated


if __name__ == "__main__":
    # Add run separator to distinguish between different runs
    log_run_separator()

    # Log run header with unique run ID
    run_id = log_run_header(BOT_NAME, BOT_VERSION)

    try:
        # Check for existing instances first
        if not check_existing_instances():
            log_run_end(run_id, "Instance check failed")
            print("\nExiting...")
            sys.exit(0)

        # Start the bot
        log_section_start(f"Starting {BOT_NAME} v{BOT_VERSION}...", "🚀")
        log_tree_branch("version", BOT_VERSION)
        log_tree_branch("discord_token", "***HIDDEN***")
        log_tree_branch("structure", "Organized in src/ directory")
        log_tree_branch("instance_check", "✅ Passed (automated)")
        log_tree_final("entry_point", "main.py")

        try:
            bot.run(DISCORD_TOKEN)
        except KeyboardInterrupt:
            log_section_start("Shutdown", "👋")
            log_tree_final("status", "Bot stopped by user")
            log_run_end(run_id, "User interrupt (Ctrl+C)")
        except Exception as e:
            log_section_start("Error", "❌")
            log_error_with_traceback("Bot crashed with unhandled exception", e)
            log_tree_final("status", "Bot crashed")
            log_run_end(run_id, f"Crashed: {str(e)}")
            raise

    except Exception as e:
        log_critical_error("Fatal error in main entry point", e)
        log_run_end(run_id, f"Fatal error: {str(e)}")
        raise
