@echo off
echo 📥 Downloading QuranBot logs from VPS...
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Get current date in YYYY-MM-DD format
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "datestamp=%YYYY%-%MM%-%DD%"

REM Download today's log file
scp -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90:/opt/quranbot/logs/%datestamp%.log logs/quranbot_vps_%datestamp%.log

echo ✅ Logs downloaded to logs/quranbot_vps_%datestamp%.log
echo.
pause 