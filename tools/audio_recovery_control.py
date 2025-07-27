#!/usr/bin/env python3
# =============================================================================
# QuranBot - Audio Recovery Control Tool
# =============================================================================
# Controls the auto-recovery system for QuranBot audio playback
# =============================================================================

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.tree_log import log_perfect_tree_section, log_error_with_traceback

# Configuration file path
CONFIG_FILE = Path(__file__).parent.parent / "data" / "audio_recovery_config.json"

def load_config():
    """Load the audio recovery configuration"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "auto_recovery_enabled": True,
                "max_recovery_attempts": 3,
                "recovery_cooldown": 300,  # 5 minutes
                "monitoring_interval": 120,  # 2 minutes
                "playback_failure_threshold": 3,
                "connection_failure_threshold": 2,
                "expected_playback_interval": 300  # 5 minutes
            }
    except Exception as e:
        log_error_with_traceback("Error loading recovery config", e)
        return None

def save_config(config):
    """Save the audio recovery configuration"""
    try:
        CONFIG_FILE.parent.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        log_error_with_traceback("Error saving recovery config", e)
        return False

def display_status():
    """Display current recovery system status"""
    config = load_config()
    if not config:
        print("❌ Error loading configuration")
        return
    
    print("\n" + "="*60)
    print("🛡️  QURANBOT AUDIO RECOVERY SYSTEM STATUS")
    print("="*60)
    
    status_icon = "✅" if config["auto_recovery_enabled"] else "❌"
    print(f"Auto-Recovery: {status_icon} {'ENABLED' if config['auto_recovery_enabled'] else 'DISABLED'}")
    print(f"Max Attempts: {config['max_recovery_attempts']}")
    print(f"Recovery Cooldown: {config['recovery_cooldown']} seconds ({config['recovery_cooldown']//60} minutes)")
    print(f"Monitoring Interval: {config['monitoring_interval']} seconds ({config['monitoring_interval']//60} minutes)")
    print(f"Playback Failure Threshold: {config['playback_failure_threshold']} failures")
    print(f"Connection Failure Threshold: {config['connection_failure_threshold']} failures")
    print(f"Expected Playback Interval: {config['expected_playback_interval']} seconds ({config['expected_playback_interval']//60} minutes)")
    
    print("\n" + "="*60)
    print("🔧 AVAILABLE COMMANDS:")
    print("  enable    - Enable auto-recovery")
    print("  disable   - Disable auto-recovery")
    print("  reset     - Reset to default settings")
    print("  config    - Interactive configuration")
    print("  status    - Show this status")
    print("="*60)

def enable_recovery():
    """Enable auto-recovery"""
    config = load_config()
    if not config:
        return False
    
    config["auto_recovery_enabled"] = True
    if save_config(config):
        log_perfect_tree_section(
            "Audio Recovery - Enabled",
            [
                ("status", "✅ Auto-recovery enabled"),
                ("max_attempts", str(config["max_recovery_attempts"])),
                ("recovery_cooldown", f"{config['recovery_cooldown']}s"),
                ("config_saved", "✅ Configuration saved"),
            ],
            "🛡️",
        )
        return True
    return False

def disable_recovery():
    """Disable auto-recovery"""
    config = load_config()
    if not config:
        return False
    
    config["auto_recovery_enabled"] = False
    if save_config(config):
        log_perfect_tree_section(
            "Audio Recovery - Disabled",
            [
                ("status", "❌ Auto-recovery disabled"),
                ("manual_intervention", "Required for audio failures"),
                ("config_saved", "✅ Configuration saved"),
            ],
            "🛡️",
        )
        return True
    return False

def reset_config():
    """Reset to default configuration"""
    default_config = {
        "auto_recovery_enabled": True,
        "max_recovery_attempts": 3,
        "recovery_cooldown": 300,
        "monitoring_interval": 120,
        "playback_failure_threshold": 3,
        "connection_failure_threshold": 2,
        "expected_playback_interval": 300
    }
    
    if save_config(default_config):
        log_perfect_tree_section(
            "Audio Recovery - Reset to Defaults",
            [
                ("status", "✅ Configuration reset"),
                ("auto_recovery", "✅ Enabled"),
                ("max_attempts", "3"),
                ("recovery_cooldown", "300s (5 minutes)"),
                ("monitoring_interval", "120s (2 minutes)"),
            ],
            "🔄",
        )
        return True
    return False

def interactive_config():
    """Interactive configuration setup"""
    config = load_config()
    if not config:
        return False
    
    print("\n🔧 INTERACTIVE CONFIGURATION")
    print("Press Enter to keep current value, or enter new value:")
    
    try:
        # Auto-recovery enabled
        current = "yes" if config["auto_recovery_enabled"] else "no"
        response = input(f"Enable auto-recovery? (yes/no) [{current}]: ").strip().lower()
        if response in ["yes", "y"]:
            config["auto_recovery_enabled"] = True
        elif response in ["no", "n"]:
            config["auto_recovery_enabled"] = False
        
        # Max recovery attempts
        response = input(f"Max recovery attempts [{config['max_recovery_attempts']}]: ").strip()
        if response and response.isdigit():
            config["max_recovery_attempts"] = int(response)
        
        # Recovery cooldown
        response = input(f"Recovery cooldown (seconds) [{config['recovery_cooldown']}]: ").strip()
        if response and response.isdigit():
            config["recovery_cooldown"] = int(response)
        
        # Monitoring interval
        response = input(f"Monitoring interval (seconds) [{config['monitoring_interval']}]: ").strip()
        if response and response.isdigit():
            config["monitoring_interval"] = int(response)
        
        # Playback failure threshold
        response = input(f"Playback failure threshold [{config['playback_failure_threshold']}]: ").strip()
        if response and response.isdigit():
            config["playback_failure_threshold"] = int(response)
        
        # Connection failure threshold
        response = input(f"Connection failure threshold [{config['connection_failure_threshold']}]: ").strip()
        if response and response.isdigit():
            config["connection_failure_threshold"] = int(response)
        
        if save_config(config):
            print("\n✅ Configuration saved successfully!")
            return True
        else:
            print("\n❌ Error saving configuration")
            return False
            
    except KeyboardInterrupt:
        print("\n\n❌ Configuration cancelled")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        display_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        display_status()
    elif command == "enable":
        if enable_recovery():
            print("✅ Auto-recovery enabled successfully")
        else:
            print("❌ Failed to enable auto-recovery")
    elif command == "disable":
        if disable_recovery():
            print("✅ Auto-recovery disabled successfully")
        else:
            print("❌ Failed to disable auto-recovery")
    elif command == "reset":
        if reset_config():
            print("✅ Configuration reset to defaults")
        else:
            print("❌ Failed to reset configuration")
    elif command == "config":
        interactive_config()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: status, enable, disable, reset, config")

if __name__ == "__main__":
    main() 