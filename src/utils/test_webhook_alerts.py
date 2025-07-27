#!/usr/bin/env python3
# =============================================================================
# QuranBot - Webhook Alert Testing System
# =============================================================================
# This script tests all webhook alert functionality including:
# - Audio playback failures
# - Voice connection issues  
# - Escalation alerts (critical/emergency)
# - Extended silence detection
# - AI service failures
# - Translation failures
# - Quiz system failures
# - Owner ping functionality
#
# Usage:
#     python tools/test_webhook_alerts.py [test_type]
#     
# Test types:
#     audio_failure     - Test audio playback failure alerts
#     connection_issue  - Test voice connection failure alerts
#     escalation        - Test critical/emergency escalation alerts
#     silence           - Test extended silence detection
#     ai_failure        - Test AI service failure alerts
#     translation       - Test translation service failure alerts
#     quiz_failure      - Test quiz system failure alerts
#     all               - Run all tests
# =============================================================================

import asyncio
import sys
import os
from datetime import datetime, timezone
import traceback

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.di_container import get_container
from src.core.webhook_logger import ModernWebhookLogger
from src.utils.tree_log import log_perfect_tree_section, log_error_with_traceback
from src.utils.audio_manager import _audio_monitor


class WebhookAlertTester:
    """Test all webhook alert functionality"""
    
    def __init__(self):
        self.container = None
        self.webhook_logger = None
        self.test_results = []
    
    async def initialize(self):
        """Initialize the testing environment"""
        try:
            # Get the DI container
            self.container = get_container()
            if not self.container:
                raise Exception("Could not get DI container")
            
            # Get webhook logger
            self.webhook_logger = self.container.get(ModernWebhookLogger)
            if not self.webhook_logger:
                raise Exception("Could not get webhook logger from container")
            
            if not self.webhook_logger.initialized:
                await self.webhook_logger.initialize()
            
            log_perfect_tree_section(
                "Webhook Alert Tester - Initialized",
                [
                    ("webhook_logger", "✅ Available"),
                    ("initialized", "✅ Ready"),
                    ("timestamp", datetime.now().strftime("%H:%M:%S")),
                ],
                "⚡",
            )
            
            return True
            
        except Exception as e:
            log_error_with_traceback("Failed to initialize webhook alert tester", e)
            return False
    
    async def test_audio_failure_alert(self):
        """Test audio playback failure alerts"""
        try:
            log_perfect_tree_section(
                "Testing Audio Failure Alert",
                [("test_type", "Audio Playback Failure")],
                "🎵"
            )
            
            result = await self.webhook_logger.log_audio_event(
                event_type="playback_failure",
                error_message="TEST: Simulated audio playback failure",
                audio_details={
                    "error_type": "test_simulation",
                    "consecutive_failures": 5,
                    "minutes_down": 10,
                    "impact": "❌ Test: Audio playback stopped - bot is silent",
                    "status": "🔇 Test: Audio System Down",
                    "action_required": "Test: Check voice connection and audio files"
                },
                ping_owner=True
            )
            
            self.test_results.append(("Audio Failure Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Audio failure alert test failed", e)
            self.test_results.append(("Audio Failure Alert", False))
            return False
    
    async def test_connection_issue_alert(self):
        """Test voice connection issue alerts"""
        try:
            log_perfect_tree_section(
                "Testing Connection Issue Alert",
                [("test_type", "Voice Connection Issue")],
                "🔌"
            )
            
            result = await self.webhook_logger.log_voice_connection_issue(
                issue_type="connection_failed",
                error_details="TEST: Simulated voice connection failure",
                channel_name="QuranBot Voice Channel",
                recovery_action="Test: Attempting automatic reconnection",
                additional_info={
                    "consecutive_failures": 3,
                    "minutes_down": 5,
                    "impact": "❌ Test: Bot disconnected from voice channel",
                    "status": "🔌 Test: Voice Connection Down"
                },
                ping_owner=True
            )
            
            self.test_results.append(("Connection Issue Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Connection issue alert test failed", e)
            self.test_results.append(("Connection Issue Alert", False))
            return False
    
    async def test_critical_escalation_alert(self):
        """Test critical escalation alerts"""
        try:
            log_perfect_tree_section(
                "Testing Critical Escalation Alert",
                [("test_type", "Critical Failure Escalation")],
                "🚨"
            )
            
            result = await self.webhook_logger.log_audio_event(
                event_type="critical_failure_escalation",
                error_message="🚨 TEST CRITICAL: 15 Consecutive Audio Failures",
                audio_details={
                    "escalation_level": "CRITICAL",
                    "consecutive_failures": 15,
                    "hours_down": 2,
                    "error_type": "test_simulation",
                    "impact": "❌ Test: Audio system has been down for extended period",
                    "status": "🔴 TEST CRITICAL FAILURE - MANUAL INTERVENTION REQUIRED",
                    "action_required": "🆘 Test: Immediate admin attention needed"
                },
                ping_owner=True
            )
            
            self.test_results.append(("Critical Escalation Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Critical escalation alert test failed", e)
            self.test_results.append(("Critical Escalation Alert", False))
            return False
    
    async def test_emergency_escalation_alert(self):
        """Test emergency escalation alerts"""
        try:
            log_perfect_tree_section(
                "Testing Emergency Escalation Alert",
                [("test_type", "Emergency Failure Escalation")],
                "🆘"
            )
            
            result = await self.webhook_logger.log_audio_event(
                event_type="emergency_failure_escalation",
                error_message="🆘 TEST EMERGENCY: 25 Consecutive Audio Failures - SYSTEM DOWN",
                audio_details={
                    "escalation_level": "EMERGENCY",
                    "consecutive_failures": 25,
                    "hours_down": 6,
                    "error_type": "test_simulation",
                    "impact": "🆘 TEST: COMPLETE AUDIO SYSTEM FAILURE - BOT NOT FUNCTIONING",
                    "status": "🔴 TEST EMERGENCY - SYSTEM COMPLETELY DOWN",
                    "action_required": "🚨 TEST URGENT: Bot requires immediate manual restart/repair"
                },
                ping_owner=True
            )
            
            self.test_results.append(("Emergency Escalation Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Emergency escalation alert test failed", e)
            self.test_results.append(("Emergency Escalation Alert", False))
            return False
    
    async def test_extended_silence_alert(self):
        """Test extended silence detection alerts"""
        try:
            log_perfect_tree_section(
                "Testing Extended Silence Alert",
                [("test_type", "Extended Silence Emergency")],
                "🔇"
            )
            
            result = await self.webhook_logger.log_audio_event(
                event_type="extended_silence_emergency",
                error_message="🆘 TEST EMERGENCY: Bot Silent for 20 Minutes",
                audio_details={
                    "escalation_level": "EXTENDED SILENCE EMERGENCY",
                    "minutes_silent": 20,
                    "threshold_minutes": 15,
                    "last_playback": "12:00:00 UTC",
                    "impact": "🆘 TEST: BOT COMPLETELY SILENT - NOT SERVING USERS",
                    "status": "🔇 TEST EMERGENCY SILENCE - IMMEDIATE ACTION REQUIRED",
                    "action_required": "🚨 TEST URGENT: Bot has been silent too long"
                },
                ping_owner=True
            )
            
            self.test_results.append(("Extended Silence Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Extended silence alert test failed", e)
            self.test_results.append(("Extended Silence Alert", False))
            return False
    
    async def test_ai_service_failure_alert(self):
        """Test AI service failure alerts"""
        try:
            log_perfect_tree_section(
                "Testing AI Service Failure Alert",
                [("test_type", "AI Service Failure")],
                "🤖"
            )
            
            result = await self.webhook_logger.log_error(
                title="TEST: AI Service Failure",
                description="TEST: Enhanced Islamic AI service failed to process user question",
                context={
                    "user_id": "123456789",
                    "question_length": 50,
                    "error_type": "TestError",
                    "error_message": "TEST: Simulated AI processing failure",
                    "component": "Enhanced Islamic AI Service",
                    "impact": "Test: User received generic error message"
                },
                ping_owner=True
            )
            
            self.test_results.append(("AI Service Failure Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("AI service failure alert test failed", e)
            self.test_results.append(("AI Service Failure Alert", False))
            return False
    
    async def test_translation_failure_alert(self):
        """Test translation service failure alerts"""
        try:
            log_perfect_tree_section(
                "Testing Translation Failure Alert",
                [("test_type", "Translation Service Failure")],
                "🌐"
            )
            
            result = await self.webhook_logger.log_error(
                title="TEST: Translation Service Failure",
                description="TEST: ChatGPT translation service failed to translate AI response",
                context={
                    "target_language": "Arabic",
                    "text_length": 200,
                    "error_type": "TestTranslationError",
                    "error_message": "TEST: Simulated translation failure",
                    "component": "Translation Service",
                    "impact": "Test: User translation request failed"
                },
                ping_owner=False
            )
            
            self.test_results.append(("Translation Failure Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Translation failure alert test failed", e)
            self.test_results.append(("Translation Failure Alert", False))
            return False
    
    async def test_quiz_failure_alert(self):
        """Test quiz system failure alerts"""
        try:
            log_perfect_tree_section(
                "Testing Quiz Failure Alert",
                [("test_type", "Quiz System Failure")],
                "❓"
            )
            
            result = await self.webhook_logger.log_error(
                title="TEST: Quiz System Failure",
                description="TEST: Failed to send quiz results to Discord channel",
                context={
                    "channel_id": "987654321",
                    "guild_id": "123456789",
                    "error_type": "TestQuizError",
                    "error_message": "TEST: Simulated quiz results sending failure",
                    "component": "Quiz Manager",
                    "impact": "Test: Quiz results not displayed to users"
                },
                ping_owner=False
            )
            
            self.test_results.append(("Quiz Failure Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Quiz failure alert test failed", e)
            self.test_results.append(("Quiz Failure Alert", False))
            return False
    
    async def test_recovery_alert(self):
        """Test recovery success alerts"""
        try:
            log_perfect_tree_section(
                "Testing Recovery Alert",
                [("test_type", "Audio Recovery Success")],
                "✅"
            )
            
            result = await self.webhook_logger.log_audio_event(
                event_type="playback_recovery",
                error_message="TEST: Audio Playback Successfully Recovered",
                audio_details={
                    "status": "✅ Test: Audio Playback Restored",
                    "recovery_time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                    "action": "Test: Audio playback resumed successfully",
                    "auto_recovery": "✅ Test: Automatic recovery successful"
                },
                ping_owner=False
            )
            
            self.test_results.append(("Recovery Alert", result))
            return result
            
        except Exception as e:
            log_error_with_traceback("Recovery alert test failed", e)
            self.test_results.append(("Recovery Alert", False))
            return False
    
    async def run_all_tests(self):
        """Run all webhook alert tests"""
        log_perfect_tree_section(
            "Webhook Alert Testing - Starting All Tests",
            [
                ("total_tests", "8"),
                ("includes_owner_pings", "Yes"),
                ("timestamp", datetime.now().strftime("%H:%M:%S")),
            ],
            "🧪",
        )
        
        # Run all tests with delays between them
        test_methods = [
            self.test_audio_failure_alert,
            self.test_connection_issue_alert,
            self.test_critical_escalation_alert,
            self.test_emergency_escalation_alert,
            self.test_extended_silence_alert,
            self.test_ai_service_failure_alert,
            self.test_translation_failure_alert,
            self.test_quiz_failure_alert,
            self.test_recovery_alert,
        ]
        
        for i, test_method in enumerate(test_methods, 1):
            try:
                await test_method()
                print(f"✅ Test {i}/{len(test_methods)} completed")
                
                # Wait between tests to avoid rate limiting
                if i < len(test_methods):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"❌ Test {i}/{len(test_methods)} failed: {e}")
        
        # Print final results
        self.print_test_results()
    
    def print_test_results(self):
        """Print summary of all test results"""
        successful_tests = sum(1 for _, result in self.test_results if result)
        total_tests = len(self.test_results)
        
        log_perfect_tree_section(
            "Webhook Alert Testing - Results Summary",
            [
                ("successful_tests", f"{successful_tests}/{total_tests}"),
                ("success_rate", f"{(successful_tests/total_tests)*100:.1f}%"),
                ("webhook_health", "✅ Operational" if successful_tests > 0 else "❌ Issues Detected"),
            ],
            "📊",
        )
        
        # Detailed results
        for test_name, result in self.test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {status} - {test_name}")


async def main():
    """Main testing function"""
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    tester = WebhookAlertTester()
    
    if not await tester.initialize():
        print("❌ Failed to initialize webhook alert tester")
        return 1
    
    try:
        if test_type == "audio_failure":
            await tester.test_audio_failure_alert()
        elif test_type == "connection_issue":
            await tester.test_connection_issue_alert()
        elif test_type == "escalation":
            await tester.test_critical_escalation_alert()
            await asyncio.sleep(2)
            await tester.test_emergency_escalation_alert()
        elif test_type == "silence":
            await tester.test_extended_silence_alert()
        elif test_type == "ai_failure":
            await tester.test_ai_service_failure_alert()
        elif test_type == "translation":
            await tester.test_translation_failure_alert()
        elif test_type == "quiz_failure":
            await tester.test_quiz_failure_alert()
        elif test_type == "all":
            await tester.run_all_tests()
        else:
            print(f"❌ Unknown test type: {test_type}")
            print("Available test types: audio_failure, connection_issue, escalation, silence, ai_failure, translation, quiz_failure, all")
            return 1
        
        tester.print_test_results()
        return 0
        
    except Exception as e:
        log_error_with_traceback("Webhook alert testing failed", e)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Webhook alert testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error in webhook alert testing: {e}")
        traceback.print_exc()
        sys.exit(1) 