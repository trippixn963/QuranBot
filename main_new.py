#!/usr/bin/env python3
# =============================================================================
# QuranBot - Simplified Main Entry Point
# =============================================================================
# Simplified main entry point using modular architecture.
# The bot functionality has been broken down into focused modules for better
# maintainability and separation of concerns.
# =============================================================================

import asyncio
import os
from pathlib import Path
import signal
import sys
import time

import psutil

# Add src to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.bot import ModernizedQuranBot
from src.utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_run_end,
    log_spacing,
    log_status,
)


def check_existing_instances():
    """
    Detect and automatically terminate existing bot instances.

    This function prevents multiple QuranBot instances from running simultaneously
    to avoid conflicts with Discord API, voice channels, and database access.

    Returns:
        bool: True if safe to proceed, False if critical error occurred
    """
    current_pid = os.getpid()
    bot_processes = []

    try:
        # Scan all running processes for QuranBot instances
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] == current_pid:
                    continue

                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if "main.py" in cmdline_str or "main_new.py" in cmdline_str:
                            try:
                                proc_cwd = proc.cwd()
                                current_cwd = os.getcwd()
                                if "QuranBot" in proc_cwd:
                                    if os.path.normpath(proc_cwd) == os.path.normpath(
                                        current_cwd
                                    ):
                                        bot_processes.append(proc)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    except Exception as e:
        log_error_with_traceback("Process scanning failed during instance detection", e)
        log_perfect_tree_section(
            "Instance Detection - Warning",
            [("detection_result", "⚠️ Proceeding without complete instance check")],
            "⚠️",
        )
        return True

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

    # Found existing instances - terminate them
    log_perfect_tree_section(
        "Instance Detection",
        [
            ("existing_instances", f"{len(bot_processes)} found"),
            ("detection_result", "🤖 Automatically stopping existing instances"),
        ],
        "🔍",
    )

    return stop_existing_instances(bot_processes)


def stop_existing_instances(bot_processes):
    """
    Terminate existing bot instances gracefully with fallback to force kill.

    Args:
        bot_processes: List of psutil.Process objects to terminate

    Returns:
        bool: True if termination process completed
    """
    stopped_count = 0
    failed_count = 0

    for proc in bot_processes:
        try:
            # Attempt graceful termination first
            proc.terminate()

            try:
                proc.wait(timeout=5)
                stopped_count += 1
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                proc.kill()
                proc.wait(timeout=3)
                stopped_count += 1

        except psutil.NoSuchProcess:
            stopped_count += 1
        except psutil.AccessDenied:
            failed_count += 1
        except Exception as e:
            log_error_with_traceback(f"Failed to terminate process PID {proc.pid}", e)
            failed_count += 1

    # Allow time for processes to fully terminate
    if bot_processes:
        time.sleep(2)

    # Report results
    if failed_count == 0:
        log_perfect_tree_section(
            "Instance Termination",
            [("termination_result", f"✅ All {stopped_count} instances terminated")],
            "🛑",
        )
    else:
        log_perfect_tree_section(
            "Instance Termination",
            [
                (
                    "termination_result",
                    f"⚠️ {stopped_count} stopped, {failed_count} failed",
                )
            ],
            "🛑",
        )

    return True


async def main():
    """
    Main entry point for the modernized bot.

    This function orchestrates the complete bot lifecycle from startup to shutdown
    using the modular architecture with proper separation of concerns.
    """
    bot_instance = None

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        if bot_instance:

            async def shutdown_and_exit():
                await bot_instance.shutdown()
                loop = asyncio.get_running_loop()
                loop.stop()

            asyncio.create_task(shutdown_and_exit())

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Generate unique run ID for this session
        run_id = f"run_{int(time.time())}"

        log_perfect_tree_section(
            "🚀 QuranBot Starting",
            [
                ("run_id", run_id),
                ("architecture", "Modular with Dependency Injection"),
                ("mode", "100% Automated + Interactive Commands"),
            ],
        )

        # Check for existing instances and terminate them
        log_status("Checking for existing instances", "🔍")
        if not check_existing_instances():
            log_critical_error("Failed to resolve instance conflicts")
            return

        log_spacing()

        # Initialize and run the modernized bot
        log_status("Initializing modernized bot", "🏗️")
        bot_instance = ModernizedQuranBot(project_root)

        # Run the bot
        await bot_instance.run()

        log_run_end(run_id, "Normal shutdown")

    except KeyboardInterrupt:
        log_spacing()
        log_perfect_tree_section(
            "🛑 Shutdown Requested",
            [
                ("trigger", "User interrupt (Ctrl+C)"),
                ("status", "Initiating graceful shutdown"),
            ],
        )
        if bot_instance:
            await bot_instance.shutdown()

    except Exception as e:
        log_critical_error(f"Critical error in main: {e}")
        log_error_with_traceback("Main function error", e)
        if bot_instance:
            await bot_instance.shutdown()

    finally:
        log_perfect_tree_section(
            "🏁 QuranBot Stopped",
            [
                ("status", "All processes terminated"),
                ("cleanup", "Resources released"),
            ],
        )


if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(project_root)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
