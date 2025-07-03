# QuranBot VPS Management - Restart Bot
# This script restarts the QuranBot service on the VPS

# Import configuration
$configPath = Join-Path $PSScriptRoot "..\..\config\vps_config.json"
$config = Get-Content $configPath | ConvertFrom-Json

# Set up SSH command
$sshKey = $config.vps.ssh_key
$sshUser = $config.vps.user
$sshHost = $config.vps.host
$serviceName = $config.bot.service_name

Write-Host "`n🔄 Restarting QuranBot..." -ForegroundColor Cyan

# Connect to VPS and restart service
ssh -i $sshKey "$sshUser@$sshHost" "sudo systemctl restart $serviceName"

# Wait a moment for the service to restart
Start-Sleep -Seconds 2

# Check status
$status = ssh -i $sshKey "$sshUser@$sshHost" "systemctl status $serviceName"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Bot restarted successfully!" -ForegroundColor Green
    
    # Show status details
    Write-Host "`n📊 Current Status:" -ForegroundColor Cyan
    $status | ForEach-Object {
        if ($_ -match "Active:") {
            Write-Host $_ -ForegroundColor Green
        } elseif ($_ -match "Memory:|CPU:") {
            Write-Host $_ -ForegroundColor Yellow
        } else {
            Write-Host $_
        }
    }
} else {
    Write-Host "`n❌ Failed to restart bot" -ForegroundColor Red
    Write-Host "`nError details:" -ForegroundColor Yellow
    Write-Host $status
}

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 