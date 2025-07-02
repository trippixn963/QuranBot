@echo off
title QuranBot Enhanced VPS Manager v2.0
color 0B
setlocal enabledelayedexpansion

:: Configuration
set "VPS_HOST=159.89.90.90"
set "VPS_USER=root"
set "SSH_KEY=C:/Users/hanna/.ssh/id_rsa"
set "BOT_SERVICE=quranbot"
set "BOT_PATH=/opt/quranbot"
set "LOG_PATH=/opt/quranbot/logs"

:: Create necessary directories
if not exist "logs\vps" mkdir "logs\vps"
if not exist "backups\vps" mkdir "backups\vps"

:: Initialize session log
set "SESSION_LOG=logs\vps\session_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%.log"
echo [%date% %time%] VPS Manager session started > "%SESSION_LOG%"

:main_menu
cls
echo.
echo =========================================================
echo           QuranBot Enhanced VPS Manager v2.0
echo =========================================================
echo.
echo 🚀 BOT CONTROL:
echo   1. ▶️  Start Bot
echo   2. ⏹️  Stop Bot  
echo   3. 🔄 Restart Bot
echo   4. 📊 Bot Status
echo   5. ⬆️  Update Bot
echo   6. 🔧 Advanced Status
echo.
echo 📋 LOG MANAGEMENT:
echo   7. 🔄 Live Stream Logs
echo   8. 📥 Download Today's Logs
echo   9. 📊 Log Analytics
echo   10. 🧹 Cleanup Old Logs
echo.
echo 💾 BACKUP ^& RESTORE:
echo   11. 💾 Create Backup
echo   12. 📦 List Backups
echo   13. 📥 Download Backup
echo.
echo 📊 MONITORING:
echo   14. 🖥️  System Info
echo   15. 📈 Performance Monitor
echo   16. 🔍 Health Check
echo.
echo 🛠️  UTILITIES:
echo   17. 🔌 SSH Terminal
echo   18. 💀 Emergency Stop
echo   19. 🐍 Python Console
echo   20. ⚙️  Settings
echo.
echo   21. ❌ Exit
echo.
echo =========================================================
echo VPS: %VPS_HOST% ^| Service: %BOT_SERVICE% ^| Session: %time:~0,8%
echo.

set /p "choice=Enter your choice (1-21): "

if "%choice%"=="1" goto start_bot
if "%choice%"=="2" goto stop_bot
if "%choice%"=="3" goto restart_bot
if "%choice%"=="4" goto bot_status
if "%choice%"=="5" goto update_bot
if "%choice%"=="6" goto advanced_status
if "%choice%"=="7" goto stream_logs
if "%choice%"=="8" goto download_logs
if "%choice%"=="9" goto log_analytics
if "%choice%"=="10" goto cleanup_logs
if "%choice%"=="11" goto create_backup
if "%choice%"=="12" goto list_backups
if "%choice%"=="13" goto download_backup
if "%choice%"=="14" goto system_info
if "%choice%"=="15" goto performance_monitor
if "%choice%"=="16" goto health_check
if "%choice%"=="17" goto ssh_terminal
if "%choice%"=="18" goto emergency_stop
if "%choice%"=="19" goto python_console
if "%choice%"=="20" goto settings
if "%choice%"=="21" goto exit_manager

echo Invalid choice! Please try again.
timeout /t 2 >nul
goto main_menu

:start_bot
cls
echo 🚀 Starting QuranBot...
echo.
echo [%date% %time%] Starting bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl start %BOT_SERVICE% && echo 'Bot started successfully' && systemctl status %BOT_SERVICE% --no-pager -l"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Bot started successfully!
) else (
    echo.
    echo ❌ Failed to start bot. Check logs for details.
)
echo.
pause
goto main_menu

:stop_bot
cls
echo ⏹️  Stopping QuranBot...
echo.
echo [%date% %time%] Stopping bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl stop %BOT_SERVICE% && echo 'Bot stopped successfully'"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Bot stopped successfully!
) else (
    echo.
    echo ❌ Failed to stop bot.
)
echo.
pause
goto main_menu

:restart_bot
cls
echo 🔄 Restarting QuranBot...
echo.
echo [%date% %time%] Restarting bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl restart %BOT_SERVICE% && echo 'Bot restarted successfully' && sleep 3 && systemctl status %BOT_SERVICE% --no-pager -l"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Bot restarted successfully!
) else (
    echo.
    echo ❌ Failed to restart bot.
)
echo.
pause
goto main_menu

:bot_status
cls
echo 📊 QuranBot Status
echo.
echo [%date% %time%] Checking bot status >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Service Status ===' && systemctl status %BOT_SERVICE% --no-pager -l && echo '' && echo '=== Process Info ===' && ps aux | grep -E '(python|quran)' | grep -v grep && echo '' && echo '=== Recent Logs ===' && tail -10 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null || echo 'No logs found for today'"
echo.
pause
goto main_menu

:advanced_status
cls
echo 🔧 Advanced Bot Status
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Detailed Service Info ===' && systemctl show %BOT_SERVICE% --no-pager && echo '' && echo '=== Memory Usage ===' && ps -p $(pgrep -f %BOT_SERVICE%) -o pid,ppid,%%cpu,%%mem,vsz,rss,tty,stat,start,time,command 2>/dev/null || echo 'Service not running' && echo '' && echo '=== Network Connections ===' && netstat -tulpn | grep python || echo 'No Python network connections' && echo '' && echo '=== Disk Usage ===' && df -h %BOT_PATH% && echo '' && echo '=== System Load ===' && uptime && echo '' && echo '=== Memory Info ===' && free -h"
echo.
pause
goto main_menu

:stream_logs
cls
echo 🔄 Live Streaming Logs...
echo Press Ctrl+C to stop streaming
echo.
echo [%date% %time%] Starting log stream >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "tail -f %LOG_PATH%/$(date +%%Y-%%m-%%d).log"
goto main_menu

:download_logs
cls
echo 📥 Downloading Today's Logs...
echo.
set "TODAY=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%"
set "LOCAL_LOG=logs\vps\quranbot_%TODAY%.log"
echo [%date% %time%] Downloading logs for %TODAY% >> "%SESSION_LOG%"
scp -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST%:%LOG_PATH%/%TODAY%.log "%LOCAL_LOG%"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Logs downloaded to: %LOCAL_LOG%
    echo.
    set /p "open_log=Open log file? (y/n): "
    if /i "!open_log!"=="y" (
        notepad "%LOCAL_LOG%"
    )
) else (
    echo.
    echo ❌ Failed to download logs.
)
echo.
pause
goto main_menu

:log_analytics
cls
echo 📊 Log Analytics
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Log Summary ===' && ls -la %LOG_PATH%/*.log 2>/dev/null | tail -10 && echo '' && echo '=== Error Count (Last 1000 lines) ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i error | wc -l && echo '' && echo '=== Warning Count (Last 1000 lines) ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i warning | wc -l && echo '' && echo '=== Recent Errors ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i error | tail -5 || echo 'No recent errors found'"
echo.
pause
goto main_menu

:create_backup
cls
echo 💾 Creating Backup...
echo.
set "BACKUP_NAME=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%"
echo [%date% %time%] Creating backup: %BACKUP_NAME% >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "mkdir -p /opt/quranbot/backups && cd %BOT_PATH% && tar -czf /opt/quranbot/backups/%BACKUP_NAME%.tar.gz data/ *.json *.yml 2>/dev/null && echo 'Backup created: %BACKUP_NAME%.tar.gz' && ls -lh /opt/quranbot/backups/%BACKUP_NAME%.tar.gz"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Backup created successfully!
) else (
    echo.
    echo ❌ Failed to create backup.
)
echo.
pause
goto main_menu

:system_info
cls
echo 🖥️  System Information
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== OS Information ===' && cat /etc/os-release | head -3 && echo '' && echo '=== System Uptime ===' && uptime && echo '' && echo '=== Memory Usage ===' && free -h && echo '' && echo '=== Disk Usage ===' && df -h && echo '' && echo '=== CPU Info ===' && nproc && cat /proc/loadavg && echo '' && echo '=== Network Info ===' && ip route get 1 | awk '{print $7}' | head -1"
echo.
pause
goto main_menu

:ssh_terminal
cls
echo 🔌 Opening SSH Terminal...
echo Type 'exit' to return to VPS Manager
echo.
echo [%date% %time%] Opening SSH terminal >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST%
goto main_menu

:python_console
cls
echo 🐍 QuranBot Python Console
echo.
echo [%date% %time%] Starting Python console >> "%SESSION_LOG%"
if exist "scripts\vps\enhanced\vps_manager.py" (
    python "scripts\vps\enhanced\vps_manager.py"
) else (
    echo ❌ Python VPS manager not found. Using basic status check...
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "cd %BOT_PATH% && python3 -c \"import sys; print('Python version:', sys.version); print('Working directory:', sys.path[0])\""
)
echo.
pause
goto main_menu

:emergency_stop
cls
echo 💀 Emergency Stop - Killing All Python Processes
echo ⚠️  WARNING: This will forcefully terminate all Python processes!
echo.
set /p "confirm=Are you sure? Type 'KILL' to confirm: "
if "!confirm!"=="KILL" (
    echo [%date% %time%] Emergency stop executed >> "%SESSION_LOG%"
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "pkill -f python && echo 'All Python processes terminated'"
    echo.
    echo ✅ Emergency stop completed.
) else (
    echo Operation cancelled.
)
echo.
pause
goto main_menu

:settings
cls
echo ⚙️  VPS Manager Settings
echo.
echo Current Configuration:
echo   VPS Host: %VPS_HOST%
echo   VPS User: %VPS_USER%
echo   SSH Key: %SSH_KEY%
echo   Bot Service: %BOT_SERVICE%
echo   Bot Path: %BOT_PATH%
echo.
echo 1. Test SSH Connection
echo 2. View Session Log
echo 3. Back to Main Menu
echo.
set /p "setting_choice=Choose option: "

if "%setting_choice%"=="1" (
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo 'SSH connection successful' && date"
) else if "%setting_choice%"=="2" (
    if exist "%SESSION_LOG%" (
        notepad "%SESSION_LOG%"
    ) else (
        echo Session log not found
    )
)

pause
goto main_menu

:exit_manager
cls
echo 👋 Thank you for using QuranBot VPS Manager!
echo [%date% %time%] VPS Manager session ended >> "%SESSION_LOG%"
echo.
timeout /t 2 >nul
exit /b 