# QuranBot API Reference

Complete API documentation for QuranBot - Professional Discord bot for 24/7 Quranic recitation.

## 📋 Documentation Index

### Core API Documentation
- **[API Overview](api/README.md)** - Complete introduction and getting started guide
- **[OpenAPI Specification](api/openapi.yaml)** - Machine-readable API specification
- **[Integration Guide](api/integration-guide.md)** - Step-by-step integration instructions
- **[Usage Examples](api/usage-examples.md)** - Practical code examples in multiple languages
- **[Error Codes Reference](api/error-codes.md)** - Comprehensive error handling guide

### Development Resources
- **[Postman Collection](api/postman-collection.json)** - Ready-to-use API testing collection
- **[SDK Documentation](api/sdk-documentation.md)** - Official and community SDKs
- **[WebSocket Events](api/websocket-events.md)** - Real-time event streaming
- **[Rate Limiting Guide](api/rate-limiting.md)** - Understanding and handling rate limits

## 🚀 Quick Start

### 1. Authentication
```http
Authorization: Bot YOUR_DISCORD_BOT_TOKEN
Content-Type: application/json
```

### 2. First API Call
```bash
curl -X GET "https://api.quranbot.example.com/audio/status" \
  -H "Authorization: Bot YOUR_BOT_TOKEN"
```

### 3. Response Format
```json
{
  "is_playing": true,
  "current_surah": 1,
  "current_reciter": "Saad Al Ghamdi",
  "position_seconds": 45.7,
  "listeners_count": 5
}
```

## 🎵 Core Features

### Audio System
- **24/7 Continuous Playback** - Automated Quran recitation
- **Multiple Reciters** - 6+ world-class Quranic reciters
- **Smart Resume** - Remembers position across restarts
- **Voice Channel Management** - Automatic connection and reconnection

### Interactive Features
- **Islamic Quiz System** - 200+ questions across multiple categories
- **AI Assistant** - GPT-powered Islamic Q&A
- **Daily Verses** - Automated verse delivery with translations
- **User Analytics** - Detailed listening and engagement statistics

### Administration
- **Real-time Monitoring** - Health checks and system metrics
- **Configuration Management** - Dynamic settings updates
- **User Management** - Role-based access control
- **Comprehensive Logging** - Detailed audit trails

## 📊 API Endpoints Overview

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Audio** | 5 endpoints | Playback control and status |
| **Quiz** | 4 endpoints | Interactive Islamic quizzes |
| **AI** | 2 endpoints | Islamic AI assistant |
| **Commands** | 3 endpoints | Discord slash commands |
| **Analytics** | 3 endpoints | User and server statistics |
| **Admin** | 4 endpoints | Administrative functions |

## 🔧 Integration Examples

### Python (discord.py)
```python
import discord
from discord.ext import commands

@bot.slash_command()
async def play_quran(ctx, surah: int = 1):
    audio_service = bot.get_cog('AudioService')
    result = await audio_service.start_playback(surah_number=surah)

    if result['success']:
        await ctx.respond(f"🎵 Now playing Surah {surah}")
    else:
        await ctx.respond("❌ Failed to start playback")
```

### JavaScript (discord.js)
```javascript
const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('play')
        .setDescription('Start Quran playback'),

    async execute(interaction) {
        const result = await quranbot.audio.play();
        await interaction.reply('🎵 Quran playback started!');
    }
};
```

### cURL
```bash
# Start audio playback
curl -X POST "https://api.quranbot.example.com/audio/play" \
  -H "Authorization: Bot YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"surah_number": 1, "reciter": "Saad Al Ghamdi"}'
```

## 🛡️ Error Handling

### Standard Error Format
```json
{
  "error": {
    "code": "AUDIO_INVALID_SURAH",
    "message": "Surah number must be between 1 and 114",
    "details": {
      "provided": 150,
      "valid_range": "1-114"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Common Error Codes
- `AUDIO_PLAYBACK_FAILED` - Audio system error
- `QUIZ_RATE_LIMITED` - Too many quiz attempts
- `AI_SERVICE_UNAVAILABLE` - AI assistant unavailable
- `AUTH_INSUFFICIENT_PERMISSIONS` - Permission denied
- `RATE_LIMIT_EXCEEDED` - Rate limit hit

## 📈 Rate Limits

| Operation | Limit | Window | Scope |
|-----------|-------|---------|-------|
| Audio Commands | 5 requests | 1 minute | Per user |
| Quiz Sessions | 1 session | 5 minutes | Per user |
| AI Questions | 1 question | 1 hour | Per user |
| General Commands | 10 requests | 1 minute | Per user |

## 🔌 WebSocket Events

Real-time events for live updates:

```javascript
const ws = new WebSocket('wss://api.quranbot.example.com/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch(data.type) {
        case 'audio.started':
            console.log(`Audio started: Surah ${data.surah_number}`);
            break;
        case 'user.joined':
            console.log(`User joined voice channel`);
            break;
    }
};
```

## 📦 SDKs and Libraries

### Official SDKs
- **Python**: `pip install quranbot-sdk`
- **JavaScript**: `npm install quranbot-sdk`
- **Go**: `go get github.com/quranbot/go-sdk`

### Community Libraries
- **Java**: Maven Central
- **C#**: NuGet Package
- **Rust**: crates.io
- **PHP**: Packagist

## 🧪 Testing

### Postman Collection
Import our [Postman collection](api/postman-collection.json) for easy testing:

1. Download the collection file
2. Import into Postman
3. Set your bot token as environment variable
4. Start testing endpoints

### Sandbox Environment
Test safely in our sandbox:
```
Base URL: https://sandbox-api.quranbot.example.com
WebSocket: wss://sandbox-api.quranbot.example.com/ws
```

## 📚 Additional Resources

### Documentation
- [Architecture Overview](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Development Guide](DEVELOPMENT_GUIDE.md)
- [Security Guidelines](SECURITY.md)

### Community
- **GitHub**: Issues and discussions
- **Discord**: Community support
- **Stack Overflow**: Tag with `quranbot`
- **Reddit**: r/QuranBot

### Support
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Discussions
- **Security Issues**: security@quranbot.example.com
- **General Support**: support@quranbot.example.com

## 🔄 Changelog

### Version 4.0.1 (Current)
- Enhanced error handling and validation
- Improved rate limiting algorithms
- New analytics endpoints
- WebSocket event streaming
- Performance optimizations

### Version 4.0.0
- Complete API redesign
- Modern authentication system
- Comprehensive error codes
- Real-time WebSocket events
- Multi-language SDK support

## 🤝 Contributing

We welcome contributions to improve the API:

1. **Fork** the repository
2. **Create** a feature branch
3. **Implement** your changes
4. **Add** tests and documentation
5. **Submit** a pull request

### Development Setup
```bash
git clone https://github.com/trippixn963/QuranBot.git
cd QuranBot
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## 📄 License

QuranBot API is released under the [MIT License](../LICENSE).

---

**"And We have certainly made the Quran easy for remembrance, so is there any who will remember?"** - *Quran 54:17*

For the latest updates and announcements, follow our [GitHub repository](https://github.com/trippixn963/QuranBot).
