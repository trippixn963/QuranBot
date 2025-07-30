# QuranBot Integration Guide

Step-by-step guide for integrating QuranBot into your Discord server and applications.

## Quick Start

### 1. Bot Setup
1. Create Discord application at https://discord.com/developers/applications
2. Create bot user and copy token
3. Invite bot to server with required permissions
4. Configure environment variables

### 2. Basic Integration
```python
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.slash_command()
async def play_quran(ctx):
    # Integration with QuranBot audio system
    pass

bot.run('paste_your_bot_token_here')
```

### 3. Advanced Features
- Audio playback control
- Quiz system integration  
- AI assistant queries
- User analytics tracking

## Configuration

### Required Settings
```env
DISCORD_TOKEN=paste_your_bot_token_here
GUILD_ID=your_discord_server_id_18_digits
TARGET_CHANNEL_ID=your_voice_channel_id_18_digits
```

### Optional Features
```env
OPENAI_API_KEY=sk-your_openai_api_key_starts_with_sk
WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
```

## API Integration Examples

### Audio Control
```python
# Start playback
await quranbot.audio.play(surah=1, reciter="Saad Al Ghamdi")

# Get status
status = await quranbot.audio.get_status()
```

### Quiz System
```python
# Start quiz
quiz = await quranbot.quiz.start(category="quran")

# Submit answer
result = await quranbot.quiz.answer(session_id, answer_index)
```

## Error Handling

Always implement proper error handling:

```python
try:
    result = await quranbot.audio.play()
except QuranBotError as e:
    if e.code == 'RATE_LIMITED':
        await asyncio.sleep(e.retry_after)
    else:
        logger.error(f"QuranBot error: {e}")
```

## Best Practices

1. **Rate Limiting**: Respect API limits
2. **Error Handling**: Handle all error cases
3. **Permissions**: Ensure proper Discord permissions
4. **Logging**: Log important events
5. **Testing**: Test in development environment first

## Support

For integration help:
- Check error codes documentation
- Review usage examples
- Join community Discord
- Open GitHub issues for bugs