# 🔗 Discord API Health Monitoring

*"And it is He who created the heavens and earth in truth."* - **Quran 6:73**

## Overview

The Discord API Health Monitoring system provides comprehensive real-time tracking of Discord API performance, rate limits, gateway health, and overall system status. This monitoring is integrated into the QuranBot web dashboard for easy visualization and alerting.

---

## 🎯 **Features**

### **Real-time API Monitoring**
- **Response Time Tracking**: Monitor average API response times
- **Rate Limit Monitoring**: Track rate limit usage and warn before limits
- **Error Rate Tracking**: Monitor API call success/failure rates  
- **Endpoint Analytics**: Track slowest and most-used endpoints

### **Gateway Health Monitoring**
- **Connection Status**: Real-time gateway connection monitoring
- **Latency Tracking**: Monitor Discord gateway latency
- **Reconnection Tracking**: Count and log reconnection events
- **Heartbeat Monitoring**: Track gateway heartbeat health

### **Web Dashboard Integration**
- **Real-time Panels**: Live Discord API health status in dashboard
- **Visual Indicators**: Color-coded status indicators (healthy/warning/critical)
- **API Endpoints**: RESTful endpoints for external monitoring
- **Historical Data**: 24-hour data retention with trend analysis

### **Intelligent Alerting**
- **Rate Limit Warnings**: Alerts at 80% and 95% rate limit usage
- **Performance Thresholds**: Warnings for slow response times
- **Critical Status Detection**: Automatic health status calculation
- **Tree Logging**: Beautiful formatted logs with emoji indicators

---

## 📊 **Dashboard Panels**

### **Discord API Health Panel**
```
🔗 Discord API Health              [🟢]
├─ API Status: ✅ Healthy
├─ Response Time: 0.15s  
└─ Rate Limit Usage: 12.5%
```

### **Gateway Status Panel**
```
🌐 Gateway Status                  [🟢]
├─ Connection: Connected
├─ Latency: 85ms
└─ Reconnects: 2
```

---

## 🛠️ **Technical Implementation**

### **Core Components**

#### **DiscordAPIMonitor Class**
```python
from src.utils.discord_api_monitor import initialize_discord_monitor

# Initialize in bot startup
discord_monitor = initialize_discord_monitor(bot)

# Get current health
health = discord_monitor.get_current_health()
```

#### **Data Collection**
- **API Call Metrics**: Response time, status codes, rate limits
- **Gateway Metrics**: Latency, connection events, reconnections  
- **Health History**: Aggregated health status over time
- **Rate Limit Buckets**: Per-endpoint rate limit tracking

#### **Data Persistence**
- **File Storage**: JSON-based data storage in `data/discord_api_monitor.json`
- **Automatic Cleanup**: 24-hour data retention with automatic cleanup
- **Atomic Writes**: Corruption-resistant data persistence
- **Background Tasks**: Automatic data saving every 30 seconds

### **Web Dashboard Integration**

#### **API Endpoints**
```bash
# Discord API health status
GET /api/discord/health

# API metrics summary  
GET /api/discord/metrics

# Gateway connection status
GET /api/discord/gateway
```

#### **Dashboard Functions**
```python
# Get Discord API health for dashboard
health = get_discord_api_health()

# Get gateway status for dashboard  
gateway = get_discord_gateway_status()
```

---

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Optional: VPS host for remote monitoring
VPS_HOST=root@your.vps.ip

# Optional: Dashboard URL for monitoring links
DASHBOARD_URL=http://your.dashboard.url:8080
```

### **Monitoring Thresholds**
```python
# Response time thresholds (seconds)
RESPONSE_TIME_WARNING = 2.0    # Warn if > 2 seconds
RESPONSE_TIME_CRITICAL = 5.0   # Critical if > 5 seconds

# Rate limit thresholds (percentage)
RATE_LIMIT_WARNING_THRESHOLD = 0.8    # 80%
RATE_LIMIT_CRITICAL_THRESHOLD = 0.95  # 95%

# Data retention
MAX_AGE_HOURS = 24  # Keep data for 24 hours
```

---

## 📈 **Status Indicators**

### **Health Status Levels**
- **🟢 Healthy**: All systems operating normally
- **🟡 Warning**: Performance degraded but functional
- **🔴 Critical**: Significant issues requiring attention
- **⚫ Unavailable**: Monitoring system not available

### **Status Calculation Logic**
```python
# Critical conditions
if (response_time > 5.0 or 
    error_rate > 10% or 
    rate_limit_usage > 95% or
    not gateway_connected):
    status = "critical"

# Warning conditions  
elif (response_time > 2.0 or
      error_rate > 5% or
      rate_limit_usage > 80% or
      gateway_latency > 500ms):
    status = "warning"

else:
    status = "healthy"
```

---

## 🚨 **Alerting System**

### **Rate Limit Alerts**
```
🚨 Discord API - Critical Rate Limit
├─ endpoint: POST:/channels/{channel_id}/messages
├─ usage: 96.2%
├─ remaining: 12
├─ limit: 300
└─ status: 🚨 CRITICAL
```

### **Performance Alerts**
```
⚠️ Discord API - Response Time Warning
├─ endpoint: GET:/guilds/{guild_id}/members
├─ avg_response_time: 3.2s
├─ threshold: 2.0s
└─ status: ⚠️ WARNING
```

---

## 🔍 **Monitoring Data**

### **API Call Metrics**
```json
{
  "timestamp": 1704067200.0,
  "endpoint": "/channels/{channel_id}/messages",
  "method": "POST",
  "response_time": 0.15,
  "status_code": 200,
  "rate_limit_remaining": 45,
  "rate_limit_limit": 50,
  "error_message": null
}
```

### **Gateway Metrics**
```json
{
  "timestamp": 1704067200.0,
  "latency": 0.085,
  "is_connected": true,
  "reconnect_count": 2,
  "event_type": "heartbeat"
}
```

### **Health Summary**
```json
{
  "timestamp": 1704067200.0,
  "is_healthy": true,
  "avg_response_time": 0.15,
  "rate_limit_usage": 0.125,
  "gateway_latency": 0.085,
  "gateway_connected": true,
  "total_api_calls": 1247,
  "error_rate": 0.02,
  "status": "healthy"
}
```

---

## 🧪 **Testing**

### **Test Suite**
```bash
# Run comprehensive monitoring tests
python tools/test_discord_api_monitor.py
```

### **Test Coverage**
- ✅ **Discord Monitor Core**: Monitor initialization and data collection
- ✅ **Web Dashboard Integration**: Dashboard functions and API endpoints
- ✅ **Data Persistence**: File storage and data integrity

### **Expected Test Results**
```
📋 Test Results Summary:
✅ PASS - Web Dashboard Integration
✅ PASS - Data Persistence  
❌ FAIL - Discord Monitor Core (expected when bot not running)
```

---

## 📚 **Usage Examples**

### **Basic Monitoring**
```python
# Get current health status
from src.utils.discord_api_monitor import get_discord_monitor

monitor = get_discord_monitor()
if monitor:
    health = monitor.get_current_health()
    print(f"Status: {health['status']}")
    print(f"Response Time: {health['avg_response_time']:.3f}s")
```

### **Dashboard Integration**
```python
# Get data for web dashboard
from tools.web_dashboard import get_discord_api_health

health = get_discord_api_health()
status_indicator = "online" if health.get('is_healthy') else "warning"
```

### **API Monitoring**
```bash
# Check Discord API health via REST API
curl http://localhost:8080/api/discord/health

# Get API metrics summary
curl http://localhost:8080/api/discord/metrics

# Check gateway status
curl http://localhost:8080/api/discord/gateway
```

---

## 🔮 **Future Enhancements**

### **Planned Features**
- **Historical Charts**: Graphical trend analysis in dashboard
- **Email Alerts**: SMTP notifications for critical issues
- **Slack Integration**: Webhook notifications to Slack channels
- **Custom Thresholds**: User-configurable alert thresholds
- **Export Functionality**: Data export for external analysis

### **Advanced Monitoring**
- **Endpoint Performance Profiling**: Detailed per-endpoint analytics
- **Predictive Alerting**: Machine learning for proactive alerts
- **Cross-Service Correlation**: Integration with system monitoring
- **Real-time Streaming**: WebSocket-based real-time updates

---

## 🎯 **Best Practices**

### **Monitoring Strategy**
1. **Monitor Proactively**: Set up alerts before issues occur
2. **Review Regularly**: Check dashboard daily for trends
3. **Optimize Performance**: Use metrics to identify bottlenecks
4. **Plan Capacity**: Monitor rate limits to plan usage

### **Alert Management**
1. **Set Appropriate Thresholds**: Avoid alert fatigue
2. **Escalate Properly**: Critical alerts need immediate attention
3. **Document Responses**: Track how issues are resolved
4. **Review Patterns**: Look for recurring issues

### **Data Management**
1. **Regular Cleanup**: Automatic 24-hour retention
2. **Backup Important Data**: Export critical metrics
3. **Monitor Storage**: Ensure adequate disk space
4. **Validate Integrity**: Regular data consistency checks

---

## 🎉 **Summary**

The Discord API Health Monitoring system provides comprehensive real-time monitoring of QuranBot's Discord integration:

- **✅ Real-time Monitoring**: API response times, rate limits, gateway health
- **✅ Web Dashboard**: Beautiful visual panels with status indicators  
- **✅ Intelligent Alerting**: Proactive warnings and critical alerts
- **✅ Data Persistence**: 24-hour historical data with automatic cleanup
- **✅ RESTful APIs**: External integration capabilities
- **✅ Perfect Tree Logging**: Beautiful formatted logs for troubleshooting

This monitoring system ensures QuranBot maintains optimal Discord API performance while serving the Islamic community 24/7 with reliability and excellence. 🕌✨ 