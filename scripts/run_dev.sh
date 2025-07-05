#!/bin/bash

# =============================================================================
# QuranBot - Development Startup Script
# =============================================================================
# Activates virtual environment and runs bot locally for development testing
# Run this script from the project root directory
# =============================================================================

# Change to project root directory
cd "$(dirname "$0")/.."

echo "🚀 Starting QuranBot Development Environment..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run setup first!"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if .env file exists
if [ ! -f "config/.env" ]; then
    echo "❌ .env file not found. Please create it with your Discord credentials."
    exit 1
fi

# Run tests first
echo "🧪 Running pre-flight tests..."
python tools/test_bot.py

if [ $? -eq 0 ]; then
    echo "✅ Tests passed! Starting bot..."
    echo "🎵 QuranBot is starting in development mode..."
    echo "📝 Press Ctrl+C to stop the bot"
    echo "════════════════════════════════════════════════"

    # Run the bot
    python main.py
else
    echo "❌ Tests failed! Fix issues before running the bot."
    exit 1
fi
