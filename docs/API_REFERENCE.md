# 🕌 QuranBot API Reference

*"And We have certainly made the Qur'an easy for remembrance, so is there any who will remember?"* - **Quran 54:17**

## Overview

QuranBot provides a comprehensive set of Discord slash commands for Quran audio playback, learning, and community engagement. All commands are designed to serve the Muslim community with respect and Islamic values.

---

## 📋 Command Categories

### 🎵 Audio Commands
- [`/verse`](#verse) - Play specific Quran verses
- [`/interval`](#interval) - Play verses in intervals (ranges)

### 📚 Learning Commands  
- [`/question`](#question) - Interactive Quran quizzes
- [`/leaderboard`](#leaderboard) - View quiz rankings

### ℹ️ Information Commands
- [`/credits`](#credits) - View bot information and credits

---

## 🎵 Audio Commands

### `/verse`
Play specific Quran verses with professional audio recitation.

**Usage:**
```
/verse surah:<number> ayah:<number> [reciter:<name>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `surah` | Integer | ✅ Yes | Surah number (1-114) |
| `ayah` | Integer | ✅ Yes | Ayah number within the surah |
| `reciter` | String | ❌ No | Reciter name (default: Mishary Rashid Alafasy) |

**Available Reciters:**
- Mishary Rashid Alafasy (default)
- Abdul Basit Abdul Samad
- Maher Al Mueaqly
- Ahmed ibn Ali al-Ajamy
- Hani ar-Rifai
- Khalifa al-Tunaiji
- Saad al-Ghamdi
- Saud ash-Shuraim
- AbdulRahman as-Sudais
- Abu Bakr ash-Shaatree

**Examples:**
```
/verse surah:1 ayah:1
/verse surah:2 ayah:255 reciter:Abdul Basit Abdul Samad
/verse surah:112 ayah:1 reciter:Maher Al Mueaqly
```

**Response Format:**
```json
{
  "type": "audio_playback",
  "surah": 1,
  "ayah": 1,
  "reciter": "Mishary Rashid Alafasy",
  "arabic_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
  "translation": "In the name of Allah, the Entirely Merciful, the Especially Merciful.",
  "audio_url": "https://...",
  "duration": "00:03",
  "status": "playing"
}
```

---

### `/interval`
Play multiple verses in sequence with customizable intervals.

**Usage:**
```
/interval surah:<number> start_ayah:<number> end_ayah:<number> [reciter:<name>] [pause_duration:<seconds>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `surah` | Integer | ✅ Yes | Surah number (1-114) |
| `start_ayah` | Integer | ✅ Yes | Starting ayah number |
| `end_ayah` | Integer | ✅ Yes | Ending ayah number |
| `reciter` | String | ❌ No | Reciter name (default: Mishary Rashid Alafasy) |
| `pause_duration` | Integer | ❌ No | Pause between verses in seconds (default: 2) |

**Examples:**
```
/interval surah:1 start_ayah:1 end_ayah:7
/interval surah:2 start_ayah:1 end_ayah:5 reciter:Abdul Basit Abdul Samad pause_duration:3
```

**Response Format:**
```json
{
  "type": "interval_playback",
  "surah": 1,
  "start_ayah": 1,
  "end_ayah": 7,
  "total_verses": 7,
  "reciter": "Mishary Rashid Alafasy",
  "pause_duration": 2,
  "estimated_duration": "00:45",
  "status": "starting"
}
```

---

## 📚 Learning Commands

### `/question`
Interactive Quran quiz system with multiple choice questions.

**Usage:**
```
/question [difficulty:<level>] [category:<type>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `difficulty` | String | ❌ No | Question difficulty: easy, medium, hard |
| `category` | String | ❌ No | Question category: verses, surahs, general |

**Difficulty Levels:**
- **Easy**: Basic Quran knowledge, well-known verses
- **Medium**: Intermediate Islamic knowledge
- **Hard**: Advanced Quranic studies

**Categories:**
- **Verses**: Questions about specific ayahs and their meanings
- **Surahs**: Questions about surah names, numbers, and characteristics  
- **General**: Broader Islamic knowledge related to the Quran

**Examples:**
```
/question
/question difficulty:easy category:verses
/question difficulty:hard category:surahs
```

**Response Format:**
```json
{
  "type": "quiz_question",
  "question_id": "q_1234",
  "difficulty": "medium",
  "category": "verses",
  "question": "Which surah is known as 'The Opening'?",
  "options": [
    "A) Al-Baqarah",
    "B) Al-Fatiha", 
    "C) An-Nas",
    "D) Al-Ikhlas"
  ],
  "correct_answer": "B",
  "explanation": "Al-Fatiha (The Opening) is the first surah of the Quran...",
  "points": 10,
  "time_limit": 30
}
```

---

### `/leaderboard`
View quiz rankings and community statistics.

**Usage:**
```
/leaderboard [scope:<type>] [limit:<number>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | String | ❌ No | Leaderboard scope: server, global, personal |
| `limit` | Integer | ❌ No | Number of entries to show (default: 10, max: 25) |

**Scope Types:**
- **Server**: Rankings for current Discord server only
- **Global**: Rankings across all servers using the bot
- **Personal**: Your personal statistics and progress

**Examples:**
```
/leaderboard
/leaderboard scope:server limit:15
/leaderboard scope:personal
```

**Response Format:**
```json
{
  "type": "leaderboard",
  "scope": "server",
  "total_players": 156,
  "rankings": [
    {
      "rank": 1,
      "user": "Abdullah#1234",
      "score": 2450,
      "correct_answers": 245,
      "total_questions": 280,
      "accuracy": "87.5%",
      "streak": 15
    }
  ],
  "user_stats": {
    "rank": 12,
    "score": 890,
    "accuracy": "82.3%"
  }
}
```

---

## ℹ️ Information Commands

### `/credits`
Display bot information, credits, and acknowledgments.

**Usage:**
```
/credits
```

**Response Format:**
```json
{
  "type": "credits",
  "bot_info": {
    "name": "QuranBot",
    "version": "3.5.0",
    "uptime": "15 days, 8 hours",
    "servers": 42,
    "users": 1256
  },
  "features": [
    "High-quality Quran audio playback",
    "Interactive learning quizzes",
    "Multiple reciter support",
    "Community leaderboards"
  ],
  "acknowledgments": {
    "audio_source": "Quran.com API",
    "translations": "Sahih International",
    "reciters": "Various renowned Qaris"
  }
}
```

---

## 🔧 Bot Behavior & Features

### Audio Playback System
- **High-quality audio**: 128kbps+ MP3 files
- **Automatic voice channel joining**: Bot joins your current voice channel
- **Queue management**: Multiple requests are queued automatically
- **Rich presence**: Shows currently playing verse information
- **Auto-disconnect**: Leaves voice channel after 5 minutes of inactivity

### Quiz System
- **Point-based scoring**: Earn points for correct answers
- **Streak bonuses**: Consecutive correct answers increase points
- **Time limits**: 30 seconds per question (configurable)
- **Difficulty scaling**: Questions adapt to your performance
- **Progress tracking**: Personal statistics and achievements

### State Management
- **Persistent data**: User progress saved across sessions
- **Server-specific settings**: Each Discord server has independent settings
- **Backup system**: Regular data backups for reliability
- **Performance optimization**: Efficient caching and resource management

### Islamic Values Integration
- **Respectful presentation**: All content follows Islamic guidelines
- **Educational focus**: Designed to increase Quranic knowledge
- **Community building**: Features encourage positive interaction
- **Accessibility**: Easy-to-use interface for all skill levels

---

## 🔒 Permissions & Security

### Required Bot Permissions
- **Send Messages**: For command responses and notifications
- **Use Slash Commands**: For all bot interactions
- **Connect to Voice**: For audio playback
- **Speak in Voice**: For playing Quran recitations
- **Read Message History**: For context and error handling

### User Permissions
- **No special permissions required**: All commands available to all users
- **Rate limiting**: Prevents spam and abuse
- **Content filtering**: Ensures appropriate usage

### Privacy & Data
- **Minimal data collection**: Only stores quiz progress and preferences
- **No personal information**: Discord usernames and IDs only
- **Secure storage**: All data encrypted and protected
- **GDPR compliant**: Users can request data deletion

---

## 📊 Response Codes & Error Handling

### Success Responses
- `200`: Command executed successfully
- `201`: New resource created (quiz question, leaderboard entry)
- `202`: Request accepted and queued (audio playback)

### Error Responses
- `400`: Invalid parameters or malformed request
- `404`: Requested resource not found (invalid surah/ayah)
- `429`: Rate limit exceeded
- `500`: Internal server error
- `503`: Service temporarily unavailable

### Error Format
```json
{
  "error": true,
  "code": 404,
  "message": "Surah 115 does not exist. Please use surah numbers 1-114.",
  "details": "The Quran contains 114 surahs. Please check your input.",
  "suggestion": "Try /verse surah:114 ayah:1 for the last surah (An-Nas)"
}
```

---

## 🚀 Rate Limits & Performance

### Command Rate Limits
- **Audio commands**: 1 per 10 seconds per user
- **Quiz commands**: 1 per 5 seconds per user  
- **Information commands**: 2 per 10 seconds per user
- **Leaderboard**: 1 per 30 seconds per user

### Performance Metrics
- **Average response time**: < 500ms
- **Audio loading time**: < 3 seconds
- **Uptime**: 99.9% availability
- **Concurrent users**: Supports 1000+ simultaneous users

---

## 📱 Integration Examples

### Discord.py Integration
```python
import discord
from discord.ext import commands

# Example of handling QuranBot responses
@bot.event
async def on_message(message):
    if message.author.bot and message.author.name == "QuranBot":
        # Handle QuranBot responses
        if message.embeds:
            embed = message.embeds[0]
            if "verse" in embed.title.lower():
                # Process verse information
                await handle_verse_response(embed)
```

### Webhook Integration
```javascript
// Example webhook handler for QuranBot events
app.post('/quranbot-webhook', (req, res) => {
    const { event_type, data } = req.body;
    
    switch(event_type) {
        case 'verse_played':
            console.log(`Verse played: ${data.surah}:${data.ayah}`);
            break;
        case 'quiz_completed':
            console.log(`Quiz score: ${data.score}`);
            break;
    }
    
    res.status(200).send('OK');
});
```

---

## 🤝 Community & Support

### Getting Help
- **Discord Server**: Join discord.gg/syria for support
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides and tutorials

### Contributing
- **Open Source**: MIT License - contributions welcome
- **Code Standards**: Follow Islamic values and clean code principles
- **Testing**: Comprehensive test coverage required

### Educational Purpose
This bot is provided AS-IS for educational purposes to help Muslims learn and connect with the Quran. May Allah accept our efforts and grant us beneficial knowledge.

---

*"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."* - **Quran 65:3**

**بارك الله فيكم** (May Allah bless you) 