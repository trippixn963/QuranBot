#!/usr/bin/env python3
"""
QuranBot - Discord 24/7 Quran Streaming Bot
============================================

Main entry point for the QuranBot Discord application.
This module initializes the bot and starts the Quran streaming service.

Features:
    - 24/7 continuous Quran recitation
    - Multiple professional reciters
    - Interactive Discord control panel
    - Health monitoring and logging
    - Auto-reconnection and error recovery

Usage:
    python run.py                    # Start the bot
    python run.py --help            # Show help (if implemented)
    python run.py --debug           # Enable debug mode (if implemented)

Environment Variables:
    DISCORD_TOKEN                   # Discord bot token (required)
    TARGET_CHANNEL_ID               # Voice channel ID (required)
    PANEL_CHANNEL_ID                # Control panel channel ID (required)
    LOGS_CHANNEL_ID                 # Logs channel ID (optional)

Dependencies:
    - discord.py >= 2.3.0
    - python-dotenv >= 1.0.0
    - psutil >= 5.9.0
    - colorama >= 0.4.6

Author: QuranBot Team
License: MIT
Version: 2.1.0
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path for module imports
# This allows importing from src.bot, src.utils, etc.
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the main bot function
from bot.quran_bot import main

if __name__ == "__main__":
    # Start the QuranBot Discord application
    main() 