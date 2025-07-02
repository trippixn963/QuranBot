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
set "CONFIG_FILE=scripts\vps\config\vps_config.json"

:: Create necessary directories
if not exist "logs\vps" mkdir "logs\vps"
if not exist "backups\vps" mkdir "backups\vps"
if not exist "temp\vps" mkdir "temp\vps"

:: Initialize session log
set "SESSION_LOG=logs\vps\session_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%.log"
echo [%date% %time%] VPS Manager session started > "%SESSION_LOG%"

:main_menu
cls
echo.
echo %ESC%[96m==========================================================%ESC%[0m
echo %ESC%[96m           QuranBot Enhanced VPS Manager v2.0           %ESC%[0m
echo %ESC%[96m==========================================================%ESC%[0m
echo.
echo %ESC%[92m🚀 BOT CONTROL:%ESC%[0m
echo   1. %ESC%[93m▶️  Start Bot%ESC%[0m
echo   2. %ESC%[91m⏹️  Stop Bot%ESC%[0m  
echo   3. %ESC%[94m🔄 Restart Bot%ESC%[0m
echo   4. %ESC%[96m📊 Bot Status%ESC%[0m
echo   5. %ESC%[95m⬆️  Update Bot%ESC%[0m
echo   6. %ESC%[93m🔧 Advanced Status%ESC%[0m
echo.
echo %ESC%[92m📋 LOG MANAGEMENT:%ESC%[0m
echo   7. %ESC%[94m🔄 Live Stream Logs%ESC%[0m
echo   8. %ESC%[93m📥 Download Today's Logs%ESC%[0m
echo   9. %ESC%[96m📊 Log Analytics%ESC%[0m
echo   10. %ESC%[91m🧹 Cleanup Old Logs%ESC%[0m
echo   11. %ESC%[95m📦 Archive Logs%ESC%[0m
echo.
echo %ESC%[92m💾 BACKUP ^& RESTORE:%ESC%[0m
echo   12. %ESC%[93m💾 Create Backup%ESC%[0m
echo   13. %ESC%[94m📦 List Backups%ESC%[0m
echo   14. %ESC%[96m🔄 Restore Backup%ESC%[0m
echo   15. %ESC%[92m📥 Download Backup%ESC%[0m
echo.
echo %ESC%[92m📊 MONITORING:%ESC%[0m
echo   16. %ESC%[94m🖥️  System Info%ESC%[0m
echo   17. %ESC%[93m📈 Performance Monitor%ESC%[0m
echo   18. %ESC%[96m🔍 Health Check%ESC%[0m
echo   19. %ESC%[95m📊 Resource Usage%ESC%[0m
echo   20. %ESC%[91m🔥 Process Monitor%ESC%[0m
echo.
echo %ESC%[92m🛠️  UTILITIES:%ESC%[0m
echo   21. %ESC%[94m🔌 SSH Terminal%ESC%[0m
echo   22. %ESC%[91m💀 Emergency Stop%ESC%[0m
echo   23. %ESC%[93m🔧 Service Manager%ESC%[0m
echo   24. %ESC%[96m📁 File Manager%ESC%[0m
echo   25. %ESC%[95m⚙️  Settings%ESC%[0m
echo.
echo %ESC%[92m🎯 ADVANCED:%ESC%[0m
echo   26. %ESC%[94m🐍 Python Console%ESC%[0m
echo   27. %ESC%[93m📊 Dashboard%ESC%[0m
echo   28. %ESC%[96m🔍 Troubleshoot%ESC%[0m
echo   29. %ESC%[95m🛡️  Security Scan%ESC%[0m
echo.
echo   30. %ESC%[91m❌ Exit%ESC%[0m
echo.
echo %ESC%[96m==========================================================%ESC%[0m
echo %ESC%[93mVPS:%ESC%[0m %VPS_HOST% ^| %ESC%[93mService:%ESC%[0m %BOT_SERVICE% ^| %ESC%[93mSession:%ESC%[0m %time:~0,8%
echo.

set /p "choice=Enter your choice (1-30): "

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
if "%choice%"=="11" goto archive_logs
if "%choice%"=="12" goto create_backup
if "%choice%"=="13" goto list_backups
if "%choice%"=="14" goto restore_backup
if "%choice%"=="15" goto download_backup
if "%choice%"=="16" goto system_info
if "%choice%"=="17" goto performance_monitor
if "%choice%"=="18" goto health_check
if "%choice%"=="19" goto resource_usage
if "%choice%"=="20" goto process_monitor
if "%choice%"=="21" goto ssh_terminal
if "%choice%"=="22" goto emergency_stop
if "%choice%"=="23" goto service_manager
if "%choice%"=="24" goto file_manager
if "%choice%"=="25" goto settings
if "%choice%"=="26" goto python_console
if "%choice%"=="27" goto dashboard
if "%choice%"=="28" goto troubleshoot
if "%choice%"=="29" goto security_scan
if "%choice%"=="30" goto exit_manager

echo Invalid choice! Please try again.
timeout /t 2 >nul
goto main_menu

:start_bot
cls
echo %ESC%[93m🚀 Starting QuranBot...%ESC%[0m
echo.
echo [%date% %time%] Starting bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl start %BOT_SERVICE% && echo 'Bot started successfully' && systemctl status %BOT_SERVICE% --no-pager -l"
if %errorlevel% equ 0 (
    echo.
    echo %ESC%[92m✅ Bot started successfully!%ESC%[0m
) else (
    echo.
    echo %ESC%[91m❌ Failed to start bot. Check logs for details.%ESC%[0m
)
echo.
pause
goto main_menu

:stop_bot
cls
echo %ESC%[91m⏹️  Stopping QuranBot...%ESC%[0m
echo.
echo [%date% %time%] Stopping bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl stop %BOT_SERVICE% && echo 'Bot stopped successfully'"
if %errorlevel% equ 0 (
    echo.
    echo %ESC%[92m✅ Bot stopped successfully!%ESC%[0m
) else (
    echo.
    echo %ESC%[91m❌ Failed to stop bot.%ESC%[0m
)
echo.
pause
goto main_menu

:restart_bot
cls
echo %ESC%[94m🔄 Restarting QuranBot...%ESC%[0m
echo.
echo [%date% %time%] Restarting bot >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "systemctl restart %BOT_SERVICE% && echo 'Bot restarted successfully' && sleep 3 && systemctl status %BOT_SERVICE% --no-pager -l"
if %errorlevel% equ 0 (
    echo.
    echo %ESC%[92m✅ Bot restarted successfully!%ESC%[0m
) else (
    echo.
    echo %ESC%[91m❌ Failed to restart bot.%ESC%[0m
)
echo.
pause
goto main_menu

:bot_status
cls
echo %ESC%[96m📊 QuranBot Status%ESC%[0m
echo.
echo [%date% %time%] Checking bot status >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Service Status ===' && systemctl status %BOT_SERVICE% --no-pager -l && echo '' && echo '=== Process Info ===' && ps aux | grep -E '(python|quran)' | grep -v grep && echo '' && echo '=== Recent Logs ===' && tail -10 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null || echo 'No logs found for today'"
echo.
pause
goto main_menu

:advanced_status
cls
echo %ESC%[96m🔧 Advanced Bot Status%ESC%[0m
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Detailed Service Info ===' && systemctl show %BOT_SERVICE% --no-pager && echo '' && echo '=== Memory Usage ===' && ps -p $(pgrep -f %BOT_SERVICE%) -o pid,ppid,%%cpu,%%mem,vsz,rss,tty,stat,start,time,command 2>/dev/null || echo 'Service not running' && echo '' && echo '=== Network Connections ===' && netstat -tulpn | grep python || echo 'No Python network connections' && echo '' && echo '=== Disk Usage ===' && df -h %BOT_PATH% && echo '' && echo '=== System Load ===' && uptime && echo '' && echo '=== Memory Info ===' && free -h"
echo.
pause
goto main_menu

:stream_logs
cls
echo %ESC%[94m🔄 Live Streaming Logs...%ESC%[0m
echo %ESC%[93mPress Ctrl+C to stop streaming%ESC%[0m
echo.
echo [%date% %time%] Starting log stream >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "tail -f %LOG_PATH%/$(date +%%Y-%%m-%%d).log"
goto main_menu

:download_logs
cls
echo %ESC%[93m📥 Downloading Today's Logs...%ESC%[0m
echo.
set "TODAY=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%"
set "LOCAL_LOG=logs\vps\quranbot_%TODAY%.log"
echo [%date% %time%] Downloading logs for %TODAY% >> "%SESSION_LOG%"
scp -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST%:%LOG_PATH%/%TODAY%.log "%LOCAL_LOG%"
if %errorlevel% equ 0 (
    echo.
    echo %ESC%[92m✅ Logs downloaded to: %LOCAL_LOG%%ESC%[0m
    echo.
    set /p "open_log=Open log file? (y/n): "
    if /i "!open_log!"=="y" (
        notepad "%LOCAL_LOG%"
    )
) else (
    echo.
    echo %ESC%[91m❌ Failed to download logs.%ESC%[0m
)
echo.
pause
goto main_menu

:log_analytics
cls
echo %ESC%[96m📊 Log Analytics%ESC%[0m
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== Log Summary ===' && ls -la %LOG_PATH%/*.log 2>/dev/null | tail -10 && echo '' && echo '=== Error Count (Last 1000 lines) ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i error | wc -l && echo '' && echo '=== Warning Count (Last 1000 lines) ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i warning | wc -l && echo '' && echo '=== Recent Errors ===' && tail -1000 %LOG_PATH%/$(date +%%Y-%%m-%%d).log 2>/dev/null | grep -i error | tail -5 || echo 'No recent errors found'"
echo.
pause
goto main_menu

:create_backup
cls
echo %ESC%[93m💾 Creating Backup...%ESC%[0m
echo.
set "BACKUP_NAME=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%"
echo [%date% %time%] Creating backup: %BACKUP_NAME% >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "mkdir -p /opt/quranbot/backups && cd %BOT_PATH% && tar -czf /opt/quranbot/backups/%BACKUP_NAME%.tar.gz data/ *.json *.yml 2>/dev/null && echo 'Backup created: %BACKUP_NAME%.tar.gz' && ls -lh /opt/quranbot/backups/%BACKUP_NAME%.tar.gz"
if %errorlevel% equ 0 (
    echo.
    echo %ESC%[92m✅ Backup created successfully!%ESC%[0m
) else (
    echo.
    echo %ESC%[91m❌ Failed to create backup.%ESC%[0m
)
echo.
pause
goto main_menu

:system_info
cls
echo %ESC%[94m🖥️  System Information%ESC%[0m
echo.
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo '=== OS Information ===' && cat /etc/os-release | head -3 && echo '' && echo '=== System Uptime ===' && uptime && echo '' && echo '=== Memory Usage ===' && free -h && echo '' && echo '=== Disk Usage ===' && df -h && echo '' && echo '=== CPU Info ===' && nproc && cat /proc/loadavg && echo '' && echo '=== Network Info ===' && ip route get 1 | awk '{print $7}' | head -1"
echo.
pause
goto main_menu

:ssh_terminal
cls
echo %ESC%[94m🔌 Opening SSH Terminal...%ESC%[0m
echo %ESC%[93mType 'exit' to return to VPS Manager%ESC%[0m
echo.
echo [%date% %time%] Opening SSH terminal >> "%SESSION_LOG%"
ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST%
goto main_menu

:python_console
cls
echo %ESC%[94m🐍 QuranBot Python Console%ESC%[0m
echo.
echo [%date% %time%] Starting Python console >> "%SESSION_LOG%"
if exist "scripts\vps\core\vps_manager.py" (
    python "scripts\vps\core\vps_manager.py"
) else (
    echo %ESC%[91m❌ Python VPS manager not found. Using basic status check...%ESC%[0m
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "cd %BOT_PATH% && python3 -c \"import sys; print('Python version:', sys.version); print('Working directory:', sys.path[0])\""
)
echo.
pause
goto main_menu

:emergency_stop
cls
echo %ESC%[91m💀 Emergency Stop - Killing All Python Processes%ESC%[0m
echo %ESC%[93m⚠️  WARNING: This will forcefully terminate all Python processes!%ESC%[0m
echo.
set /p "confirm=Are you sure? Type 'KILL' to confirm: "
if "!confirm!"=="KILL" (
    echo [%date% %time%] Emergency stop executed >> "%SESSION_LOG%"
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "pkill -f python && echo 'All Python processes terminated'"
    echo.
    echo %ESC%[92m✅ Emergency stop completed.%ESC%[0m
) else (
    echo %ESC%[93mOperation cancelled.%ESC%[0m
)
echo.
pause
goto main_menu

:exit_manager
cls
echo %ESC%[93m👋 Thank you for using QuranBot VPS Manager!%ESC%[0m
echo [%date% %time%] VPS Manager session ended >> "%SESSION_LOG%"
echo.
timeout /t 2 >nul
exit /b

:settings
cls
echo %ESC%[95m⚙️  VPS Manager Settings%ESC%[0m
echo.
echo Current Configuration:
echo   VPS Host: %VPS_HOST%
echo   VPS User: %VPS_USER%
echo   SSH Key: %SSH_KEY%
echo   Bot Service: %BOT_SERVICE%
echo   Bot Path: %BOT_PATH%
echo.
echo 1. Edit Configuration File
echo 2. Test SSH Connection
echo 3. View Session Log
echo 4. Back to Main Menu
echo.
set /p "setting_choice=Choose option: "

if "%setting_choice%"=="1" (
    if exist "%CONFIG_FILE%" (
        notepad "%CONFIG_FILE%"
    ) else (
        echo Configuration file not found: %CONFIG_FILE%
    )
) else if "%setting_choice%"=="2" (
    ssh -i "%SSH_KEY%" %VPS_USER%@%VPS_HOST% "echo 'SSH connection successful' && date"
) else if "%setting_choice%"=="3" (
    if exist "%SESSION_LOG%" (
        notepad "%SESSION_LOG%"
    ) else (
        echo Session log not found
    )
)

pause
goto main_menu

:: Additional functions would continue here...
:: (The file is getting long, so I'll create separate files for specific functionalities) 