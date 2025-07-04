#!/usr/bin/env python3
"""
Discord Quran Bot - Main Entry Point
Professional 24/7 Quran streaming bot with comprehensive logging and error handling.

This module serves as the main entry point for the Quran Bot application.
It handles startup initialization, logging setup, and graceful error handling.

Usage:
    python run.py

Features:
    - Comprehensive logging with different levels
    - Graceful error handling and recovery
    - Startup validation and health checks
    - Clean shutdown procedures
"""

import sys
import os
import traceback
import psutil
import signal
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.monitoring.logging.logger import logger
from src.monitoring.logging.tree_log import tree_log


def check_existing_instance():
    """
    Check if another instance of the bot is already running.
    
    Returns:
        bool: True if no other instance is running, False if another instance exists
    """
    try:
        current_pid = os.getpid()
        current_cmdline = ['python', 'run.py']
        
        # Check all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                
                # Check if it's a Python process running run.py
                if (proc.info['name'] and 'python' in proc.info['name'].lower() and 
                    proc.info['cmdline'] and len(proc.info['cmdline']) >= 2):
                    
                    cmdline = proc.info['cmdline']
                    if 'run.py' in ' '.join(cmdline):
                        tree_log('warning', f"Found existing QuranBot instance", {
                            'event': 'EXISTING_INSTANCE_FOUND',
                            'existing_pid': proc.info['pid'],
                            'existing_cmdline': cmdline,
                            'current_pid': current_pid
                        })
                        
                        # Ask user what to do
                        print(f"\n⚠️  Another QuranBot instance is already running (PID: {proc.info['pid']})")
                        print("Options:")
                        print("1. Stop the existing instance and start this one")
                        print("2. Exit and let the existing instance continue")
                        
                        while True:
                            choice = input("\nEnter your choice (1 or 2): ").strip()
                            if choice == '1':
                                tree_log('info', f"Stopping existing instance (PID: {proc.info['pid']})", {
                                    'event': 'STOPPING_EXISTING_INSTANCE',
                                    'existing_pid': proc.info['pid']
                                })
                                try:
                                    # Try graceful shutdown first
                                    proc.terminate()
                                    proc.wait(timeout=10)
                                    tree_log('info', "Existing instance stopped gracefully", {
                                        'event': 'EXISTING_INSTANCE_STOPPED',
                                        'method': 'graceful'
                                    })
                                except psutil.TimeoutExpired:
                                    # Force kill if graceful shutdown fails
                                    proc.kill()
                                    tree_log('warning', "Existing instance force killed", {
                                        'event': 'EXISTING_INSTANCE_KILLED',
                                        'method': 'force'
                                    })
                                except Exception as e:
                                    tree_log('error', f"Failed to stop existing instance: {e}", {
                                        'event': 'STOP_EXISTING_FAILED',
                                        'error': str(e)
                                    })
                                    return False
                                return True
                            elif choice == '2':
                                tree_log('info', "User chose to exit - keeping existing instance", {
                                    'event': 'USER_EXIT_KEEP_EXISTING'
                                })
                                return False
                            else:
                                print("Please enter 1 or 2")
                                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Process might have ended or we don't have permission
                continue
        
        tree_log('info', "No existing QuranBot instance found", {'event': 'NO_EXISTING_INSTANCE'})
        return True
        
    except Exception as e:
        tree_log('error', f"Error checking existing instance: {e}", {
            'event': 'CHECK_EXISTING_ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        return True  # Continue if we can't check


def validate_environment():
    """
    Validate the runtime environment and dependencies.

    Returns:
        bool: True if environment is valid, False otherwise
    """
    try:
        # Check if we're in the correct directory
        if not Path("src").exists():
            tree_log('error', "Invalid working directory: 'src' folder not found", {'event': 'ENV_VALIDATE', 'cwd': str(os.getcwd())})
            return False

        # Check for required directories
        required_dirs = ["data", "logs", "audio"]
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                tree_log('warning', f"Directory '{dir_name}' not found - creating it", {'event': 'DIR_CREATE', 'dir': dir_name})
                Path(dir_name).mkdir(exist_ok=True)

        tree_log('info', "Environment validation completed successfully", {'event': 'ENV_VALIDATE'})
        return True

    except Exception as e:
        tree_log('error', f"Environment validation failed: {e}", {'event': 'ENV_VALIDATE', 'traceback': traceback.format_exc()})
        return False


def setup_exception_handling():
    """Set up global exception handling for uncaught errors."""

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions with comprehensive logging."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle graceful shutdown
            tree_log('info', "Received interrupt signal - shutting down gracefully", {'event': 'SHUTDOWN', 'type': str(exc_type)})
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Log the full exception details
        tree_log('critical', f"Uncaught exception: {exc_type.__name__}: {exc_value}", {
            'event': 'UNCAUGHT_EXCEPTION',
            'type': exc_type.__name__,
            'value': str(exc_value),
            'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        })

    sys.excepthook = handle_exception


def main():
    """
    Main entry point for the Quran Bot application.

    This function handles:
    - Environment validation
    - Logging setup
    - Exception handling configuration
    - Bot initialization and startup
    - Graceful shutdown procedures
    """
    try:
        tree_log('info', "QuranBot startup initiated", {'event': 'STARTUP'})
        tree_log('info', "=" * 50)
        
        # Check for existing instances first
        tree_log('info', "Checking for existing QuranBot instances...", {'event': 'INSTANCE_CHECK_START'})
        if not check_existing_instance():
            tree_log('info', "Exiting due to existing instance or user choice", {'event': 'EXIT_EXISTING_INSTANCE'})
            sys.exit(0)
        
        tree_log('info', "Starting environment validation...", {'event': 'ENV_VALIDATE_START'})

        # Validate environment
        if not validate_environment():
            tree_log('error', "Environment validation failed - exiting", {'event': 'ENV_VALIDATE_FAIL'})
            sys.exit(1)

        # Setup exception handling
        setup_exception_handling()
        tree_log('info', "Exception handling configured", {'event': 'EXCEPTION_HOOK'})

        # Import and start the bot
        tree_log('info', "Importing bot modules...", {'event': 'IMPORT_BOT'})
        from src.bot.quran_bot import main as bot_main

        tree_log('info', "Starting Quran Bot...", {'event': 'BOT_START'})
        bot_main()

    except ImportError as e:
        tree_log('error', f"Import error: {e}", {'event': 'IMPORT_ERROR', 'traceback': traceback.format_exc()})
        tree_log('info', "Make sure all dependencies are installed: pip install -r requirements.txt", {'event': 'DEPENDENCY_HINT'})
        sys.exit(1)

    except Exception as e:
        tree_log('error', f"Startup failed: {e}", {'event': 'STARTUP_FAIL', 'traceback': traceback.format_exc()})
        sys.exit(1)

    finally:
        tree_log('info', "QuranBot shutdown complete", {'event': 'SHUTDOWN'})


if __name__ == "__main__":
    main()
