#!/usr/bin/env python3
# =============================================================================
# QuranBot - Unified Configuration Usage Examples
# =============================================================================
# This file demonstrates how to use the new simplified configuration system.
# =============================================================================

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.config.unified_config import (
    get_config,
    validate_config,
    print_config_summary,
    # Convenience functions
    is_admin,
    get_discord_token,
    get_guild_id,
    get_target_channel_id,
)


def basic_usage_example():
    """Basic configuration usage example."""
    print("=" * 60)
    print("Basic Configuration Usage")
    print("=" * 60)
    
    # Get the global configuration instance
    config = get_config()
    
    # Access configuration values directly
    print(f"Discord Token: {config.discord_token[:20]}...")
    print(f"Guild ID: {config.guild_id}")
    print(f"Target Channel: {config.target_channel_id}")
    print(f"Default Reciter: {config.default_reciter.value}")
    print(f"Environment: {config.environment.value}")
    print(f"Is Production: {config.is_production}")
    
    # Use computed properties
    print(f"Admin Users: {config.admin_user_id_list}")
    print(f"Reciter Folder: {config.reciter_audio_folder}")


def convenience_functions_example():
    """Convenience functions usage example."""
    print("\n" + "=" * 60)
    print("Convenience Functions Usage")
    print("=" * 60)
    
    # Use convenience functions for common operations
    print(f"Discord Token: {get_discord_token()[:20]}...")
    print(f"Guild ID: {get_guild_id()}")
    print(f"Target Channel: {get_target_channel_id()}")
    
    # Check admin status
    user_id = 123456789  # Example user ID
    print(f"User {user_id} is admin: {is_admin(user_id)}")


def validation_example():
    """Configuration validation example."""
    print("\n" + "=" * 60)
    print("Configuration Validation")
    print("=" * 60)
    
    # Validate configuration
    validation_result = validate_config()
    
    if validation_result["valid"]:
        print("✅ Configuration is valid!")
        summary = validation_result["summary"]
        for key, value in summary.items():
            status = "✅" if value else "❌"
            print(f"{status} {key}: {value}")
    else:
        print("❌ Configuration has errors:")
        for error in validation_result["errors"]:
            print(f"  - {error}")


def admin_check_example():
    """Admin user checking example."""
    print("\n" + "=" * 60)
    print("Admin User Checking")
    print("=" * 60)
    
    config = get_config()
    
    # Example user IDs to check
    test_user_ids = [123456789, 987654321, 555666777]
    
    for user_id in test_user_ids:
        is_admin_user = config.is_admin_user(user_id)
        status = "✅ Admin" if is_admin_user else "❌ Not Admin"
        print(f"User {user_id}: {status}")


def audio_configuration_example():
    """Audio configuration example."""
    print("\n" + "=" * 60)
    print("Audio Configuration")
    print("=" * 60)
    
    config = get_config()
    
    print(f"Audio Folder: {config.audio_folder}")
    print(f"Default Reciter: {config.default_reciter.value}")
    print(f"Reciter Audio Folder: {config.reciter_audio_folder}")
    print(f"FFmpeg Path: {config.ffmpeg_path}")
    print(f"Audio Quality: {config.audio_quality}")
    
    # Get folder for different reciter
    from src.config.unified_config import ReciterName
    
    abdul_basit_folder = config.get_reciter_folder(ReciterName.ABDUL_BASIT)
    print(f"Abdul Basit Folder: {abdul_basit_folder}")


def logging_configuration_example():
    """Logging configuration example."""
    print("\n" + "=" * 60)
    print("Logging Configuration")
    print("=" * 60)
    
    config = get_config()
    
    print(f"Log Level: {config.log_level.value}")
    print(f"Webhook Logging Enabled: {config.use_webhook_logging}")
    
    if config.discord_webhook_url:
        print(f"Webhook URL: {config.discord_webhook_url[:50]}...")
    else:
        print("Webhook URL: Not configured")


def environment_detection_example():
    """Environment detection example."""
    print("\n" + "=" * 60)
    print("Environment Detection")
    print("=" * 60)
    
    config = get_config()
    
    print(f"Environment: {config.environment.value}")
    print(f"Is Development: {config.is_development}")
    print(f"Is Production: {config.is_production}")
    
    # Use environment for conditional logic
    if config.is_development:
        print("🔧 Running in development mode - extra logging enabled")
    else:
        print("🚀 Running in production mode - optimized for performance")


def migration_from_old_system_example():
    """Example of migrating from old configuration system."""
    print("\n" + "=" * 60)
    print("Migration from Old System")
    print("=" * 60)
    
    print("OLD WAY (complex, multiple files):")
    print("  from src.config import ConfigService, BotConfig")
    print("  config_service = ConfigService()")
    print("  config = config_service.config")
    print("  token = config_service.get_discord_token()")
    print("")
    
    print("NEW WAY (simple, single source of truth):")
    print("  from src.config.unified_config import get_config, get_discord_token")
    print("  config = get_config()")
    print("  token = get_discord_token()  # or config.discord_token")
    print("")
    
    print("✅ Much simpler and easier to understand!")


def main():
    """Run all examples."""
    try:
        # Print configuration summary first
        print_config_summary()
        
        # Run examples
        basic_usage_example()
        convenience_functions_example()
        validation_example()
        admin_check_example()
        audio_configuration_example()
        logging_configuration_example()
        environment_detection_example()
        migration_from_old_system_example()
        
        print("\n" + "=" * 60)
        print("All Examples Completed Successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have a valid .env file in the config/ directory")
        print("You can copy config/.env.unified to config/.env and edit it")


if __name__ == "__main__":
    main()