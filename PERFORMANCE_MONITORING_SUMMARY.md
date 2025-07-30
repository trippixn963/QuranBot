# QuranBot - Performance Metrics Monitoring

## Overview
I've added comprehensive performance monitoring to your QuranBot with webhook alerts for all key performance metrics. This provides deep insights into bot performance and helps identify bottlenecks before they impact users.

## 🚀 **New Performance Monitoring Features**

### 1. **Command Response Time Tracking**
- **Automatic tracking** of all Discord command response times
- **Slow command alerts** when commands take >5 seconds
- **Success rate monitoring** for command execution
- **User-specific tracking** to identify problematic interactions

**Webhook Alerts:**
- 🐌 **Slow Command Response Times** - When multiple commands are slow
- Includes average response time, slowest command, and impact assessment

### 2. **Memory Usage Trends & Leak Detection**
- **Continuous memory monitoring** every 30 seconds
- **Memory leak detection** - alerts when memory increases >50MB in 10 minutes
- **Memory trend tracking** over time periods
- **Process-specific monitoring** (RSS, VMS, percentage)

**Webhook Alerts:**
- ⚠️ **Potential Memory Leak Detected** - When memory usage spikes
- Shows memory increase, previous/current usage, and severity level

### 3. **Database Query Performance**
- **Automatic query timing** for all database operations
- **Slow query detection** when queries take >1 second
- **Query type classification** (SELECT, INSERT, UPDATE, etc.)
- **Privacy-safe query hashing** for identification

**Webhook Alerts:**
- 🗄️ **Slow Database Queries Detected** - When multiple queries are slow
- Includes average query time, slowest query type, and performance impact

### 4. **Discord API Rate Limit Visualization**
- **Real-time API usage tracking** from Discord responses
- **Rate limit monitoring** per endpoint
- **Usage percentage calculation** and trending
- **High usage alerts** when approaching limits

**Webhook Alerts:**
- 📡 **High Discord API Usage** - When usage exceeds 80%
- Shows max usage percentage, affected endpoints, and risk level

## 📊 **Performance Metrics in Daily Reports**

Your daily health reports now include comprehensive performance data:

### **Performance Metrics Section:**
- **Avg Command Response**: 0.45s
- **Slow Commands**: 2 commands  
- **Avg Database Query**: 0.023s
- **Max API Usage**: 67.3%

### **Enhanced Context Fields:**
- Command Success Rate: 98.5%
- Memory Trend: +12.3 MB
- Slow Queries: 1 queries
- High Usage Endpoints: 0 endpoints

## 🔧 **Implementation Details**

### **Files Added:**
- `src/monitoring/performance_monitor.py` - Main performance monitoring system
- `src/monitoring/performance_decorators.py` - Automatic tracking decorators

### **Integration Points:**
- **Database Layer**: All queries automatically tracked via `execute_query()`
- **Discord API**: Rate limits tracked via API monitor integration
- **Commands**: Performance decorator applied to commands
- **Daily Reports**: Performance metrics included in daily summaries

### **Automatic Tracking:**
```python
# Commands automatically tracked
@track_command_performance("question_command")
async def question(self, interaction):
    # Command logic here
    pass

# Database queries automatically tracked
async def execute_query(self, query, params=None):
    # Automatic performance tracking built-in
    pass

# API rate limits automatically recorded
# Via Discord.py HTTP request monitoring
```

## ⚡ **Performance Thresholds**

### **Alert Thresholds:**
- **Slow Commands**: >5.0 seconds
- **Slow Queries**: >1.0 seconds  
- **Memory Leak**: >50MB increase in 10 minutes
- **High API Usage**: >80% of rate limit

### **Alert Cooldowns:**
- **5 minutes** between similar alerts to prevent spam
- **Smart grouping** of related performance issues
- **Escalation levels** based on severity

## 📈 **Monitoring Intervals**

- **Performance Check**: Every 30 seconds
- **Memory Snapshots**: Every 30 seconds
- **Alert Evaluation**: Every 30 seconds
- **Daily Summary**: 9:00 AM UTC with performance trends

## 🎯 **Benefits for 24/7 VPS Operation**

1. **Proactive Performance Monitoring**: Catch slowdowns before users notice
2. **Memory Leak Prevention**: Early detection prevents crashes
3. **Database Optimization**: Identify slow queries for optimization
4. **API Rate Limit Management**: Avoid Discord API throttling
5. **Performance Trending**: Track performance over time
6. **Automated Alerting**: No manual monitoring required
7. **Rich Webhook Notifications**: Visual progress bars and detailed context

## 📱 **What You'll See in Discord**

### **Performance Alerts:**
```
🐌 Slow Command Response Times
Multiple commands responding slowly (avg: 6.23s)

Fields:
• Slow Commands Count: 3 commands
• Average Response Time: 6.23s  
• Slowest Command: question_command
• Threshold: 5.0s
• Impact: User experience degraded
```

### **Memory Leak Alerts:**
```
⚠️ Potential Memory Leak Detected  
Memory usage increased by 67.3 MB in 10 minutes

Fields:
• Memory Increase: 67.3 MB
• Previous Memory: 245.1 MB
• Current Memory: 312.4 MB
• Severity: HIGH
```

### **Daily Performance Summary:**
```
📊 Daily Health Report - 2025-07-30

Performance Metrics:
• Avg Command Response: 0.45s
• Slow Commands: 2
• Avg Database Query: 0.023s  
• Max API Usage: 67.3%
```

Your bot now has enterprise-level performance monitoring with comprehensive webhook notifications for optimal 24/7 VPS operation!