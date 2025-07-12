#!/bin/bash
# =============================================================================
# QuranBot One-Command VPS Deployment Script
# =============================================================================
# This script automates the complete deployment of QuranBot on a VPS
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/QuranBot/main/vps/deployment/deploy.sh | bash
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
BOT_DIR="/opt/QuranBot"
GITHUB_REPO="https://github.com/yourusername/QuranBot.git"  # Update this

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

log_header "QuranBot VPS Deployment"

# Update system
log_info "Updating system packages..."
apt update && apt upgrade -y

# Install system dependencies
log_info "Installing system dependencies..."
apt install -y python3 python3-pip python3-venv git ffmpeg curl htop ufw

# Create bot directory
log_info "Creating bot directory..."
mkdir -p "$BOT_DIR"
cd "$BOT_DIR"

# Clone repository
log_info "Cloning QuranBot repository..."
git clone "$GITHUB_REPO" .

# Create virtual environment
log_info "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
log_info "Installing Python dependencies..."
pip install -r requirements.txt

# Install dashboard dependencies
log_info "Installing dashboard dependencies..."
pip install -r vps/web_dashboard/requirements.txt

# Make scripts executable
log_info "Setting up scripts..."
chmod +x vps/scripts/manage_quranbot.sh

# Setup systemd services
log_info "Installing systemd services..."
cp vps/systemd/quranbot.service /etc/systemd/system/
cp vps/systemd/quranbot-dashboard.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable quranbot.service
systemctl enable quranbot-dashboard.service

# Create directories
log_info "Creating necessary directories..."
mkdir -p logs data backup/temp

# Setup firewall
log_info "Configuring firewall..."
ufw allow 22  # SSH
ufw allow 8080  # Dashboard
ufw --force enable

# Create environment file template
log_info "Creating environment file template..."
cat > config/.env << 'EOF'
# QuranBot Configuration
# ======================
# Fill in these values with your Discord bot settings

# Discord Bot Token (REQUIRED)
DISCORD_TOKEN=your_discord_bot_token_here

# Discord Server Settings (REQUIRED)
GUILD_ID=your_discord_server_id
TARGET_CHANNEL_ID=voice_channel_id_for_audio
PANEL_CHANNEL_ID=text_channel_id_for_control_panel
LOGS_CHANNEL_ID=text_channel_id_for_logs
DEVELOPER_ID=your_discord_user_id

# Audio Settings
FFMPEG_PATH=/usr/bin/ffmpeg
DEFAULT_RECITER=Saad Al Ghamdi
DEFAULT_SHUFFLE=false
DEFAULT_LOOP=false

# Optional Settings
DAILY_VERSE_CHANNEL_ID=0
PANEL_ACCESS_ROLE_ID=0
EOF

# Create shell aliases
log_info "Creating shell aliases..."
vps/scripts/manage_quranbot.sh aliases

log_success "QuranBot deployment completed successfully!"
echo
log_header "Next Steps"
echo "1. Configure your Discord bot settings:"
echo "   nano $BOT_DIR/config/.env"
echo
echo "2. Start the bot:"
echo "   qb-start"
echo
echo "3. Check status:"
echo "   qb-status"
echo
echo "4. Start web dashboard (24/7 service):"
echo "   qb-dashboard"
echo
echo "5. Access dashboard at:"
echo "   http://$(curl -s ifconfig.me):8080"
echo
echo "6. Dashboard will auto-start on boot and restart on failure"
echo
log_header "Available Commands"
echo "qb-status    - Show bot status"
echo "qb-start     - Start bot"
echo "qb-stop      - Stop bot"
echo "qb-restart   - Restart bot"
echo "qb-logs      - Show logs"
echo "qb-errors    - Show error logs"
echo "qb-update    - Update bot"
echo "qb-dashboard - Start web dashboard"
echo
log_warning "Remember to configure your .env file before starting the bot!"
log_success "Deployment complete! 🎉" 