#!/usr/bin/env python3
# =============================================================================
# QuranBot - Modernized Architecture Demo
# =============================================================================
# This script demonstrates the modernized QuranBot architecture with
# dependency injection, modern services, and proper error handling.
# =============================================================================

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Core modernized components
    from core.cache_service import CacheService, CacheStrategy
    from core.di_container import DIContainer
    from core.exceptions import AudioError, QuranBotError, StateError
    from core.structured_logger import StructuredLogger

    from config.bot_config import BotConfig
    from data.models import BotStatistics, PlaybackPosition, PlaybackState

    print("✅ Successfully imported modernized QuranBot components!")

except ImportError as e:
    print(f"❌ Import failed: {e}")
    print(
        "The modernized codebase has some import path issues that need to be resolved."
    )
    sys.exit(1)


async def demo_modernized_architecture():
    """Demonstrate the modernized QuranBot architecture."""

    print("\n🚀 QuranBot Modernized Architecture Demo")
    print("=" * 50)

    # 1. Dependency Injection Container
    print("\n1. 🔧 Dependency Injection Container")
    container = DIContainer()

    # Register services
    def logger_factory():
        return StructuredLogger(name="demo_logger", level="INFO")

    def cache_factory():
        return CacheService(strategy=CacheStrategy.LRU, max_size=100, default_ttl=300)

    container.register_singleton(StructuredLogger, logger_factory)
    container.register_singleton(CacheService, cache_factory)

    print("✅ DI Container initialized with services")

    # 2. Get services from container
    logger = container.resolve(StructuredLogger)
    cache_service = container.resolve(CacheService)

    print("✅ Services resolved from DI container")

    # 3. Initialize services
    await cache_service.initialize()
    await logger.info("Cache service initialized", {"component": "demo"})

    print("✅ Services initialized successfully")

    # 4. Test cache service
    print("\n2. 🗄️ Modern Cache Service")
    await cache_service.set("demo_key", "demo_value")
    value = await cache_service.get("demo_key")
    print(f"✅ Cache test: stored and retrieved '{value}'")

    # Get cache statistics
    stats = await cache_service.get_statistics()
    print(
        f"✅ Cache stats: {stats['total_operations']} operations, {stats['hit_rate']:.2f}% hit rate"
    )

    # 5. Test Pydantic models
    print("\n3. 📊 Modern Data Models (Pydantic V2)")

    playback_state = PlaybackState(
        is_playing=True,
        is_paused=False,
        is_shuffled=False,
        is_looped=False,
        current_reciter="Saad Al Ghamdi",
        current_surah=2,
        current_file="002.mp3",
        voice_channel_id=1389675580253016144,
        guild_id=1228455909827805308,
        position=PlaybackPosition(current_seconds=45.0, total_duration=300.0),
        volume=0.8,
        last_updated=datetime.now(UTC),
    )

    print("✅ Created PlaybackState model with validation")
    print(
        f"   Current: {playback_state.current_reciter} - Surah {playback_state.current_surah}"
    )
    print(
        f"   Position: {playback_state.position.current_seconds:.1f}s / {playback_state.position.total_duration:.1f}s"
    )

    bot_stats = BotStatistics(
        total_sessions=15,
        total_playtime_seconds=7200.0,
        total_commands_executed=150,
        unique_users=8,
        favorite_reciter="Saad Al Ghamdi",
        favorite_surah=2,
        last_reset=datetime.now(UTC),
    )

    print("✅ Created BotStatistics model")
    print(f"   Sessions: {bot_stats.total_sessions}, Users: {bot_stats.unique_users}")
    print(f"   Total playtime: {bot_stats.total_playtime_seconds/3600:.1f} hours")

    # 6. Test modern exception handling
    print("\n4. ⚠️ Modern Exception Handling")

    try:
        raise AudioError(
            "Demo audio error", audio_source="demo.mp3", error_code="DEMO_001"
        )
    except QuranBotError as e:
        print(f"✅ Caught custom exception: {e}")
        print(f"   Error ID: {e.error_id}")
        print(f"   Context: {e.context}")

    # 7. Test configuration management
    print("\n5. ⚙️ Modern Configuration Management")

    try:
        # This will validate environment variables
        config = BotConfig()
        print("✅ Configuration loaded and validated successfully")
        print(f"   Guild ID: {config.GUILD_ID}")
        print(f"   Audio folder: {config.AUDIO_FOLDER}")
        print(f"   Default reciter: {config.DEFAULT_RECITER}")
        print(f"   FFmpeg path: {config.FFMPEG_PATH}")
        print(f"   Webhook logging: {config.USE_WEBHOOK_LOGGING}")

        # Show admin users
        admin_users = config.admin_user_ids
        print(f"   Admin users: {len(admin_users)} configured")

    except Exception as e:
        print(f"⚠️ Configuration validation failed: {e}")
        print(
            "   This is expected if environment variables are not properly configured"
        )

    # 8. Demonstrate service shutdown
    print("\n6. 🔄 Graceful Shutdown")
    await cache_service.shutdown()
    print("✅ Services shut down gracefully")

    print("\n🎉 Modernized Architecture Demo Complete!")
    print("\nKey Improvements Demonstrated:")
    print("• Dependency Injection for loose coupling")
    print("• Type-safe data models with Pydantic V2")
    print("• Modern async cache service with statistics")
    print("• Structured logging with context")
    print("• Custom exception hierarchy with error tracking")
    print("• Configuration management with validation")
    print("• Graceful service lifecycle management")


async def show_architecture_overview():
    """Show an overview of the modernized architecture."""

    print("\n📋 QuranBot Modernization Overview")
    print("=" * 50)

    components = [
        (
            "🏗️ Dependency Injection",
            "DIContainer for service management and loose coupling",
        ),
        (
            "🗄️ Cache Service",
            "High-performance caching with multiple strategies (LRU, LFU, TTL)",
        ),
        ("⚡ Performance Monitor", "Real-time metrics collection and alerting"),
        (
            "🔗 Connection Pool",
            "Efficient connection management for SQLite, HTTP, File operations",
        ),
        (
            "📦 Resource Manager",
            "Automatic resource tracking and cleanup with leak detection",
        ),
        ("🔄 Lazy Loader", "On-demand resource loading with background scanning"),
        (
            "🎵 Audio Service",
            "Modern audio playback with metadata caching and recovery",
        ),
        (
            "💾 State Service",
            "Atomic state management with backup, compression, and validation",
        ),
        (
            "🔒 Security Service",
            "Rate limiting, input validation, and permission checking",
        ),
        ("📊 Data Models", "Type-safe Pydantic V2 models for all data structures"),
        ("⚙️ Configuration", "Environment-based config with validation and type safety"),
        ("🏃 Structured Logger", "Context-aware logging with multiple output formats"),
        (
            "⚠️ Exception Hierarchy",
            "Custom exceptions with error tracking and correlation",
        ),
        ("🧪 Testing Suite", "Comprehensive unit, integration, and performance tests"),
    ]

    for name, description in components:
        print(f"{name:<25} {description}")

    print("\n📈 Test Coverage: 80%+ requirement with automated CI/CD")
    print("🔧 Code Quality: Black, Ruff, MyPy, pre-commit hooks")
    print("🚀 CI/CD Pipeline: GitHub Actions with matrix testing")


def main():
    """Main entry point for the demo."""

    print("🎵 QuranBot - Modernized Architecture Demonstration")

    # Check if we're in the right directory
    if not Path("config/.env").exists():
        print("❌ Error: config/.env file not found")
        print("   Please run this script from the QuranBot project root directory")
        sys.exit(1)

    # Show architecture overview
    asyncio.run(show_architecture_overview())

    # Run the demo
    try:
        asyncio.run(demo_modernized_architecture())
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
