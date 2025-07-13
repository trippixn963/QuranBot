#!/usr/bin/env python3
# =============================================================================
# VPS Bot Restart Simulation Test
# =============================================================================

import json
from pathlib import Path
from datetime import datetime, timezone

def test_bot_restart_simulation():
    """Test what happens during bot restart simulation"""
    print("🔄 Testing Bot Restart Simulation")
    print("=" * 40)
    
    # Setup paths
    data_dir = Path('data')
    quiz_state_file = data_dir / 'quiz_state.json'
    
    # Step 1: Set a custom interval (simulating dashboard change)
    test_interval = 1.5  # 1.5 hours
    print(f"Step 1: Setting custom interval to {test_interval} hours")
    
    with open(quiz_state_file, 'r') as f:
        config_data = json.load(f)
    
    config_data['schedule_config']['send_interval_hours'] = test_interval
    config_data['schedule_config']['last_updated'] = datetime.now(timezone.utc).isoformat()
    
    with open(quiz_state_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"✅ Custom interval set: {test_interval} hours")
    
    # Step 2: Simulate what happens during QuizManager initialization
    print("Step 2: Simulating QuizManager initialization...")
    
    def get_interval_hours():
        """Simulate get_interval_hours() method"""
        try:
            if quiz_state_file.exists():
                with open(quiz_state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('schedule_config', {}).get('send_interval_hours', 3.0)
            return 3.0
        except Exception as e:
            print(f"Error: {e}")
            return 3.0
    
    init_interval = get_interval_hours()
    print(f"✅ QuizManager would load: {init_interval} hours")
    
    # Step 3: Simulate what happens when save_state() is called
    print("Step 3: Simulating save_state() call...")
    
    # Load existing state to preserve schedule_config (this is what save_state does)
    existing_state = {}
    if quiz_state_file.exists():
        try:
            with open(quiz_state_file, 'r') as f:
                existing_state = json.load(f)
        except Exception:
            existing_state = {}
    
    # Create new state (simulating what save_state does)
    state = {
        'questions': existing_state.get('questions', []),
        'user_scores': existing_state.get('user_scores', {}),
        'recent_questions': existing_state.get('recent_questions', []),
        'last_sent_time': datetime.now(timezone.utc).isoformat()
    }
    
    # Preserve existing schedule_config if it exists (this is the key part)
    if 'schedule_config' in existing_state:
        state['schedule_config'] = existing_state['schedule_config']
        print(f"✅ Preserved schedule_config: {existing_state['schedule_config']}")
    else:
        print("❌ No schedule_config found to preserve!")
    
    # Save the state
    with open(quiz_state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    # Step 4: Verify the interval is still there
    final_interval = get_interval_hours()
    print(f"Step 4: Final interval check: {final_interval} hours")
    success = final_interval == test_interval
    print(f"Persistence test: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Step 5: Test actual bot restart by restarting the service
    print("Step 5: Testing actual bot restart...")
    
    import subprocess
    import time
    
    try:
        # Restart the bot service
        print("   Restarting quranbot service...")
        subprocess.run(['systemctl', 'restart', 'quranbot.service'], check=True)
        
        # Wait a moment for restart
        time.sleep(5)
        
        # Check if service is running
        result = subprocess.run(['systemctl', 'is-active', 'quranbot.service'], 
                              capture_output=True, text=True)
        service_status = result.stdout.strip()
        print(f"   Service status: {service_status}")
        
        # Check interval after restart
        post_restart_interval = get_interval_hours()
        print(f"   Interval after restart: {post_restart_interval} hours")
        
        restart_success = post_restart_interval == test_interval
        print(f"   Restart persistence: {'✅ SUCCESS' if restart_success else '❌ FAILED'}")
        
        if not restart_success:
            print(f"   Expected: {test_interval}, Got: {post_restart_interval}")
            print("   ⚠️ This indicates the bot restart is resetting the interval!")
        
    except Exception as e:
        print(f"   Error during restart test: {e}")
    
    # Reset back to 3 hours
    print("Step 6: Cleanup - Reset to 3 hours")
    config_data['schedule_config']['send_interval_hours'] = 3.0
    config_data['schedule_config']['last_updated'] = datetime.now(timezone.utc).isoformat()
    with open(quiz_state_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print("🧹 Reset to 3 hours for cleanup")
    print("🏁 Test complete!")

if __name__ == "__main__":
    test_bot_restart_simulation() 