#!/usr/bin/env python3
# =============================================================================
# Quiz Interval Monitor
# =============================================================================
# This script monitors the quiz interval setting and logs any changes
# to help identify when and why intervals revert to default values.
# =============================================================================

from datetime import UTC, datetime
import json
from pathlib import Path
import time


def monitor_interval_changes():
    """Monitor quiz interval changes and log them"""
    print("🔍 Quiz Interval Monitor Started")
    print("=" * 40)
    print("This will monitor the quiz interval setting and alert you to any changes.")
    print("Press Ctrl+C to stop monitoring.\n")

    # Setup paths
    data_dir = Path("data")
    quiz_state_file = data_dir / "state.json"

    # Track previous values
    previous_interval = None
    previous_update_time = None
    check_count = 0

    try:
        while True:
            check_count += 1
            current_time = datetime.now(UTC)

            if quiz_state_file.exists():
                try:
                    with open(quiz_state_file) as f:
                        data = json.load(f)

                    schedule_config = data.get("schedule_config", {})
                    current_interval = schedule_config.get("send_interval_hours", 3.0)
                    last_updated = schedule_config.get("last_updated", "NEVER")

                    # Check for changes
                    if previous_interval is None:
                        # First check
                        print(
                            f"[{current_time.strftime('%H:%M:%S')}] Initial interval: {current_interval} hours"
                        )
                        print(f"                    Last updated: {last_updated}")
                    elif current_interval != previous_interval:
                        # Interval changed!
                        print("\n🚨 INTERVAL CHANGE DETECTED!")
                        print(
                            f"[{current_time.strftime('%H:%M:%S')}] Changed from {previous_interval}h to {current_interval}h"
                        )
                        print(f"                    Last updated: {last_updated}")
                        print(
                            f"                    Previous update: {previous_update_time}"
                        )

                        if current_interval == 3.0:
                            print("⚠️  REVERTED TO DEFAULT (3 hours)!")
                            print("   This indicates something reset the interval.")
                    elif last_updated != previous_update_time:
                        # File was updated but interval didn't change
                        print(
                            f"[{current_time.strftime('%H:%M:%S')}] File updated (interval unchanged: {current_interval}h)"
                        )
                        print(f"                    New update time: {last_updated}")
                    elif check_count % 12 == 0:  # Every 2 minutes
                        # Periodic status update
                        print(
                            f"[{current_time.strftime('%H:%M:%S')}] Status: {current_interval}h (no changes)"
                        )

                    previous_interval = current_interval
                    previous_update_time = last_updated

                except json.JSONDecodeError as e:
                    print(
                        f"[{current_time.strftime('%H:%M:%S')}] ❌ Error reading quiz state file: {e}"
                    )
                except Exception as e:
                    print(
                        f"[{current_time.strftime('%H:%M:%S')}] ❌ Unexpected error: {e}"
                    )
            else:
                print(
                    f"[{current_time.strftime('%H:%M:%S')}] ❌ Quiz state file not found!"
                )

            # Wait 10 seconds before next check
            time.sleep(10)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Monitoring stopped after {check_count} checks.")
        print("Final status:")
        if previous_interval is not None:
            print(f"   Last known interval: {previous_interval} hours")
            print(f"   Last update time: {previous_update_time}")


def check_current_status():
    """Check and display current interval status"""
    print("📊 Current Interval Status")
    print("-" * 30)

    data_dir = Path("data")
    quiz_state_file = data_dir / "state.json"

    if quiz_state_file.exists():
        try:
            with open(quiz_state_file) as f:
                data = json.load(f)

            schedule_config = data.get("schedule_config", {})
            current_interval = schedule_config.get("send_interval_hours", "NOT_SET")
            last_updated = schedule_config.get("last_updated", "NEVER")

            print(f"Current interval: {current_interval} hours")
            print(f"Last updated: {last_updated}")

            if current_interval == 3.0:
                print("Status: ✅ Default value (3 hours)")
            elif isinstance(current_interval, (int, float)) and current_interval != 3.0:
                print(f"Status: 🔧 Custom value ({current_interval} hours)")
            else:
                print("Status: ❓ Unknown/Invalid value")

        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print("❌ Quiz state file not found")


def main():
    """Main function for the interval monitor"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_current_status()
    else:
        check_current_status()
        print()
        monitor_interval_changes()


if __name__ == "__main__":
    main()
