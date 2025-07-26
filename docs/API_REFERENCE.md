# 🕌 QuranBot API Reference

_"And We have certainly made the Qur'an easy for remembrance, so is there any who will remember?"_ - **Quran 54:17**

## Overview

QuranBot provides both Discord slash commands for user interaction and a comprehensive internal API architecture for developers. The modernized architecture features dependency injection, type-safe services, and comprehensive error handling. All components are designed to serve the Muslim community with respect and Islamic values.

## 🏗️ Architecture APIs

### **Dependency Injection Container**

The `DIContainer` is the core of the modernized architecture, managing service lifecycle and dependencies.

### **Configuration System**

The new configuration system uses Pydantic for type-safe validation and environment-based configuration management.

### **Core Services**

Modern core services provide infrastructure capabilities like caching, logging, performance monitoring, and security.

### **Modern Services**

Application-specific services handle audio playback, state management, and metadata caching with full dependency injection support.

---

## 🏗️ Modernized Architecture APIs

### **DIContainer**

```python
class DIContainer:
    """Dependency injection container for service management."""

    def register_singleton(self, interface: Type[T], instance_or_factory: Any) -> None:
        """Register a singleton service."""

    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a transient service factory."""

    def get(self, interface: Type[T]) -> T:
        """Resolve a service instance."""

    def has(self, interface: Type[T]) -> bool:
        """Check if a service is registered."""
```

### **ConfigService**

```python
class ConfigService:
    """Centralized configuration service with Pydantic validation."""

    @property
    def config(self) -> BotConfig:
        """Get the current configuration instance."""

    def reload_config(self) -> bool:
        """Reload configuration from environment."""

    def validate_config(self) -> bool:
        """Validate current configuration."""
```

### **StructuredLogger**

```python
class StructuredLogger:
    """Structured logging with JSON output and correlation IDs."""

    async def info(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log info message with structured context."""

    async def error(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log error message with structured context."""

    async def debug(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log debug message with structured context."""
```

### **AudioService**

```python
class AudioService:
    """Modern audio service with dependency injection."""

    async def initialize(self) -> bool:
        """Initialize the audio service."""

    async def connect_to_voice_channel(self, channel_id: int, guild_id: int) -> bool:
        """Connect to a Discord voice channel."""

    async def start_playback(self, resume_position: bool = True) -> bool:
        """Start audio playback with optional resume."""

    async def pause_playback(self) -> bool:
        """Pause current audio playback."""

    async def resume_playback(self) -> bool:
        """Resume paused audio playback."""

    async def set_surah(self, surah_number: int) -> bool:
        """Jump to a specific surah."""

    async def set_reciter(self, reciter_name: str) -> bool:
        """Switch to a different reciter."""

    async def get_playback_state(self) -> PlaybackState:
        """Get current playback state."""
```

### **StateService**

```python
class StateService:
    """State management with backup and validation."""

    async def initialize(self) -> bool:
        """Initialize the state service."""

    async def save_playback_state(self, state: PlaybackState) -> bool:
        """Save playback state with validation and backup."""

    async def load_playback_state(self) -> Optional[PlaybackState]:
        """Load playback state from storage."""

    async def save_quiz_statistics(self, user_id: int, stats: QuizStatistics) -> bool:
        """Save user quiz statistics."""

    async def load_quiz_statistics(self, user_id: int) -> Optional[QuizStatistics]:
        """Load user quiz statistics."""
```

### **CacheService**

```python
class CacheService:
    """Multi-strategy caching with persistence."""

    async def initialize(self) -> bool:
        """Initialize the cache service."""

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""

    async def clear(self) -> bool:
        """Clear all cached values."""

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
```

### **PerformanceMonitor**

```python
class PerformanceMonitor:
    """Performance monitoring and metrics collection."""

    async def initialize(self) -> bool:
        """Initialize performance monitoring."""

    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""

    def profile_context(self, operation_name: str) -> ContextManager:
        """Context manager for profiling operations."""

    async def record_operation_time(self, operation: str, duration: float) -> None:
        """Record operation execution time."""
```

### **SecurityService**

```python
class SecurityService:
    """Security features including rate limiting."""

    def rate_limit(self, max_requests: int, time_window: int) -> Callable:
        """Decorator for rate limiting functions."""

    def validate_input(self, validation_rules: Dict[str, Any]) -> Callable:
        """Decorator for input validation."""

    def require_admin(self, func: Callable) -> Callable:
        """Decorator requiring admin permissions."""

    async def check_rate_limit(self, user_id: int, operation: str) -> bool:
        """Check if user is within rate limits."""
```

---

## 📊 Data Models

### **PlaybackState**

```python
class PlaybackState(BaseModel):
    """Validated playback state model."""

    current_position: AudioPosition
    current_reciter: str
    mode: PlaybackMode = PlaybackMode.NORMAL
    is_playing: bool = False
    is_paused: bool = False
    volume: float = Field(ge=0.0, le=1.0, default=1.0)
    session_id: str
    timestamp: datetime
```

### **AudioPosition**

```python
class AudioPosition(BaseModel):
    """Audio position with validation."""

    surah_number: int = Field(ge=1, le=114)
    position_seconds: float = Field(ge=0.0)
    total_duration: Optional[float] = Field(ge=0.0)
```

### **SystemMetrics**

```python
class SystemMetrics(BaseModel):
    """System performance metrics."""

    cpu_percent: float = Field(ge=0.0, le=100.0)
    memory_percent: float = Field(ge=0.0, le=100.0)
    disk_percent: float = Field(ge=0.0, le=100.0)
    timestamp: datetime
```

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
  "options": ["A) Al-Baqarah", "B) Al-Fatiha", "C) An-Nas", "D) Al-Ikhlas"],
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
app.post("/quranbot-webhook", (req, res) => {
  const { event_type, data } = req.body;

  switch (event_type) {
    case "verse_played":
      console.log(`Verse played: ${data.surah}:${data.ayah}`);
      break;
    case "quiz_completed":
      console.log(`Quiz score: ${data.score}`);
      break;
  }

  res.status(200).send("OK");
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

_"And whoever relies upon Allah - then He is sufficient for him. Indeed, Allah will accomplish His purpose."_ - **Quran 65:3**

**بارك الله فيكم** (May Allah bless you)
