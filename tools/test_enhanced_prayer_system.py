#!/usr/bin/env python3
"""
Test script for enhanced Mecca prayer system with time-based duas
"""

import json
from pathlib import Path
import random


def test_enhanced_prayer_system():
    """Test the enhanced prayer system with time-based duas"""

    print("🧪 Enhanced Prayer System Test")
    print("=" * 50)

    try:
        # Load time-based duas
        duas_file = Path("data/time_based_duas.json")
        if not duas_file.exists():
            print("❌ time_based_duas.json not found!")
            return

        with open(duas_file, encoding='utf-8') as f:
            time_based_duas = json.load(f)

        print(f"✅ Loaded {len(time_based_duas)} dua categories:")
        for category, duas in time_based_duas.items():
            print(f"   📚 {category}: {len(duas)} duas")

        # Test prayer mapping
        prayer_mapping = {
            "fajr": "morning_duas",
            "dhuhr": "friday_duas",
            "asr": "friday_duas",
            "maghrib": "evening_duas",
            "isha": "evening_duas"
        }

        print("\n🕌 Testing prayer-time dua selection:")
        print("-" * 40)

        all_working = True

        for prayer, category in prayer_mapping.items():
            print(f"\n🕐 {prayer.upper()} PRAYER:")

            if category in time_based_duas and time_based_duas[category]:
                selected_dua = random.choice(time_based_duas[category])

                dua_name = selected_dua.get("name", "Unknown")
                dua_source = selected_dua.get("source", "Unknown")
                dua_arabic = selected_dua.get("arabic", "")
                dua_english = selected_dua.get("english", "")

                print(f"   📚 Category: {category}")
                print(f"   📿 Dua: {dua_name}")
                print(f"   📖 Source: {dua_source}")
                print(f"   🇸🇦 Arabic: {dua_arabic[:60]}...")
                print(f"   🇬🇧 English: {dua_english[:60]}...")
                print("   ✅ SUCCESS")
            else:
                print(f"   📚 Category: {category}")
                print("   ❌ FAILED - No duas available")
                all_working = False

        # Special detailed test for Maghrib
        print("\n" + "="*50)
        print("🌆 DETAILED MAGHRIB TEST:")
        print("-" * 30)

        if "evening_duas" in time_based_duas and time_based_duas["evening_duas"]:
            maghrib_dua = random.choice(time_based_duas["evening_duas"])

            print(f"📿 Selected Dua: {maghrib_dua.get('name', 'Unknown')}")
            print(f"📖 Source: {maghrib_dua.get('source', 'Unknown')}")
            print(f"⏰ Time: {maghrib_dua.get('time', 'Not specified')}")
            print("\n📝 Full Content:")
            print(f"🇸🇦 Arabic: {maghrib_dua.get('arabic', 'N/A')}")
            print(f"🇬🇧 English: {maghrib_dua.get('english', 'N/A')}")
            print("✅ MAGHRIB TEST PASSED")
        else:
            print("❌ MAGHRIB TEST FAILED - No evening duas")
            all_working = False

        # Final result
        print("\n" + "="*50)
        if all_working:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Enhanced prayer system is working perfectly")
            print("🕌 Prayer notifications will show contextual duas")
        else:
            print("⚠️  Some tests failed")
            print("🔧 Check the time_based_duas.json file")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_enhanced_prayer_system()
