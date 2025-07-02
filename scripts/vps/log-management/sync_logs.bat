@echo off
echo 🔄 Auto-syncing QuranBot logs from VPS...
echo This will sync logs every 30 seconds
echo Press Ctrl+C to stop
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:loop
REM Download the latest log file
scp -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90:/opt/quranbot/logs/quranbot.log logs/quranbot_vps.log >nul 2>&1

echo [%date% %time%] ✅ Logs synced
timeout /t 30 /nobreak >nul
goto loop 