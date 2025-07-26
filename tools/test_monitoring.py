#!/usr/bin/env python3
"""
QuranBot - Monitoring System Test
=================================
Test script to verify the Discord alert monitoring system works correctly.
This simulates various failure conditions to ensure alerts are sent.

Usage:
    python tools/test_monitoring.py
"""

import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.control_panel import ControlPanelMonitor

# Note: AudioPlaybackMonitor was part of legacy AudioManager - monitoring now handled by modern AudioService


async def test_control_panel_monitoring():
    """Test control panel monitoring alerts"""
    print("🔍 Testing Control Panel Monitoring...")

    monitor = ControlPanelMonitor()

    # Test successful updates
    print("✅ Recording successful updates...")
    monitor.record_success()
    monitor.record_success()

    # Test failure threshold
    print("❌ Recording failures to trigger alert...")
    monitor.record_failure("test_error", "This is a test error message")
    monitor.record_failure("test_error", "This is a test error message")
    monitor.record_failure(
        "test_error", "This is a test error message"
    )  # Should trigger alert

    # Wait for alert to be sent
    await asyncio.sleep(2)

    # Test recovery
    print("✅ Recording recovery...")
    monitor.record_success()  # Should trigger recovery alert

    await asyncio.sleep(2)
    print("✅ Control panel monitoring test complete")


async def test_audio_monitoring():
    """Test audio playback monitoring alerts"""
    print("🔍 Audio Monitoring Test Disabled...")
    print("ℹ️  AudioPlaybackMonitor was part of legacy AudioManager")
    print("ℹ️  Audio monitoring is now handled by modern AudioService")
    print("ℹ️  This test needs to be updated to use the modern architecture")

    # TODO: Update this test to use modern AudioService monitoring
    # when the monitoring functionality is implemented in the new service
    print("✅ Audio monitoring test complete")


async def main():
    """Main test function"""
    print("🚨 QuranBot Monitoring System Test")
    print("=" * 50)
    print("This will test the Discord alert system by simulating failures.")
    print("Check your Discord log channel for test alerts.")
    print()

    try:
        await test_control_panel_monitoring()
        print()
        await test_audio_monitoring()
        print()
        print("🎯 All monitoring tests completed!")
        print("Check your Discord log channel to verify alerts were sent.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
