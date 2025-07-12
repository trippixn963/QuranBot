#!/bin/bash
# =============================================================================
# Deploy QuranBot to DiscordBots/QuranBot Structure
# =============================================================================
# This script creates the proper directory structure on VPS and transfers all files
# Usage: ./deploy-to-discordbots.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# VPS Configuration
VPS_IP="159.89.90.90"
VPS_USER="root"
VPS_PATH="/opt/DiscordBots/QuranBot"
LOCAL_PROJECT_PATH="/Users/johnhamwi/Developer/QuranBot"

log_info "Starting deployment to DiscordBots/QuranBot structure..."
log_info "VPS: $VPS_USER@$VPS_IP"
log_info "Target Path: $VPS_PATH"

# Check if .env file exists locally
if [ ! -f "$LOCAL_PROJECT_PATH/config/.env" ]; then
    log_error ".env file not found at $LOCAL_PROJECT_PATH/config/.env"
    log_error "Please ensure your .env file is in the config/ directory"
    exit 1
fi

# Check if we can connect to VPS
log_info "Testing VPS connection..."
if ! ssh -o ConnectTimeout=10 "$VPS_USER@$VPS_IP" "echo 'Connection successful'" > /dev/null 2>&1; then
    log_error "Cannot connect to VPS at $VPS_USER@$VPS_IP"
    log_error "Please check your SSH configuration and VPS status"
    exit 1
fi
log_success "VPS connection verified"

# Create directory structure on VPS
log_info "Creating directory structure on VPS..."
ssh "$VPS_USER@$VPS_IP" << 'EOF'
# Create main directory structure
mkdir -p /opt/DiscordBots/QuranBot/{src,config,logs,audio,backup,data,images,tests,tools,vps_logs}

# Create subdirectories
mkdir -p /opt/DiscordBots/QuranBot/src/{bot,commands,utils,backup}
mkdir -p /opt/DiscordBots/QuranBot/vps_logs/{app_logs,system_logs}

# Set proper permissions
chown -R root:root /opt/DiscordBots/QuranBot
chmod -R 755 /opt/DiscordBots/QuranBot

echo "Directory structure created successfully"
EOF

log_success "Directory structure created on VPS"

# Transfer Python files and project structure
log_info "Transferring Python files and project structure..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='logs/*' \
    --exclude='vps_logs/*' \
    "$LOCAL_PROJECT_PATH/src/" "$VPS_USER@$VPS_IP:$VPS_PATH/src/"

log_success "Python source files transferred"

# Transfer configuration files
log_info "Transferring configuration files..."
rsync -avz --progress \
    "$LOCAL_PROJECT_PATH/config/" "$VPS_USER@$VPS_IP:$VPS_PATH/config/"

log_success "Configuration files transferred"

# Transfer main files
log_info "Transferring main project files..."
rsync -avz --progress \
    "$LOCAL_PROJECT_PATH/main.py" \
    "$LOCAL_PROJECT_PATH/requirements.txt" \
    "$LOCAL_PROJECT_PATH/pyproject.toml" \
    "$VPS_USER@$VPS_IP:$VPS_PATH/"

log_success "Main project files transferred"

# Transfer audio files
log_info "Transferring audio files..."
if [ -d "$LOCAL_PROJECT_PATH/audio" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/audio 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/audio/" "$VPS_USER@$VPS_IP:$VPS_PATH/audio/"
    log_success "Audio files transferred"
else
    log_warning "No audio files found to transfer"
fi

# Transfer images
log_info "Transferring images..."
if [ -d "$LOCAL_PROJECT_PATH/images" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/images 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/images/" "$VPS_USER@$VPS_IP:$VPS_PATH/images/"
    log_success "Images transferred"
else
    log_warning "No images found to transfer"
fi

# Transfer data files
log_info "Transferring data files..."
if [ -d "$LOCAL_PROJECT_PATH/data" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/data 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/data/" "$VPS_USER@$VPS_IP:$VPS_PATH/data/"
    log_success "Data files transferred"
else
    log_warning "No data files found to transfer"
fi

# Transfer backup files
log_info "Transferring backup files..."
if [ -d "$LOCAL_PROJECT_PATH/backup" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/backup 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/backup/" "$VPS_USER@$VPS_IP:$VPS_PATH/backup/"
    log_success "Backup files transferred"
else
    log_warning "No backup files found to transfer"
fi

# Transfer tests
log_info "Transferring test files..."
if [ -d "$LOCAL_PROJECT_PATH/tests" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/tests 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/tests/" "$VPS_USER@$VPS_IP:$VPS_PATH/tests/"
    log_success "Test files transferred"
else
    log_warning "No test files found to transfer"
fi

# Transfer tools
log_info "Transferring tool files..."
if [ -d "$LOCAL_PROJECT_PATH/tools" ] && [ "$(ls -A $LOCAL_PROJECT_PATH/tools 2>/dev/null)" ]; then
    rsync -avz --progress \
        "$LOCAL_PROJECT_PATH/tools/" "$VPS_USER@$VPS_IP:$VPS_PATH/tools/"
    log_success "Tool files transferred"
else
    log_warning "No tool files found to transfer"
fi

# Set up Python environment on VPS
log_info "Setting up Python environment on VPS..."
ssh "$VPS_USER@$VPS_IP" << EOF
cd $VPS_PATH

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo "Python dependencies installed"
else
    echo "No requirements.txt found"
fi

# Fix FFmpeg path for Linux
if [ -f config/.env ]; then
    # Update FFmpeg path for Linux
    sed -i 's|/opt/homebrew/bin/ffmpeg|/usr/bin/ffmpeg|g' config/.env
    echo "FFmpeg path updated for Linux"
fi

# Set proper permissions
chown -R root:root $VPS_PATH
chmod +x main.py
chmod -R 755 $VPS_PATH
chmod 600 config/.env

echo "Python environment setup completed"
EOF

log_success "Python environment configured"

# Install system dependencies
log_info "Installing system dependencies..."
ssh "$VPS_USER@$VPS_IP" << 'EOF'
# Update system packages
apt update

# Install FFmpeg if not present
if ! command -v ffmpeg &> /dev/null; then
    apt install -y ffmpeg
    echo "FFmpeg installed"
else
    echo "FFmpeg already installed"
fi

# Install Python3 and pip if not present
if ! command -v python3 &> /dev/null; then
    apt install -y python3 python3-pip python3-venv
    echo "Python3 installed"
else
    echo "Python3 already installed"
fi

# Verify installations
echo "System verification:"
echo "Python: $(python3 --version)"
echo "FFmpeg: $(ffmpeg -version | head -1)"
EOF

log_success "System dependencies verified"

# Create systemd service with new path
log_info "Creating systemd service..."
ssh "$VPS_USER@$VPS_IP" << EOF
cat > /etc/systemd/system/quranbot.service << 'SERVICE_EOF'
[Unit]
Description=QuranBot Discord Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$VPS_PATH
Environment=PATH=$VPS_PATH/.venv/bin
ExecStart=$VPS_PATH/.venv/bin/python $VPS_PATH/main.py
Restart=always
RestartSec=10

# Resource limits
MemoryMax=512M
CPUQuota=50%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$VPS_PATH
ReadWritePaths=/tmp

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=quranbot

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable quranbot.service

echo "Systemd service created and enabled"
EOF

log_success "Systemd service configured"

# Test the deployment
log_info "Testing deployment..."
ssh "$VPS_USER@$VPS_IP" << EOF
cd $VPS_PATH

# Test Python imports
source .venv/bin/activate
python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from bot.main import DISCORD_TOKEN
    print('✅ Bot imports successful')
    print('✅ Discord token configured')
except Exception as e:
    print(f'❌ Import error: {e}')
"

# Check file structure
echo ""
echo "📁 Deployment structure:"
ls -la $VPS_PATH/
echo ""
echo "📁 Source structure:"
ls -la $VPS_PATH/src/
echo ""
echo "📁 Config files:"
ls -la $VPS_PATH/config/
EOF

log_success "Deployment testing completed"

# Final summary
log_info "Deployment Summary:"
echo ""
echo "🎯 Deployment completed successfully!"
echo "📍 VPS Location: $VPS_PATH"
echo "🔧 Service: quranbot.service"
echo "🐍 Python Environment: $VPS_PATH/.venv"
echo ""
echo "Next steps:"
echo "1. Start the bot: ssh $VPS_USER@$VPS_IP 'systemctl start quranbot'"
echo "2. Check status: ssh $VPS_USER@$VPS_IP 'systemctl status quranbot'"
echo "3. View logs: ssh $VPS_USER@$VPS_IP 'journalctl -u quranbot -f'"
echo ""
echo "🌐 Bot will be accessible at: http://$VPS_IP:8080 (when dashboard is running)"

log_success "Deployment to DiscordBots/QuranBot structure completed!" 