#!/bin/bash
# =============================================================================
# QuranBot Development Environment Startup
# =============================================================================
# Quick startup script for Mac development environment
# =============================================================================

echo "🕌 QuranBot Development Environment"
echo "=================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found (.venv)"
    echo "   Create one with: python3 -m venv .venv"
fi

# Check if we're in development branch
current_branch=$(git branch --show-current 2>/dev/null)
if [ "$current_branch" != "development" ]; then
    echo "⚠️  Not on development branch (currently on: $current_branch)"
    echo "   Switch with: git checkout development"
fi

# Run comprehensive tests
echo ""
echo "🧪 Running development tests..."
python tools/test_bot.py

# Check test result
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed! Starting bot..."
    echo ""
    python main.py
else
    echo ""
    echo "❌ Tests failed! Fix issues before starting bot."
    echo "   Check the test output above for details."
    exit 1
fi
