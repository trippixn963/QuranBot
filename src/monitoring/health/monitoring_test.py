"""
Comprehensive monitoring test script for the Quran Bot.
Demonstrates all the new logging capabilities without emojis.
"""

import asyncio
import time
import random
import psutil
from datetime import datetime
from monitoring.logging.logger import (
    logger, log_bot_startup, log_audio_playback, log_connection_attempt,
    log_connection_success, log_connection_failure, log_health_report,
    log_performance, log_error, log_discord_event, log_ffmpeg_operation,
    log_security_event, log_retry_operation, log_shutdown, log_disconnection,
    log_latency_monitoring, log_system_health, log_voice_state_change,
    log_audio_buffer_status, log_network_latency, log_memory_usage,
    log_discord_rate_limit, log_audio_file_access, log_voice_connection_quality,
    log_bot_presence_update, log_interaction_response_time, log_file_operation,
    log_external_api_call, log_security_alert, log_performance_metrics,
    log_startup_sequence, log_shutdown_sequence, log_heartbeat_latency,
    log_guild_join_leave, log_channel_activity, log_error_recovery,
    log_resource_cleanup, log_configuration_change, log_backup_operation,
    log_database_operation, log_cache_operation, log_websocket_event,
    log_authentication_attempt, log_permission_check, log_rate_limit_info,
    log_connection_pool_status, log_task_completion, log_memory_leak_detection,
    log_thread_activity, log_async_task_status, log_environment_check,
    log_dependency_check, log_system_event, log_health_check_component,
    log_metrics_summary, performance_tracker, system_monitor
)
from .log_helpers import log_function_call, log_operation

async def test_basic_logging():
    """Test basic logging functions."""
    print("\n=== Testing Basic Logging ===")
    
    log_bot_startup("QuranBot Test", 123456789)
    log_audio_playback("001.mp3", 180.5)
    log_connection_attempt("Quran Channel", 1, 3)
    log_connection_success("Quran Channel", "Test Guild")
    log_health_report(True, 987654321)
    log_shutdown("Test completion")

async def test_error_logging():
    """Test error logging with comprehensive tracking."""
    print("\n=== Testing Error Logging ===")
    
    try:
        # Simulate an error
        raise ValueError("Test error for logging")
    except Exception as e:
        log_error(e, "test_error_logging", retry_attempt=1, 
                 additional_data={"test_data": "value", "timestamp": datetime.now().isoformat()})

async def test_performance_logging():
    """Test performance monitoring."""
    print("\n=== Testing Performance Logging ===")
    
    # Test performance tracking
    performance_tracker.start_timer("test_operation")
    await asyncio.sleep(0.1)  # Simulate work
    duration = performance_tracker.end_timer("test_operation")
    log_performance("test_operation", duration, True)
    
    # Test latency monitoring
    log_latency_monitoring("api_call", 2500, 1000)  # Should trigger warning
    log_latency_monitoring("file_read", 500, 1000)   # Should be OK

async def test_system_monitoring():
    """Test system monitoring capabilities."""
    print("\n=== Testing System Monitoring ===")
    
    log_system_health()
    log_performance_metrics()
    log_metrics_summary()
    
    # Test memory usage logging
    process = psutil.Process()
    memory_info = process.memory_info()
    log_memory_usage(memory_info.rss / 1024 / 1024, memory_info.rss / 1024 / 1024, 100)

async def test_voice_and_audio_logging():
    """Test voice and audio related logging."""
    print("\n=== Testing Voice and Audio Logging ===")
    
    log_voice_state_change(None, type('VoiceState', (), {'channel': type('Channel', (), {'name': 'Test Channel'})()})(), "test_connection")
    log_audio_buffer_status(80, 100, 2)
    log_voice_connection_quality(96, 1.5, 150)
    log_audio_file_access("/path/to/audio/001.mp3", "read", 180.5)

async def test_discord_event_logging():
    """Test Discord event logging."""
    print("\n=== Testing Discord Event Logging ===")
    
    log_discord_event("message_create", {"user_id": 123456, "channel_id": 789012, "content": "test message"})
    log_bot_presence_update("Quran Recitation", "online")
    log_interaction_response_time("interaction_123", 2500, "/admin restart")
    log_guild_join_leave("Test Guild", 123456789, "join", 150)
    log_channel_activity("general", "text", "message_sent", 25)

async def test_network_and_api_logging():
    """Test network and API logging."""
    print("\n=== Testing Network and API Logging ===")
    
    log_network_latency(150, "Discord Gateway")
    log_discord_rate_limit("/api/v10/channels/123/messages", 2.5, 45)
    log_external_api_call("Discord API", "/api/v10/guilds/123", 200, 0.5)
    log_websocket_event("MESSAGE_CREATE", 1024, 0.1)

async def test_security_logging():
    """Test security event logging."""
    print("\n=== Testing Security Logging ===")
    
    log_security_event("permission_denied", {"user_id": 123456, "command": "admin restart", "reason": "insufficient_permissions"})
    log_security_alert("suspicious_activity", 123456, {"action": "rapid_commands", "count": 10, "timeframe": "1min"})
    log_authentication_attempt(123456, True, "token")
    log_permission_check(123456, "administrator", False, "admin command")

async def test_file_and_database_logging():
    """Test file and database operations logging."""
    print("\n=== Testing File and Database Logging ===")
    
    log_file_operation("read", "/path/to/config.json", 2048, 0.05)
    log_backup_operation("create", "/backup/state.json", 10240, True)
    log_database_operation("SELECT", "bot_state", 1, 0.02)
    log_cache_operation("get", "user_permissions:123456", True, 0.001)

async def test_resource_management_logging():
    """Test resource management logging."""
    print("\n=== Testing Resource Management Logging ===")
    
    log_resource_cleanup("file_handle", "audio_stream.mp3", True)
    log_connection_pool_status("database", 2, 3, 10)
    log_task_completion("audio_processing", 2.5, True, 1024)
    log_memory_leak_detection("audio_buffer", 100, 150, 10)

async def test_async_and_thread_logging():
    """Test async and thread logging."""
    print("\n=== Testing Async and Thread Logging ===")
    
    log_thread_activity("audio_thread", "processing_chunk", 0.1)
    log_async_task_status("voice_connection", "COMPLETED", 1.5)
    log_async_task_status("message_send", "FAILED", 0.5)

async def test_health_and_monitoring_logging():
    """Test health check and monitoring logging."""
    print("\n=== Testing Health and Monitoring Logging ===")
    
    log_health_check_component("voice_connection", "HEALTHY", 0.1, "Connected to Discord")
    log_health_check_component("audio_playback", "DEGRADED", 2.0, "High latency detected")
    log_environment_check("ffmpeg", "PASS", "FFmpeg 4.4.2 available")
    log_dependency_check("discord.py", "2.3.0", "OK")

async def test_system_event_logging():
    """Test system event logging."""
    print("\n=== Testing System Event Logging ===")
    
    log_system_event("startup", "INFO", "Bot initialization started", {"version": "2.0.0", "environment": "production"})
    log_system_event("configuration_change", "WARNING", "Audio quality setting changed", {"old_value": "high", "new_value": "medium"})
    log_system_event("critical_error", "CRITICAL", "Voice connection lost", {"reason": "network_timeout", "duration": 30})

async def test_rate_limit_and_connection_logging():
    """Test rate limit and connection logging."""
    print("\n=== Testing Rate Limit and Connection Logging ===")
    
    log_rate_limit_info("message_create", 45, 2.5)
    log_connection_pool_status("websocket", 1, 0, 1)
    log_heartbeat_latency(75)

async def test_error_recovery_logging():
    """Test error recovery logging."""
    print("\n=== Testing Error Recovery Logging ===")
    
    log_error_recovery("voice_connection", "auto_reconnect", True)
    log_error_recovery("audio_playback", "restart_stream", False)

async def test_configuration_logging():
    """Test configuration change logging."""
    print("\n=== Testing Configuration Logging ===")
    
    log_configuration_change("audio_quality", "high", "medium")
    log_configuration_change("log_level", "INFO", "DEBUG")

async def main():
    """Run all monitoring tests."""
    print("Starting comprehensive monitoring test...")
    print("=" * 50)
    
    # Test all logging categories
    await test_basic_logging()
    await test_error_logging()
    await test_performance_logging()
    await test_system_monitoring()
    await test_voice_and_audio_logging()
    await test_discord_event_logging()
    await test_network_and_api_logging()
    await test_security_logging()
    await test_file_and_database_logging()
    await test_resource_management_logging()
    await test_async_and_thread_logging()
    await test_health_and_monitoring_logging()
    await test_system_event_logging()
    await test_rate_limit_and_connection_logging()
    await test_error_recovery_logging()
    await test_configuration_logging()
    
    print("\n" + "=" * 50)
    print("Comprehensive monitoring test completed!")
    print("Check the logs for detailed output without emojis.")
    
    # Final system health check
    log_system_health()

if __name__ == "__main__":
    asyncio.run(main()) 