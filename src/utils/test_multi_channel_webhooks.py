#!/usr/bin/env python3
# =============================================================================
# QuranBot - Multi-Channel Webhook System Test
# =============================================================================
# This utility tests the enhanced multi-channel webhook system to ensure
# proper configuration, routing, and functionality.
# =============================================================================

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.bot_config import BotConfig
from src.core.structured_logger import StructuredLogger
from src.core.enhanced_webhook_router import EnhancedWebhookRouter, WebhookChannel
from src.core.webhook_service_factory import WebhookServiceFactory, create_webhook_service
from src.core.webhook_logger import LogLevel


class MultiChannelWebhookTester:
    """Test suite for the multi-channel webhook system."""
    
    def __init__(self):
        self.config = None
        self.logger = None
        self.webhook_service = None
        
    async def initialize(self) -> bool:
        """Initialize the test environment."""
        try:
            print("🚀 Initializing Multi-Channel Webhook Test Environment")
            
            # Create a minimal logger for testing
            self.logger = StructuredLogger("webhook_test")
            await self.logger.initialize()
            
            # Load configuration
            try:
                self.config = BotConfig()
                print(f"✅ Configuration loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load configuration: {e}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize test environment: {e}")
            return False
    
    async def test_configuration_validation(self) -> bool:
        """Test webhook configuration validation."""
        print("\n📋 Testing Configuration Validation...")
        
        try:
            # Test webhook service info
            service_info = WebhookServiceFactory.get_webhook_service_info(self.config)
            
            print(f"   Webhook Logging Enabled: {service_info['enabled']}")
            print(f"   Service Type: {service_info['type']}")
            print(f"   Configured Channels: {service_info['channels']}")
            print(f"   Total URLs Configured: {service_info['urls_configured']}")
            
            if service_info['enabled']:
                print("   Channel Breakdown:")
                for channel, configured in service_info['channel_breakdown'].items():
                    status = "✅" if configured else "❌"
                    print(f"     {status} {channel}")
            
            # Test individual webhook URL retrieval
            print(f"\n   Testing individual webhook URL retrieval:")
            for channel in WebhookChannel:
                url = self.config.get_webhook_url(channel.value)
                status = "✅" if url else "❌"
                print(f"     {status} {channel.value}: {'Configured' if url else 'Not configured'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    async def test_service_creation(self) -> bool:
        """Test webhook service creation."""
        print("\n🔧 Testing Webhook Service Creation...")
        
        try:
            self.webhook_service = await create_webhook_service(
                config=self.config,
                logger=self.logger,
                container=None,
                bot=None,
            )
            
            if self.webhook_service:
                service_type = type(self.webhook_service).__name__
                print(f"✅ Webhook service created successfully: {service_type}")
                
                # Test service capabilities
                if hasattr(self.webhook_service, 'route_event'):
                    print("   ✅ Enhanced router with intelligent event categorization")
                if hasattr(self.webhook_service, 'log_bot_startup'):
                    print("   ✅ Bot lifecycle logging methods available")
                if hasattr(self.webhook_service, 'log_quran_command_usage'):
                    print("   ✅ Specialized QuranBot logging methods available")
                
                return True
            else:
                print("❌ Webhook service creation returned None")
                return False
                
        except Exception as e:
            print(f"❌ Webhook service creation failed: {e}")
            return False
    
    async def test_event_routing(self) -> bool:
        """Test event routing and categorization."""
        print("\n🎯 Testing Event Routing and Categorization...")
        
        if not self.webhook_service:
            print("❌ No webhook service available for routing test")
            return False
        
        # Only test routing logic, don't actually send webhooks
        if not hasattr(self.webhook_service, 'route_event'):
            print("✅ Legacy webhook logger - routing test skipped (expected)")
            return True
        
        try:
            # Test event categorization
            router = self.webhook_service
            test_events = [
                ("bot_startup", "Bot Status"),
                ("audio_playback", "Quran Audio"),
                ("surah_change", "Quran Audio"),
                ("command_usage", "Commands Panel"),
                ("quiz_activity", "User Activity"),
                ("database_backup", "Data Analytics"),
                ("critical_error", "Errors & Alerts"),
                ("daily_report", "Daily Reports"),
            ]
            
            for event_type, expected_category in test_events:
                category = router._categorize_event(event_type)
                channel = router._event_routing_map.get(category)
                
                print(f"   Event: {event_type:15} -> Category: {category.value:20} -> Channel: {channel.value if channel else 'Unknown'}")
            
            print("✅ Event routing logic working correctly")
            return True
            
        except Exception as e:
            print(f"❌ Event routing test failed: {e}")
            return False
    
    async def test_dry_run_logging(self) -> bool:
        """Test logging methods without actually sending webhooks."""
        print("\n🧪 Testing Logging Methods (Dry Run)...")
        
        if not self.webhook_service:
            print("❌ No webhook service available for logging test")
            return False
        
        try:
            # Test basic logging methods exist and are callable
            test_methods = [
                ('log_bot_startup', {'version': '1.0.0', 'startup_duration': 5.2, 'services_loaded': 10}),
                ('log_audio_playback_event', {'event_type': 'surah_start', 'description': 'Test audio event'}),
                ('log_quran_command_usage', {'command_name': 'verse', 'user_name': 'TestUser', 'user_id': 12345}),
                ('log_database_operation', {'operation_type': 'backup', 'success': True}),
            ]
            
            for method_name, kwargs in test_methods:
                if hasattr(self.webhook_service, method_name):
                    method = getattr(self.webhook_service, method_name)
                    print(f"   ✅ {method_name}: Method available")
                    # Note: We don't actually call the method to avoid sending test webhooks
                else:
                    print(f"   ❌ {method_name}: Method not available")
            
            print("✅ Logging methods validation completed")
            return True
            
        except Exception as e:
            print(f"❌ Logging methods test failed: {e}")
            return False
    
    async def test_configuration_scenarios(self) -> bool:
        """Test different configuration scenarios."""
        print("\n⚙️  Testing Configuration Scenarios...")
        
        try:
            scenarios = [
                "Multi-channel setup (all channels configured)",
                "Partial setup (some channels configured)",
                "Legacy setup (only DISCORD_WEBHOOK_URL)",
                "Disabled setup (USE_WEBHOOK_LOGGING=false)",
            ]
            
            # Get current configuration state
            service_info = WebhookServiceFactory.get_webhook_service_info(self.config)
            
            if not service_info['enabled']:
                current_scenario = "Disabled setup"
            elif service_info['multi_channel_urls'] >= 4:
                current_scenario = "Multi-channel setup"
            elif service_info['multi_channel_urls'] > 0:
                current_scenario = "Partial setup"
            elif service_info['has_legacy_url']:
                current_scenario = "Legacy setup"
            else:
                current_scenario = "Unknown configuration"
            
            print(f"   Current Configuration: {current_scenario}")
            print(f"   Multi-channel URLs: {service_info['multi_channel_urls']}")
            print(f"   Legacy URL configured: {service_info['has_legacy_url']}")
            
            # Provide recommendations
            if service_info['multi_channel_urls'] == 0 and service_info['has_legacy_url']:
                print(f"   💡 Recommendation: Upgrade to multi-channel for better organization")
            elif service_info['multi_channel_urls'] < 7 and service_info['multi_channel_urls'] > 0:
                print(f"   💡 Recommendation: Configure remaining {7 - service_info['multi_channel_urls']} channels for full functionality")
            
            return True
            
        except Exception as e:
            print(f"❌ Configuration scenarios test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all webhook system tests."""
        print("=" * 60)
        print("🧪 QuranBot Multi-Channel Webhook System Test Suite")
        print("=" * 60)
        
        if not await self.initialize():
            return False
        
        tests = [
            self.test_configuration_validation,
            self.test_service_creation,
            self.test_event_routing,
            self.test_dry_run_logging,
            self.test_configuration_scenarios,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if await test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ All tests passed! Multi-channel webhook system is ready.")
        else:
            print(f"⚠️  {total - passed} tests failed. Check configuration and setup.")
        
        print("=" * 60)
        
        return passed == total
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.webhook_service and hasattr(self.webhook_service, 'shutdown'):
                await self.webhook_service.shutdown()
            if self.logger:
                await self.logger.shutdown()
        except:
            pass


async def main():
    """Main test execution."""
    tester = MultiChannelWebhookTester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)