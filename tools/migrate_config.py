#!/usr/bin/env python3
# =============================================================================
# QuranBot - Configuration Migration Tool
# =============================================================================
# This tool helps migrate from the old complex configuration system
# to the new unified configuration system.
# =============================================================================

from pathlib import Path
import sys

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def migrate_configuration():
    """Migrate from old configuration system to unified configuration."""

    print("=" * 60)
    print("QuranBot Configuration Migration Tool")
    print("=" * 60)

    old_env_file = project_root / "config" / ".env"
    new_env_file = project_root / "config" / ".env.unified"
    backup_env_file = project_root / "config" / ".env.backup"

    # Check if old config exists
    if not old_env_file.exists():
        print("❌ No existing .env file found to migrate")
        print("✅ You can start fresh with the unified configuration")
        print(f"📝 Copy {new_env_file} to {old_env_file} and edit it")
        return

    # Backup existing config
    if old_env_file.exists():
        print(f"📦 Backing up existing config to {backup_env_file}")
        old_env_file.rename(backup_env_file)

    # Read old configuration
    old_config = {}
    if backup_env_file.exists():
        with open(backup_env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    old_config[key.strip()] = value.strip()

    # Create new unified configuration
    print("🔄 Creating unified configuration...")

    # Mapping from old config keys to new unified keys
    key_mapping = {
        "DISCORD_TOKEN": "DISCORD_TOKEN",
        "GUILD_ID": "GUILD_ID",
        "TARGET_CHANNEL_ID": "TARGET_CHANNEL_ID",
        "PANEL_CHANNEL_ID": "PANEL_CHANNEL_ID",
        "LOGS_CHANNEL_ID": "LOGS_CHANNEL_ID",
        "DAILY_VERSE_CHANNEL_ID": "DAILY_VERSE_CHANNEL_ID",
        "PANEL_ACCESS_ROLE_ID": "PANEL_ACCESS_ROLE_ID",
        "ADMIN_USER_ID": "ADMIN_USER_IDS",  # Note: renamed for clarity
        "DEVELOPER_ID": "DEVELOPER_ID",
        "AUDIO_FOLDER": "AUDIO_FOLDER",
        "DEFAULT_RECITER": "DEFAULT_RECITER",
        "FFMPEG_PATH": "FFMPEG_PATH",
        "AUDIO_QUALITY": "AUDIO_QUALITY",
        "DEFAULT_SHUFFLE": "DEFAULT_SHUFFLE",
        "DEFAULT_LOOP": "DEFAULT_LOOP",
        "LOG_LEVEL": "LOG_LEVEL",
        "USE_WEBHOOK_LOGGING": "USE_WEBHOOK_LOGGING",
        "DISCORD_WEBHOOK_URL": "DISCORD_WEBHOOK_URL",
        "CACHE_TTL": "CACHE_TTL_SECONDS",  # Note: renamed for clarity
        "RATE_LIMIT_PER_MINUTE": "RATE_LIMIT_PER_MINUTE",
        "MAX_CONCURRENT_AUDIO": "MAX_CONCURRENT_AUDIO",
        "BACKUP_INTERVAL_HOURS": "BACKUP_INTERVAL_HOURS",
        "ENVIRONMENT": "ENVIRONMENT",
        "OPENAI_API_KEY": "OPENAI_API_KEY",
        "VPS_HOST": "VPS_HOST",
    }

    # Create new configuration content
    new_config_lines = [
        "# =============================================================================",
        "# QuranBot - Unified Configuration",
        "# =============================================================================",
        "# Migrated from old configuration system",
        "# =============================================================================",
        "",
        "# =============================================================================",
        "# REQUIRED SETTINGS",
        "# =============================================================================",
        "",
    ]

    # Required settings
    required_settings = ["DISCORD_TOKEN", "GUILD_ID", "TARGET_CHANNEL_ID"]
    for key in required_settings:
        old_key = key
        if old_key in old_config:
            new_config_lines.append(f"{key}={old_config[old_key]}")
        else:
            new_config_lines.append(
                f"# {key}=paste_your_value_here  # ⚠️ REQUIRED - Please set this!"
            )

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# OPTIONAL DISCORD SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    # Optional Discord settings
    optional_discord = [
        "PANEL_CHANNEL_ID",
        "LOGS_CHANNEL_ID",
        "DAILY_VERSE_CHANNEL_ID",
        "PANEL_ACCESS_ROLE_ID",
    ]
    for key in optional_discord:
        if key in old_config:
            new_config_lines.append(f"{key}={old_config[key]}")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# ADMIN SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    # Admin settings (handle the rename from ADMIN_USER_ID to ADMIN_USER_IDS)
    if "ADMIN_USER_ID" in old_config:
        new_config_lines.append(f"ADMIN_USER_IDS={old_config['ADMIN_USER_ID']}")
    if "DEVELOPER_ID" in old_config:
        new_config_lines.append(f"DEVELOPER_ID={old_config['DEVELOPER_ID']}")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# AUDIO SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    # Audio settings
    audio_settings = [
        "AUDIO_FOLDER",
        "DEFAULT_RECITER",
        "FFMPEG_PATH",
        "AUDIO_QUALITY",
        "DEFAULT_SHUFFLE",
        "DEFAULT_LOOP",
    ]
    for key in audio_settings:
        if key in old_config:
            new_config_lines.append(f"{key}={old_config[key]}")
        else:
            # Provide sensible defaults
            defaults = {
                "AUDIO_FOLDER": "audio",
                "DEFAULT_RECITER": "Saad Al Ghamdi",
                "FFMPEG_PATH": "/usr/bin/ffmpeg",
                "AUDIO_QUALITY": "128k",
                "DEFAULT_SHUFFLE": "false",
                "DEFAULT_LOOP": "false",
            }
            if key in defaults:
                new_config_lines.append(f"{key}={defaults[key]}")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# LOGGING SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    # Logging settings
    logging_settings = ["LOG_LEVEL", "USE_WEBHOOK_LOGGING", "DISCORD_WEBHOOK_URL"]
    for key in logging_settings:
        if key in old_config:
            new_config_lines.append(f"{key}={old_config[key]}")
        else:
            defaults = {
                "LOG_LEVEL": "INFO",
                "USE_WEBHOOK_LOGGING": "true",
            }
            if key in defaults:
                new_config_lines.append(f"{key}={defaults[key]}")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# PERFORMANCE SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    # Performance settings (handle CACHE_TTL -> CACHE_TTL_SECONDS rename)
    if "CACHE_TTL" in old_config:
        new_config_lines.append(f"CACHE_TTL_SECONDS={old_config['CACHE_TTL']}")
    else:
        new_config_lines.append("CACHE_TTL_SECONDS=300")

    perf_settings = [
        "RATE_LIMIT_PER_MINUTE",
        "MAX_CONCURRENT_AUDIO",
        "BACKUP_INTERVAL_HOURS",
    ]
    for key in perf_settings:
        if key in old_config:
            new_config_lines.append(f"{key}={old_config[key]}")
        else:
            defaults = {
                "RATE_LIMIT_PER_MINUTE": "10",
                "MAX_CONCURRENT_AUDIO": "1",
                "BACKUP_INTERVAL_HOURS": "24",
            }
            if key in defaults:
                new_config_lines.append(f"{key}={defaults[key]}")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# ENVIRONMENT SETTINGS",
            "# =============================================================================",
            "",
        ]
    )

    if "ENVIRONMENT" in old_config:
        new_config_lines.append(f"ENVIRONMENT={old_config['ENVIRONMENT']}")
    else:
        new_config_lines.append("ENVIRONMENT=production")

    new_config_lines.extend(
        [
            "",
            "# =============================================================================",
            "# OPTIONAL INTEGRATIONS",
            "# =============================================================================",
            "",
        ]
    )

    # Optional integrations
    optional_settings = ["OPENAI_API_KEY", "VPS_HOST"]
    for key in optional_settings:
        if key in old_config:
            new_config_lines.append(f"{key}={old_config[key]}")

    # Write new configuration
    with open(old_env_file, "w") as f:
        f.write("\n".join(new_config_lines))

    print("✅ Migration completed!")
    print(f"📝 New unified config saved to: {old_env_file}")
    print(f"💾 Old config backed up to: {backup_env_file}")

    # Test the new configuration
    print("\n🧪 Testing new configuration...")
    try:
        from src.config.unified_config import get_config, print_config_summary

        config = get_config()
        print("✅ Configuration loaded successfully!")
        print("\n📊 Configuration Summary:")
        print_config_summary()

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        print("🔧 Please review and fix the configuration manually")

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print("Next steps:")
    print("1. Review the new .env file and adjust any settings")
    print(
        "2. Update your imports to use: from src.config.unified_config import get_config"
    )
    print("3. Test the bot with the new configuration")
    print("4. Remove old configuration files when satisfied")


if __name__ == "__main__":
    migrate_configuration()
