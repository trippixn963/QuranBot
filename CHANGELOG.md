# Changelog

All notable changes to QuranBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.5.0] - 2025-01-10

### Added

#### 🎯 Admin Answer Key System

- **Private Admin DM System**: Admin users now receive correct answers via private DM before quiz timer starts
- **Environmental Configuration**: Admin user ID configurable via `ADMIN_USER_ID` environment variable
- **Secure Answer Delivery**: Admin answers sent privately without affecting public quiz experience
- **Enhanced Admin Experience**: Admins can participate in quizzes while having answer knowledge for moderation

#### 🔧 Enhanced User Experience

- **Improved Quiz Flow**: Seamless admin answer delivery integrated into existing quiz system
- **Better Moderation Tools**: Admins can better moderate quiz sessions with answer knowledge
- **Flexible Configuration**: Easy admin user configuration through environment variables

### Technical Improvements

- **🛡️ Security**: Admin-only features with proper user validation
- **⚡ Performance**: Efficient DM delivery system with error handling
- **🔧 Configuration**: Environment-based admin user management
- **📊 Logging**: Comprehensive logging for admin answer delivery

## [3.4.0] - 2025-07-10

### Fixed

#### 🎵 Audio Position Tracking System

- **Position Bounds Checking**: Fixed audio position tracking to prevent current time from exceeding track duration
- **Invalid Resume Prevention**: Added validation to prevent resuming from positions beyond track end
- **Track Completion Detection**: Enabled proper checking for completed tracks on startup (within 10 seconds of end)
- **Time Display Accuracy**: Fixed time display showing incorrect values like "2:13:35 / 1:57:34"

#### 🔧 Audio Manager Improvements

- **Resume Position Validation**: Added validation to ensure resume positions are within track duration limits
- **Position Tracking Loop**: Enhanced position tracking with proper bounds checking every 15 seconds
- **Playback Time Display**: Fixed `_get_playback_time_display()` to use proper bounds checking
- **Track Duration Integration**: Improved integration with MP3 duration detection for accurate positioning

#### 🎮 Quiz System Enhancements

- **Perfect Logging**: Implemented comprehensive user interaction logging with EST timestamps
- **Hardcoded ID Removal**: Replaced hardcoded Discord IDs with environment variable defaults
- **Question Embed Cleanup**: Added automatic deletion of question embeds after timer expires

#### 📊 Leaderboard System Improvements

- **Pagination System**: Added pagination for leaderboard showing top 30 users with 5 per page
- **Navigation Buttons**: Implemented left/right arrow navigation (⬅️➡️) with 5-minute timeout
- **Visual Enhancements**: Restored bot profile picture thumbnail and admin footer across all pages
- **User Access Control**: Added user-specific button access control for navigation

#### 🕐 Timezone & Logging Enhancements

- **EST Timezone Support**: Changed all timestamps from UTC to EST for better readability
- **Username Logging**: Enhanced logs to show actual usernames instead of just user IDs
- **Verse Reaction Logging**: Added comprehensive reaction monitoring for verse commands
- **Playback State Frequency**: Reduced playback state logging from every minute to every 5 minutes

### Enhanced

- **🎯 User Experience**: More accurate audio position tracking and time displays
- **📱 Visual Feedback**: Better progress indicators and countdown systems for quizzes
- **🔍 Debug Information**: Improved logging with readable usernames and EST timestamps
- **⚡ Performance**: Optimized position tracking and reduced unnecessary logging

### Technical Improvements

- **🎵 Audio Engine**: Robust position tracking with proper validation and bounds checking
- **📊 State Management**: Enhanced state persistence with accurate position tracking
- **🛡️ Error Handling**: Better error handling for invalid positions and track completion
- **🔄 Real-time Updates**: Improved real-time position updates with proper time synchronization

## [3.3.0] - 2025-07-09

### Enhanced

#### 🎮 Quiz System Display Improvements

- **User-Friendly Results**: Quiz results now display Discord mentions (`<@user_id>`) in embeds for easy user identification
- **Readable Logs**: Quiz processing logs show actual usernames (e.g., "Golden", "The Caliph") instead of user IDs for better debugging
- **Black Box Explanations**: Quiz explanations now display in formatted black code boxes while keeping titles outside for better readability
- **Dual Display System**: Optimized display system - mentions in Discord embeds for tagging, usernames in logs for debugging

#### 🔧 Quiz Results Processing

- **Enhanced User Lookup**: Improved user fetching system for better username resolution in quiz results
- **Consistent Formatting**: Standardized quiz results format with proper Discord mention handling
- **Error Handling**: Better fallback handling when user lookup fails during quiz processing
- **Log Clarity**: Clear separation between user-facing display and developer debugging information

### Technical Improvements

- **📱 Embed Optimization**: Maintained Discord mention functionality in embeds for proper user notifications
- **🔍 Debug Enhancement**: Enhanced logging with readable usernames for easier troubleshooting
- **🎨 Visual Formatting**: Improved explanation display with proper code block formatting
- **⚡ Performance**: Optimized user lookup process during quiz results generation

## [3.1.0] - 2025-07-09

### Added

#### 🎮 Rich Presence Playback Time Display

- **Enhanced Status Display**: Rich presence now shows playback time alongside surah name
- **Format**: `{emoji} {surah} ・ {current_time} / {total_time}` (e.g., "👤 Al-Insan ・ 1:06:40 / 1:40:00")
- **Control Panel Consistency**: Playback time format matches control panel exactly (MM:SS or H:MM:SS)
- **Progress Tracking**: Users can see their progress through the Quran directly in Discord status

#### 🔧 Audio Manager Enhancements

- **Time Formatting**: Added `_format_time()` method for consistent time display across systems
- **Progress Calculation**: Enhanced `_get_playback_time_display()` with track-based progress calculation
- **Template Integration**: Updated rich presence template calls to include formatted playback time

### Enhanced

- **🎯 User Experience**: Rich presence provides more detailed information about listening progress
- **📊 Progress Visibility**: Clear indication of current position in Quran recitation
- **🎨 Visual Consistency**: Unified time formatting between rich presence and control panel
- **⚡ Real-time Updates**: Playback time updates dynamically as user progresses through surahs

### Technical Improvements

- **📱 Rich Presence Templates**: Updated listening template to include playback time with ・ separator
- **🔢 Time Calculation**: Intelligent track-based progress calculation when audio duration unavailable
- **🎵 Audio Integration**: Seamless integration between audio manager and rich presence systems
- **📊 Progress Scaling**: Smart scaling of 114 surahs to ~100 "minutes" for intuitive progress display

## [3.0.0] - 2025-07-08

### Major Release - Discord.py Update & System Fixes

#### 🔧 Critical Discord.py Update

- **Discord Voice Fix**: Updated discord.py from 2.3.2 to development version (2.6.0a5224+gb1be7dea) to resolve widespread voice connection error 4006 ("Session no longer valid")
- **Voice Connection Stability**: Fixed bot voice connection issues affecting all Discord bots mid-June 2025
- **Requirements Update**: Updated requirements.txt to use git repository version for latest voice fixes

#### 🎮 Rich Presence Enhancements

- **Method Fixes**: Replaced non-existent `stop_track()` with `clear_presence()` and `start_track()` with `update_presence_with_template()`
- **Template Improvements**: Fixed rich presence templates to avoid duplicate "Listening to" text (Discord adds this automatically)
- **Surah Emojis**: Added proper surah emojis matching control panel dropdown (e.g., 👤 for Al-Insan)
- **Async Updates**: Fixed async presence updates with proper event loop handling

#### 🎛️ Control Panel Improvements

- **Progress Bar Fix**: Enhanced `get_playback_status()` to provide track-based progress instead of time-based when audio duration unavailable
- **Status Display**: Fixed control panel showing meaningful progress information (Surah X/114)
- **Panel Updates**: Improved real-time control panel updates during playback

#### 📖 Daily Verses System Fixes

- **KeyError Fix**: Fixed `KeyError: 0` in `get_random_verse()` due to incorrect JSON data structure handling
- **Data Structure**: Fixed `load_verses()` to properly handle JSON structure with verses under "verses" key
- **Verse Loading**: Enhanced daily verses system to correctly load and display 10 verses

#### ⚡ Command System Overhaul

- **Missing Commands**: Fixed `/interval` command not loading due to Cog-based implementation
- **Command Conversion**: Converted IntervalCog class to direct `interval_slash_command` function matching other commands
- **All Commands Working**: Ensured all commands now functional: `/credits`, `/interval`, `/leaderboard`, `/question`, `/verse`

#### 🔇 Logging Improvements

- **Spam Reduction**: Added `silent` parameter to `save_playback_state()` to reduce logging frequency
- **Smart Logging**: Only log playback state saves every 60 seconds (12th save) instead of every 5 seconds
- **Log Cleanliness**: 92% reduction in log noise while maintaining data protection

#### 🛠️ State Management & Error Handling

- **Parameter Fixes**: Removed `total_duration` parameter from `save_playback_state()` calls in AudioManager
- **File Path Corrections**: Fixed RichPresenceManager initialization to use "data" directory instead of FFMPEG_PATH
- **Import Fixes**: Corrected import paths and method calls throughout the codebase

#### 🎵 Audio System Stability

- **Continuous Playback**: Maintained 24/7 audio playback stability through all fixes
- **State Persistence**: Enhanced playback state saving and restoration
- **Error Recovery**: Improved error handling for voice client disconnections and reconnections

### Technical Improvements

- **Error Handling**: Enhanced exception handling across all systems
- **Code Quality**: Improved code organization and method consistency
- **Documentation**: Updated inline documentation and error messages
- **Performance**: Optimized logging frequency and system responsiveness

---

## [Previous Versions]

_For older version history, see previous releases in the GitHub repository._

## [Unreleased]

### In Development

- 🔄 Additional admin moderation tools
- 🎵 Enhanced audio quality options
- 📊 Extended leaderboard features
- 🌍 Multi-language support improvements
