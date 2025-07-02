@echo off
title QuranBot Log Manager
color 0A

:menu
cls
echo.
echo ========================================
echo           QuranBot Log Manager
echo ========================================
echo.
echo 1. 🔄 Stream logs (real-time)
echo 2. 📥 Download latest logs
echo 3. 🔄 Auto-sync logs (continuous)
echo 4. 📋 View local logs
echo 5. 🗑️  Clear local logs
echo 6. ❌ Exit
echo.
echo ========================================
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto stream
if "%choice%"=="2" goto download
if "%choice%"=="3" goto sync
if "%choice%"=="4" goto view
if "%choice%"=="5" goto clear
if "%choice%"=="6" goto exit
goto menu

:stream
cls
echo 🔄 Streaming QuranBot logs from VPS...
echo Press Ctrl+C to stop streaming
echo.
ssh -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90 "tail -f /opt/quranbot/logs/quranbot.log"
pause
goto menu

:download
cls
echo 📥 Downloading QuranBot logs from VPS...
echo.
if not exist "logs" mkdir logs
scp -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90:/opt/quranbot/logs/quranbot.log logs/quranbot_vps.log
echo ✅ Logs downloaded to logs/quranbot_vps.log
echo.
pause
goto menu

:sync
cls
echo 🔄 Auto-syncing QuranBot logs from VPS...
echo This will sync logs every 30 seconds
echo Press Ctrl+C to stop
echo.
if not exist "logs" mkdir logs
:syncloop
scp -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90:/opt/quranbot/logs/quranbot.log logs/quranbot_vps.log >nul 2>&1
echo [%date% %time%] ✅ Logs synced
timeout /t 30 /nobreak >nul
goto syncloop

:view
cls
echo 📋 Local log files:
echo.
if exist "logs" (
    dir logs /b
    echo.
    set /p viewlog="Enter log filename to view (or press Enter to skip): "
    if not "%viewlog%"=="" (
        if exist "logs\%viewlog%" (
            notepad logs\%viewlog%
        ) else (
            echo ❌ File not found!
            pause
        )
    )
) else (
    echo No logs directory found.
)
pause
goto menu

:clear
cls
echo 🗑️ Clearing local logs...
if exist "logs" (
    del /q logs\*.*
    echo ✅ Local logs cleared
) else (
    echo No logs to clear
)
pause
goto menu

:exit
echo 👋 Goodbye!
exit 