# 🚨 QuranBot Modernized Troubleshooting Guide

This guide helps diagnose and resolve common issues with the modernized QuranBot architecture featuring dependency injection, microservices, and enterprise-grade components.

## 🔍 Quick Diagnosis

### **Health Check Commands**

```bash
# Check service status
sudo systemctl status quranbot

# Check recent logs
sudo journalctl -u quranbot -n 50 --no-pager

# Check resource usage
top -p $(pgrep -f main_modernized.py)

# Check Discord connection
curl -s https://discordstatus.com/api/v2/status.json | jq '.status.indicator'
```

## 🚀 Startup Issues

### **Bot Won't Start**

#### **Problem**: Service fails to start

```bash
# Check detailed logs
sudo journalctl -u quranbot -n 100 --no-pager

# Check Python environment
/opt/QuranBot/.venv/bin/python --version

# Test configuration loading
cd /opt/QuranBot
source .venv/bin/activate
python -c "
from src.config.config_service import ConfigService
try:
    config = ConfigService()
    print('✅ Configuration loaded successfully')
    print(f'Guild ID: {config.config.GUILD_ID}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"
```

#### **Problem**: Dependency injection initialization fails

```bash
# Test DI Container initialization
cd /opt/QuranBot
source .venv/bin/activate
python -c "
from src.core.di_container import DIContainer
from src.config.config_service import ConfigService
try:
    container = DIContainer()
    config_service = ConfigService()
    container.register_singleton(ConfigService, config_service)
    print('✅ DI Container and ConfigService working')
except Exception as e:
    print(f'❌ DI Container error: {e}')
    import traceback
    traceback.print_exc()
"

# Test core services initialization
python -c "
from src.core.structured_logger import StructuredLogger
from pathlib import Path
try:
    logger = StructuredLogger(
        name='test',
        level='INFO',
        log_file=Path('logs/test.log')
    )
    print('✅ StructuredLogger working')
except Exception as e:
    print(f'❌ StructuredLogger error: {e}')
"
python -c "
from src.core.di_container import DIContainer
try:
    container = DIContainer()
    print('✅ DI Container initialized')
except Exception as e:
    print(f'❌ DI Container error: {e}')
    import traceback
    traceback.print_exc()
"
```

#### **Problem**: Configuration validation fails (New Pydantic System)

```bash
# The modernized bot uses Pydantic for type-safe configuration validation
cd /opt/QuranBot
source .venv/bin/activate

# Test configuration validation step by step
python -c "
from src.config.bot_config import BotConfig
from pydantic import ValidationError
try:
    config = BotConfig()
    print('✅ Configuration validation passed')
    print(f'Environment: {config.ENVIRONMENT}')
    print(f'Guild ID: {config.GUILD_ID}')
    print(f'Audio Folder: {config.AUDIO_FOLDER}')
except ValidationError as e:
    print('❌ Configuration validation failed:')
    for error in e.errors():
        field = error['loc'][0] if error['loc'] else 'unknown'
        message = error['msg']
        print(f'  - {field}: {message}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
"

# Check specific required fields
python -c "
import os
required_fields = [
    'DISCORD_TOKEN', 'GUILD_ID', 'TARGET_CHANNEL_ID',
    'PANEL_CHANNEL_ID', 'ADMIN_USER_ID'
]

print('Checking required environment variables:')
missing_fields = []
for field in required_fields:
    value = os.getenv(field)
    if value:
        print(f'✅ {field}: SET')
    else:
        print(f'❌ {field}: MISSING')
        missing_fields.append(field)

if missing_fields:
    print(f'\\nAdd these to config/.env:')
    for field in missing_fields:
        print(f'{field}=YOUR_VALUE_HERE')
"
```

#### **Problem**: Missing environment variables

```bash
# Check environment file exists and is readable
ls -la /opt/QuranBot/config/.env

# Check environment file content (without showing sensitive data)
cat /opt/QuranBot/config/.env | grep -E "(DISCORD_TOKEN|GUILD_ID|TARGET_CHANNEL_ID)" | sed 's/=.*/=***HIDDEN***/'

# Test ConfigService with new architecture
cd /opt/QuranBot
source .venv/bin/activate
python -c "
from src.config.config_service import ConfigService
try:
    config_service = ConfigService()
    print('✅ ConfigService initialized successfully')
    print(f'Config file: {config_service._config_file}')
    print(f'Guild ID: {config_service.config.GUILD_ID}')
    print(f'Target Channel: {config_service.config.TARGET_CHANNEL_ID}')
    print(f'Environment: {config_service.config.ENVIRONMENT}')
except Exception as e:
    print(f'❌ ConfigService error: {e}')
    import traceback
    traceback.print_exc()
"

# Validate file paths in configuration
python -c "
from src.config.bot_config import BotConfig
from pathlib import Path

try:
    config = BotConfig()

    # Check audio folder
    audio_path = Path(config.AUDIO_FOLDER)
    if audio_path.exists():
        print(f'✅ Audio folder exists: {audio_path}')
        reciters = [d.name for d in audio_path.iterdir() if d.is_dir()]
        print(f'   Available reciters: {reciters[:3]}...' if len(reciters) > 3 else f'   Available reciters: {reciters}')
    else:
        print(f'❌ Audio folder missing: {audio_path}')

    # Check FFmpeg
    ffmpeg_path = Path(config.FFMPEG_PATH)
    if ffmpeg_path.exists():
        print(f'✅ FFmpeg found: {ffmpeg_path}')
    else:
        print(f'❌ FFmpeg not found: {ffmpeg_path}')
        print('   Try: which ffmpeg')

except Exception as e:
    print(f'❌ Path validation error: {e}')
"
```

### **Discord Connection Issues**

#### **Problem**: Invalid bot token

```bash
# Test bot token
python -c "
import asyncio
import discord

async def test_token():
    token = 'YOUR_TOKEN_HERE'  # Replace with actual token
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    try:
        await client.login(token)
        print('✅ Bot token is valid')
        await client.close()
    except discord.LoginFailure:
        print('❌ Invalid bot token')
    except Exception as e:
        print(f'❌ Connection error: {e}')

asyncio.run(test_token())
"
```

#### **Problem**: Missing bot permissions

```bash
# Check bot permissions in Discord
# Ensure bot has:
# - Send Messages
# - Connect to Voice Channels
# - Speak in Voice Channels
# - Use Slash Commands
# - Read Message History
```

## 🎵 Audio System Issues

### **Audio Service Won't Initialize**

#### **Problem**: FFmpeg not found

```bash
# Check FFmpeg installation
which ffmpeg
ffmpeg -version

# Test FFmpeg path from config
python -c "
from src.config.config_service import ConfigService
import subprocess
import os

config = ConfigService()
ffmpeg_path = config.config.FFMPEG_PATH

if os.path.exists(ffmpeg_path):
    print(f'✅ FFmpeg found at {ffmpeg_path}')
    try:
        result = subprocess.run([ffmpeg_path, '-version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print('✅ FFmpeg is working')
        else:
            print(f'❌ FFmpeg error: {result.stderr}')
    except Exception as e:
        print(f'❌ FFmpeg test failed: {e}')
else:
    print(f'❌ FFmpeg not found at {ffmpeg_path}')
"
```

#### **Problem**: Audio folder missing or empty

```bash
# Check audio folder
ls -la /opt/QuranBot/audio/

# Check for reciter folders
python -c "
import os
from pathlib import Path

audio_folder = Path('/opt/QuranBot/audio')
if not audio_folder.exists():
    print('❌ Audio folder not found')
    exit(1)

reciters = [d for d in audio_folder.iterdir() if d.is_dir()]
if not reciters:
    print('❌ No reciter folders found')
else:
    print(f'✅ Found reciters: {[r.name for r in reciters]}')

    # Check for audio files
    for reciter in reciters:
        mp3_files = list(reciter.glob('*.mp3'))
        print(f'  {reciter.name}: {len(mp3_files)} MP3 files')
"
```

### **Voice Channel Connection Issues**

#### **Problem**: Can't connect to voice channel

```bash
# Test voice channel access
python -c "
import asyncio
import discord
from src.config.config_service import ConfigService

async def test_voice_connection():
    config = ConfigService()

    intents = discord.Intents.default()
    intents.voice_states = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(config.config.GUILD_ID)
        if not guild:
            print(f'❌ Guild {config.config.GUILD_ID} not found')
            await client.close()
            return

        channel = guild.get_channel(config.config.TARGET_CHANNEL_ID)
        if not channel:
            print(f'❌ Channel {config.config.TARGET_CHANNEL_ID} not found')
            await client.close()
            return

        if not isinstance(channel, discord.VoiceChannel):
            print(f'❌ Channel is not a voice channel')
            await client.close()
            return

        print(f'✅ Voice channel found: {channel.name}')

        try:
            voice_client = await channel.connect()
            print(f'✅ Connected to voice channel')
            await voice_client.disconnect()
        except Exception as e:
            print(f'❌ Connection failed: {e}')

        await client.close()

    await client.start(config.config.DISCORD_TOKEN)

asyncio.run(test_voice_connection())
"
```

## 🗄️ State Management Issues

### **State Service Problems**

#### **Problem**: State not persisting

```bash
# Check state service initialization
python -c "
import asyncio
from src.core.di_container import DIContainer
from src.services.state_service import StateService

async def test_state_service():
    container = DIContainer()
    # Setup minimal container for testing

    try:
        from src.core.structured_logger import StructuredLogger
        logger = StructuredLogger('test', 'INFO')
        container.register_singleton(StructuredLogger, lambda: logger)

        from src.data.models import StateServiceConfig
        from pathlib import Path

        config = StateServiceConfig(
            data_directory=Path('/opt/QuranBot/data'),
            backup_directory=Path('/opt/QuranBot/backup'),
            backup_interval_hours=24,
            max_backups=7
        )

        state_service = StateService(container, config, logger)
        await state_service.initialize()

        print('✅ State service initialized successfully')
        await state_service.shutdown()

    except Exception as e:
        print(f'❌ State service error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_state_service())
"
```

#### **Problem**: Backup directory issues

```bash
# Check backup directory permissions
ls -la /opt/QuranBot/backup/

# Check data directory
ls -la /opt/QuranBot/data/

# Create directories if missing
sudo mkdir -p /opt/QuranBot/{data,backup}
sudo chown -R $USER:$USER /opt/QuranBot/{data,backup}
```

## 💾 Cache Service Issues

### **Cache Performance Problems**

#### **Problem**: Cache service not working

```bash
# Test cache service
python -c "
import asyncio
from src.core.cache_service import CacheService, CacheConfig, CacheStrategy
from src.core.structured_logger import StructuredLogger

async def test_cache():
    logger = StructuredLogger('test', 'INFO')
    config = CacheConfig(
        max_entries=100,
        default_ttl_seconds=300,
        strategy=CacheStrategy.LRU
    )

    cache = CacheService(None, config, logger)  # None for container in test
    await cache.initialize()

    # Test basic operations
    await cache.set('test_key', 'test_value')
    value = await cache.get('test_key')

    if value == 'test_value':
        print('✅ Cache service working')
    else:
        print('❌ Cache service not working')

    stats = await cache.get_statistics()
    print(f'Cache stats: {stats}')

    await cache.shutdown()

asyncio.run(test_cache())
"
```

## 📊 Performance Issues

### **High Memory Usage**

#### **Problem**: Memory leaks

```bash
# Monitor memory usage
ps aux | grep python | grep main_modernized

# Check memory details
sudo cat /proc/$(pgrep -f main_modernized.py)/status | grep -E "(VmSize|VmRSS|VmHWM)"

# Monitor over time
watch -n 5 'ps aux | grep main_modernized | grep -v grep'
```

#### **Problem**: Performance degradation

```bash
# Check performance metrics
python -c "
import asyncio
from src.core.performance_monitor import PerformanceMonitor

async def check_performance():
    # This would need proper container setup
    # For quick check, use system commands
    import psutil

    print(f'CPU Usage: {psutil.cpu_percent()}%')
    print(f'Memory Usage: {psutil.virtual_memory().percent}%')
    print(f'Disk Usage: {psutil.disk_usage(\"/\").percent}%')

asyncio.run(check_performance())
"
```

## 🔐 Security Issues

### **Rate Limiting Problems**

#### **Problem**: Rate limiting too strict/loose

```bash
# Check current rate limit settings
grep RATE_LIMIT /opt/QuranBot/config/.env

# Test security service
python -c "
from src.core.security import RateLimiter, SecurityService
from src.core.structured_logger import StructuredLogger
import asyncio

async def test_security():
    logger = StructuredLogger('test', 'INFO')
    rate_limiter = RateLimiter(logger=logger)
    security = SecurityService(rate_limiter=rate_limiter, logger=logger)

    # Test rate limiting
    user_id = 12345
    for i in range(15):  # Test beyond limit
        allowed = await security.check_rate_limit(user_id, 'command')
        print(f'Request {i+1}: {\"✅\" if allowed else \"❌\"} allowed')

asyncio.run(test_security())
"
```

## 🌐 Discord API Issues

### **API Rate Limiting**

#### **Problem**: Discord API rate limits

```bash
# Check Discord API status
curl -s https://discordstatus.com/api/v2/status.json | jq '.status'

# Monitor rate limits in logs
sudo journalctl -u quranbot --since "1 hour ago" | grep -i "rate\|limit\|429"
```

### **Webhook Issues**

#### **Problem**: Webhook logging not working

```bash
# Test webhook
python -c "
import requests
import json

webhook_url = 'YOUR_WEBHOOK_URL'  # Replace with actual URL
test_data = {
    'content': 'Test message from troubleshooting',
    'username': 'QuranBot-Test'
}

try:
    response = requests.post(webhook_url, json=test_data, timeout=10)
    if response.status_code == 204:
        print('✅ Webhook working')
    else:
        print(f'❌ Webhook error: {response.status_code} - {response.text}')
except Exception as e:
    print(f'❌ Webhook request failed: {e}')
"
```

## 🔧 Service Integration Issues

### **Service Dependencies**

#### **Problem**: Service initialization order

```bash
# Check service initialization in logs
sudo journalctl -u quranbot --since "10 minutes ago" | grep -E "(initializ|start|ready)"

# Test service dependency chain
python -c "
# This would test the full DI container setup
# Check main_modernized.py for the correct initialization order
print('Check main_modernized.py for service initialization order')
print('Services should initialize in this order:')
print('1. StructuredLogger')
print('2. CacheService')
print('3. PerformanceMonitor')
print('4. ResourceManager')
print('5. SecurityService')
print('6. AudioService')
print('7. StateService')
"
```

## 📋 Debugging Tools

### **Comprehensive Health Check**

```bash
#!/bin/bash
# Save as health_check.sh and run: bash health_check.sh

echo "🔍 QuranBot Modernized Health Check"
echo "=================================="

# Service status
echo "📊 Service Status:"
sudo systemctl is-active quranbot
sudo systemctl is-enabled quranbot

# Python environment
echo -e "\n🐍 Python Environment:"
/opt/QuranBot/.venv/bin/python --version
/opt/QuranBot/.venv/bin/pip list | grep discord

# Configuration
echo -e "\n⚙️ Configuration:"
if [ -f "/opt/QuranBot/config/.env" ]; then
    echo "✅ .env file exists"
    echo "Variables found: $(grep -c "=" /opt/QuranBot/config/.env)"
else
    echo "❌ .env file missing"
fi

# FFmpeg
echo -e "\n🎵 Audio System:"
which ffmpeg && echo "✅ FFmpeg found" || echo "❌ FFmpeg not found"

# Audio files
echo -e "\n📁 Audio Files:"
if [ -d "/opt/QuranBot/audio" ]; then
    echo "✅ Audio folder exists"
    echo "Reciters: $(ls -1 /opt/QuranBot/audio | wc -l)"
else
    echo "❌ Audio folder missing"
fi

# Logs
echo -e "\n📋 Recent Logs:"
sudo journalctl -u quranbot -n 5 --no-pager

# Resource usage
echo -e "\n💻 Resource Usage:"
ps aux | grep main_modernized | grep -v grep | head -1

echo -e "\n✅ Health check complete!"
```

### **Advanced Logging Debug**

```bash
# Enable debug logging temporarily
sudo systemctl edit quranbot --full

# Add this line under [Service]:
# Environment=LOG_LEVEL=DEBUG

# Restart and monitor
sudo systemctl restart quranbot
sudo journalctl -u quranbot -f
```

### **Performance Profiling**

```bash
# Profile the bot with py-spy (install with: pip install py-spy)
sudo py-spy top --pid $(pgrep -f main_modernized.py)

# Generate flame graph
sudo py-spy record -o profile.svg --pid $(pgrep -f main_modernized.py) --duration 60
```

## 🆘 Emergency Recovery

### **Complete Reset**

```bash
# Stop service
sudo systemctl stop quranbot

# Backup current installation
sudo cp -r /opt/QuranBot /opt/QuranBot.backup.$(date +%Y%m%d-%H%M%S)

# Fresh installation
cd /opt/QuranBot
git fetch origin
git reset --hard origin/main

# Reinstall dependencies
source .venv/bin/activate
poetry install --only=main

# Restore configuration
cp /opt/QuranBot.backup.*/config/.env config/

# Restart
sudo systemctl start quranbot
```

### **Rollback to Previous Version**

```bash
# Stop service
sudo systemctl stop quranbot

# Find backup
ls -la /opt/QuranBot.backup.*

# Restore from backup
sudo rm -rf /opt/QuranBot
sudo cp -r /opt/QuranBot.backup.YYYYMMDD /opt/QuranBot

# Start service
sudo systemctl start quranbot
```

## 📞 Getting Help

### **Collecting Debug Information**

```bash
# Generate debug report
cat > debug_report.txt << EOF
=== QuranBot Debug Report ===
Date: $(date)
System: $(uname -a)

=== Service Status ===
$(sudo systemctl status quranbot --no-pager)

=== Recent Logs ===
$(sudo journalctl -u quranbot -n 50 --no-pager)

=== Configuration ===
$(cat /opt/QuranBot/config/.env | sed 's/DISCORD_TOKEN=.*/DISCORD_TOKEN=***HIDDEN***/g')

=== Resource Usage ===
$(ps aux | grep main_modernized | grep -v grep)

=== Disk Space ===
$(df -h /opt/QuranBot)
EOF

echo "Debug report saved to debug_report.txt"
```

### **Support Channels**

- **GitHub Issues**: [Create an issue](https://github.com/trippixn963/QuranBot/issues)
- **Documentation**: [Full docs](../docs/)
- **Discord**: Join the support server

---

**🚨 If issues persist, provide the debug report when seeking help!**
