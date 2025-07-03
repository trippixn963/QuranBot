@echo off
setlocal enabledelayedexpansion

REM QuranBot VPS Manager - Windows Batch Script
REM VPS Configuration
set VPS_IP=159.89.90.90
set VPS_USER=root
set SSH_KEY_PATH=C:\Users\hanna\Documents\QuranBot\quranbot_key
set BOT_DIR=/home/QuranAudioBot
set LOCAL_PROJECT=C:\Users\hanna\Documents\QuranBot

REM Colors removed for Windows CMD compatibility

echo.
echo ========================================
echo    QuranBot VPS Manager
echo ========================================
echo.

:menu
cls
echo ================================================================================
echo                    QuranBot VPS Manager
echo ================================================================================
echo.
echo BOT CONTROL:
echo 1.  Check Connection          - Test SSH connection to VPS
echo 2.  Get Bot Status           - Check if bot is running and get uptime
echo 3.  Start Bot                - Start the QuranBot on VPS
echo 4.  Stop Bot                 - Stop the QuranBot on VPS
echo 5.  Restart Bot              - Stop and restart the bot
echo 6.  Deploy Bot               - Pull latest code and restart
echo.
echo LOGS ^& MONITORING:
echo 7.  View Logs                - Show recent bot log entries
echo 8.  Search Logs              - Search logs for specific terms
echo 9.  Download All Logs        - Download all log files to local logs folder
echo 10. Clear Old Logs           - Remove log files older than 7 days
echo.
echo BACKUP ^& RESTORE:
echo 11. Create Backup            - Create timestamped backup of bot
echo 12. List Backups             - Show all available backup files
echo 13. Restore Backup           - Restore bot from backup file
echo 14. Cleanup Old Backups      - Remove backups older than 7 days
echo.
echo SYSTEM MANAGEMENT:
echo 15. Setup Environment        - Initial bot setup (first time only)
echo 16. Monitor Bot              - Continuous monitoring with alerts
echo 17. System Information       - CPU, memory, disk usage, uptime
echo 18. Check Disk Space         - Show disk space on VPS
echo 19. Check Network Status     - Test internet, DNS, open ports
echo.
echo UTILITIES:
echo 20. Upload Audio Files       - Upload audio files to VPS
echo 21. Update System            - Update system packages on VPS
echo 22. Emergency Restart        - Force kill and restart everything
echo 23. Exit                     - Close the VPS manager
echo.
echo ================================================================================

set /p choice="Enter your choice (1-23): "

if "%choice%"=="1" goto check_connection
if "%choice%"=="2" goto get_status
if "%choice%"=="3" goto start_bot
if "%choice%"=="4" goto stop_bot
if "%choice%"=="5" goto restart_bot
if "%choice%"=="6" goto deploy_bot
if "%choice%"=="7" goto view_logs
if "%choice%"=="8" goto search_logs
if "%choice%"=="9" goto download_logs
if "%choice%"=="10" goto clear_logs
if "%choice%"=="11" goto create_backup
if "%choice%"=="12" goto list_backups
if "%choice%"=="13" goto restore_backup
if "%choice%"=="14" goto cleanup_backups
if "%choice%"=="15" goto setup_env
if "%choice%"=="16" goto monitor_bot
if "%choice%"=="17" goto system_info
if "%choice%"=="18" goto disk_space
if "%choice%"=="19" goto network_status
if "%choice%"=="20" goto upload_audio
if "%choice%"=="21" goto update_system
if "%choice%"=="22" goto emergency_restart
if "%choice%"=="23" goto exit
echo Invalid choice!
pause
goto menu

:check_connection
echo Testing SSH connection...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "echo 'Connection successful'"
if %errorlevel%==0 (
    echo SUCCESS: SSH connection successful!
) else (
    echo ERROR: SSH connection failed!
)
pause
goto menu

:get_status
echo Getting bot status...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "ps aux | grep 'python run.py' | grep -v grep"
if %errorlevel%==0 (
    echo SUCCESS: Bot is running!
) else (
    echo ERROR: Bot is not running!
)
echo.
echo Recent logs:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "tail -10 %BOT_DIR%/bot.log"
pause
goto menu

:start_bot
echo Starting QuranBot...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && source venv/bin/activate && nohup python run.py &"
if %errorlevel%==0 (
    echo SUCCESS: Bot started successfully!
) else (
    echo ERROR: Failed to start bot!
)
pause
goto menu

:stop_bot
echo Stopping QuranBot...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "pkill -f 'python run.py'"
if %errorlevel%==0 (
    echo SUCCESS: Bot stopped successfully!
) else (
    echo WARNING: Bot may not have been running or failed to stop.
)
pause
goto menu

:restart_bot
echo Restarting QuranBot...
echo.
echo Step 1: Stopping bot...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "pkill -f 'python run.py'"
echo Step 1 completed.
timeout /t 3 /nobreak >nul
echo.
echo Step 2: Starting bot...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && source venv/bin/activate && nohup python run.py &"
echo Step 2 completed.
timeout /t 3 /nobreak >nul
echo.
echo Step 3: Verifying bot is running...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "ps aux | grep 'python run.py' | grep -v grep"
if %errorlevel%==0 (
    echo.
    echo SUCCESS: Bot restarted successfully!
) else (
    echo.
    echo ERROR: Bot restart failed! Bot is not running.
)
echo.
echo Press any key to return to menu...
pause >nul
goto menu

:deploy_bot
echo Deploying QuranBot...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && git pull origin main"
if %errorlevel%==0 (
    echo SUCCESS: Code updated successfully!
    ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && source venv/bin/activate && pip install -r requirements.txt"
    call :restart_bot
) else (
    echo ERROR: Failed to pull latest changes!
)
pause
goto menu

:view_logs
set /p lines="Number of log lines to show (default 50): "
if "%lines%"=="" set lines=50
echo Showing last %lines% lines of bot logs...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "tail -%lines% %BOT_DIR%/bot.log"
pause
goto menu

:search_logs
set /p search_term="Enter search term: "
if "%search_term%"=="" (
    echo ERROR: No search term provided!
    pause
    goto menu
)
set /p lines="Number of lines to search (default 100): "
if "%lines%"=="" set lines=100
echo Searching logs for '%search_term%'...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "grep -n '%search_term%' %BOT_DIR%/bot.log | tail -%lines%"
pause
goto menu

:download_logs
echo Downloading all log files from VPS...
echo.
echo Step 1: Creating log archive on VPS...
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"
set "remote_logs_archive=logs_backup_%timestamp%.tar.gz"
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && tar -czf %remote_logs_archive% logs/ *.log 2>/dev/null || echo 'No logs found'"
if %errorlevel%==0 (
    echo Step 1 completed successfully.
) else (
    echo ERROR: Failed to create log archive on VPS!
    pause
    goto menu
)
echo.
echo Step 2: Creating local logs directory...
if not exist "%LOCAL_PROJECT%\logs" (
    mkdir "%LOCAL_PROJECT%\logs"
    echo Local logs directory created.
) else (
    echo Local logs directory already exists.
)
echo.
echo Step 3: Downloading log archive...
scp -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP%:%BOT_DIR%/%remote_logs_archive% "%LOCAL_PROJECT%\\logs\\"
if %errorlevel%==0 (
    echo Step 3 completed successfully.
) else (
    echo ERROR: Failed to download log archive!
    pause
    goto menu
)
echo.
echo Step 4: Extracting logs...
cd /d "%LOCAL_PROJECT%\logs"
tar -xzf %remote_logs_archive%
if %errorlevel%==0 (
    echo Step 4 completed successfully.
    del %remote_logs_archive%
    echo SUCCESS: Temporary archive removed.
) else (
    echo ERROR: Failed to extract log archive!
    pause
    goto menu
)
echo.
echo Step 5: Listing downloaded files...
dir /b *.log 2>nul
if %errorlevel%==0 (
    echo.
    echo SUCCESS: Log files downloaded and extracted successfully!
) else (
    echo No log files found on VPS.
)
echo.
echo Step 6: Cleaning up remote archive...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && rm -f %remote_logs_archive%"
echo Step 6 completed.
echo.
echo SUCCESS: All log files downloaded to %LOCAL_PROJECT%\logs\
pause
goto menu

:clear_logs
echo Clearing old log files...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && find . -name '*.log*' -mtime +7 -delete"
if %errorlevel%==0 (
    echo SUCCESS: Old log files cleared successfully!
) else (
    echo ERROR: Failed to clear log files!
)
pause
goto menu

:upload_audio
set /p audio_path="Enter local audio files path: "
if "%audio_path%"=="" (
    echo ERROR: No path provided!
    pause
    goto menu
)
echo Uploading audio files...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "mkdir -p %BOT_DIR%/audio"
scp -i "%SSH_KEY_PATH%" -r "%audio_path%\*" %VPS_USER%@%VPS_IP%:%BOT_DIR%/audio/
if %errorlevel%==0 (
    echo SUCCESS: Audio files uploaded successfully!
) else (
    echo ERROR: Failed to upload audio files!
)
pause
goto menu

:create_backup
echo Creating backup...
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && tar -czf backup_%timestamp%.tar.gz --exclude=venv --exclude=*.log --exclude=__pycache__ ."
if %errorlevel%==0 (
    echo SUCCESS: Backup created: backup_%timestamp%.tar.gz
) else (
    echo ERROR: Failed to create backup!
)
pause
goto menu

:list_backups
echo Listing available backups...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && ls -la *.tar.gz 2>/dev/null || echo 'No backup files found'"
pause
goto menu

:restore_backup
set /p backup_name="Enter backup filename: "
if "%backup_name%"=="" (
    echo ERROR: No backup name provided!
    pause
    goto menu
)
echo Restoring from backup: %backup_name%
call :stop_bot
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && tar -xzf %backup_name% --strip-components=0"
if %errorlevel%==0 (
    echo SUCCESS: Backup restored successfully!
    call :start_bot
) else (
    echo ERROR: Failed to restore backup!
)
pause
goto menu

:cleanup_backups
echo Cleaning up old backups...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && find . -name '*.tar.gz' -mtime +7 -delete"
if %errorlevel%==0 (
    echo SUCCESS: Old backups (older than 7 days) cleaned up!
) else (
    echo ERROR: Failed to cleanup old backups!
)
pause
goto menu

:setup_env
echo Setting up bot environment...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "if [ ! -d '%BOT_DIR%' ]; then git clone https://github.com/yourusername/QuranBot.git %BOT_DIR%; fi"
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && python3 -m venv venv"
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && source venv/bin/activate && pip install -r requirements.txt"
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cd %BOT_DIR% && mkdir -p logs audio"
echo SUCCESS: Environment setup completed!
pause
goto menu

:monitor_bot
set /p duration="Monitoring duration in minutes (default 60): "
if "%duration%"=="" set duration=60
echo Monitoring bot for %duration% minutes...
echo Press Ctrl+C to stop monitoring early
for /l %%i in (1,1,%duration%) do (
    echo.
    echo ================================================================================
    echo Status Check - %%i/%duration%
    echo ================================================================================
    ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "ps aux | grep 'python run.py' | grep -v grep"
    if !errorlevel!==0 (
        echo Bot Running: YES
    ) else (
        echo Bot Running: NO
    )
    echo CPU Info:
    ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "top -bn1 | head -5"
    echo Memory Info:
    ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "free -h"
    timeout /t 300 /nobreak >nul
)
pause
goto menu

:system_info
echo Getting system information...
echo CPU Info:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "top -bn1 | head -5"
echo.
echo Memory Info:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "free -h"
echo.
echo Disk Usage:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "df -h"
echo.
echo Uptime:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "uptime -p"
echo.
echo Load Average:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "cat /proc/loadavg"
pause
goto menu

:disk_space
echo Checking disk space...
echo.
echo Main Disk Usage:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "df -h /"
echo.
echo All Mounted Disks:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "df -h | grep -E '^/dev/'"
pause
goto menu

:network_status
echo Checking network status...
echo Internet Connectivity:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "ping -c 3 8.8.8.8"
echo DNS Resolution:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "nslookup google.com"
echo Open Ports:
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "netstat -tlnp | grep LISTEN"
pause
goto menu

:update_system
echo Updating system packages...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "apt update && apt upgrade -y"
if %errorlevel%==0 (
    echo SUCCESS: System updated successfully!
) else (
    echo ERROR: Failed to update system!
)
pause
goto menu

:emergency_restart
echo EMERGENCY: Emergency restart initiated...
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "pkill -9 -f python"
timeout /t 5 /nobreak >nul
ssh -i "%SSH_KEY_PATH%" %VPS_USER%@%VPS_IP% "killall -9 python"
timeout /t 2 /nobreak >nul
call :start_bot
pause
goto menu

:exit
echo Goodbye!
exit /b 0 