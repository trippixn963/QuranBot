# QuranBot VPS Manager - PowerShell Script
# VPS Configuration
$VPS_IP = "159.89.90.90"
$VPS_USER = "root"
$SSH_KEY = "C:\Users\hanna\Documents\QuranBot\quranbot_key"
$BOT_DIR = "/home/QuranAudioBot"
$LOCAL_PROJECT = "C:\Users\hanna\Documents\QuranBot"

function Show-Menu {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "    QuranBot VPS Manager" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Choose an action:" -ForegroundColor White
    Write-Host "1. Check SSH Connection" -ForegroundColor Green
    Write-Host "2. Get Bot Status" -ForegroundColor Green
    Write-Host "3. Start Bot" -ForegroundColor Green
    Write-Host "4. Stop Bot" -ForegroundColor Green
    Write-Host "5. Restart Bot" -ForegroundColor Green
    Write-Host "6. Deploy Bot (Pull & Restart)" -ForegroundColor Green
    Write-Host "7. View Logs" -ForegroundColor Green
    Write-Host "8. Upload Audio Files" -ForegroundColor Green
    Write-Host "9. Create Backup" -ForegroundColor Green
    Write-Host "10. Setup Environment" -ForegroundColor Green
    Write-Host "11. Exit" -ForegroundColor Red
    Write-Host ""
}

function Test-SSHConnection {
    Write-Host "Testing SSH connection..." -ForegroundColor Yellow
    try {
        $result = ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "echo 'Connection successful'" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ SSH connection successful!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ SSH connection failed!" -ForegroundColor Red
            Write-Host "Error: $result" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ SSH connection failed!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        return $false
    }
}

function Get-BotStatus {
    Write-Host "Getting bot status..." -ForegroundColor Yellow
    
    # Check if bot is running
    $running = ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "ps aux | grep 'python run.py' | grep -v grep" 2>&1
    if ($LASTEXITCODE -eq 0 -and $running) {
        Write-Host "✅ Bot is running!" -ForegroundColor Green
    } else {
        Write-Host "🔴 Bot is not running!" -ForegroundColor Red
    }
    
    # Get recent logs
    Write-Host "`nRecent logs:" -ForegroundColor Yellow
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "tail -10 ${BOT_DIR}/bot.log" 2>&1
}

function Start-Bot {
    Write-Host "Starting QuranBot..." -ForegroundColor Yellow
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && pkill -f 'python run.py' && sleep 2 && source venv/bin/activate && nohup python run.py > bot.log 2>&1 &" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Bot started!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to start bot!" -ForegroundColor Red
    }
}

function Stop-Bot {
    Write-Host "Stopping QuranBot..." -ForegroundColor Yellow
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "pkill -f 'python run.py'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Bot stopped!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Bot may not have been running or failed to stop." -ForegroundColor Yellow
    }
}

function Restart-Bot {
    Write-Host "Restarting QuranBot..." -ForegroundColor Yellow
    Stop-Bot
    Start-Sleep -Seconds 2
    Start-Bot
}

function Deploy-Bot {
    Write-Host "Deploying QuranBot..." -ForegroundColor Yellow
    
    Write-Host "Pulling latest changes..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && git pull origin main" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to pull latest changes!" -ForegroundColor Red
        return
    }
    
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && source venv/bin/activate && pip install -r requirements.txt" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Warning: Some dependencies may not have installed properly." -ForegroundColor Yellow
    }
    
    Write-Host "Restarting bot..." -ForegroundColor Cyan
    Restart-Bot
}

function View-Logs {
    $lines = Read-Host "Number of log lines to show (default 50)"
    if (-not $lines -or $lines -notmatch '^\d+$') {
        $lines = 50
    }
    
    Write-Host "Showing last $lines lines of logs:" -ForegroundColor Yellow
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "tail -$lines ${BOT_DIR}/bot.log" 2>&1
}

function Upload-AudioFiles {
    $audioPath = Read-Host "Enter local audio files path"
    if (-not $audioPath -or -not (Test-Path $audioPath)) {
        Write-Host "❌ Invalid path provided!" -ForegroundColor Red
        return
    }
    
    Write-Host "Uploading audio files..." -ForegroundColor Yellow
    scp -i $SSH_KEY -r "${audioPath}\*" "${VPS_USER}@${VPS_IP}:${BOT_DIR}/audio/" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Audio files uploaded successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to upload audio files!" -ForegroundColor Red
    }
}

function New-Backup {
    Write-Host "Creating backup..." -ForegroundColor Yellow
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && tar -czf backup_${timestamp}.tar.gz --exclude=venv --exclude=*.log --exclude=__pycache__ ." 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backup created: backup_${timestamp}.tar.gz" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create backup!" -ForegroundColor Red
    }
}

function Setup-Environment {
    Write-Host "Setting up bot environment..." -ForegroundColor Yellow
    
    Write-Host "Cloning repository..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "if [ ! -d '${BOT_DIR}' ]; then git clone https://github.com/yourusername/QuranBot.git ${BOT_DIR}; fi" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to clone repository!" -ForegroundColor Red
        return
    }
    
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && python3 -m venv venv" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment!" -ForegroundColor Red
        return
    }
    
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && source venv/bin/activate && pip install -r requirements.txt" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️ Warning: Some dependencies may not have installed properly." -ForegroundColor Yellow
    }
    
    Write-Host "Creating directories..." -ForegroundColor Cyan
    ssh -i $SSH_KEY "${VPS_USER}@${VPS_IP}" "cd ${BOT_DIR} && mkdir -p logs audio" 2>&1
    
    Write-Host "✅ Environment setup completed!" -ForegroundColor Green
}

# Main menu loop
do {
    Show-Menu
    $choice = Read-Host "Enter your choice (1-11)"
    
    switch ($choice) {
        "1" { Test-SSHConnection }
        "2" { Get-BotStatus }
        "3" { Start-Bot }
        "4" { Stop-Bot }
        "5" { Restart-Bot }
        "6" { Deploy-Bot }
        "7" { View-Logs }
        "8" { Upload-AudioFiles }
        "9" { New-Backup }
        "10" { Setup-Environment }
        "11" { 
            Write-Host "👋 Goodbye!" -ForegroundColor Yellow
            exit 
        }
        default { 
            Write-Host "❌ Invalid choice!" -ForegroundColor Red
        }
    }
    
    if ($choice -ne "11") {
        Read-Host "`nPress Enter to continue"
    }
} while ($choice -ne "11") 