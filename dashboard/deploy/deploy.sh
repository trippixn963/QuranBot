#!/bin/bash
# =============================================================================
# QuranBot Dashboard - Automated Deployment Script
# =============================================================================
# This script automates the deployment process for the dashboard
# Usage: ./deploy.sh [server] [path]
# =============================================================================

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
SERVER="${1:-root@your-server.com}"
REMOTE_PATH="${2:-/root/quranbot}"
LOCAL_PATH="$(cd "$(dirname "$0")/../.." && pwd)"

echo -e "${GREEN}🕌 QuranBot Dashboard Deployment Script${NC}"
echo -e "${YELLOW}Deploying to: $SERVER:$REMOTE_PATH${NC}"
echo ""

# Step 1: Create remote directory
echo -e "${GREEN}📁 Creating remote directories...${NC}"
ssh "$SERVER" "mkdir -p $REMOTE_PATH/dashboard"

# Step 2: Copy dashboard files
echo -e "${GREEN}📤 Copying dashboard files...${NC}"
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='logs' --exclude='.env' \
    "$LOCAL_PATH/dashboard/" "$SERVER:$REMOTE_PATH/dashboard/"

# Step 3: Copy data files
echo -e "${GREEN}📊 Copying data files...${NC}"
rsync -avz "$LOCAL_PATH/data/" "$SERVER:$REMOTE_PATH/data/"

# Step 4: Setup Python environment
echo -e "${GREEN}🐍 Setting up Python environment...${NC}"
ssh "$SERVER" << EOF
    cd $REMOTE_PATH/dashboard
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
EOF

# Step 5: Update service file paths
echo -e "${GREEN}⚙️  Configuring service file...${NC}"
ssh "$SERVER" << EOF
    cd $REMOTE_PATH/dashboard/deploy
    sed -i "s|/path/to/quranbot|$REMOTE_PATH|g" quranbot-dashboard.service
    chmod +x start_dashboard.sh
EOF

# Step 6: Install and start service
echo -e "${GREEN}🚀 Installing systemd service...${NC}"
ssh "$SERVER" << EOF
    cp $REMOTE_PATH/dashboard/deploy/quranbot-dashboard.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable quranbot-dashboard
    systemctl restart quranbot-dashboard
EOF

# Step 7: Configure firewall
echo -e "${GREEN}🔒 Configuring firewall...${NC}"
ssh "$SERVER" << EOF
    ufw allow 5000/tcp || true
    ufw reload || true
EOF

# Step 8: Check service status
echo -e "${GREEN}✅ Checking service status...${NC}"
ssh "$SERVER" "systemctl status quranbot-dashboard --no-pager"

# Get server IP
SERVER_IP=$(echo "$SERVER" | cut -d'@' -f2)

echo ""
echo -e "${GREEN}✨ Deployment Complete!${NC}"
echo -e "${GREEN}🌐 Dashboard URL: http://$SERVER_IP:5000${NC}"
echo ""
echo -e "${YELLOW}📝 Useful commands:${NC}"
echo "  Check status:  ssh $SERVER 'systemctl status quranbot-dashboard'"
echo "  View logs:     ssh $SERVER 'journalctl -u quranbot-dashboard -f'"
echo "  Restart:       ssh $SERVER 'systemctl restart quranbot-dashboard'"
echo ""
echo -e "${GREEN}🕌 May Allah accept this work and make it beneficial for the Ummah${NC}"