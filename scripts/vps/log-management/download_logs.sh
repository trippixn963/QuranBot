#!/bin/bash
echo "📥 Downloading QuranBot logs from VPS..."
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Download the latest log file
scp -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90:/opt/quranbot/logs/quranbot.log logs/quranbot_vps.log

echo "✅ Logs downloaded to logs/quranbot_vps.log"
echo "" 