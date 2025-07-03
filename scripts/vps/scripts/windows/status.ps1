# QuranBot VPS Management - Status Check
# This script checks the status of the QuranBot service on the VPS

# Import configuration
$configPath = Join-Path $PSScriptRoot "..\..\config\vps_config.json"
$config = Get-Content $configPath | ConvertFrom-Json

# Set up SSH command
$sshKey = $config.vps.ssh_key
$sshUser = $config.vps.user
$sshHost = $config.vps.host
$serviceName = $config.bot.service_name

Write-Host "`n📊 Checking QuranBot Status..." -ForegroundColor Cyan

# Get service status
$status = ssh -i $sshKey "$sshUser@$sshHost" "systemctl status $serviceName"

# Get system resources
$resources = ssh -i $sshKey "$sshUser@$sshHost" @"
    echo "Memory Usage:";
    free -h | grep Mem;
    echo;
    echo "CPU Usage:";
    top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}';
    echo;
    echo "Disk Usage:";
    df -h / | tail -n 1;
"@

Write-Host "`n📊 Service Status:" -ForegroundColor Cyan
$status | ForEach-Object {
    if ($_ -match "Active:.*running") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "Active:.*dead") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "Memory:|CPU:") {
        Write-Host $_ -ForegroundColor Yellow
    } else {
        Write-Host $_
    }
}

Write-Host "`n💻 System Resources:" -ForegroundColor Cyan
$resources | ForEach-Object {
    if ($_ -match "Memory Usage:|CPU Usage:|Disk Usage:") {
        Write-Host "`n$_" -ForegroundColor Yellow
    } else {
        Write-Host $_
    }
}

# Check logs for recent errors
Write-Host "`n🔍 Recent Errors:" -ForegroundColor Cyan
$errors = ssh -i $sshKey "$sshUser@$sshHost" "journalctl -u $serviceName -n 50 --no-pager | grep -i error"
if ($LASTEXITCODE -eq 0) {
    $errors | ForEach-Object {
        Write-Host "❌ $_" -ForegroundColor Red
    }
} else {
    Write-Host "✅ No recent errors found" -ForegroundColor Green
}

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 