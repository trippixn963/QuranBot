@echo off
setlocal enabledelayedexpansion

title QuranBot Manager

:mainmenu
cls
echo.
echo ========================================
echo           QuranBot Manager
========================================
echo.
echo 1. Local Tools
Echo 2. VPS Manager
Echo 3. Exit
echo.
set /p mainchoice="Enter your choice (1-3): "

if "%mainchoice%"=="1" goto localtools
if "%mainchoice%"=="2" goto vpsmenu
if "%mainchoice%"=="3" goto exit

goto mainmenu

:localtools
cls
echo.
echo ========== Local Tools ==========
echo 1. Backup Data
echo 2. Check FFmpeg Status
echo 3. Update FFmpeg
echo 4. Validate MP3 Files
echo 5. Back to Main Menu
echo.
set /p choice="Enter your choice (1-5): "
if "%choice%"=="1" goto backup
if "%choice%"=="2" goto check_ffmpeg
if "%choice%"=="3" goto update_ffmpeg
if "%choice%"=="4" goto validate_mp3s
if "%choice%"=="5" goto mainmenu
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
echo 26. Back to Main Menu
echo.
set /p vpschoice="Enter your choice (1-26): "

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
if "%vpschoice%"=="26" goto mainmenu
goto vpsmenu

:exit
echo.
echo Goodbye!
exit /b 0 