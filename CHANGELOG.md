# Changelog

All notable changes to QuranBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- **Admin Answer Key System**: Added private DM system for admin users to receive correct answers
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

## [Unreleased]

## [2.3.2] - 2025-01-07

### Enhanced

- **✨ Credits Command Spacing**: Added visual separators between categories in /credits command
- **📖 Enhanced Readability**: Improved spacing between sections for better visual organization
- **🎨 Clean Design**: Maintains simple, clean design with better user experience
- **🔧 UI Polish**: Small patch focusing on visual improvements and readability

### Technical Improvements

- **📱 Visual Separators**: Added invisible spacer fields between embed categories
- **🎯 User Experience**: Enhanced command layout for better information consumption

## [2.3.1] - 2025-01-07

### Fixed

- **📖 Truncated Verses**: Fixed 27 truncated verses in daily verse database
- **✅ Complete Verse Display**: All verses now show complete Arabic text and translations
- **🔍 No More Truncation**: Eliminated '...' truncation in verse content
- **📊 Database Quality**: Enhanced verse display quality across all daily verses

### Verses Fixed

- **🕌 Al-Hadid 57:4**: Complete creation verse
- **💡 An-Nur 24:35**: Complete Light verse
- **⏰ Al-Asr 103:1-3**: Complete time surah
- **🏆 An-Nasr 110:1-3**: Complete victory surah
- **🌅 Al-Falaq 113:1-5**: Complete dawn surah
- **👥 An-Nas 114:1-6**: Complete mankind surah
- **📚 21 Additional Verses**: With complete Arabic & translations

### Enhanced

- **📈 Verse Quality**: Better user experience with full verse content
- **🎯 Consistent Formatting**: Uniform formatting across all verses
- **🔄 Database Integrity**: Maintained original verse database structure

## [2.3.0] - 2025-01-07

### Added

- **⚡ Command Registration**: Fixed /verse command registration and initialization timing
- **🕐 EST Timezone Support**: Added EST timezone support for all verse timers
- **👤 Admin Profile Integration**: Enhanced daily verse embeds with admin profile picture in footer
- **📱 Message ID Tracking**: Improved /verse command response with message ID tracking
- **🛡️ Enhanced Error Handling**: Better error handling and user feedback

### Technical Improvements

- **🔄 Module Import Timing**: Resolved module import timing issues in daily verses system
- **⚡ Dynamic Instance Fetching**: Implemented dynamic daily_verses_manager instance fetching
- **📋 Command Initialization**: Streamlined command initialization order
- **🧹 Production Readiness**: Cleaned up debug code for production readiness

### Enhanced

- **🎨 Footer Styling**: Consistent footer styling with admin profile picture
- **📊 Status Information**: Replaced queue status with more useful message ID information
- **🕐 Timezone Display**: Better timezone display (EST instead of UTC)
- **📱 Embed Formatting**: Improved embed formatting and visual consistency

### Fixed

- **🔧 Daily Verses Configuration**: Fixed 'Daily Verses Not Configured' error despite proper initialization
- **⏰ Timing Issues**: Resolved timing issues between command registration and system setup
- **👤 Profile Picture Fetching**: Fixed profile picture fetching in embed footers
- **🛡️ Avatar Loading**: Improved error handling for avatar loading

## [2.2.1] - 2025-01-18

### Fixed

- **🎛️ Control Panel Cleanup**: Fixed control panel stuck issue with robust cleanup system at bot startup
- **🔄 Existing Users Detection**: Fixed bot not tracking listening time for users already in voice channel when bot starts
- **👥 Role Assignment Bug**: Fixed role being assigned when users joined ANY voice channel instead of only Quran channel
- **📊 Time Tracking Persistence**: Fixed listening time not continuing across bot restarts
- **🐛 Syntax Error Resolution**: Fixed misplaced break statement causing SyntaxError in voice state handler
- **📝 Import Path Fix**: Fixed control panel creation error due to incorrect import path
- **📋 README Formatting**: Fixed messy version history formatting with clean, professional structure

### Enhanced

- **🧹 Panel Cleanup System**: Added comprehensive control panel cleanup with rate limiting protection
- **🔍 Existing Users Scanner**: Implemented system to detect and start tracking users already in voice channel
- **🎯 Channel-Specific Roles**: Enhanced role management to only work for designated Quran voice channel
- **📊 Persistent Time Tracking**: Time tracking now seamlessly continues across bot restarts
- **🛡️ Error Handling**: Improved exception handling for role operations and panel cleanup
- **📝 Documentation**: Clean, organized README with professional formatting and correct repository references

### Technical Improvements

- **🔄 Bot Startup Flow**: Enhanced startup sequence with existing user detection and panel cleanup
- **🎭 Role Management**: Added proper channel ID validation before role assignment/removal
- **📱 Control Panel Registry**: Global panel tracking to prevent stuck panels
- **🔒 Thread Safety**: Improved cleanup operations with list copying for thread safety
- **📊 Logging Enhancement**: Better logging for all cleanup and tracking operations

## [2.2.0] - 2025-01-18

### Added

- **🛡️ Bulletproof Data Protection**: Implemented 5-layer protection system for all data files
- **📦 Automated ZIP Backup System**: EST-scheduled hourly backups with intuitive date/time naming (e.g., "7/6 - 10PM.zip")
- **🔍 Missing Surah Detection**: Automatic detection and logging of incomplete reciter collections with range formatting
- **🎯 Enhanced Audio Management**: Intelligent mapping of surah numbers to available files with comprehensive analysis
- **🗂️ Perfect Tree Logging**: Complete backup logging with full visibility into all operations
- **🔄 Smart Looping**: Default looping enabled for continuous playback experience
- **📊 Audio File Indexing**: Intelligent surah-to-file mapping with missing file detection
- **🚨 Emergency Backup System**: Multiple fallback mechanisms for critical data protection
- **🔄 Atomic File Operations**: Corruption-proof saves with automatic recovery mechanisms
- **⏰ EST Timezone Support**: All backup operations use Eastern Standard Time for consistent scheduling

### Enhanced

- **🎵 Audio Playback**: Fixed surah indexing issues where incomplete reciter collections caused wrong surah numbers
- **🔄 Looping Behavior**: Changed DEFAULT_LOOP to true for seamless continuous playback
- **📝 Backup Logging**: Enhanced all backup operations with comprehensive tree-style logging
- **🕰️ Backup Scheduling**: Modified to run on EST hour marks (1:00, 2:00, etc.) instead of startup intervals
- **💾 Data Integrity**: Improved all file operations with atomic saves and integrity verification
- **🔍 Error Detection**: Added comprehensive missing surah detection with user-friendly range formatting
- **📊 Status Reporting**: Enhanced backup status with current EST time and next backup window information

### Fixed

- **🎵 Surah Indexing**: Fixed issue where Surah 114 showed as index 71 due to incomplete reciter collections
- **🔄 Playlist Looping**: Fixed bot not looping back to Surah 1 after finishing Surah 114
- **📦 Backup Timing**: Fixed backup scheduling to use clock hour marks instead of startup-based intervals
- **🗂️ File Compression**: Replaced individual file copying with efficient ZIP compression
- **⚠️ Missing File Handling**: Added proper detection and explanation of missing surahs in collections

### Repository Improvements

- **📋 Code of Conduct**: Added comprehensive Code of Conduct with Islamic values integration
- **🔄 GitHub Actions**: Implemented CI/CD pipeline with automated testing, linting, and releases
- **🏷️ Release Automation**: Added automated version management and GitHub release creation
- **📝 Issue Templates**: Enhanced GitHub issue templates with better no-support policy communication
- **📊 Documentation**: Updated README with latest features and current version information
- **🔒 Security Scanning**: Added automated security scanning with Bandit integration

### Technical Improvements

- **🧪 Testing Integration**: Enhanced CI/CD with multi-Python version testing (3.8-3.11)
- **🎨 Code Quality**: Integrated Black formatting, isort, and flake8 linting in CI pipeline
- **📦 Release Management**: Automated version bumping with centralized version management
- **🔍 Syntax Validation**: Added comprehensive Python syntax validation in CI
- **📊 Security Reports**: Automated security scanning with artifact generation
- **🚀 Deployment Safety**: Enhanced deployment pipeline with comprehensive testing requirements

### Configuration

- **DEFAULT_LOOP**: Changed from false to true for continuous playback
- **Backup Schedule**: Modified to run on EST hour marks for predictable timing
- **ZIP Compression**: Enabled ZIP_DEFLATED compression for efficient backup storage
- **EST Timezone**: Added timezone(timedelta(hours=-5)) for consistent time handling

## [2.1.0] - 2025-01-17

### Added

- **🎯 Centralized Version Management**: Single source of truth version system with src/version.py
- **🔄 Automated Version Updates**: tools/update_version.py utility for consistent version management
- **👤 Centralized Author Management**: Standardized author format "John (Discord: Trippixn)"
- **🗂️ Perfect Tree Logging**: Enhanced logging system with comprehensive backup visibility
- **📊 Backup Status Reporting**: Real-time backup status with file counts and next backup timing

### Enhanced

- **🔢 Version Consistency**: All files now import from centralized version module
- **📝 Author Standardization**: Consistent author information across all project files
- **🛠️ Development Tools**: Enhanced update_version.py with automatic file detection and verification
- **📊 Logging Improvements**: Better backup logging with detailed file information

## [1.5.0] - 2025-07-05

### Added

- **Environment Default Settings**: Added configurable default settings for reciter, shuffle, and loop modes
- **Startup Reset Behavior**: Bot now resets to default reciter (Saad Al Ghamdi) on every restart
- **Toggle State Persistence**: Loop and shuffle modes reset to environment defaults on bot restart
- **Enhanced Control Panel**: Added emojis to buttons and dropdown menus for better user experience
- **Improved Dropdown Design**: Reciter dropdown now shows English names as labels with Arabic names as descriptions

### Configuration

- **New Environment Variables**:
  - `DEFAULT_RECITER=Saad Al Ghamdi` - Sets default reciter on bot startup
  - `DEFAULT_SHUFFLE=false` - Sets default shuffle mode state
  - `DEFAULT_LOOP=false` - Sets default loop mode state

### Enhanced

- **State Manager**: Updated to use environment defaults for fresh state initialization
- **Audio Manager**: Modified to accept and use environment default values
- **Control Panel Design**:
  - Added emojis to all buttons (⬅️ ➡️ ⏮️ ⏭️ 🔁 🔀)
  - Enhanced dropdown options with appropriate emojis
  - Improved reciter dropdown format with English/Arabic separation
- **Startup Behavior**: Consistent default state regardless of previous session

### Technical Improvements

- **Environment Integration**: Proper loading and parsing of boolean environment variables
- **Default Value Cascading**: Environment defaults flow through StateManager → AudioManager → Control Panel
- **State Synchronization**: Control panel toggle states sync with audio manager on connection

## [1.4.0] - 2025-07-05

### Added

- **Interactive Control Panel**: Complete Discord embed-based control panel with real-time status updates
- **Audio Manager System**: Centralized audio playback management with comprehensive state tracking
- **Rich Presence Integration**: Dynamic Discord Rich Presence showing current Surah with Arabic names and playback timer
- **User Attribution System**: Track and display which user enabled Loop/Shuffle modes with Discord mentions
- **Progress Bar Display**: Visual playback progress bars in control panel with 20-character precision
- **Surah Selection Dropdown**: Paginated dropdown menu with emoji indicators and Arabic descriptions
- **Reciter Selection**: Dynamic reciter switching with automatic audio file discovery
- **Playback Controls**: Previous/Next track buttons with seamless audio transitions
- **Loop & Shuffle Modes**: Toggle controls with user attribution and real-time status updates
- **Search Functionality**: Quick Surah search with fuzzy matching capabilities
- **Error Recovery**: Robust error handling with automatic control panel recreation
- **Real-time Updates**: Live status updates every 5 seconds with progress tracking

### Enhanced

- **Rich Presence Display**: Simplified to show only Surah name (emoji + Arabic) with timer in single line
- **Control Panel Layout**: Clean, organized embed with essential information only
- **Surah Dropdown Format**: Shows "1. Al-Fatiha" format with emoji on left, no duplication
- **Audio State Management**: Comprehensive playback state tracking and synchronization
- **User Experience**: Removed redundant status displays, focused on essential information
- **Error Handling**: Graceful handling of deleted control panel messages with automatic recreation

### Technical Improvements

- **AudioManager Class**: Complete audio playback state management system
- **Control Panel View**: Discord UI components with button interactions and dropdown menus
- **Rich Presence Manager**: FFmpeg integration for audio duration detection and progress tracking
- **Surah Database**: JSON-based Surah information with emojis, Arabic names, and metadata
- **Automatic Discovery**: Dynamic reciter detection from audio folder structure
- **Progress Synchronization**: Coordinated progress updates between Rich Presence and control panel

### User Interface

- **Control Panel Features**:
  - Now Playing display with Surah emoji and name
  - Visual progress bar with current/total time
  - Current reciter information
  - Loop status with user attribution (e.g., "Loop: 🔁 ON - <@user_id>")
  - Shuffle status with user attribution
  - Last activity tracking
- **Rich Presence Features**:
  - Compact display: "🕌 الفاتحة • 02:34 / 05:67"
  - Dynamic states: Starting, Playing, Paused
  - Clean, minimalist design

### Fixed

- **Control Panel Persistence**: Proper handling of message deletion and recreation
- **Progress Bar Accuracy**: Correct timing calculations and display formatting
- **Button Interactions**: All control buttons now properly connected to audio system
- **State Synchronization**: Real-time updates between all components
- **Error Recovery**: Graceful handling of Discord API errors and reconnection

## [1.2.0] - 2025-07-05

### Added

- **Professional project structure**: Reorganized entire project with tools/, docs/, config/, scripts/ directories
- **Enhanced development tools**: Comprehensive testing suite, code formatting, and deployment safety tools
- **Complete error handling**: Added traceback support throughout with enhanced tree_log functions
- **Development environment setup**: Automated virtual environment, ffmpeg installation, and audio file management
- **Production safety framework**: Bulletproof deployment system preventing broken code from reaching VPS

### Changed

- **Project organization**: Moved development tools to tools/ directory for better structure
- **Configuration management**: Centralized config files in config/ directory
- **Documentation structure**: Organized all documentation in docs/ directory
- **Import paths**: Updated all tools to work with new directory structure

### Technical Improvements

- **Automatic path resolution**: All tools work correctly from any directory
- **Comprehensive testing**: 41 tests with 100% success rate validation
- **Code consistency**: Black formatting with 88-character lines and box-style headers
- **Memory management**: Updated memory system with project structure standards

### Added

- **Automated instance detection**: Fully automated prevention of multiple bot instances running simultaneously
- **Automatic instance termination**: Seamlessly detects and stops existing instances without user interaction
- **Bot manager utility**: Command-line tool for easy bot management (start, stop, restart, status)
- **Process monitoring**: Detailed process information including uptime, memory usage, and command details
- **Graceful shutdown handling**: Proper termination with fallback to force kill if needed
- **Enhanced error handling**: Robust process management with comprehensive error logging
- **Structured Discord logging**: Custom logging handler that formats Discord.py logs in beautiful tree style
- **Intelligent log filtering**: Automatically categorizes and formats Discord logs with appropriate icons and context
- **Timestamped logging**: All terminal logs now include timestamps in EST timezone with MM/DD HH:MM AM/PM format
- **Professional log formatting**: Enhanced readability with consistent timestamp prefixes on all log entries
- **Comprehensive file logging**: Automatic logging to organized date-based folder structure
- **Multi-format log files**: Simultaneous logging to .log (text), .json (structured), and -errors.log (errors only) files
- **Date-organized structure**: Logs saved to `logs/YYYY-MM-DD/` folders for easy organization and archival
- **Error isolation**: Separate error log file captures only WARNING, ERROR, CRITICAL, and EXCEPTION level messages

### Security

- **Process isolation**: Prevents conflicts and unexpected behavior from multiple instances
- **Safe termination**: Graceful shutdown with timeout protection to prevent hanging processes

### Dependencies

- **psutil**: Added for advanced process monitoring and management capabilities

## [1.1.0] - 2025-07-05

### Added

- **Extremely structured project organization**: Reorganized entire codebase into proper src/ directory structure
- **Modular package architecture**: Created separate packages for bot/, utils/, and config/
- **Proper Python packaging**: Added **init**.py files for all packages with proper imports
- **Clean entry point**: Created main.py as the single entry point with proper import handling
- **Enhanced version tracking**: Added version information display in structured logging

### Changed

- **File organization**: Moved bot.py to src/bot/main.py for better organization
- **Logging module**: Moved tree_log.py to src/utils/tree_log.py
- **Import structure**: Updated all imports to use proper package structure
- **Entry point**: Changed from bot.py to main.py for cleaner project structure

### Technical Structure

```
├── main.py                    # Main entry point
├── requirements.txt           # Dependencies
├── CHANGELOG.md              # This changelog
├── update_version.py         # Version management tool
├── .env                      # Environment configuration
├── audio/                    # Audio files directory
└── src/                      # Source code package
    ├── __init__.py           # Main package init
    ├── bot/                  # Bot functionality package
    │   ├── __init__.py       # Bot package init
    │   └── main.py           # Main bot implementation
    ├── utils/                # Utilities package
    │   ├── __init__.py       # Utils package init
    │   └── tree_log.py       # Tree-style logging functions
    └── config/               # Configuration package
        └── __init__.py       # Config package init (future use)
```

## [1.0.0] - 2025-07-05

### Added

- **Complete bot rewrite**: Started fresh from ground zero with minimal, clean codebase
- **Tree-style logging system**: Implemented structured logging with symbols (├─, └─) for better readability
- **Modular architecture**: Separated logging functionality into `tree_log.py` module
- **Box-style comments**: Added consistent formatting with `# =============================================================================` headers
- **Environment variable integration**: Proper configuration using .env file with exact ID names
- **Audio playback system**: Basic Discord voice channel connection and MP3 playback
- **Auto-reconnection**: Bot automatically attempts to reconnect if disconnected from voice
- **Progress tracking**: Visual progress indicators for audio playback (current/total format)
- **Error handling**: Comprehensive error logging with tree-style format

### Technical Details

- **Dependencies**: Minimal setup with only discord.py, PyNaCl, and python-dotenv
- **Configuration**: Uses GUILD_ID and TARGET_CHANNEL_ID from .env file
- **Audio source**: Plays from 'audio/Saad Al Ghamdi' folder by default
- **FFmpeg integration**: Configurable FFmpeg path for audio processing

### Files Structure

```
├── bot.py              # Main Discord bot functionality
├── tree_log.py         # Tree-style logging functions
├── requirements.txt    # Minimal dependencies
├── .env               # Environment configuration
├── audio/             # Audio files directory
└── CHANGELOG.md       # This changelog file
```

### Removed

- **Previous complex codebase**: Deleted entire previous implementation that had multiple issues
- **Instance detection**: Removed problematic instance management that was causing startup loops
- **Complex logging**: Replaced with simpler, more readable tree-style logging
- **Excessive dependencies**: Reduced from 20+ packages to just 3 core dependencies

### Fixed

- **Voice connection stability**: Resolved WebSocket 4006 errors with clean reconnection logic
- **FFmpeg path detection**: Proper handling of FFmpeg executable path configuration
- **Startup process**: Eliminated hanging during bot initialization
- **Memory management**: Cleaner resource handling without complex monitoring systems
