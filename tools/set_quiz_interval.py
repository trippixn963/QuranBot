#!/usr/bin/env python3
# =============================================================================
# Quiz Interval Setter
# =============================================================================
# Simple script to set quiz intervals for testing
# =============================================================================

from datetime import UTC, datetime
import json
from pathlib import Path
import sys


def set_quiz_interval(hours):
    """Set the quiz interval to specified hours"""
    try:
        hours = float(hours)
        if hours < 0.017 or hours > 24:  # 1 minute to 24 hours
            print("❌ Error: Interval must be between 1 minute (0.017h) and 24 hours")
            print(f"   You provided: {hours} hours")
            return False

        # Setup paths
        data_dir = Path("data")
        quiz_state_file = data_dir / "state.json"

        if not quiz_state_file.exists():
            print(f"❌ Error: Quiz state file not found: {quiz_state_file}")
            return False

        # Load existing config
        with open(quiz_state_file) as f:
            config_data = json.load(f)

        # Update the schedule config
        if "schedule_config" not in config_data:
            config_data["schedule_config"] = {}

        old_interval = config_data["schedule_config"].get(
            "send_interval_hours", "NOT_SET"
        )
        config_data["schedule_config"]["send_interval_hours"] = hours
        config_data["schedule_config"]["last_updated"] = datetime.now(UTC).isoformat()

        # Save the updated config
        with open(quiz_state_file, "w") as f:
            json.dump(config_data, f, indent=2)

        print("✅ Quiz interval updated successfully!")
        print(f"   Old interval: {old_interval} hours")
        print(f"   New interval: {hours} hours")
        print(f"   Updated at: {config_data['schedule_config']['last_updated']}")

        return True

    except ValueError:
        print(f"❌ Error: Invalid number format: {hours}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_current_interval():
    """Get the current quiz interval"""
    try:
        data_dir = Path("data")
        quiz_state_file = data_dir / "state.json"

        if not quiz_state_file.exists():
            print(f"❌ Quiz state file not found: {quiz_state_file}")
            return None

        with open(quiz_state_file) as f:
            data = json.load(f)

        schedule_config = data.get("schedule_config", {})
        current_interval = schedule_config.get("send_interval_hours", 3.0)
        last_updated = schedule_config.get("last_updated", "NEVER")

        print("📊 Current Quiz Interval")
        print(f"   Interval: {current_interval} hours")
        print(f"   Last updated: {last_updated}")

        return current_interval

    except Exception as e:
        print(f"❌ Error reading interval: {e}")
        return None


def show_usage():
    """Show usage instructions"""
    print("🔧 Quiz Interval Setter")
    print("=" * 25)
    print("Usage:")
    print("  python set_quiz_interval.py <hours>     # Set interval")
    print("  python set_quiz_interval.py status      # Show current interval")
    print()
    print("Examples:")
    print("  python set_quiz_interval.py 1.5         # Set to 1.5 hours")
    print("  python set_quiz_interval.py 0.5         # Set to 30 minutes")
    print("  python set_quiz_interval.py 6           # Set to 6 hours")
    print("  python set_quiz_interval.py status      # Show current setting")
    print()
    print("Valid range: 1 minute (0.017h) to 24 hours")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_usage()
    elif sys.argv[1].lower() == "status":
        get_current_interval()
    elif sys.argv[1].lower() in ["help", "-h", "--help"]:
        show_usage()
    else:
        try:
            hours = float(sys.argv[1])
            set_quiz_interval(hours)
        except ValueError:
            print(f"❌ Error: '{sys.argv[1]}' is not a valid number")
            print()
            show_usage()
