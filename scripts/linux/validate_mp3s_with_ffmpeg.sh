#!/bin/bash

# Validate all MP3 files in the audio/ directory using FFmpeg
# Logs any corrupt or unreadable files to bad_mp3s.txt

AUDIO_DIR="../../audio"
LOG_FILE="bad_mp3s.txt"
BAD_COUNT=0
CHECKED_COUNT=0

if [ ! -d "$AUDIO_DIR" ]; then
    echo "Audio directory not found: $AUDIO_DIR"
    exit 1
fi

if [ -f "$LOG_FILE" ]; then
    rm "$LOG_FILE"
fi

echo "Checking all MP3 files in $AUDIO_DIR..."

for file in "$AUDIO_DIR"/*.mp3; do
    if [ -f "$file" ]; then
        ((CHECKED_COUNT++))
        if ffmpeg -v error -i "$file" -f null - 2>&1; then
            echo "OK: $file"
        else
            ((BAD_COUNT++))
            echo "Corrupt: $file" >> "$LOG_FILE"
            ffmpeg -v error -i "$file" -f null - 2>&1 >> "$LOG_FILE"
            echo "" >> "$LOG_FILE"
            echo "Corrupt: $file"
        fi
    fi
done

echo "Checked $CHECKED_COUNT files. Bad files: $BAD_COUNT"

if [ $BAD_COUNT -gt 0 ]; then
    echo "See $LOG_FILE for details."
fi

read -p "Press Enter to exit" 