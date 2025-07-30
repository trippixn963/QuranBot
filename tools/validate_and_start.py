#!/usr/bin/env python3
# =============================================================================
# QuranBot - Validate and Start Script
# =============================================================================
# This script runs validation checks before starting the bot.
# If validation fails, the bot won't start.
# =============================================================================

import sys
import subprocess
from pathlib import Path

def run_validation():
    """Run validation and return success status."""
    print("🔍 Running startup validation...")
    
    try:
        result = subprocess.run([
            sys.executable, 
            "tools/validate_bot_startup.py"
        ], capture_output=True, text=True)
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running validation: {e}")
        return False

def start_bot():
    """Start the bot."""
    print("🚀 Starting QuranBot...")
    
    try:
        # Start the bot
        subprocess.run([
            sys.executable, 
            "main.py"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

def main():
    """Main function."""
    print("=" * 60)
    print("🤖 QuranBot - Validate and Start")
    print("=" * 60)
    
    # Run validation first
    if not run_validation():
        print("\n❌ Validation failed! Bot will not start.")
        print("Please fix the issues above and try again.")
        sys.exit(1)
    
    print("\n✅ Validation passed! Starting bot...")
    print("=" * 60)
    
    # Start the bot
    start_bot()

if __name__ == "__main__":
    main() 