# QuranBot - Comprehensive Webhook Monitoring for 24/7 VPS Operation

## Overview
Your QuranBot now has comprehensive webhook logging for complete 24/7 VPS monitoring. You'll receive Discord notifications for all critical events without needing to SSH into your server.

## New Monitoring Systems Added

### 1. System Resource Monitor (`src/monitoring/system_monitor.py`)
**Monitors every 2 minutes:**
- CPU usage (warns at 80%, critical at 95%)
- Memory usage (warns at 85%, critical at 95%)
- Disk usage (warns at 90%, critical at 95%)
- Sends webhook alerts with 5-minute cooldowns

### 2. Daily Health Reporter (`src/monitoring/daily_reporter.py`)
**Daily reports at 9:00 AM UTC:**
- Complete system health summary
- Resource usage statistics
- Bot activity metrics (audio sessions, user interactions)
- Error/warning counts
- Overall health status

### 3. Enhanced Bot Lifecycle Monitoring
**New webhook events:**
- ✅ Bot startup success with timing and service counts
- 🚨 Critical initialization failures
- ⚠️ Discord connection lost
- ✅ Discord reconnection restored
- ❌ Discord event errors with stack traces

### 4. Database Operation Monitoring
**Database webhook alerts:**
- ⚠️ Database load failures
- 🚨 Critical database save failures (data loss risk)
- Database operation context and error details

### 5. Audio System Monitoring
**Audio system webhook events:**
- ✅ Voice channel connection success
- 🚨 Voice connection failures after multiple attempts
- ✅ Audio system recovery notifications
- Connection attempt tracking and latency info

## Webhook Channel Routing

Your enhanced webhook router intelligently routes events to appropriate Discord channels:

- **🤖 Bot Status**: Startup, shutdown, Discord connection events
- **🎵 Quran Audio**: Voice channel connections, audio playback events
- **⚡ Commands Panel**: Command usage, control panel interactions
- **👤 User Activity**: User engagement, quiz activities, voice joins/leaves
- **📊 Data Analytics**: Database operations, performance metrics
- **🚨 Errors & Alerts**: System errors, resource alerts, critical failures
- **📈 Daily Reports**: Daily health summaries and analytics

## What You'll See in Discord

### Critical Alerts (with owner pings)
- 🚨 Bot initialization failures
- 🚨 Database save failures (data loss risk)
- 🚨 System resource critical usage (CPU/Memory/Disk >95%)
- 🚨 Voice connection failures after multiple attempts

### Warning Notifications
- ⚠️ Discord connection lost
- ⚠️ Database load errors
- ⚠️ High resource usage (CPU >80%, Memory >85%, Disk >90%)

### Success Notifications
- ✅ Bot startup completed
- ✅ Discord reconnection restored
- ✅ Voice channel connected
- ✅ Audio system recovered
- ✅ System monitoring activated

### Daily Health Reports
- 📊 Complete system status at 9:00 AM UTC
- Resource usage trends
- Bot activity statistics
- Error/warning summaries
- Overall health assessment

## Configuration

The monitoring systems are automatically initialized when your bot starts. You can adjust:

**System Monitor Thresholds** (`src/monitoring/system_monitor.py`):
```python
self.cpu_warning_threshold = 80.0  # %
self.cpu_critical_threshold = 95.0  # %
self.memory_warning_threshold = 85.0  # %
self.memory_critical_threshold = 95.0  # %
```

**Daily Report Time** (`src/core/main.py`):
```python
await daily_reporter.start_daily_reporting(report_hour=9)  # 9 AM UTC
```

**Resource Check Interval** (`src/core/main.py`):
```python
await system_monitor.start_monitoring(interval_seconds=120)  # 2 minutes
```

## Benefits for 24/7 VPS Operation

1. **Proactive Monitoring**: Get alerts before problems become critical
2. **Complete Visibility**: See all bot activity without SSH access
3. **Quick Response**: Owner pings for critical issues requiring immediate attention
4. **Historical Tracking**: Daily reports help identify trends and patterns
5. **System Health**: Monitor VPS resources to prevent crashes
6. **Audio Reliability**: Track voice connection health for 24/7 audio playback
7. **Database Integrity**: Monitor data persistence and prevent data loss

## Next Steps

1. **Configure Webhook URLs**: Ensure your Discord webhook URLs are set in the bot configuration
2. **Test Alerts**: Monitor the webhook channels to verify alerts are working
3. **Adjust Thresholds**: Fine-tune alert thresholds based on your VPS specifications
4. **Set Up Monitoring Dashboard**: Consider creating a dedicated Discord server/channels for monitoring

Your bot now provides enterprise-level monitoring and alerting for reliable 24/7 operation!
