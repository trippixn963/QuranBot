#!/bin/bash

# QuranBot v1.4.0 Release Creation Script
# Usage: ./create_release.sh YOUR_GITHUB_TOKEN

if [ -z "$1" ]; then
    echo "Usage: $0 <GITHUB_TOKEN>"
    echo "Get your token from: https://github.com/settings/tokens"
    exit 1
fi

GITHUB_TOKEN="$1"

echo "Creating QuranBot v1.4.0 release..."

curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/JohnHamwi/QuranBot/releases \
  -d '{
    "tag_name": "v1.4.0",
    "target_commitish": "development",
    "name": "🎵 QuranBot v1.4.0: Interactive Control Panel & Rich Presence Integration",
    "body": "## 🎵 QuranBot v1.4.0 - Major Interactive Features Release\n\n### ✨ Major Features Added\n\n- **Interactive Discord Control Panel**: Complete embed-based control panel with real-time status updates\n- **Centralized AudioManager System**: Comprehensive audio playback state management\n- **Dynamic Rich Presence**: Shows current Surah with Arabic names and playback timer\n- **User Attribution System**: Track and display which user enabled Loop/Shuffle modes\n- **Visual Progress Bars**: 20-character precision progress bars in control panel\n- **Paginated Surah Selection**: Dropdown menu with emoji indicators and Arabic descriptions\n- **Dynamic Reciter Switching**: Automatic audio file discovery and seamless switching\n- **Playback Controls**: Previous/Next track buttons with smooth transitions\n- **Search Functionality**: Quick Surah search with fuzzy matching capabilities\n- **Robust Error Recovery**: Automatic control panel recreation and error handling\n\n### 🎨 UI/UX Improvements\n\n- **Rich Presence**: Simplified to show `🕌 الفاتحة • 02:34 / 05:67` format\n- **Control Panel**: Clean, organized embed with essential information only\n- **Surah Dropdown**: Shows `1. Al-Fatiha` format with emoji on left\n- **User Experience**: Removed redundant status displays, focused on essential information\n- **Real-time Updates**: Live status updates every 5 seconds with progress tracking\n\n### 🔧 Technical Enhancements\n\n- **AudioManager Class**: Complete audio playback state management system\n- **Control Panel View**: Discord UI components with button interactions and dropdown menus\n- **Rich Presence Manager**: FFmpeg integration for audio duration detection and progress tracking\n- **Surah Database**: JSON-based Surah information with emojis, Arabic names, and metadata\n- **Automatic Discovery**: Dynamic reciter detection from audio folder structure\n- **Progress Synchronization**: Coordinated updates between Rich Presence and control panel\n\n### 🐛 Bug Fixes\n\n- **Control Panel Persistence**: Proper handling of message deletion and recreation\n- **Progress Bar Accuracy**: Correct timing calculations and display formatting\n- **Button Interactions**: All control buttons properly connected to audio system\n- **State Synchronization**: Real-time updates between all components\n- **Error Recovery**: Graceful handling of Discord API errors and reconnection\n\n### 📋 Control Panel Features\n\n- Now Playing display with Surah emoji and name\n- Visual progress bar with current/total time\n- Current reciter information\n- Loop status with user attribution (e.g., \"Loop: 🔁 ON - <@user_id>\")\n- Shuffle status with user attribution\n- Last activity tracking\n\n### 🎵 Rich Presence Features\n\n- Compact display: \"🕌 الفاتحة • 02:34 / 05:67\"\n- Dynamic states: Starting, Playing, Paused\n- Clean, minimalist design\n\n---\n\n**This release represents a major step forward in QuranBot functionality with a complete interactive control system and enhanced user experience.**",
    "draft": false,
    "prerelease": false,
    "generate_release_notes": false
  }'

echo ""
echo "Release creation completed!"
echo "Visit: https://github.com/JohnHamwi/QuranBot/releases"
