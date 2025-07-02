Write-Host "🔄 Streaming QuranBot logs from VPS..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop streaming" -ForegroundColor Yellow
Write-Host ""

# Stream logs in real-time
ssh -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90 "tail -f /opt/quranbot/logs/quranbot.log" 