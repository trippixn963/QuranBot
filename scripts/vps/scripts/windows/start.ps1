# QuranBot VPS Management - Start Bot
# This script starts the QuranBot service on the VPS

# Import configuration
$configPath = Join-Path $PSScriptRoot "..\..\config\vps_config.json"
$config = Get-Content $configPath | ConvertFrom-Json

# Set up SSH command
$sshKey = $config.vps.ssh_key
$sshUser = $config.vps.user
$sshHost = $config.vps.host
$serviceName = $config.bot.service_name

Write-Host "`n🚀 Starting QuranBot..." -ForegroundColor Cyan

# Connect to VPS and start service
ssh -i $sshKey "$sshUser@$sshHost" "sudo systemctl start $serviceName"

# Check status
$status = ssh -i $sshKey "$sshUser@$sshHost" "systemctl status $serviceName"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Bot started successfully!" -ForegroundColor Green
    
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
    Write-Host "`n❌ Failed to start bot" -ForegroundColor Red
    Write-Host "`nError details:" -ForegroundColor Yellow
    Write-Host $status
}

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 