@echo off
echo Validating MP3 files...

REM Create temporary PowerShell script
echo $ErrorActionPreference = 'Stop' > "%TEMP%\validate_mp3s.ps1"
echo Write-Host 'Checking for FFmpeg...' -ForegroundColor Cyan >> "%TEMP%\validate_mp3s.ps1"
echo $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue >> "%TEMP%\validate_mp3s.ps1"
echo if (-not $ffmpeg) { >> "%TEMP%\validate_mp3s.ps1"
echo     Write-Host 'FFmpeg not found! Please run check_and_update_ffmpeg.bat first.' -ForegroundColor Red >> "%TEMP%\validate_mp3s.ps1"
echo     Write-Host 'Or install FFmpeg manually and add it to your system PATH.' -ForegroundColor Yellow >> "%TEMP%\validate_mp3s.ps1"
echo     Read-Host 'Press Enter to exit' >> "%TEMP%\validate_mp3s.ps1"
echo     exit 1 >> "%TEMP%\validate_mp3s.ps1"
echo } >> "%TEMP%\validate_mp3s.ps1"
echo Write-Host ('FFmpeg found: ' + $ffmpeg.Source) -ForegroundColor Green >> "%TEMP%\validate_mp3s.ps1"
echo $audioDir = '../../audio' >> "%TEMP%\validate_mp3s.ps1"
echo $logFile = 'bad_mp3s.txt' >> "%TEMP%\validate_mp3s.ps1"
echo $badCount = 0 >> "%TEMP%\validate_mp3s.ps1"
echo $checkedCount = 0 >> "%TEMP%\validate_mp3s.ps1"
echo if (!(Test-Path $audioDir)) { >> "%TEMP%\validate_mp3s.ps1"
echo     Write-Host ('Audio directory not found: ' + $audioDir) -ForegroundColor Red >> "%TEMP%\validate_mp3s.ps1"
echo     exit 1 >> "%TEMP%\validate_mp3s.ps1"
echo } >> "%TEMP%\validate_mp3s.ps1"
echo if (Test-Path $logFile) { Remove-Item $logFile } >> "%TEMP%\validate_mp3s.ps1"
echo Write-Host ('Checking all MP3 files in ' + $audioDir + '...') -ForegroundColor Cyan >> "%TEMP%\validate_mp3s.ps1"
echo Get-ChildItem -Path $audioDir -Filter *.mp3 ^| ForEach-Object { >> "%TEMP%\validate_mp3s.ps1"
echo     $file = $_.FullName >> "%TEMP%\validate_mp3s.ps1"
echo     $checkedCount++ >> "%TEMP%\validate_mp3s.ps1"
echo     $ffmpegResult = ffmpeg -v error -i $file -f null - 2^>^&1 >> "%TEMP%\validate_mp3s.ps1"
echo     if ($LASTEXITCODE -ne 0) { >> "%TEMP%\validate_mp3s.ps1"
echo         $badCount++ >> "%TEMP%\validate_mp3s.ps1"
echo         Add-Content -Path $logFile -Value ($file + '`n' + $ffmpegResult + '`n') >> "%TEMP%\validate_mp3s.ps1"
echo         Write-Host ('Corrupt: ' + $file) -ForegroundColor Red >> "%TEMP%\validate_mp3s.ps1"
echo     } else { >> "%TEMP%\validate_mp3s.ps1"
echo         Write-Host ('OK: ' + $file) -ForegroundColor Green >> "%TEMP%\validate_mp3s.ps1"
echo     } >> "%TEMP%\validate_mp3s.ps1"
echo } >> "%TEMP%\validate_mp3s.ps1"
echo Write-Host ('Checked ' + $checkedCount + ' files. Bad files: ' + $badCount) -ForegroundColor Yellow >> "%TEMP%\validate_mp3s.ps1"
echo if ($badCount -gt 0) { >> "%TEMP%\validate_mp3s.ps1"
echo     Write-Host ('See ' + $logFile + ' for details.') -ForegroundColor Yellow >> "%TEMP%\validate_mp3s.ps1"
echo } >> "%TEMP%\validate_mp3s.ps1"
echo Read-Host 'Press Enter to exit' >> "%TEMP%\validate_mp3s.ps1"

REM Run the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\validate_mp3s.ps1"

REM Clean up
del "%TEMP%\validate_mp3s.ps1" 2>nul 