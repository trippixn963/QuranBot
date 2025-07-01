@echo off
echo Checking FFmpeg status...

REM Create temporary PowerShell script
echo Write-Host 'Checking FFmpeg installation...' -ForegroundColor Cyan > "%TEMP%\check_status.ps1"
echo $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue >> "%TEMP%\check_status.ps1"
echo if ($ffmpeg) { >> "%TEMP%\check_status.ps1"
echo     Write-Host 'FFmpeg is installed!' -ForegroundColor Green >> "%TEMP%\check_status.ps1"
echo     Write-Host ('Location: ' + $ffmpeg.Source) -ForegroundColor Green >> "%TEMP%\check_status.ps1"
echo     $version = ffmpeg -version ^| Select-Object -First 1 >> "%TEMP%\check_status.ps1"
echo     Write-Host ('Version: ' + $version) -ForegroundColor Green >> "%TEMP%\check_status.ps1"
echo } else { >> "%TEMP%\check_status.ps1"
echo     Write-Host 'FFmpeg is NOT installed or not in PATH.' -ForegroundColor Red >> "%TEMP%\check_status.ps1"
echo     Write-Host 'Please run check_and_update_ffmpeg.bat to install it.' -ForegroundColor Yellow >> "%TEMP%\check_status.ps1"
echo } >> "%TEMP%\check_status.ps1"
echo Write-Host '' >> "%TEMP%\check_status.ps1"
echo Write-Host 'System PATH entries:' -ForegroundColor Cyan >> "%TEMP%\check_status.ps1"
echo $env:PATH -split ';' ^| Where-Object { $_ -like '*ffmpeg*' } ^| ForEach-Object { Write-Host $_ -ForegroundColor Yellow } >> "%TEMP%\check_status.ps1"
echo Read-Host 'Press Enter to exit' >> "%TEMP%\check_status.ps1"

REM Run the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\check_status.ps1"

REM Clean up
del "%TEMP%\check_status.ps1" 2>nul 