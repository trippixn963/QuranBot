@echo off
title QuranBot VPS Manager
color 0B

:menu
cls
echo.
echo ========================================
echo         QuranBot VPS Manager
echo ========================================
echo.
echo 📁 Bot Control:
echo   1. 🚀 Start Bot
echo   2. 🛑 Stop Bot  
echo   3. 🔄 Restart Bot
echo   4. 📊 Check Status
echo   5. ⬆️  Update Bot
echo.
echo 📋 Log Management:
echo   6. 🔄 Stream Logs (real-time)
echo   7. 📥 Download Logs
echo   8. 🔄 Auto-Sync Logs
echo   9. 📋 Log Manager
echo.
echo 🛠️  Utilities:
echo   10. 🔌 Connect to VPS
echo   11. 💀 Kill All Python
echo.
echo 12. ❌ Exit
echo.
echo ========================================
echo.

set /p choice="Enter your choice (1-12): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto update
if "%choice%"=="6" goto stream
if "%choice%"=="7" goto download
if "%choice%"=="8" goto sync
if "%choice%"=="9" goto logmanager
if "%choice%"=="10" goto connect
if "%choice%"=="11" goto kill
if "%choice%"=="12" goto exit
goto menu

:start
cls
echo 🚀 Starting QuranBot...
call scripts\vps\bot-control\start_bot.sh
pause
goto menu

:stop
cls
echo 🛑 Stopping QuranBot...
call scripts\vps\bot-control\stop_bot.sh
pause
goto menu

:restart
cls
echo 🔄 Restarting QuranBot...
call scripts\vps\bot-control\restart_bot.sh
pause
goto menu

:status
cls
echo 📊 Checking QuranBot status...
call scripts\vps\bot-control\status_bot.sh
pause
goto menu

:update
cls
echo ⬆️ Updating QuranBot...
call scripts\vps\bot-control\update_bot.sh
pause
goto menu

:stream
cls
echo 🔄 Streaming logs...
call scripts\vps\log-management\stream_logs.bat
goto menu

:download
cls
echo 📥 Downloading logs...
call scripts\vps\log-management\download_logs.bat
goto menu

:sync
cls
echo 🔄 Auto-syncing logs...
call scripts\vps\log-management\sync_logs.bat
goto menu

:logmanager
cls
echo 📋 Opening log manager...
call scripts\vps\log-management\manage_logs.bat
goto menu

:connect
cls
echo 🔌 Connecting to VPS...
call scripts\vps\utilities\connect_vps.sh
pause
goto menu

:kill
cls
echo 💀 Killing all Python processes...
call scripts\vps\utilities\kill_all_python.sh
pause
goto menu

:exit
echo 👋 Goodbye!
exit 