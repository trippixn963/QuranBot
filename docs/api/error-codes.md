# QuranBot API Error Codes

This document provides a comprehensive reference for all error codes returned by the QuranBot API.

## Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "additional": "context-specific information"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

## HTTP Status Codes

| Status Code | Description | When Used |
|-------------|-------------|-----------|
| 400 | Bad Request | Invalid input parameters or malformed request |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions for the requested action |
| 404 | Not Found | Requested resource does not exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server-side error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Error Code Categories

### Audio System Errors (AUDIO_*)

#### AUDIO_PLAYBACK_FAILED
- **HTTP Status**: 500
- **Description**: Failed to start or continue audio playback
- **Common Causes**:
  - FFmpeg not available or misconfigured
  - Audio file corruption or missing
  - Voice channel connection issues
- **Resolution**: Check audio configuration and file integrity

```json
{
  "error": {
    "code": "AUDIO_PLAYBACK_FAILED",
    "message": "Failed to start audio playback",
    "details": {
      "surah_number": 1,
      "reciter": "Saad Al Ghamdi",
      "reason": "Audio file not found"
    }
  }
}
```

#### AUDIO_INVALID_SURAH
- **HTTP Status**: 400
- **Description**: Invalid surah number provided
- **Valid Range**: 1-114
- **Resolution**: Provide a valid surah number

```json
{
  "error": {
    "code": "AUDIO_INVALID_SURAH",
    "message": "Surah number must be between 1 and 114",
    "details": {
      "provided": 150,
      "valid_range": "1-114"
    }
  }
}
```

#### AUDIO_INVALID_RECITER
- **HTTP Status**: 400
- **Description**: Invalid or unsupported reciter name
- **Resolution**: Use one of the supported reciters

```json
{
  "error": {
    "code": "AUDIO_INVALID_RECITER",
    "message": "Unsupported reciter name",
    "details": {
      "provided": "Unknown Reciter",
      "supported_reciters": [
        "Saad Al Ghamdi",
        "Abdul Basit Abdul Samad",
        "Maher Al Muaiqly"
      ]
    }
  }
}
```

#### AUDIO_VOICE_CHANNEL_ERROR
- **HTTP Status**: 403
- **Description**: Cannot connect to or access voice channel
- **Common Causes**:
  - Bot lacks voice channel permissions
  - Voice channel is full
  - Voice channel doesn't exist
- **Resolution**: Check bot permissions and channel configuration

```json
{
  "error": {
    "code": "AUDIO_VOICE_CHANNEL_ERROR",
    "message": "Cannot connect to voice channel",
    "details": {
      "channel_id": "123456789012345678",
      "reason": "Missing permissions",
      "required_permissions": ["CONNECT", "SPEAK"]
    }
  }
}
```

#### AUDIO_CONCURRENT_LIMIT
- **HTTP Status**: 429
- **Description**: Maximum concurrent audio streams reached
- **Resolution**: Wait for current stream to end or stop existing stream

```json
{
  "error": {
    "code": "AUDIO_CONCURRENT_LIMIT",
    "message": "Maximum concurrent audio streams reached",
    "details": {
      "current_streams": 1,
      "max_allowed": 1,
      "retry_after": 300
    }
  }
}
```

### Quiz System Errors (QUIZ_*)

#### QUIZ_SESSION_NOT_FOUND
- **HTTP Status**: 404
- **Description**: Quiz session ID not found or expired
- **Resolution**: Start a new quiz session

```json
{
  "error": {
    "code": "QUIZ_SESSION_NOT_FOUND",
    "message": "Quiz session not found or expired",
    "details": {
      "session_id": "quiz_123456789",
      "possible_reasons": ["Session expired", "Invalid session ID"]
    }
  }
}
```

#### QUIZ_INVALID_ANSWER
- **HTTP Status**: 400
- **Description**: Invalid answer index provided
- **Valid Range**: 0-3 (for multiple choice questions)
- **Resolution**: Provide a valid answer index

```json
{
  "error": {
    "code": "QUIZ_INVALID_ANSWER",
    "message": "Answer index must be between 0 and 3",
    "details": {
      "provided": 5,
      "valid_range": "0-3"
    }
  }
}
```

#### QUIZ_RATE_LIMITED
- **HTTP Status**: 429
- **Description**: Too many quiz attempts in a short period
- **Resolution**: Wait before starting another quiz

```json
{
  "error": {
    "code": "QUIZ_RATE_LIMITED",
    "message": "Too many quiz attempts. Please wait before trying again.",
    "details": {
      "retry_after": 300,
      "limit": "1 quiz per 5 minutes"
    }
  }
}
```

#### QUIZ_CATEGORY_INVALID
- **HTTP Status**: 400
- **Description**: Invalid quiz category specified
- **Resolution**: Use a supported quiz category

```json
{
  "error": {
    "code": "QUIZ_CATEGORY_INVALID",
    "message": "Invalid quiz category",
    "details": {
      "provided": "invalid_category",
      "supported_categories": ["quran", "hadith", "fiqh", "history"]
    }
  }
}
```

### AI Assistant Errors (AI_*)

#### AI_RATE_LIMITED
- **HTTP Status**: 429
- **Description**: AI query rate limit exceeded (1 per hour per user)
- **Resolution**: Wait before making another AI query

```json
{
  "error": {
    "code": "AI_RATE_LIMITED",
    "message": "AI query rate limit exceeded",
    "details": {
      "limit": "1 query per hour per user",
      "retry_after": 3600,
      "next_available": "2024-01-15T11:30:00Z"
    }
  }
}
```

#### AI_QUESTION_TOO_LONG
- **HTTP Status**: 400
- **Description**: Question exceeds maximum length
- **Max Length**: 500 characters
- **Resolution**: Shorten the question

```json
{
  "error": {
    "code": "AI_QUESTION_TOO_LONG",
    "message": "Question exceeds maximum length",
    "details": {
      "provided_length": 750,
      "max_length": 500
    }
  }
}
```

#### AI_INAPPROPRIATE_CONTENT
- **HTTP Status**: 400
- **Description**: Question contains inappropriate or non-Islamic content
- **Resolution**: Ask questions related to Islamic topics only

```json
{
  "error": {
    "code": "AI_INAPPROPRIATE_CONTENT",
    "message": "Question must be related to Islamic topics",
    "details": {
      "reason": "Content not related to Islam"
    }
  }
}
```

#### AI_SERVICE_UNAVAILABLE
- **HTTP Status**: 503
- **Description**: AI service is temporarily unavailable
- **Common Causes**:
  - OpenAI API issues
  - Service maintenance
  - Configuration problems
- **Resolution**: Try again later

```json
{
  "error": {
    "code": "AI_SERVICE_UNAVAILABLE",
    "message": "AI service is temporarily unavailable",
    "details": {
      "reason": "External service unavailable",
      "retry_after": 300
    }
  }
}
```

### Authentication & Authorization Errors (AUTH_*)

#### AUTH_MISSING_TOKEN
- **HTTP Status**: 401
- **Description**: Authentication token is missing
- **Resolution**: Provide valid Discord bot token

```json
{
  "error": {
    "code": "AUTH_MISSING_TOKEN",
    "message": "Authentication token is required"
  }
}
```

#### AUTH_INVALID_TOKEN
- **HTTP Status**: 401
- **Description**: Authentication token is invalid or expired
- **Resolution**: Provide a valid Discord bot token

```json
{
  "error": {
    "code": "AUTH_INVALID_TOKEN",
    "message": "Invalid or expired authentication token"
  }
}
```

#### AUTH_INSUFFICIENT_PERMISSIONS
- **HTTP Status**: 403
- **Description**: User lacks required permissions for the action
- **Resolution**: Ensure user has appropriate Discord permissions

```json
{
  "error": {
    "code": "AUTH_INSUFFICIENT_PERMISSIONS",
    "message": "Insufficient permissions for this action",
    "details": {
      "required_permissions": ["ADMINISTRATOR"],
      "user_permissions": ["SEND_MESSAGES"]
    }
  }
}
```

#### AUTH_ADMIN_REQUIRED
- **HTTP Status**: 403
- **Description**: Admin privileges required for this endpoint
- **Resolution**: Contact an administrator

```json
{
  "error": {
    "code": "AUTH_ADMIN_REQUIRED",
    "message": "Administrator privileges required"
  }
}
```

### Rate Limiting Errors (RATE_*)

#### RATE_LIMIT_EXCEEDED
- **HTTP Status**: 429
- **Description**: General rate limit exceeded
- **Resolution**: Wait before making another request

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 10,
      "window": "1 minute",
      "retry_after": 45,
      "reset_time": "2024-01-15T10:31:00Z"
    }
  }
}
```

#### RATE_LIMIT_COMMAND_SPAM
- **HTTP Status**: 429
- **Description**: Too many commands in a short period
- **Resolution**: Reduce command frequency

```json
{
  "error": {
    "code": "RATE_LIMIT_COMMAND_SPAM",
    "message": "Too many commands sent too quickly",
    "details": {
      "commands_sent": 15,
      "limit": 10,
      "window": "1 minute",
      "retry_after": 30
    }
  }
}
```

### Configuration Errors (CONFIG_*)

#### CONFIG_INVALID_GUILD
- **HTTP Status**: 400
- **Description**: Invalid or unconfigured Discord guild
- **Resolution**: Ensure bot is properly configured for the guild

```json
{
  "error": {
    "code": "CONFIG_INVALID_GUILD",
    "message": "Bot is not configured for this guild",
    "details": {
      "guild_id": "123456789012345678",
      "configured_guild": "987654321098765432"
    }
  }
}
```

#### CONFIG_MISSING_CHANNEL
- **HTTP Status**: 404
- **Description**: Required channel is not configured or accessible
- **Resolution**: Configure the required channel in bot settings

```json
{
  "error": {
    "code": "CONFIG_MISSING_CHANNEL",
    "message": "Required channel is not configured",
    "details": {
      "channel_type": "target_voice_channel",
      "required_for": "audio_playback"
    }
  }
}
```

### System Errors (SYSTEM_*)

#### SYSTEM_MAINTENANCE
- **HTTP Status**: 503
- **Description**: System is under maintenance
- **Resolution**: Wait for maintenance to complete

```json
{
  "error": {
    "code": "SYSTEM_MAINTENANCE",
    "message": "System is currently under maintenance",
    "details": {
      "estimated_completion": "2024-01-15T12:00:00Z",
      "maintenance_type": "Scheduled update"
    }
  }
}
```

#### SYSTEM_OVERLOADED
- **HTTP Status**: 503
- **Description**: System is temporarily overloaded
- **Resolution**: Try again later

```json
{
  "error": {
    "code": "SYSTEM_OVERLOADED",
    "message": "System is temporarily overloaded",
    "details": {
      "retry_after": 60,
      "current_load": "95%"
    }
  }
}
```

#### SYSTEM_DATABASE_ERROR
- **HTTP Status**: 500
- **Description**: Database operation failed
- **Resolution**: Contact support if error persists

```json
{
  "error": {
    "code": "SYSTEM_DATABASE_ERROR",
    "message": "Database operation failed",
    "details": {
      "operation": "user_stats_query",
      "error_id": "db_error_123456"
    }
  }
}
```

## Error Handling Best Practices

### 1. Always Check HTTP Status Codes
```javascript
if (response.status >= 400) {
  const error = await response.json();
  console.error(`API Error: ${error.error.code} - ${error.error.message}`);
}
```

### 2. Implement Retry Logic for Transient Errors
```javascript
const retryableErrors = [
  'SYSTEM_OVERLOADED',
  'SYSTEM_MAINTENANCE',
  'AI_SERVICE_UNAVAILABLE'
];

if (retryableErrors.includes(error.error.code)) {
  const retryAfter = error.error.details?.retry_after || 60;
  setTimeout(() => retryRequest(), retryAfter * 1000);
}
```

### 3. Handle Rate Limiting Gracefully
```javascript
if (error.error.code === 'RATE_LIMIT_EXCEEDED') {
  const retryAfter = error.error.details.retry_after;
  console.log(`Rate limited. Retrying in ${retryAfter} seconds`);
  setTimeout(() => retryRequest(), retryAfter * 1000);
}
```

### 4. Provide User-Friendly Error Messages
```javascript
const userFriendlyMessages = {
  'AUDIO_INVALID_SURAH': 'Please enter a surah number between 1 and 114.',
  'QUIZ_RATE_LIMITED': 'Please wait a few minutes before starting another quiz.',
  'AI_RATE_LIMITED': 'You can ask one AI question per hour. Please try again later.',
  'AUTH_INSUFFICIENT_PERMISSIONS': 'You don\'t have permission to use this command.'
};

const friendlyMessage = userFriendlyMessages[error.error.code] || error.error.message;
```

### 5. Log Errors for Debugging
```javascript
console.error('QuranBot API Error:', {
  code: error.error.code,
  message: error.error.message,
  details: error.error.details,
  timestamp: error.error.timestamp,
  requestId: error.error.request_id
});
```

## Support

If you encounter persistent errors or need assistance:

1. Check this error code reference
2. Review the API documentation
3. Ensure your configuration is correct
4. Check the bot's status and logs
5. Contact support with the error code and request ID

For system-level errors (5xx status codes), include the `request_id` from the error response when contacting support.
