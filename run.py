#!/usr/bin/env python3
"""
Discord Quran Bot - Main Entry Point
Professional 24/7 Quran streaming bot.

Usage:
    python run.py
"""

import sys
import os

from src.monitoring.logging.logger import logger
logger.info("QuranBot run.py startup test log")

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bot.quran_bot import main

if __name__ == "__main__":
    main() 