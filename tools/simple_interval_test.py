#!/usr/bin/env python3
# =============================================================================
# Simple Interval Persistence Test
# =============================================================================
# Direct test of interval persistence without complex imports
# =============================================================================

import json
from pathlib import Path
from datetime import datetime, timezone

def test_interval_file_operations():
    """Test interval file operations directly"""
    print("🧪 Simple Interval Persistence Test")
    print("=" * 45)
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    quiz_state_file = data_dir / "quiz_state.json"
    
    print(f"\n📁 Data directory: {data_dir}")
    print(f"📄 Quiz state file: {quiz_state_file}")
    
    # Check current state
    print(f"\n1️⃣ Current State Check")
    if quiz_state_file.exists():
        with open(quiz_state_file, 'r') as f:
            current_data = json.load(f)
        
        schedule_config = current_data.get('schedule_config', {})
        current_interval = schedule_config.get('send_interval_hours', 'NOT_SET')
        print(f"   Current interval: {current_interval}")
        
        if 'schedule_config' in current_data:
            print(f"   Schedule config exists: ✅")
            print(f"   Config details: {schedule_config}")
        else:
            print(f"   Schedule config exists: ❌")
    else:
        print(f"   File exists: ❌")
        current_data = {}
    
    # Test setting a new interval
    print(f"\n2️⃣ Setting Test Interval")
    test_interval = 2.5  # 2.5 hours
    
    # Load existing or create new
    if quiz_state_file.exists():
        with open(quiz_state_file, 'r') as f:
            config_data = json.load(f)
    else:
        config_data = {}
    
    # Update schedule config
    if "schedule_config" not in config_data:
        config_data["schedule_config"] = {}
    
    config_data["schedule_config"]["send_interval_hours"] = test_interval
    config_data["schedule_config"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Save updated config
    data_dir.mkdir(exist_ok=True)
    with open(quiz_state_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"   Set interval to: {test_interval} hours")
    print(f"   File written: ✅")
    
    # Verify the change
    print(f"\n3️⃣ Verification")
    with open(quiz_state_file, 'r') as f:
        verification_data = json.load(f)
    
    verified_interval = verification_data.get('schedule_config', {}).get('send_interval_hours', 'NOT_FOUND')
    print(f"   Retrieved interval: {verified_interval}")
    print(f"   Verification: {'✅ Success' if verified_interval == test_interval else '❌ Failed'}")
    
    # Test the get_interval_hours logic directly
    print(f"\n4️⃣ Testing Get Interval Logic")
    
    def get_interval_hours_direct():
        """Direct implementation of get_interval_hours logic"""
        try:
            if quiz_state_file.exists():
                with open(quiz_state_file, "r") as f:
                    data = json.load(f)
                    return data.get("schedule_config", {}).get("send_interval_hours", 3.0)
            return 3.0  # Default 3 hours
        except Exception as e:
            print(f"   Error: {e}")
            return 3.0
    
    direct_interval = get_interval_hours_direct()
    print(f"   Direct get_interval_hours(): {direct_interval}")
    print(f"   Logic test: {'✅ Correct' if direct_interval == test_interval else '❌ Wrong'}")
    
    # Show file content
    print(f"\n5️⃣ File Content")
    with open(quiz_state_file, 'r') as f:
        content = f.read()
    
    print("   Current file content:")
    print("   " + "-" * 40)
    for line in content.split('\n')[:10]:  # Show first 10 lines
        print(f"   {line}")
    if len(content.split('\n')) > 10:
        print(f"   ... ({len(content.split('\n')) - 10} more lines)")
    print("   " + "-" * 40)
    
    # Reset to default
    print(f"\n6️⃣ Cleanup - Reset to Default")
    config_data["schedule_config"]["send_interval_hours"] = 3.0
    config_data["schedule_config"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    with open(quiz_state_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    final_interval = get_interval_hours_direct()
    print(f"   Reset to: {final_interval} hours")
    
    print(f"\n🏁 Test Complete!")

if __name__ == "__main__":
    test_interval_file_operations() 