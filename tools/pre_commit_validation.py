#!/usr/bin/env python3
# =============================================================================
# QuranBot - Pre-Commit Validation Hook
# =============================================================================
# This script runs validation checks before git commits to ensure
# the bot is in a valid state before pushing changes.
# =============================================================================

import sys
import subprocess
from pathlib import Path

def run_validation():
    """Run the validation script and return success status."""
    try:
        # Run the validation script
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

def main():
    """Main pre-commit validation function."""
    print("🔍 Running pre-commit validation...")
    
    success = run_validation()
    
    if not success:
        print("\n❌ Pre-commit validation FAILED!")
        print("Please fix the issues above before committing.")
        sys.exit(1)
    else:
        print("\n✅ Pre-commit validation PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main() 