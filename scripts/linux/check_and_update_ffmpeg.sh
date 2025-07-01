#!/bin/bash

# Check and update FFmpeg for Linux
# Usage: Run this script in bash

echo "Checking for FFmpeg..."

# Check if ffmpeg is installed
if command -v ffmpeg &> /dev/null; then
    version=$(ffmpeg -version | head -n 1)
    echo "FFmpeg found: $(which ffmpeg)"
    echo "Version: $version"
    read -p "Do you want to update FFmpeg to the latest version? (y/n): " update
    if [[ $update != "y" ]]; then
        echo "No update performed. Exiting."
        exit 0
    fi
fi

# Update FFmpeg using package manager
echo "Updating FFmpeg..."

# Detect package manager and update
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y ffmpeg
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y ffmpeg
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y ffmpeg
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S ffmpeg
elif command -v zypper &> /dev/null; then
    # openSUSE
    sudo zypper install ffmpeg
else
    echo "No supported package manager found. Please install FFmpeg manually."
    exit 1
fi

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg updated successfully!"
    ffmpeg -version | head -n 1
else
    echo "Failed to install FFmpeg."
    exit 1
fi

read -p "Press Enter to exit" 