# =============================================================================
# QuranBot - Changelog (Project Now Archived)
# =============================================================================
# Complete changelog of all releases and updates for QuranBot.
# Project is now archived with no future development planned.
# =============================================================================

## [4.0.1] - Final Release (Archived Project)

> **⚠️ This is the final release. Project is now ARCHIVED with no future development.**

### 🎯 Final Project Cleanup

#### **Codebase Optimization**
- **Removed Legacy Code**: Eliminated 5 duplicate/unused files (70KB saved)
- **Cleaned Documentation**: Removed 5 redundant docs (64KB saved) 
- **Standardized Style**: Applied consistent box comments to all 100+ Python files
- **Updated Dependencies**: Fixed version mismatches and outdated packages
- **Streamlined Structure**: Removed performance test data and unused scripts

#### **Feature Enhancements**
- **Quiz Auto-Deletion**: Questions and results now auto-delete after 2 minutes
- **Modern Architecture**: Complete modernization with DI container and microservices
- **Dependency Management**: Unified pyproject.toml and requirements.txt

#### **Final Documentation**
- **Archived Status**: Updated all documentation to reflect archived status
- **No Support Policy**: Clear warnings about zero ongoing support
- **Streamlined Docs**: Kept only essential documentation (10 files)

### 🚫 Project Archived
- ❌ **No further development** will occur
- ❌ **No support** will be provided
- ❌ **No issues** will be addressed
- ❌ **No pull requests** will be accepted
- ❌ **No community** will be maintained

---

## [3.5.1] - Enhanced Monitoring and UI

### 🎯 **Comprehensive Bot Enhancements**

#### **Advanced Monitoring Systems**
- **Discord API Monitor**: Real-time API health tracking with response times and rate limits
- **Audio Playback Monitor**: Failure detection with automatic Discord alerts
- **Control Panel Monitor**: Health tracking with smart update intervals
- **System Resource Monitor**: CPU, memory, and disk usage tracking

#### **Professional Web Dashboard**
- **Real-time Monitoring**: Live bot status, system resources, and health metrics
- **Interactive Controls**: Direct bot and audio control from web interface
- **Enhanced UI/UX**: Loading states, notifications, charts, and activity feeds
- **Log Viewer**: Advanced filtering and search capabilities

#### **Integrated Log Management**
- **Automated Log Sync**: Real-time VPS log synchronization
- **Background Daemon**: Standalone log sync service with systemd support
- **Health Monitoring**: Log sync status tracking and alerts
- **Cross-platform Support**: macOS and Linux service installation

#### **Audio & Voice Features**
- **Enhanced Role Management**: Improved "Listening to Quran" role assignment with retry logic
- **Voice Connection Fixes**: Better detection and state management
- **Audio Status Display**: Proper track names and connection indicators
- **Timezone Synchronization**: Aligned monitoring with bot's EST timezone

#### **Quiz System Improvements**
- **Explanation Integration**: Added missing explanation fields
- **Interval Persistence**: Robust quiz timing across bot restarts
- **Enhanced Formatting**: Better visual presentation and user experience

### 🔧 Bug Fixes

#### **Critical Import and Module Issues**
- **Fixed /interval Command**: Resolved `ImportError: cannot import name 'daily_verses_manager'` by correcting import from `daily_verses_manager` (plural) to `daily_verse_manager` (singular)
- **Fixed Timezone Import**: Corrected timezone import from `datetime.now(timezone.utc).isoformat()` to `datetime.now(pytz.UTC).isoformat()` in daily verses module
- **Enhanced Module Loading**: Improved error handling and module discovery for better reliability

#### **Role Management System Overhaul**
- **Enhanced Role Assignment**: Added retry logic with 3 attempts and exponential backoff (1s, 2s, 4s delays)
- **Verification System**: Actually checks if role was assigned/removed after API calls to prevent phantom roles
- **Member Refresh**: Refreshes member data before role operations to ensure accuracy
- **Rate Limit Handling**: Intelligent waiting and retry when Discord rate limits occur
- **Enhanced Error Context**: Detailed logging with user IDs, role IDs, and specific error messages
- **Fixed "Listening to Quran" Role Bug**: Users no longer keep role after leaving voice channel

#### **Bot Data Display Issues**
- **Audio Status Enhancement**: Fixed audio controls showing "None" for current track and "Not connected" for voice channel
- **Surah Name Integration**: Connected with bot's surahs.json file for proper transliterated names (e.g., "An-Nisa" instead of "Surah 4")
- **Voice Connection Detection**: Intelligent analysis of recent logs for accurate voice connection indicators
- **Timezone Synchronization**: Fixed monitoring timezone mismatch by aligning with bot's EST timezone
- **Real-time Data Updates**: Improved synchronization between bot services and monitoring data

#### **Quiz System Improvements**
- **Explanation Box Fix**: Added missing explanation field to automated quiz scheduler

---

## [3.5.0] - Previous Release

### Features
- Initial monitoring system implementation
- Basic audio playback system
- Quiz management functionality
- State persistence system
- Deployment configuration examples

### Bug Fixes
- Various stability improvements
- Audio playback optimizations
- Command handling enhancements

---

**الحمد لله رب العالمين**

*This project has served its purpose and is now preserved for posterity.* 