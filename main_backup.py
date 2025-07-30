#!/usr/bin/env python3
# =============================================================================
# QuranBot - Modernized Main Entry Point
# =============================================================================
# This is the modernized main entry point that uses the modern architecture
# with dependency injection, proper service management, and error handling.
# The bot is 100% automated for continuous Quran recitation while also
# providing optional commands for interaction.
# =============================================================================

import asyncio
import os
from pathlib import Path
import signal
import sys
import time

# Add src to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import the modernized bot
from src.bot import ModernizedQuranBot

# Import tree logging for compatibility
from src.utils.tree_log import (
    log_critical_error,
    log_error_with_traceback,
    log_perfect_tree_section,
    log_run_end,
    log_run_header,
    log_run_separator,
    log_spacing,
    log_status,
)

# Import version information
from src.version import BOT_NAME, BOT_VERSION


def check_existing_instances():
    """Check for existing bot instances and handle conflicts."""
    try:
        import psutil

        # Check for existing Python processes running main.py
        current_pid = os.getpid()
        bot_processes = []

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] == "python" and proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"])
                    if "main.py" in cmdline and proc.info["pid"] != current_pid:
                        bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if bot_processes:
            log_perfect_tree_section(
                "⚠️ Existing Bot Instances Detected",
                [
                    ("instances_found", f"{len(bot_processes)} running instances"),
                    ("action", "Attempting to stop existing instances"),
                ],
                "⚠️",
            )

            # Try to stop existing instances
            for proc in bot_processes:
                try:
                    proc.terminate()
                    log_status(f"Terminated process {proc.info['pid']}", "🛑")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Wait a moment for processes to terminate
            time.sleep(2)

            # Check if any are still running
            still_running = []
            for proc in bot_processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if still_running:
                log_perfect_tree_section(
                    "⚠️ Force Stopping Remaining Instances",
                    [
                        ("remaining_instances", f"{len(still_running)} still running"),
                        ("action", "Force killing remaining processes"),
                    ],
                    "⚠️",
                )

                for proc in still_running:
                    try:
                        proc.kill()
                        log_status(f"Force killed process {proc.info['pid']}", "💀")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                time.sleep(1)

        return True

    except Exception as e:
        log_error_with_traceback("Error checking existing instances", e)
        return False


async def main():
    """
    Main entry point for the modernized bot.

    This function orchestrates the complete bot lifecycle from startup to shutdown:

    Startup Sequence:
    1. Signal handler registration for graceful shutdown
    2. Instance conflict detection and resolution
    3. Bot initialization with dependency injection
    4. Automated service activation
    5. Discord connection and event loop management

    Signal Handling:
    - SIGINT (Ctrl+C): User-initiated shutdown
    - SIGTERM: System shutdown or service management
    - Graceful cleanup with resource deallocation
    - Final state persistence before termination

    Error Management:
    - Comprehensive exception handling at the top level
    - Crash reporting with webhook notifications
    - Clean exit codes for system integration
    - Detailed logging for troubleshooting

    The function ensures reliable operation in various deployment scenarios
    including development, production, and containerized environments.
    """

    # Set up signal handlers for graceful shutdown
    bot_instance = None

    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        if bot_instance:
            # Create a task to shutdown the bot and then stop the event loop
            async def shutdown_and_exit():
                await bot_instance.shutdown()
                # Get the current event loop and stop it
                loop = asyncio.get_running_loop()
                loop.stop()

            asyncio.create_task(shutdown_and_exit())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize logging session
    log_run_separator()
    run_id = log_run_header(BOT_NAME, BOT_VERSION)

    try:
        # Phase 1: Instance Detection and Management
        if not check_existing_instances():
            log_critical_error("Instance detection failed", "Cannot proceed safely")
            log_run_end(run_id, "Instance detection failure")
            sys.exit(1)

        # Phase 2: Create and run the modernized bot
        bot_instance = ModernizedQuranBot(project_root)
        await bot_instance.run()

        # Phase 3: Clean Exit
        log_run_end(run_id, "Normal shutdown")

    except KeyboardInterrupt:
        log_spacing()
        log_perfect_tree_section(
            "User Shutdown",
            [
                ("shutdown_reason", "User interrupt (Ctrl+C)"),
                ("shutdown_status", "✅ Graceful shutdown completed"),
            ],
            "👋",
        )
        log_run_end(run_id, "User shutdown")
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
        log_run_end(run_id, f"Critical failure: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(project_root)

    # Run the modernized bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
