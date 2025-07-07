# =============================================================================
# QuranBot - Bot Manager Utility
# =============================================================================
# Easy management of bot instances with start, stop, restart, and status commands
# =============================================================================

import os
import signal
import subprocess
import sys
import time
import traceback

import psutil

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import logging utilities
from src.utils.tree_log import (
    log_error_with_traceback,
    log_perfect_tree_section,
    log_spacing,
    log_status,
    log_user_interaction,
    log_warning_with_context,
)

BOT_NAME = "QuranBot"
MAIN_SCRIPT = "main.py"


def find_bot_processes():
    """Find all running bot processes."""
    current_pid = os.getpid()
    bot_processes = []

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
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
                                        bot_processes.append(proc)
                                    elif "QuranBot" in proc_cwd:
                                        # Regular QuranBot process
                                        bot_processes.append(proc)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                # If we can't get cwd, skip this process for safety
                                pass

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    except Exception as e:
        log_error_with_traceback("Failed to scan processes for bot instances", e)

    return bot_processes


def format_uptime(seconds):
    """Format uptime in a human-readable way."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def status_command():
    """Check the status of bot instances."""

    bot_processes = find_bot_processes()

    if not bot_processes:
        log_perfect_tree_section(
            "Bot Status Check",
            [
                ("status", "No bot instances running"),
                ("result", "✅ Bot is offline"),
            ],
            "📊",
        )
        return False

    # Collect process information
    process_items = [
        ("instances_found", f"{len(bot_processes)} instance(s)"),
        ("result", "🟢 Bot is online"),
    ]

    for i, proc in enumerate(bot_processes, 1):
        try:
            # Get process information
            create_time = proc.create_time()
            uptime = time.time() - create_time
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            process_items.extend(
                [
                    (f"instance_{i}_pid", f"PID {proc.pid}"),
                    (f"instance_{i}_uptime", format_uptime(uptime)),
                    (f"instance_{i}_memory", f"{memory_mb:.1f} MB"),
                    (f"instance_{i}_command", " ".join(proc.cmdline())),
                ]
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log_warning_with_context(
                f"Could not get process info for PID {proc.pid}", str(e)
            )
            process_items.append(
                (f"instance_{i}_error", f"PID {proc.pid} - Info unavailable")
            )

    log_perfect_tree_section(
        "Bot Status Check",
        process_items,
        "📊",
    )
    return True


def start_command():
    """Start the bot."""

    # Check if already running
    if find_bot_processes():
        log_perfect_tree_section(
            "Starting Bot",
            [
                ("error", "Bot is already running"),
                ("status", "❌ Use 'restart' to restart or 'stop' to stop first"),
            ],
            "🚀",
        )
        return False

    try:
        # Start the bot in the background
        if os.name == "nt":  # Windows
            subprocess.Popen(
                [sys.executable, MAIN_SCRIPT],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:  # Unix-like
            subprocess.Popen([sys.executable, MAIN_SCRIPT], start_new_session=True)

        # Wait a moment and check if it started
        time.sleep(3)

        if find_bot_processes():
            log_perfect_tree_section(
                "Starting Bot",
                [
                    ("command", f"python {MAIN_SCRIPT}"),
                    ("mode", "Background process"),
                    ("status", "✅ Bot started successfully"),
                    ("verification", "Process confirmed running"),
                ],
                "🚀",
            )
            return True
        else:
            log_perfect_tree_section(
                "Starting Bot",
                [
                    ("command", f"python {MAIN_SCRIPT}"),
                    ("mode", "Background process"),
                    ("status", "❌ Bot failed to start"),
                    ("verification", "Process not found after launch"),
                ],
                "🚀",
            )
            return False

    except Exception as e:
        log_error_with_traceback("Failed to start bot process", e)
        log_perfect_tree_section(
            "Starting Bot",
            [
                ("status", "❌ Failed to start bot"),
                ("error_type", type(e).__name__),
            ],
            "🚀",
        )
        return False


def stop_command():
    """Stop all bot instances."""

    bot_processes = find_bot_processes()

    if not bot_processes:
        log_perfect_tree_section(
            "Stopping Bot",
            [
                ("status", "No bot instances running"),
                ("result", "✅ Bot is already offline"),
            ],
            "🛑",
        )
        return True

    # Collect stop results
    stop_items = [
        ("instances_found", f"{len(bot_processes)} instance(s)"),
    ]

    stopped_count = 0
    failed_count = 0

    for proc in bot_processes:
        try:
            stop_items.append(("stopping", f"PID {proc.pid}"))

            # First try graceful termination
            proc.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                proc.wait(timeout=5)
                stop_items.append(("result", f"PID {proc.pid} - Gracefully stopped"))
                stopped_count += 1
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                stop_items.append(("forcing", f"PID {proc.pid} - Force killing"))
                proc.kill()
                proc.wait(timeout=3)
                stop_items.append(("result", f"PID {proc.pid} - Force killed"))
                stopped_count += 1

        except psutil.NoSuchProcess:
            stop_items.append(("result", f"PID {proc.pid} - Already stopped"))
            stopped_count += 1
        except psutil.AccessDenied:
            stop_items.append(("result", f"PID {proc.pid} - Access denied"))
            failed_count += 1
        except Exception as e:
            log_error_with_traceback(f"Error stopping process PID {proc.pid}", e)
            stop_items.append(("result", f"PID {proc.pid} - Error occurred"))
            failed_count += 1

    if failed_count == 0:
        stop_items.append(("status", f"✅ All {stopped_count} instances stopped"))
        log_perfect_tree_section(
            "Stopping Bot",
            stop_items,
            "🛑",
        )
        return True
    else:
        stop_items.append(
            ("status", f"⚠️ {stopped_count} stopped, {failed_count} failed")
        )
        log_perfect_tree_section(
            "Stopping Bot",
            stop_items,
            "🛑",
        )
        return False


def restart_command():
    """Restart the bot."""

    stop_success = stop_command()

    if stop_success:
        time.sleep(2)  # Wait a moment between stop and start
        start_success = start_command()

        if start_success:
            log_perfect_tree_section(
                "Restarting Bot",
                [
                    ("status", "✅ Bot restarted successfully"),
                    ("step_1", "✅ Stop completed"),
                    ("step_2", "✅ Start completed"),
                    ("wait_time", "2 seconds between steps"),
                ],
                "🔄",
            )
            return True
        else:
            log_perfect_tree_section(
                "Restarting Bot",
                [
                    ("status", "❌ Failed to start after stop"),
                    ("step_1", "✅ Stop completed"),
                    ("step_2", "❌ Start failed"),
                ],
                "🔄",
            )
            return False
    else:
        log_perfect_tree_section(
            "Restarting Bot",
            [
                ("status", "❌ Failed to stop existing instances"),
                ("step_1", "❌ Stop failed"),
                ("step_2", "⏸️ Start not attempted"),
            ],
            "🔄",
        )
        return False


def show_help():
    """Show help information."""
    print(
        f"""
# =============================================================================
# {BOT_NAME} - Bot Manager
# =============================================================================

Usage: python bot_manager.py <command>

Commands:
  start     Start the bot in the background
  stop      Stop all bot instances
  restart   Restart the bot (stop + start)
  status    Check bot status and uptime
  help      Show this help message

Examples:
  python bot_manager.py start
  python bot_manager.py status
  python bot_manager.py restart
  python bot_manager.py stop

# =============================================================================
"""
    )


def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) != 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "start":
        start_command()
    elif command == "stop":
        stop_command()
    elif command == "restart":
        restart_command()
    elif command == "status":
        status_command()
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
