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
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.monitoring.logging.logger import logger
from src.monitoring.logging.tree_log import tree_log


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
        from bot.quran_bot import main as bot_main

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
