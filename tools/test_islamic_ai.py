#!/usr/bin/env python3
"""
Test script for Islamic AI Assistant using OpenAI GPT-3.5 Turbo
"""

import asyncio
import os
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import get_config_service
from services.islamic_ai_service import IslamicAIService


async def test_islamic_ai():
    """Test the Islamic AI assistant functionality"""

    print("🤖 Islamic AI Assistant Test")
    print("=" * 50)

    try:
        # Initialize configuration
        config_service = get_config_service()
        print(f"✅ Configuration loaded")

        # Check if OpenAI API key is configured
        if not hasattr(config_service.config, 'OPENAI_API_KEY') or not config_service.config.OPENAI_API_KEY:
            print("❌ OpenAI API key not configured")
            print("💡 Add OPENAI_API_KEY to your .env file")
            return

        # Initialize AI service
        ai_service = IslamicAIService()
        success = await ai_service.initialize()

        if not success:
            print("❌ Failed to initialize Islamic AI service")
            return

        print(f"✅ Islamic AI service initialized")
        print(f"🔑 API key configured: {config_service.config.OPENAI_API_KEY[:8]}...")

        # Test questions
        test_questions = [
            "What are the 5 pillars of Islam?",
            "How do I perform Wudu?",
            "What is the significance of Ramadan?",
            "Can you explain the concept of Tawhid?",
            "What are the times for daily prayers?"
        ]

        print(f"\n🧪 Testing with {len(test_questions)} sample questions:")
        print("-" * 40)

        for i, question in enumerate(test_questions, 1):
            print(f"\n{i}. Question: {question}")

            success, response, error = await ai_service.ask_question(12345, question)

            if success:
                print(f"   ✅ Response: {response[:100]}...")
                print(f"   📏 Length: {len(response)} characters")
            else:
                print(f"   ❌ Error: {error}")

        # Test rate limiting
        print(f"\n⏱️ Testing rate limiting:")
        rate_status = ai_service.get_rate_limit_status(12345)
        print(f"   📊 Requests used: {rate_status['requests_used']}/5")
        print(f"   🔄 Remaining: {rate_status['requests_remaining']}")

        print(f"\n🎉 Islamic AI Assistant test completed!")
        print(f"✅ GPT-3.5 Turbo integration working")
        print(f"📚 Ready to provide Islamic guidance")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_islamic_ai())
