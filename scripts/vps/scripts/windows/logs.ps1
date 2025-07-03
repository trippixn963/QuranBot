# QuranBot VPS Management - Log Viewer
# This script displays and manages logs from the QuranBot service

# Import configuration
$configPath = Join-Path $PSScriptRoot "..\..\config\vps_config.json"
$config = Get-Content $configPath | ConvertFrom-Json

# Set up SSH command
$sshKey = $config.vps.ssh_key
$sshUser = $config.vps.user
$sshHost = $config.vps.host
$serviceName = $config.bot.service_name
$logPath = $config.bot.log_path

# Parse command line arguments
param(
    [string]$action = "view",  # view, download, analyze, cleanup
    [string]$date = "",        # YYYY-MM-DD format
    [int]$lines = 50,         # Number of lines for view/analyze
    [int]$days = 30           # Days for cleanup
)

function Show-Menu {
    Write-Host "`n📋 Log Management Menu:" -ForegroundColor Cyan
    Write-Host "1. View Recent Logs"
    Write-Host "2. Download Logs"
    Write-Host "3. Analyze Logs"
    Write-Host "4. Clean Up Old Logs"
    Write-Host "0. Exit"
    
    $choice = Read-Host "`nEnter choice (0-4)"
    return $choice
}

function View-Logs {
    param([int]$lines)
    Write-Host "`n📜 Showing last $lines lines of logs..." -ForegroundColor Cyan
    
    # Use journalctl for service logs
    ssh -i $sshKey "$sshUser@$sshHost" "journalctl -u $serviceName -n $lines --no-pager" | ForEach-Object {
        if ($_ -match "error|exception|fail" -i) {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "warning" -i) {
            Write-Host $_ -ForegroundColor Yellow
        } elseif ($_ -match "success|completed" -i) {
            Write-Host $_ -ForegroundColor Green
        } else {
            Write-Host $_
        }
    }
}

function Download-Logs {
    param([string]$date)
    
    if (-not $date) {
        $date = Get-Date -Format "yyyy-MM-dd"
    }
    
    Write-Host "`n📥 Downloading logs for $date..." -ForegroundColor Cyan
    
    # Create local logs directory
    $localLogDir = Join-Path $PSScriptRoot "..\..\logs"
    New-Item -ItemType Directory -Force -Path $localLogDir | Out-Null
    
    # Download log file
    $logFile = "$date.log"
    $localPath = Join-Path $localLogDir $logFile
    
    scp -i $sshKey "$sshUser@$sshHost`:$logPath/$logFile" $localPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Logs downloaded to: $localPath" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Failed to download logs for $date" -ForegroundColor Red
    }
}

function Analyze-Logs {
    param(
        [string]$date,
        [int]$lines
    )
    
    if (-not $date) {
        $date = Get-Date -Format "yyyy-MM-dd"
    }
    
    Write-Host "`n🔍 Analyzing logs for $date..." -ForegroundColor Cyan
    
    # Get log statistics
    $stats = ssh -i $sshKey "$sshUser@$sshHost" @"
        echo "Log Analysis for $date";
        echo "==========================================";
        echo;
        echo "Error Count:";
        journalctl -u $serviceName --since "$date 00:00:00" --until "$date 23:59:59" | grep -i error | wc -l;
        echo;
        echo "Warning Count:";
        journalctl -u $serviceName --since "$date 00:00:00" --until "$date 23:59:59" | grep -i warning | wc -l;
        echo;
        echo "Most Common Errors:";
        journalctl -u $serviceName --since "$date 00:00:00" --until "$date 23:59:59" | grep -i error | sort | uniq -c | sort -nr | head -5;
"@
    
    Write-Host $stats
    
    # Generate report
    $reportDir = Join-Path $PSScriptRoot "..\..\logs\analysis"
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
    
    $reportFile = Join-Path $reportDir "analysis_$date.txt"
    $stats | Out-File $reportFile -Encoding UTF8
    
    Write-Host "`n📋 Analysis report saved to: $reportFile" -ForegroundColor Green
}

function Cleanup-Logs {
    param([int]$days)
    
    Write-Host "`n🧹 Cleaning up logs older than $days days..." -ForegroundColor Cyan
    
    # Confirm action
    $confirm = Read-Host "⚠️ This will delete old logs. Continue? (y/N)"
    if ($confirm -ne "y") {
        Write-Host "`n❌ Cleanup cancelled" -ForegroundColor Yellow
        return
    }
    
    # Delete old logs
    $result = ssh -i $sshKey "$sshUser@$sshHost" "find $logPath -name '*.log' -type f -mtime +$days -delete"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Old logs cleaned up successfully" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Failed to clean up logs" -ForegroundColor Red
        Write-Host $result
    }
}

# Main menu loop
if ($action -eq "view") {
    while ($true) {
        $choice = Show-Menu
        
        switch ($choice) {
            "0" { 
                Write-Host "`n👋 Goodbye!" -ForegroundColor Cyan
                exit 
            }
            "1" { 
                $lines = Read-Host "Enter number of lines to show (default: 50)"
                if (-not $lines) { $lines = 50 }
                View-Logs -lines $lines
            }
            "2" {
                $date = Read-Host "Enter date (YYYY-MM-DD) or press Enter for today"
                Download-Logs -date $date
            }
            "3" {
                $date = Read-Host "Enter date (YYYY-MM-DD) or press Enter for today"
                $lines = Read-Host "Enter number of lines to analyze (default: 1000)"
                if (-not $lines) { $lines = 1000 }
                Analyze-Logs -date $date -lines $lines
            }
            "4" {
                $days = Read-Host "Enter days (default: 30)"
                if (-not $days) { $days = 30 }
                Cleanup-Logs -days $days
            }
            default {
                Write-Host "`n❌ Invalid choice" -ForegroundColor Red
            }
        }
        
        Write-Host "`nPress any key to continue..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
} else {
    # Direct command execution
    switch ($action) {
        "view" { View-Logs -lines $lines }
        "download" { Download-Logs -date $date }
        "analyze" { Analyze-Logs -date $date -lines $lines }
        "cleanup" { Cleanup-Logs -days $days }
        default {
            Write-Host "❌ Invalid action: $action" -ForegroundColor Red
            Write-Host "Valid actions: view, download, analyze, cleanup"
        }
    }
} 