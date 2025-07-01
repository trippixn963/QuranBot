#!/bin/bash

# Check and update FFmpeg for macOS
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

# Update FFmpeg using Homebrew
echo "Updating FFmpeg..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install/update FFmpeg
brew update
brew install ffmpeg

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg updated successfully!"
    ffmpeg -version | head -n 1
else
    echo "Failed to install FFmpeg."
    exit 1
fi

read -p "Press Enter to exit" 