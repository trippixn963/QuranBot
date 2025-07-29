#!/usr/bin/env python3
"""
Demo script to showcase the rich visualization capabilities of the enhanced webhook system.
This will send sample webhook messages with various visualizations to demonstrate the features.
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.bot_config import BotConfig
from src.core.structured_logger import StructuredLogger
from src.core.webhook_service_factory import create_webhook_service
from src.core.webhook_logger import LogLevel


async def demo_visualizations():
    """Run visualization demos."""
    print("🎨 Rich Visualization Demo for QuranBot Webhooks")
    print("=" * 50)
    
    try:
        # Initialize services
        config = BotConfig()
        logger = StructuredLogger("demo")
        
        # Create webhook service
        webhook_service = await create_webhook_service(
            config=config,
            logger=logger,
            container=None,
            bot=None
        )
        
        if not webhook_service:
            print("❌ Failed to create webhook service")
            return
        
        print("✅ Webhook service initialized")
        print("\n🚀 Sending visualization demos...\n")
        
        # Demo 1: Audio Playback Visualization
        print("1️⃣ Sending Audio Playback Visualization...")
        await webhook_service.log_audio_playback_visual(
            surah_number=2,
            surah_name="Al-Baqarah",
            reciter="Saad Al Ghamdi",
            progress=1250.5,  # seconds
            duration=7054.3,  # seconds
            listeners=12,
            surah_progress_in_quran=2.63  # Surah 2 out of 114
        )
        await asyncio.sleep(2)
        
        # Demo 2: Daily Statistics
        print("2️⃣ Sending Daily Statistics Visualization...")
        hourly_activity = {
            hour: random.randint(5, 50) 
            for hour in range(24)
        }
        top_surahs = [
            {"name": "Al-Fatiha", "plays": 45},
            {"name": "Al-Baqarah", "plays": 38},
            {"name": "Al-Kahf", "plays": 32},
            {"name": "Ya-Sin", "plays": 28},
            {"name": "Ar-Rahman", "plays": 25},
        ]
        
        await webhook_service.log_daily_stats_visual(
            total_playtime_hours=18.5,
            surahs_played=67,
            unique_listeners=142,
            quiz_participation=38,
            commands_used=256,
            hourly_activity=hourly_activity,
            top_surahs=top_surahs
        )
        await asyncio.sleep(2)
        
        # Demo 3: Performance Metrics
        print("3️⃣ Sending Performance Metrics Visualization...")
        cpu_history = [30 + random.randint(-10, 20) for _ in range(20)]
        memory_history = [45 + random.randint(-5, 15) for _ in range(20)]
        
        await webhook_service.log_performance_visual(
            cpu_percent=cpu_history[-1],
            memory_percent=memory_history[-1],
            latency_ms=125.4,
            cache_hit_rate=92.3,
            cpu_history=cpu_history,
            memory_history=memory_history
        )
        await asyncio.sleep(2)
        
        # Demo 4: Quiz Statistics
        print("4️⃣ Sending Quiz Statistics Visualization...")
        participants = [
            {"name": "Ahmed", "score": 850, "accuracy": 95},
            {"name": "Fatima", "score": 780, "accuracy": 88},
            {"name": "Omar", "score": 720, "accuracy": 82},
            {"name": "Aisha", "score": 650, "accuracy": 75},
            {"name": "Hassan", "score": 600, "accuracy": 70},
        ]
        difficulty_distribution = {
            "easy": 25,
            "medium": 40,
            "hard": 15
        }
        response_times = [8.2, 12.5, 6.8, 15.2, 9.4, 7.1, 11.3, 8.9, 10.2, 7.5]
        
        await webhook_service.log_quiz_stats_visual(
            total_questions=80,
            correct_answers=68,
            participants=participants,
            difficulty_distribution=difficulty_distribution,
            response_times=response_times
        )
        await asyncio.sleep(2)
        
        # Demo 5: Simple Progress Examples
        print("5️⃣ Sending Simple Progress Examples...")
        
        # Bot health status
        await webhook_service.route_event(
            event_type="health_check",
            title="🏥 Bot Health Status",
            description=(
                "**System Health Overview:**\n\n" +
                "🤖 **Bot Status:** `█████████░` 90% Healthy\n" +
                "🔊 **Audio System:** `██████████` 100% Operational\n" +
                "💾 **Database:** `████████░░` 80% Used (2.4GB/3GB)\n" +
                "🌐 **API Latency:** `██░░░░░░░░` 25ms (Excellent)\n" +
                "📊 **Cache Hit Rate:** `█████████░` 94.2%\n\n" +
                "**Uptime:** 7 days, 14 hours, 32 minutes"
            ),
            level=LogLevel.SUCCESS,
            force_channel=webhook_service.WebhookChannel.BOT_STATUS if hasattr(webhook_service, 'WebhookChannel') else None
        )
        
        print("\n✅ All visualization demos sent!")
        print("\n📊 Check your Discord webhook channels to see the rich visualizations!")
        
        # Cleanup
        await webhook_service.shutdown()
        
    except Exception as e:
        print(f"❌ Error in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(demo_visualizations())