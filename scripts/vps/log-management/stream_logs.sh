#!/bin/bash
echo "🔄 Streaming QuranBot logs from VPS..."
echo "Press Ctrl+C to stop streaming"
echo ""

# Get current date in YYYY-MM-DD format
datestamp=$(date +%Y-%m-%d)

# Stream logs in real-time
ssh -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90 "tail -f /opt/quranbot/logs/$datestamp.log" 