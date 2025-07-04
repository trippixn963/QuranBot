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


def validate_environment():
    """
    Validate the runtime environment and dependencies.

    Returns:
        bool: True if environment is valid, False otherwise
    """
    try:
        # Check if we're in the correct directory
        if not Path("src").exists():
            logger.error("❌ Invalid working directory: 'src' folder not found")
            return False

        # Check for required directories
        required_dirs = ["data", "logs", "audio"]
        for dir_name in required_dirs:
            if not Path(dir_name).exists():
                logger.warning(f"⚠️  Directory '{dir_name}' not found - creating it")
                Path(dir_name).mkdir(exist_ok=True)

        logger.info("✅ Environment validation completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        return False


def setup_exception_handling():
    """Set up global exception handling for uncaught errors."""

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions with comprehensive logging."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle graceful shutdown
            logger.info("🛑 Received interrupt signal - shutting down gracefully")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Log the full exception details
        logger.critical(
            f"💥 Uncaught exception: {exc_type.__name__}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        # Log additional context
        logger.critical("🔍 Exception context:")
        logger.critical(f"   Type: {exc_type.__name__}")
        logger.critical(f"   Value: {exc_value}")
        logger.critical(f"   Traceback: {traceback.format_tb(exc_traceback)}")

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
        logger.info("🚀 QuranBot startup initiated")
        logger.info("=" * 50)
        logger.info("📋 Starting environment validation...")

        # Validate environment
        if not validate_environment():
            logger.error("❌ Environment validation failed - exiting")
            sys.exit(1)

        # Setup exception handling
        setup_exception_handling()
        logger.info("✅ Exception handling configured")

        # Import and start the bot
        logger.info("📦 Importing bot modules...")
        from bot.quran_bot import main as bot_main

        logger.info("🎯 Starting Quran Bot...")
        bot_main()

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error(
            "💡 Make sure all dependencies are installed: pip install -r requirements.txt"
        )
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        logger.error(f"🔍 Full traceback: {traceback.format_exc()}")
        sys.exit(1)

    finally:
        logger.info("🏁 QuranBot shutdown complete")


if __name__ == "__main__":
    main()
