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

# Add app to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "app"))

from app.bot import QuranBot
from app.core.logger import TreeLogger


def check_existing_instances():
    """
    Detect and automatically terminate existing bot instances.

    This function prevents multiple QuranBot instances from running simultaneously
    to avoid conflicts with Discord API, voice channels, and database access.
    
    Process Detection Strategy:
    1. Scan all running processes for Python executables
    2. Check command line arguments for main.py or main_new.py
    3. Verify working directory contains "QuranBot"
    4. Compare normalized paths to ensure same project instance

    Returns:
        bool: True if safe to proceed, False if critical error occurred
    """
    current_pid = os.getpid()
    bot_processes = []

    try:
        # Scan all running processes for QuranBot instances
        # Using psutil to iterate through system processes with required attributes
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Skip current process to avoid self-termination
                if proc.info["pid"] == current_pid:
                    continue

                # Check if process is a Python interpreter
                if proc.info["name"] and "python" in proc.info["name"].lower():
                    cmdline = proc.info["cmdline"]
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        # Look for QuranBot main entry points
                        if "main.py" in cmdline_str or "main_new.py" in cmdline_str:
                            try:
                                # Verify this is the same QuranBot project instance
                                proc_cwd = proc.cwd()
                                current_cwd = os.getcwd()
                                if "QuranBot" in proc_cwd:
                                    # Normalize paths to handle different path formats
                                    if os.path.normpath(proc_cwd) == os.path.normpath(
                                        current_cwd
                                    ):
                                        bot_processes.append(proc)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # Process may have terminated or access denied - skip
                                continue

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    except Exception as e:
        # If process scanning fails, log error but continue startup
        # This ensures the bot can still start even if instance detection fails
        TreeLogger.error("Process scanning failed during instance detection", e, service="QuranBot")
        TreeLogger.warning("Instance Detection - Warning", {
            "detection_result": "⚠️ Proceeding without complete instance check"
        }, service="QuranBot")
        return True

    # No existing instances found - safe to proceed
    if not bot_processes:
        TreeLogger.info("Instance Detection", {
            "existing_instances": "None detected",
            "detection_result": "✅ Safe to proceed"
        }, service="QuranBot")
        return True

    # Found existing instances - initiate automatic termination
    TreeLogger.info("Instance Detection", {
        "existing_instances": f"{len(bot_processes)} found",
        "detection_result": "🤖 Automatically stopping existing instances"
    }, service="QuranBot")

    return stop_existing_instances(bot_processes)


def stop_existing_instances(bot_processes):
    """
    Terminate existing bot instances gracefully with fallback to force kill.
    
    Termination Strategy:
    1. Send SIGTERM for graceful shutdown (5 second timeout)
    2. Send SIGKILL if graceful shutdown fails (3 second timeout)
    3. Handle process access permissions and race conditions
    4. Report termination results with detailed logging

    Args:
        bot_processes (list): List of psutil.Process objects to terminate

    Returns:
        bool: True if termination process completed (always returns True)
    """
    stopped_count = 0
    failed_count = 0

    for proc in bot_processes:
        try:
            # Step 1: Attempt graceful termination with SIGTERM
            proc.terminate()

            try:
                # Wait up to 5 seconds for graceful shutdown
                proc.wait(timeout=5)
                stopped_count += 1
            except psutil.TimeoutExpired:
                # Step 2: Force kill if graceful shutdown failed
                proc.kill()
                proc.wait(timeout=3)  # Wait for force kill to complete
                stopped_count += 1

        except psutil.NoSuchProcess:
            # Process already terminated - count as success
            stopped_count += 1
        except psutil.AccessDenied:
            # Insufficient permissions to terminate process
            failed_count += 1
        except Exception as e:
            # Unexpected error during termination
            TreeLogger.error(f"Failed to terminate process PID {proc.pid}", e, service="QuranBot")
            failed_count += 1

    # Allow time for processes to fully terminate and release resources
    if bot_processes:
        time.sleep(2)

    # Report termination results with appropriate log level
    if failed_count == 0:
        TreeLogger.info("Instance Termination", {
            "termination_result": f"✅ All {stopped_count} instances terminated"
        }, service="QuranBot")
    else:
        TreeLogger.warning("Instance Termination", {
            "termination_result": f"⚠️ {stopped_count} stopped, {failed_count} failed"
        }, service="QuranBot")

    return True  # Always return True to allow bot startup to continue


async def main():
    """
    Main entry point for the QuranBot application.

    This function orchestrates the complete bot lifecycle from startup to shutdown,
    including instance management, signal handling, initialization, and cleanup.
    
    Lifecycle Flow:
    1. Set up signal handlers for graceful shutdown
    2. Generate unique run ID for session tracking
    3. Check for and terminate existing instances
    4. Initialize bot with dependency injection
    5. Start Discord connection and event loop
    6. Handle shutdown and cleanup on exit
    """
    bot_instance = None

    def signal_handler(signum, frame):
        """
        Handle shutdown signals gracefully.
        
        Responds to SIGINT (Ctrl+C) and SIGTERM signals by initiating
        a clean shutdown sequence that properly closes Discord connections
        and releases resources.
        
        Args:
            signum (int): Signal number received
            frame: Current stack frame (unused)
        """
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        if bot_instance:
            # Create async task to handle shutdown without blocking signal handler
            async def shutdown_and_exit():
                await bot_instance.shutdown()
                loop = asyncio.get_running_loop()
                loop.stop()

            asyncio.create_task(shutdown_and_exit())

    # Set up signal handlers for graceful shutdown
    # SIGINT: Interrupt signal (Ctrl+C)
    # SIGTERM: Termination request from system
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Generate unique run ID for session tracking and debugging
        run_id = f"run_{int(time.time())}"

        TreeLogger.info("🚀 QuranBot Starting", {
            "run_id": run_id,
            "architecture": "Modular with Dependency Injection",
            "mode": "100% Automated + Interactive Commands"
        }, service="QuranBot")

        # Phase 1: Instance Management
        # Check for existing instances and terminate them to prevent conflicts
        TreeLogger.info("Checking for existing instances", service="QuranBot")
        if not check_existing_instances():
            TreeLogger.error("Failed to resolve instance conflicts", service="QuranBot")
            return

        # Phase 2: Bot Initialization
        # Initialize bot with modular architecture and dependency injection
        TreeLogger.info("Initializing bot", service="QuranBot")
        bot_instance = QuranBot()

        # Phase 3: Discord Connection
        # Get configuration and establish connection to Discord API
        config = bot_instance.config
        TreeLogger.info("Starting bot with Discord token", service="QuranBot")

        # Start the bot (this will run until shutdown signal received)
        await bot_instance.start(config.discord_token)

        # This line is reached only on normal shutdown
        TreeLogger.info("Normal shutdown", service="QuranBot")

    except KeyboardInterrupt:
        # Handle Ctrl+C interrupt gracefully
        TreeLogger.info("🛑 Shutdown Requested", {
            "trigger": "User interrupt (Ctrl+C)",
            "status": "Initiating graceful shutdown"
        }, service="QuranBot")
        if bot_instance:
            await bot_instance.shutdown()

    except Exception as e:
        # Handle any unexpected errors during bot operation
        TreeLogger.error(f"Critical error in main: {e}", service="QuranBot")
        if bot_instance:
            await bot_instance.shutdown()

    finally:
        # Ensure cleanup always occurs regardless of how we exit
        TreeLogger.info("🏁 QuranBot Stopped", {
            "status": "All processes terminated",
            "cleanup": "Resources released"
        }, service="QuranBot")


# =============================================================================
# Application Entry Point
# =============================================================================
if __name__ == "__main__":
    # Ensure we're running from the correct project directory
    os.chdir(project_root)

    try:
        # Start the async event loop and run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle final Ctrl+C if it bypasses the signal handler
        print("\n🛑 Bot shutdown requested by user")
    except Exception as e:
        # Handle any fatal errors that prevent startup
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
