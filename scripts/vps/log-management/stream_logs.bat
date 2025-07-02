@echo off
echo 🔄 Streaming QuranBot logs from VPS...
echo Press Ctrl+C to stop streaming
echo.

REM Get current date in YYYY-MM-DD format
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "datestamp=%YYYY%-%MM%-%DD%"

REM Stream logs in real-time
ssh -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90 "tail -f /opt/quranbot/logs/%datestamp%.log" 