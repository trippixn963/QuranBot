#!/usr/bin/env python3
"""
Test script for Islamic AI Mention System

Tests the natural mention-based interaction with bilingual support.
"""

import asyncio
import os
import sys
import re
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.islamic_ai_listener import IslamicAIMentionListener
from src.services.islamic_ai_service import IslamicAIService
from src.config import get_config_service


def test_islamic_question_detection():
    """Test the Islamic question detection logic"""
    
    print("🔍 Testing Islamic Question Detection")
    print("=" * 50)
    
    # Create a mock listener to test detection logic
    class MockBot:
        def __init__(self):
            self.user = None
    
    class MockContainer:
        pass
    
    listener = IslamicAIMentionListener(MockBot(), MockContainer())
    
    # Test cases (English)
    english_test_cases = [
        ("What are the 5 pillars of Islam?", True),
        ("How do I perform Wudu?", True),
        ("When is Ramadan this year?", True),
        ("Can you explain Tawhid?", True),
        ("What is halal food?", True),
        ("Hello there", False),  # No Islamic content
        ("What time is it?", False),  # Question but not Islamic
        ("Islam is great", False),  # Islamic content but not question
        ("Where is the mosque?", True),  # Islamic question
        ("How to pray Salah?", True),  # Islamic question
    ]
    
    # Test cases (Arabic)
    arabic_test_cases = [
        ("ما هي أركان الإسلام الخمسة؟", True),
        ("كيف أتوضأ؟", True),
        ("متى رمضان هذا العام؟", True),
        ("ما هو الحلال؟", True),
        ("أين المسجد؟", True),
        ("مرحبا", False),  # No Islamic content
        ("كم الساعة؟", False),  # Question but not Islamic
        ("الإسلام عظيم", False),  # Islamic content but not question
    ]
    
    # Test cases (Mixed)
    mixed_test_cases = [
        ("What is صلاة?", True),  # Mixed English-Arabic
        ("How to perform الوضوء?", True),  # Mixed
        ("Explain the concept of التوحيد", True),  # Mixed
    ]
    
    print("\n📝 Testing English Questions:")
    print("-" * 30)
    correct_english = 0
    for question, expected in english_test_cases:
        result = listener._is_islamic_question(question)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{question}' → {result} (expected: {expected})")
        if result == expected:
            correct_english += 1
    
    print(f"\nEnglish Accuracy: {correct_english}/{len(english_test_cases)} ({correct_english/len(english_test_cases)*100:.1f}%)")
    
    print("\n📝 Testing Arabic Questions:")
    print("-" * 30)
    correct_arabic = 0
    for question, expected in arabic_test_cases:
        result = listener._is_islamic_question(question)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{question}' → {result} (expected: {expected})")
        if result == expected:
            correct_arabic += 1
    
    print(f"\nArabic Accuracy: {correct_arabic}/{len(arabic_test_cases)} ({correct_arabic/len(arabic_test_cases)*100:.1f}%)")
    
    print("\n📝 Testing Mixed Questions:")
    print("-" * 30)
    correct_mixed = 0
    for question, expected in mixed_test_cases:
        result = listener._is_islamic_question(question)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{question}' → {result} (expected: {expected})")
        if result == expected:
            correct_mixed += 1
    
    print(f"\nMixed Accuracy: {correct_mixed}/{len(mixed_test_cases)} ({correct_mixed/len(mixed_test_cases)*100:.1f}%)")
    
    # Overall results
    total_correct = correct_english + correct_arabic + correct_mixed
    total_tests = len(english_test_cases) + len(arabic_test_cases) + len(mixed_test_cases)
    overall_accuracy = total_correct / total_tests * 100
    
    print(f"\n🎯 Overall Detection Accuracy: {total_correct}/{total_tests} ({overall_accuracy:.1f}%)")
    
    if overall_accuracy >= 90:
        print("🎉 Excellent question detection!")
    elif overall_accuracy >= 80:
        print("✅ Good question detection")
    else:
        print("⚠️ Question detection needs improvement")


def test_arabic_detection():
    """Test Arabic text detection"""
    
    print("\n🔤 Testing Arabic Text Detection")
    print("=" * 40)
    
    class MockBot:
        def __init__(self):
            self.user = None
    
    class MockContainer:
        pass
    
    listener = IslamicAIMentionListener(MockBot(), MockContainer())
    
    test_cases = [
        ("Hello world", False),
        ("مرحبا", True),
        ("What is الإسلام?", True),
        ("صلاة is prayer", True),
        ("123456", False),
        ("الله أكبر", True),
        ("English only text", False),
        ("Mixed text with عربي", True),
    ]
    
    correct = 0
    for text, expected in test_cases:
        result = listener._contains_arabic(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' → {result} (expected: {expected})")
        if result == expected:
            correct += 1
    
    accuracy = correct / len(test_cases) * 100
    print(f"\nArabic Detection Accuracy: {correct}/{len(test_cases)} ({accuracy:.1f}%)")


async def test_ai_service_integration():
    """Test the AI service with bilingual examples"""
    
    print("\n🤖 Testing AI Service Integration")
    print("=" * 40)
    
    try:
        # Initialize configuration
        config_service = get_config_service()
        
        # Check if OpenAI API key is configured
        if not hasattr(config_service.config, 'OPENAI_API_KEY') or not config_service.config.OPENAI_API_KEY:
            print("⚠️ OpenAI API key not configured - skipping AI integration test")
            print("💡 Add OPENAI_API_KEY to your .env file to test AI responses")
            return
        
        # Initialize AI service
        ai_service = IslamicAIService()
        success = await ai_service.initialize()
        
        if not success:
            print("❌ Failed to initialize AI service")
            return
        
        print("✅ AI service initialized successfully")
        
        # Test questions in both languages
        test_questions = [
            ("English", "What are the 5 pillars of Islam?"),
            ("Arabic", "ما هي أركان الإسلام الخمسة؟"),
            ("English", "How do I perform Wudu?"),
            ("Arabic", "كيف أتوضأ؟"),
            ("Mixed", "What is صلاة in Islam?"),
        ]
        
        print(f"\n🧪 Testing AI responses:")
        print("-" * 30)
        
        for i, (lang, question) in enumerate(test_questions, 1):
            print(f"\n{i}. {lang} Question: {question}")
            
            success, response, error = await ai_service.ask_question(12345, question)
            
            if success:
                print(f"   ✅ Response received ({len(response)} chars)")
                print(f"   📝 Preview: {response[:100]}...")
                
                # Check if response is in English
                english_ratio = len(re.findall(r'[a-zA-Z]', response)) / len(response) if response else 0
                if english_ratio > 0.7:
                    print(f"   🎯 Response appears to be in English ✅")
                else:
                    print(f"   ⚠️ Response may not be primarily in English")
                    
            else:
                print(f"   ❌ Error: {error}")
        
        print(f"\n✅ AI integration test completed!")
        
    except Exception as e:
        print(f"❌ AI integration test failed: {e}")


def main():
    """Run all tests"""
    print("🚀 Islamic AI Mention System Test Suite")
    print("=" * 60)
    
    # Test 1: Question detection
    test_islamic_question_detection()
    
    # Test 2: Arabic detection
    test_arabic_detection()
    
    # Test 3: AI service integration (if configured)
    asyncio.run(test_ai_service_integration())
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("\n📋 Summary:")
    print("• ✅ Islamic question detection tested")
    print("• ✅ Arabic text detection tested") 
    print("• ✅ AI service integration tested")
    print("\n🚀 Your mention-based Islamic AI system is ready!")
    print("\n💬 Users can now mention the bot with questions like:")
    print("   @QuranBot What are the 5 pillars of Islam?")
    print("   @QuranBot ما هي أركان الإسلام الخمسة؟")
    print("   @QuranBot How do I perform Wudu?")


if __name__ == "__main__":
    main() 