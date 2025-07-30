# QuranBot API Documentation

Welcome to the comprehensive API documentation for QuranBot - a professional Discord bot for 24/7 Quranic recitation with interactive features.

## 📚 Documentation Overview

This documentation provides everything you need to integrate with and extend QuranBot:

### Core Documentation
- **[OpenAPI Specification](openapi.yaml)** - Complete API specification in OpenAPI 3.0 format
- **[Usage Examples](usage-examples.md)** - Practical code examples in multiple languages
- **[Error Codes Reference](error-codes.md)** - Comprehensive error handling guide
- **[Integration Guide](integration-guide.md)** - Step-by-step integration instructions
- **[SDK Documentation](sdk-documentation.md)** - Official and community SDKs

### Quick Links
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Rate Limits](#rate-limits)
- [API Endpoints](#api-endpoints)
- [WebSocket Events](#websocket-events)
- [SDKs & Libraries](#sdks--libraries)

## 🚀 Getting Started

### Prerequisites
- Discord bot token with appropriate permissions
- Basic understanding of Discord bot development
- Python 3.11+ or Node.js 16+ (for SDK usage)

### Quick Setup
1. **Get your bot token** from Discord Developer Portal
2. **Configure permissions**: Voice channel access, message sending, slash commands
3. **Install QuranBot** in your Discord server
4. **Start using the API** with our examples and SDKs

### First API Call
```bash
# Get current audio status
curl -X GET "https://api.quranbot.example.com/audio/status" \
  -H "Authorization: Bot paste_your_bot_token_here"
```

## 🔐 Authentication

QuranBot uses Discord's standard bot authentication:

```http
Authorization: Bot paste_your_bot_token_here
Content-Type: application/json
User-Agent: YourApp/1.0.0
```

### Required Permissions
- `CONNECT` - Connect to voice channels
- `SPEAK` - Play audio in voice channels  
- `USE_SLASH_COMMANDS` - Register and use slash commands
- `SEND_MESSAGES` - Send response messages
- `EMBED_LINKS` - Send rich embeds

## ⚡ Rate Limits

QuranBot implements intelligent rate limiting to ensure fair usage:

| Endpoint Category | Limit | Window | Notes |
|------------------|-------|---------|-------|
| Audio Commands | 5 requests | 1 minute | Per user |
| Quiz Commands | 1 quiz | 5 minutes | Per user |
| AI Questions | 1 question | 1 hour | Per user |
| General Commands | 10 requests | 1 minute | Per user |
| Admin Commands | 20 requests | 1 minute | Admin users only |

### Rate Limit Headers
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642694400
X-RateLimit-Retry-After: 45
```

### Handling Rate Limits
```python
if response.status == 429:
    retry_after = int(response.headers.get('X-RateLimit-Retry-After', 60))
    await asyncio.sleep(retry_after)
    # Retry the request
```

## 🎯 API Endpoints

### Audio System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/audio/play` | Start audio playback |
| `POST` | `/audio/stop` | Stop audio playback |
| `GET` | `/audio/status` | Get playback status |
| `POST` | `/audio/jump` | Jump to specific surah |
| `POST` | `/audio/reciter` | Change reciter |

### Quiz System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/quiz/start` | Start new quiz |
| `POST` | `/quiz/answer` | Submit quiz answer |
| `GET` | `/quiz/leaderboard` | Get leaderboard |
| `GET` | `/quiz/stats/{user_id}` | Get user quiz stats |

### AI Assistant
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ai/ask` | Ask Islamic question |
| `GET` | `/ai/history/{user_id}` | Get question history |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/user/{user_id}` | Get user analytics |
| `GET` | `/analytics/server` | Get server analytics |
| `GET` | `/analytics/listening` | Get listening statistics |

### Administration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/config` | Get bot configuration |
| `POST` | `/admin/config` | Update configuration |
| `GET` | `/admin/health` | Health check |
| `GET` | `/admin/metrics` | System metrics |

## 🔌 WebSocket Events

QuranBot supports real-time events via WebSocket connections:

### Connection
```javascript
const ws = new WebSocket('wss://api.quranbot.example.com/ws');
ws.onopen = () => {
    // Send authentication
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'paste_your_bot_token_here'
    }));
};
```

### Event Types
- `audio.started` - Audio playback started
- `audio.stopped` - Audio playback stopped
- `audio.position` - Playback position update
- `quiz.started` - Quiz session started
- `quiz.answered` - Quiz answer submitted
- `user.joined` - User joined voice channel
- `user.left` - User left voice channel

### Example Event
```json
{
    "type": "audio.started",
    "timestamp": "2024-01-15T10:30:00Z",
    "data": {
        "surah_number": 1,
        "reciter": "Saad Al Ghamdi",
        "guild_id": "123456789012345678",
        "channel_id": "987654321098765432"
    }
}
```

## 📦 SDKs & Libraries

### Official SDKs

#### Python SDK
```bash
pip install quranbot-sdk
```

```python
from quranbot_sdk import QuranBotClient

async with QuranBotClient('paste_your_bot_token_here') as client:
    status = await client.audio.get_status()
    print(f"Currently playing: Surah {status.current_surah}")
```

#### JavaScript/Node.js SDK
```bash
npm install quranbot-sdk
```

```javascript
const { QuranBotClient } = require('quranbot-sdk');

const client = new QuranBotClient('paste_your_bot_token_here');
const status = await client.audio.getStatus();
console.log(`Currently playing: Surah ${status.currentSurah}`);
```

### Community Libraries
- **Go**: `github.com/community/quranbot-go`
- **Java**: `com.github.community:quranbot-java`
- **C#**: `QuranBot.NET` (NuGet)
- **Rust**: `quranbot-rs` (crates.io)

## 🛠️ Development Tools

### Postman Collection
Import our [Postman collection](postman-collection.json) for easy API testing:

```bash
# Download collection
curl -O https://api.quranbot.example.com/docs/postman-collection.json

# Import into Postman and set your bot token as environment variable
```

### OpenAPI Tools
Generate client libraries using our OpenAPI specification:

```bash
# Generate Python client
openapi-generator generate -i openapi.yaml -g python -o ./python-client

# Generate JavaScript client  
openapi-generator generate -i openapi.yaml -g javascript -o ./js-client
```

### Testing Environment
Use our sandbox environment for testing:

```
Base URL: https://sandbox-api.quranbot.example.com
WebSocket: wss://sandbox-api.quranbot.example.com/ws
```

## 📊 Monitoring & Analytics

### Health Check
```bash
curl https://api.quranbot.example.com/health
```

```json
{
    "status": "healthy",
    "version": "4.0.1",
    "uptime": 86400,
    "services": {
        "audio": "operational",
        "quiz": "operational", 
        "ai": "operational",
        "database": "operational"
    }
}
```

### Metrics Endpoint
```bash
curl https://api.quranbot.example.com/metrics
```

Returns Prometheus-compatible metrics for monitoring.

## 🔧 Configuration

### Environment Variables
```bash
# Required
DISCORD_TOKEN=paste_your_bot_token_here
GUILD_ID=your_discord_server_id_18_digits
TARGET_CHANNEL_ID=your_voice_channel_id_18_digits

# Optional
OPENAI_API_KEY=sk-your_openai_api_key_starts_with_sk
WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
LOG_LEVEL=INFO
```

### Bot Permissions
Ensure your bot has these permissions in Discord:
- View Channels
- Send Messages
- Use Slash Commands
- Connect (Voice)
- Speak (Voice)
- Embed Links
- Read Message History

## 🐛 Troubleshooting

### Common Issues

#### Authentication Errors
```json
{
    "error": {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Invalid or expired authentication token"
    }
}
```
**Solution**: Verify your bot token is correct and hasn't been regenerated.

#### Permission Errors
```json
{
    "error": {
        "code": "AUTH_INSUFFICIENT_PERMISSIONS", 
        "message": "Bot lacks required permissions"
    }
}
```
**Solution**: Check bot permissions in Discord server settings.

#### Rate Limiting
```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests"
    }
}
```
**Solution**: Implement exponential backoff retry logic.

### Debug Mode
Enable debug logging for detailed request/response information:

```python
import logging
logging.getLogger('quranbot_sdk').setLevel(logging.DEBUG)
```

### Support Channels
- **GitHub Issues**: Report bugs and feature requests
- **Discord Server**: Community support and discussions
- **Documentation**: Check our comprehensive guides
- **Stack Overflow**: Tag questions with `quranbot`

## 📈 Changelog & Versioning

### Current Version: 4.0.1
- Enhanced error handling and validation
- Improved rate limiting algorithms
- New analytics endpoints
- WebSocket event streaming
- Performance optimizations

### Versioning Policy
- **Major versions** (4.x.x): Breaking changes
- **Minor versions** (x.1.x): New features, backward compatible
- **Patch versions** (x.x.1): Bug fixes, security updates

### Migration Guides
- [v3.x to v4.x Migration Guide](migration-v4.md)
- [v2.x to v3.x Migration Guide](migration-v3.md)

## 🤝 Contributing

We welcome contributions to improve QuranBot's API and documentation:

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Development Setup
```bash
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements-dev.txt
```

### Code Standards
- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Include comprehensive tests
- Update documentation for API changes
- Add examples for new features

## 📄 License

QuranBot is released under the [MIT License](../LICENSE). You're free to use, modify, and distribute the software according to the license terms.

## 🙏 Acknowledgments

- **Islamic Scholars** for guidance on religious content
- **Open Source Community** for tools and libraries
- **Discord.py Team** for the excellent framework
- **Contributors** who help improve QuranBot
- **Users** who provide feedback and support

---

**May Allah (SWT) bless this project and make it beneficial for the Muslim community worldwide.**

*"And whoever does righteous deeds, whether male or female, while being a believer - those will enter Paradise and will not be wronged, [even as much as] the speck on a date seed."* - **Quran 4:124**