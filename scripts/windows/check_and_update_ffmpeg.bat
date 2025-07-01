@echo off
echo Checking for FFmpeg...

REM Create temporary PowerShell script
echo $ErrorActionPreference = 'Stop' > "%TEMP%\check_ffmpeg.ps1"
echo Write-Host 'Checking for FFmpeg...' -ForegroundColor Cyan >> "%TEMP%\check_ffmpeg.ps1"
echo $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue >> "%TEMP%\check_ffmpeg.ps1"
echo if ($ffmpeg) { >> "%TEMP%\check_ffmpeg.ps1"
echo   $version = ffmpeg -version ^| Select-Object -First 1 >> "%TEMP%\check_ffmpeg.ps1"
echo   Write-Host ('FFmpeg found: ' + $ffmpeg.Source) -ForegroundColor Green >> "%TEMP%\check_ffmpeg.ps1"
echo   Write-Host ('Version: ' + $version) -ForegroundColor Green >> "%TEMP%\check_ffmpeg.ps1"
echo   $update = Read-Host 'Do you want to update FFmpeg? (y/n)' >> "%TEMP%\check_ffmpeg.ps1"
echo   if ($update -ne 'y') { exit 0 } >> "%TEMP%\check_ffmpeg.ps1"
echo } >> "%TEMP%\check_ffmpeg.ps1"
echo Write-Host 'Downloading latest FFmpeg...' -ForegroundColor Cyan >> "%TEMP%\check_ffmpeg.ps1"
echo $ffmpegUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' >> "%TEMP%\check_ffmpeg.ps1"
echo $tempZip = "$env:TEMP\ffmpeg-latest.zip" >> "%TEMP%\check_ffmpeg.ps1"
echo Invoke-WebRequest -Uri $ffmpegUrl -OutFile $tempZip >> "%TEMP%\check_ffmpeg.ps1"
echo Expand-Archive -Path $tempZip -DestinationPath $env:TEMP -Force >> "%TEMP%\check_ffmpeg.ps1"
echo $ffmpegDir = Get-ChildItem -Path $env:TEMP -Directory ^| Where-Object { $_.Name -like 'ffmpeg*' } ^| Select-Object -First 1 >> "%TEMP%\check_ffmpeg.ps1"
echo if ($ffmpegDir) { >> "%TEMP%\check_ffmpeg.ps1"
echo   $binPath = Join-Path $ffmpegDir.FullName 'bin' >> "%TEMP%\check_ffmpeg.ps1"
echo   $env:PATH = "$binPath;$env:PATH" >> "%TEMP%\check_ffmpeg.ps1"
echo   Write-Host ('FFmpeg updated! Location: ' + $binPath) -ForegroundColor Green >> "%TEMP%\check_ffmpeg.ps1"
echo   ffmpeg -version ^| Select-Object -First 1 >> "%TEMP%\check_ffmpeg.ps1"
echo   Write-Host 'Add the bin path to your system PATH for permanent use.' -ForegroundColor Yellow >> "%TEMP%\check_ffmpeg.ps1"
echo } else { >> "%TEMP%\check_ffmpeg.ps1"
echo   Write-Host 'Failed to extract FFmpeg.' -ForegroundColor Red >> "%TEMP%\check_ffmpeg.ps1"
echo } >> "%TEMP%\check_ffmpeg.ps1"
echo Remove-Item $tempZip -ErrorAction SilentlyContinue >> "%TEMP%\check_ffmpeg.ps1"
echo Read-Host 'Press Enter to exit' >> "%TEMP%\check_ffmpeg.ps1"

REM Run the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\check_ffmpeg.ps1"

REM Clean up
del "%TEMP%\check_ffmpeg.ps1" 2>nul 