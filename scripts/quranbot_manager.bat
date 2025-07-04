@echo off
setlocal enabledelayedexpansion

title QuranBot Manager

:welcome
cls
echo.
echo ========================================
echo           QuranBot Manager
echo ========================================
echo.
echo Welcome to QuranBot Manager!
echo.
echo Current Status:
if exist ".venv\Scripts\activate" (
    echo ✅ Virtual Environment: Ready
) else (
    echo ❌ Virtual Environment: Not Found
)
if exist "data\bot_state.json" (
    echo ✅ Data Files: Available
) else (
    echo ❌ Data Files: Missing
)
echo.
echo Last updated: 2025-07-04
echo.
pause

:mainmenu
cls
echo.
echo ========================================
echo           QuranBot Manager
echo ========================================
echo.
echo 1. Local Tools
echo 2. VPS Manager
echo 3. Quick Actions
echo 4. System Health Check
echo 5. Exit
echo.
set /p mainchoice="Enter your choice (1-5): "

if "%mainchoice%"=="1" goto localtools
if "%mainchoice%"=="2" goto vpsmenu
if "%mainchoice%"=="3" goto quickactions
if "%mainchoice%"=="4" goto healthcheck
if "%mainchoice%"=="5" goto exit

goto mainmenu

:localtools
cls
echo.
echo ========== Local Tools ==========
echo 1. Backup Data
echo 2. Check FFmpeg Status
echo 3. Update FFmpeg
echo 4. Validate MP3 Files
echo 5. Local Bot Management
echo 6. Back to Main Menu
echo.
set /p choice="Enter your choice (1-6): "
if "%choice%"=="1" goto backup
if "%choice%"=="2" goto check_ffmpeg
if "%choice%"=="3" goto update_ffmpeg
if "%choice%"=="4" goto validate_mp3s
if "%choice%"=="5" goto localbot
if "%choice%"=="6" goto mainmenu
goto localtools

:backup
echo.
echo Running data backup...
python scripts/local/backup_manager.py
echo.
pause
goto localtools

:check_ffmpeg
echo.
echo Checking FFmpeg status...
python scripts/local/ffmpeg_checker.py --status
echo.
pause
goto localtools

:update_ffmpeg
echo.
echo Updating FFmpeg...
python scripts/local/ffmpeg_checker.py --update
echo.
pause
goto localtools

:validate_mp3s
echo.
echo Validating MP3 files...
python scripts/local/audio_validator.py
echo.
pause
goto localtools

:localbot
cls
echo.
echo ========== Local Bot Management ==========
echo 1. Start Bot (with Virtual Environment)
echo 2. Stop Bot
echo 3. Check Bot Status
echo 4. Install Dependencies (Virtual Environment)
echo 5. View Local Logs
echo 6. Clear Local Logs
echo 7. Test Bot Connection
echo 8. Back to Local Tools
echo.
set /p botchoice="Enter your choice (1-8): "
if "%botchoice%"=="1" goto start_local_bot
if "%botchoice%"=="2" goto stop_local_bot
if "%botchoice%"=="3" goto check_local_bot
if "%botchoice%"=="4" goto install_deps
if "%botchoice%"=="5" goto view_local_logs
if "%botchoice%"=="6" goto clear_local_logs
if "%botchoice%"=="7" goto test_bot_conn
if "%botchoice%"=="8" goto localtools
goto localbot

:start_local_bot
echo.
echo Starting local bot with virtual environment...
call .venv\Scripts\activate && python run.py
echo.
pause
goto localbot

:stop_local_bot
echo.
echo Stopping local bot...
taskkill /f /im python.exe 2>nul
echo Bot stopped.
echo.
pause
goto localbot

:check_local_bot
echo.
echo Checking local bot status...
tasklist /fi "imagename eq python.exe" | findstr python.exe
echo.
pause
goto localbot

:install_deps
echo.
echo Installing dependencies in virtual environment...
call .venv\Scripts\activate && pip install -r requirements.txt
echo.
pause
goto localbot

:view_local_logs
echo.
echo Viewing local logs...
if exist "logs\bot.log" (
    echo Recent log entries:
    echo ========================================
    powershell "Get-Content logs\bot.log -Tail 20"
) else (
    echo No local logs found.
)
echo.
pause
goto localbot

:clear_local_logs
echo.
echo Clearing local logs...
if exist "logs\bot.log" (
    del "logs\bot.log"
    echo Local logs cleared.
) else (
    echo No local logs to clear.
)
echo.
pause
goto localbot

:test_bot_conn
echo.
echo Testing bot connection...
echo Checking if bot can connect to Discord...
call .venv\Scripts\activate && python -c "import discord; print('✅ Discord library available')"
echo.
pause
goto localbot

:vpsmenu
cls
echo.
echo ===============================================================================
echo                   QuranBot VPS Manager
echo ===============================================================================
echo.
echo BOT CONTROL:
echo 1.  Check Connection          - Test SSH connection to VPS
echo 2.  Get Bot Status           - Check if bot is running and get uptime
echo 3.  Start Bot                - Start the QuranBot on VPS
echo 4.  Stop Bot                 - Stop the QuranBot on VPS
echo 5.  Restart Bot              - Stop and restart the bot
echo 6.  Deploy Bot               - Pull latest code and restart
echo.
echo LOGS & MONITORING:
echo 7.  View Logs                - Show recent bot log entries
echo 8.  Search Logs              - Search logs for specific terms
echo 9.  Download All Logs        - Download all log files to local logs folder
echo 10. Clear Old Logs           - Remove log files older than 7 days
echo.
echo BACKUP & RESTORE:
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
echo 22. Kill All Python          - Force kill all Python processes
echo 23. Emergency Restart        - Force kill and restart everything
echo.
echo DATA MANAGEMENT:
echo 24. Download Data            - Download data directory from VPS for editing
echo 25. Upload Data              - Upload edited data directory back to VPS
echo 26. Sync Data Files          - Sync specific data files only
echo 27. View Data Contents       - List contents of data directory
echo 28. Back to Main Menu
echo.
set /p vpschoice="Enter your choice (1-28): "

if "%vpschoice%"=="1"  python scripts/vps/vps_manager.py --check-connection & pause & goto vpsmenu
if "%vpschoice%"=="2"  python scripts/vps/vps_manager.py --get-bot-status & pause & goto vpsmenu
if "%vpschoice%"=="3"  python scripts/vps/vps_manager.py --start-bot & pause & goto vpsmenu
if "%vpschoice%"=="4"  python scripts/vps/vps_manager.py --stop-bot & pause & goto vpsmenu
if "%vpschoice%"=="5"  python scripts/vps/vps_manager.py --restart-bot & pause & goto vpsmenu
if "%vpschoice%"=="6"  python scripts/vps/vps_manager.py --deploy-bot & pause & goto vpsmenu
if "%vpschoice%"=="7"  python scripts/vps/vps_manager.py --view-logs & pause & goto vpsmenu
if "%vpschoice%"=="8"  python scripts/vps/vps_manager.py --search-logs & pause & goto vpsmenu
if "%vpschoice%"=="9"  python scripts/vps/vps_manager.py --download-logs & pause & goto vpsmenu
if "%vpschoice%"=="10" python scripts/vps/vps_manager.py --clear-old-logs & pause & goto vpsmenu
if "%vpschoice%"=="11" python scripts/vps/vps_manager.py --create-backup & pause & goto vpsmenu
if "%vpschoice%"=="12" python scripts/vps/vps_manager.py --list-backups & pause & goto vpsmenu
if "%vpschoice%"=="13" python scripts/vps/vps_manager.py --restore-backup & pause & goto vpsmenu
if "%vpschoice%"=="14" python scripts/vps/vps_manager.py --cleanup-old-backups & pause & goto vpsmenu
if "%vpschoice%"=="15" python scripts/vps/vps_manager.py --setup-environment & pause & goto vpsmenu
if "%vpschoice%"=="16" python scripts/vps/vps_manager.py --monitor-bot & pause & goto vpsmenu
if "%vpschoice%"=="17" python scripts/vps/vps_manager.py --system-info & pause & goto vpsmenu
if "%vpschoice%"=="18" python scripts/vps/vps_manager.py --check-disk-space & pause & goto vpsmenu
if "%vpschoice%"=="19" python scripts/vps/vps_manager.py --check-network-status & pause & goto vpsmenu
if "%vpschoice%"=="20" python scripts/vps/vps_manager.py --upload-audio & pause & goto vpsmenu
if "%vpschoice%"=="21" python scripts/vps/vps_manager.py --update-system & pause & goto vpsmenu
if "%vpschoice%"=="22" python scripts/vps/vps_manager.py --kill-all-python & pause & goto vpsmenu
if "%vpschoice%"=="23" python scripts/vps/vps_manager.py --emergency-restart & pause & goto vpsmenu
if "%vpschoice%"=="24" python scripts/vps/vps_manager.py --download-data & pause & goto vpsmenu
if "%vpschoice%"=="25" python scripts/vps/vps_manager.py --upload-data & pause & goto vpsmenu
if "%vpschoice%"=="26" goto sync_data_files
if "%vpschoice%"=="27" goto view_data_contents
if "%vpschoice%"=="28" goto mainmenu
goto vpsmenu

:sync_data_files
echo.
echo Syncing specific data files...
echo Which files would you like to sync?
echo 1. All data files
echo 2. Only daily verses files
echo 3. Only questions file
echo 4. Only bot state file
echo 5. Back to VPS Menu
echo.
set /p syncchoice="Enter your choice (1-5): "
if "%syncchoice%"=="1" goto sync_all_data
if "%syncchoice%"=="2" goto sync_verses
if "%syncchoice%"=="3" goto sync_questions
if "%syncchoice%"=="4" goto sync_state
if "%syncchoice%"=="5" goto vpsmenu
goto sync_data_files

:sync_all_data
echo.
echo Syncing all data files...
python scripts/vps/vps_manager.py --download-data
echo.
pause
goto vpsmenu

:sync_verses
echo.
echo Syncing daily verses files...
echo Downloading daily_verses_pool.json and daily_verses_queue.json...
python scripts/vps/vps_manager.py --download-data
echo.
pause
goto vpsmenu

:sync_questions
echo.
echo Syncing questions file...
echo Downloading quran_questions.json...
python scripts/vps/vps_manager.py --download-data
echo.
pause
goto vpsmenu

:sync_state
echo.
echo Syncing bot state file...
echo Downloading bot_state.json...
python scripts/vps/vps_manager.py --download-data
echo.
pause
goto vpsmenu

:view_data_contents
echo.
echo Viewing data directory contents...
python scripts/vps/vps_manager.py --execute-command "ls -la /home/QuranAudioBot/data/"
echo.
pause
goto vpsmenu

:quickactions
cls
echo.
echo ========== Quick Actions ==========
echo 1. Quick VPS Status Check
echo 2. Quick Local Bot Start
echo 3. Quick VPS Bot Restart
echo 4. Quick Log Download
echo 5. Quick Backup Creation
echo 6. Back to Main Menu
echo.
set /p quickchoice="Enter your choice (1-6): "
if "%quickchoice%"=="1" goto quick_status
if "%quickchoice%"=="2" goto quick_local_start
if "%quickchoice%"=="3" goto quick_vps_restart
if "%quickchoice%"=="4" goto quick_log_download
if "%quickchoice%"=="5" goto quick_backup
if "%quickchoice%"=="6" goto mainmenu
goto quickactions

:quick_status
echo.
echo Checking VPS bot status...
python scripts/vps/vps_manager.py --get-bot-status
echo.
pause
goto quickactions

:quick_local_start
echo.
echo Starting local bot with virtual environment...
call .venv\Scripts\activate && start python run.py
echo Bot started in background.
echo.
pause
goto quickactions

:quick_vps_restart
echo.
echo Restarting VPS bot...
python scripts/vps/vps_manager.py --restart-bot
echo.
pause
goto quickactions

:quick_log_download
echo.
echo Downloading latest logs...
python scripts/vps/vps_manager.py --download-logs
echo.
pause
goto quickactions

:quick_backup
echo.
echo Creating backup...
python scripts/vps/vps_manager.py --create-backup
echo.
pause
goto quickactions

:healthcheck
cls
echo.
echo ========== System Health Check ==========
echo 1. Check Local Environment
echo 2. Check VPS Connection
echo 3. Check Dependencies
echo 4. Check Data Files
echo 5. Full System Check
echo 6. Back to Main Menu
echo.
set /p healthchoice="Enter your choice (1-6): "
if "%healthchoice%"=="1" goto check_local_env
if "%healthchoice%"=="2" goto check_vps_conn
if "%healthchoice%"=="3" goto check_deps
if "%healthchoice%"=="4" goto check_data
if "%healthchoice%"=="5" goto full_check
if "%healthchoice%"=="6" goto mainmenu
goto healthcheck

:check_local_env
echo.
echo Checking local environment...
echo Checking virtual environment...
if exist ".venv\Scripts\activate" (
    echo ✅ Virtual environment exists
    call .venv\Scripts\activate && python --version
) else (
    echo ❌ Virtual environment not found
)
echo.
echo Checking Python installation...
python --version
echo.
pause
goto healthcheck

:check_vps_conn
echo.
echo Testing VPS connection...
python scripts/vps/vps_manager.py --check-connection
echo.
pause
goto healthcheck

:check_deps
echo.
echo Checking dependencies in virtual environment...
call .venv\Scripts\activate && pip list | findstr -i "discord"
echo.
pause
goto healthcheck

:check_data
echo.
echo Checking data files...
if exist "data\daily_verses_pool.json" echo ✅ daily_verses_pool.json exists
if exist "data\daily_verses_queue.json" echo ✅ daily_verses_queue.json exists
if exist "data\quran_questions.json" echo ✅ quran_questions.json exists
if exist "data\bot_state.json" echo ✅ bot_state.json exists
echo.
pause
goto healthcheck

:full_check
echo.
echo Running full system check...
echo.
echo 1. Local Environment:
call :check_local_env
echo.
echo 2. VPS Connection:
call :check_vps_conn
echo.
echo 3. Dependencies:
call :check_deps
echo.
echo 4. Data Files:
call :check_data
echo.
echo Full check complete!
pause
goto healthcheck

:exit
echo.
echo Goodbye!
exit /b 0 