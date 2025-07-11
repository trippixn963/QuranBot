# VPS Configuration Template

Before deploying QuranBot to your VPS, you need to configure these environment variables:

## Required Environment Variables

Set these variables in your shell before running deployment scripts:

```bash
# Your VPS IP address
export VPS_IP="your.vps.ip.address"

# VPS user (usually 'root' or your username)
export VPS_USER="root"

# Target path on VPS (optional, defaults to /opt/DiscordBots/QuranBot)
export VPS_PATH="/opt/DiscordBots/QuranBot"

# Local project path (optional, defaults to current directory)
export LOCAL_PROJECT_PATH="/path/to/your/QuranBot"

# VPS host for log syncing (optional)
export VPS_HOST="root@your.vps.ip.address"
```

## Quick Setup

1. Copy this template and fill in your values:
```bash
export VPS_IP="YOUR_VPS_IP_HERE"
export VPS_USER="root"
```

2. Run the deployment script:
```bash
cd vps/deployment
./deploy-to-discordbots.sh
```

## Example

```bash
export VPS_IP="192.168.1.100"
export VPS_USER="ubuntu"
export VPS_PATH="/home/ubuntu/bots/QuranBot"

./deploy-to-discordbots.sh
``` 